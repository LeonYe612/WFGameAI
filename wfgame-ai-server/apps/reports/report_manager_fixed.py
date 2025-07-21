#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
统一报告管理器 - 集中处理所有报告相关逻辑 (修复版本)
Author: WFGameAI Team
Date: 2025-06-17
Version: 2.1 - 修复硬编码路径问题，严格使用配置文件路径
"""

import os
import shutil
import time
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import logging

try:
    # Try relative import first (for Django)
    from .report_config import get_report_config
    from .path_utils import PathUtils
    from .file_lock import get_lock_manager
except ImportError:
    # Fall back to absolute import (for standalone)
    from report_config import get_report_config
    from path_utils import PathUtils
    from file_lock import get_lock_manager

logger = logging.getLogger(__name__)

class ReportManager:
    """统一报告管理器 - 修复版本，严格使用配置路径"""

    def __init__(self, base_dir: Optional[str] = None, config_file: Optional[str] = None):
        """
        初始化报告管理器
        Args:
            base_dir: 项目根目录，如果为None则自动获取
            config_file: 配置文件路径，如果为None则使用默认配置
        """
        # 加载配置
        self.config = get_report_config() if config_file is None else get_report_config().__class__(config_file)

        # 设置基础目录
        self._custom_base_dir = bool(base_dir)
        if self._custom_base_dir:
            self.base_dir = PathUtils.normalize_path(base_dir)
        else:
            self.base_dir = PathUtils.normalize_path(Path(__file__).resolve().parent.parent.parent)

        # 获取锁管理器
        self.lock_manager = get_lock_manager(self.base_dir)

        # 初始化目录结构
        self.setup_directories()

        # 记录初始化信息
        logger.info(f"报告管理器初始化完成，基础目录: {self.base_dir}")

    def setup_directories(self):
        """设置报告目录结构 - 严格使用配置文件路径"""

        # 直接使用配置中的路径，不进行额外的拼接
        self.device_replay_reports_dir = PathUtils.normalize_path(self.config.device_replay_reports_dir)
        self.single_device_reports_dir = PathUtils.normalize_path(self.config.single_device_reports_dir)
        self.summary_reports_dir = PathUtils.normalize_path(self.config.summary_reports_dir)

        # 静态资源路径也直接使用配置
        static_dir = PathUtils.normalize_path(self.config.device_replay_reports_dir) / "static"
        self.report_static_dir = static_dir

        # 计算Web URL路径 - 基于配置动态计算，不使用硬编码
        self._reports_web_base = '/static/reports'

        # 动态计算单设备报告的Web URL路径
        self._single_device_web_path = self._calculate_single_device_web_path()

        # 动态计算汇总报告的Web URL路径
        self._summary_web_path = self._calculate_summary_web_path()

        # 确保目录存在
        directories = [
            self.device_replay_reports_dir,
            self.single_device_reports_dir,
            self.summary_reports_dir,
            self.report_static_dir,
            self.report_static_dir / 'css',
            self.report_static_dir / 'js',
            self.report_static_dir / 'fonts',
            self.report_static_dir / 'image'
        ]

        for dir_path in directories:
            if not PathUtils.ensure_dir(dir_path):
                logger.warning(f"创建目录失败: {dir_path}")

        logger.debug(f"报告目录结构已设置: {self.device_replay_reports_dir}")
        logger.debug(f"单设备报告Web路径: {self._single_device_web_path}")
        logger.debug(f"汇总报告Web路径: {self._summary_web_path}")

    def _calculate_single_device_web_path(self) -> str:
        """动态计算单设备报告的Web路径"""
        try:
            # 计算相对于device_replay_reports_dir的路径
            single_relative = os.path.relpath(
                self.config.single_device_reports_dir,
                self.config.device_replay_reports_dir
            ).replace('\\', '/')
            return f"{self._reports_web_base}/{single_relative}"
        except Exception as e:
            logger.warning(f"计算单设备Web路径失败: {e}")
            # 如果计算失败，返回基础路径
            return f"{self._reports_web_base}"

    def _calculate_summary_web_path(self) -> str:
        """动态计算汇总报告的Web路径"""
        try:
            # 计算相对于device_replay_reports_dir的路径
            summary_relative = os.path.relpath(
                self.config.summary_reports_dir,
                self.config.device_replay_reports_dir
            ).replace('\\', '/')
            return f"{self._reports_web_base}/{summary_relative}"
        except Exception as e:
            logger.warning(f"计算汇总报告Web路径失败: {e}")
            # 如果计算失败，返回基础路径
            return f"{self._reports_web_base}"

    def create_device_report_dir(self, device_name: str, timestamp: Optional[str] = None) -> Path:
        """
        为设备创建报告目录（并发安全）
        Args:
            device_name: 设备名称
            timestamp: 可选的时间戳，如果不提供则使用当前时间
        Returns:
            创建的设备报告目录路径
        """
        # 清理设备名称，确保文件系统兼容
        clean_name = "".join(c for c in device_name if c.isalnum() or c in ('-', '_', '.'))
        if not clean_name:
            clean_name = f"device_{abs(hash(device_name)) % 10000}"

        if timestamp is None:
            timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

        device_dir_name = f"{clean_name}_{timestamp}"
        device_dir = PathUtils.safe_join(self.single_device_reports_dir, device_dir_name)

        # 使用设备锁确保并发安全
        with self.lock_manager.device_report_lock(clean_name):
            try:
                # 确保设备目录不存在重复
                counter = 1
                original_dir = device_dir
                while device_dir.exists():
                    device_dir = Path(f"{original_dir}_{counter}")
                    counter += 1

                # 创建设备目录
                PathUtils.ensure_dir(device_dir)

                # 创建空的log.txt文件
                log_file = PathUtils.safe_join(device_dir, "log.txt")
                if not log_file.exists():
                    with open(log_file, 'w', encoding='utf-8') as f:
                        f.write("")

                logger.info(f"设备报告目录创建成功: {device_dir}")
                return device_dir
            except Exception as e:
                logger.error(f"创建设备报告目录失败: {device_name}, 错误: {e}")
                raise

    def generate_report_urls(self, device_dir: Path) -> Dict[str, str]:
        """
        生成报告URL - 严格使用配置路径，不使用硬编码
        Args:
            device_dir: 设备报告目录路径
        Returns:
            包含各种报告URL的字典
        """
        try:
            # 标准化路径
            device_dir = PathUtils.normalize_path(device_dir)
            single_device_reports_dir = PathUtils.normalize_path(self.single_device_reports_dir)

            # 计算从设备目录到单设备报告根目录的相对路径
            relative_path = PathUtils.make_relative_url(device_dir, single_device_reports_dir)

            # 使用动态计算的Web路径
            base_url = self._single_device_web_path

            return {
                'html_report': f"{base_url}/{relative_path}/log.html",
                'log_file': f"{base_url}/{relative_path}/log.txt",
                'screenshots': f"{base_url}/{relative_path}/",
                'directory': f"{base_url}/{relative_path}/"
            }
        except Exception as e:
            logger.warning(f"生成报告URL失败: {device_dir}, 错误: {e}")
            # 回退方案：重新计算Web路径，不使用硬编码
            device_name = device_dir.name if hasattr(device_dir, 'name') else str(device_dir).split('/')[-1]

            # 动态重新计算base_url，确保不使用硬编码
            try:
                fallback_base_url = self._calculate_single_device_web_path()
            except:
                fallback_base_url = self._reports_web_base  # 最后的回退

            return {
                'html_report': f"{fallback_base_url}/{device_name}/log.html",
                'log_file': f"{fallback_base_url}/{device_name}/log.txt",
                'screenshots': f"{fallback_base_url}/{device_name}/",
                'directory': f"{fallback_base_url}/{device_name}/"
            }

    def get_summary_report_url(self, filename: str) -> str:
        """
        获取汇总报告的访问URL - 使用配置路径
        Args:
            filename: 报告文件名
        Returns:
            报告访问URL
        """
        return f'{self._summary_web_path}/{filename}'

    def get_device_report_url(self, device_name: str, filename: str = 'log.html') -> str:
        """
        获取设备报告的访问URL - 使用配置路径
        Args:
            device_name: 设备名称
            filename: 报告文件名，默认为log.html
        Returns:
            报告访问URL
        """
        return f'{self._single_device_web_path}/{device_name}/{filename}'

    def normalize_device_report_url(self, relative_url: str) -> str:
        """
        将相对URL转换为绝对URL - 使用配置路径
        Args:
            relative_url: 相对URL路径
        Returns:
            标准化后的绝对URL
        """
        if not relative_url:
            return ''

        # 清理路径
        url = relative_url.strip().replace('\\', '/')

        # 如果已经是绝对URL，直接返回
        if url.startswith(('http://', 'https://', '/static/')):
            return url

        # 处理相对路径，使用动态路径而不是硬编码
        reports_base = self._reports_web_base

        if url.startswith('../'):
            # ../ui_run/... -> /static/reports/ui_run/...
            path_suffix = url[3:]  # 移除 ../
            return f'{reports_base}/{path_suffix}'
        elif url.startswith('./'):
            # ./ui_run/... -> /static/reports/ui_run/...
            path_suffix = url[2:]  # 移除 ./
            return f'{reports_base}/{path_suffix}'
        else:
            # 其他相对路径，假设相对于reports目录
            return f'{reports_base}/{url}'

    def get_device_reports(self) -> List[Dict]:
        """
        获取所有设备报告信息
        Returns:
            设备报告信息列表
        """
        reports = []

        if not self.single_device_reports_dir.exists():
            return reports

        for device_dir in self.single_device_reports_dir.iterdir():
            if device_dir.is_dir():
                urls = self.generate_report_urls(device_dir)

                # 获取报告创建时间
                try:
                    created_time = device_dir.stat().st_mtime
                except:
                    created_time = 0

                # 检查关键文件是否存在
                html_exists = (device_dir / "log.html").exists()
                log_exists = (device_dir / "log.txt").exists()

                reports.append({
                    'name': device_dir.name,
                    'created': created_time,
                    'created_str': datetime.fromtimestamp(created_time).strftime('%Y-%m-%d %H:%M:%S'),
                    'urls': urls,
                    'html_exists': html_exists,
                    'log_exists': log_exists,
                    'path': str(device_dir)
                })

        # 按创建时间倒序排序
        reports.sort(key=lambda x: x['created'], reverse=True)
        return reports

    def get_summary_reports(self) -> List[Dict]:
        """
        获取所有汇总报告信息
        Returns:
            汇总报告信息列表
        """
        reports = []

        if not self.summary_reports_dir.exists():
            return reports

        for report_file in self.summary_reports_dir.glob("*.html"):
            try:
                created_time = report_file.stat().st_mtime
            except:
                created_time = 0

            reports.append({
                'name': report_file.name,
                'url': f'{self._summary_web_path}/{report_file.name}',
                'created': created_time,
                'created_str': datetime.fromtimestamp(created_time).strftime('%Y-%m-%d %H:%M:%S'),
                'path': str(report_file)
            })

        # 按创建时间倒序排序
        reports.sort(key=lambda x: x['created'], reverse=True)
        return reports

    @property
    def reports_root(self) -> Path:
        """获取报告根目录"""
        return self.device_replay_reports_dir

    def get_report_stats(self) -> Dict:
        """
        获取报告统计信息
        Returns:
            报告统计信息字典
        """
        device_reports = self.get_device_reports()
        summary_reports = self.get_summary_reports()

        # 计算总大小
        total_size = 0
        if self.device_replay_reports_dir.exists():
            for file_path in self.device_replay_reports_dir.rglob("*"):
                if file_path.is_file():
                    try:
                        total_size += file_path.stat().st_size
                    except:
                        pass

        return {
            'device_reports_count': len(device_reports),
            'summary_reports_count': len(summary_reports),
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'device_replay_reports_dir': str(self.device_replay_reports_dir),
            'last_updated': datetime.now().isoformat()
        }
