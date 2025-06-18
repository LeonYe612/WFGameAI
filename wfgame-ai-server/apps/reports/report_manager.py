#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
统一报告管理器 - 集中处理所有报告相关逻辑
Author: WFGameAI Team
Date: 2025-06-17
Version: 2.0 - 增强版本，支持配置化、并发安全、错误处理
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
    """统一报告管理器 - 增强版本"""

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
        if base_dir:
            self.base_dir = PathUtils.normalize_path(base_dir)
        else:
            # 从当前文件位置推导项目根目录
            self.base_dir = PathUtils.normalize_path(Path(__file__).resolve().parent.parent.parent)

        # 获取锁管理器
        self.lock_manager = get_lock_manager(self.base_dir)

        # 初始化目录结构
        self.setup_directories()

        # 记录初始化信息
        logger.info(f"报告管理器初始化完成，基础目录: {self.base_dir}")

    def setup_directories(self):
        """设置报告目录结构"""
        # 获取报告根目录
        custom_root = self.config.reports_root
        if custom_root:
            self.reports_root = PathUtils.normalize_path(custom_root)
        else:
            self.reports_root = PathUtils.safe_join(self.base_dir, 'staticfiles', 'reports')

        # 统一报告目录结构
        self.device_reports_dir = PathUtils.safe_join(self.reports_root, 'ui_run', 'WFGameAI.air', 'log')
        self.summary_reports_dir = PathUtils.safe_join(self.reports_root, 'summary_reports')
        self.static_dir = PathUtils.safe_join(self.base_dir, 'apps', 'reports', 'staticfiles')

        # 确保目录存在
        directories = [
            self.reports_root,
            self.device_reports_dir,
            self.summary_reports_dir,
            self.static_dir,
            PathUtils.safe_join(self.static_dir, 'css'),
            PathUtils.safe_join(self.static_dir, 'js'),
            PathUtils.safe_join(self.static_dir, 'fonts'),
            PathUtils.safe_join(self.static_dir, 'image')
        ]

        for dir_path in directories:
            if not PathUtils.ensure_dir(dir_path):
                logger.warning(f"创建目录失败: {dir_path}")

        logger.debug(f"报告目录结构已设置: {self.reports_root}")

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
        device_dir = PathUtils.safe_join(self.device_reports_dir, device_dir_name)

        # 使用设备锁确保并发安全
        with self.lock_manager.device_report_lock(clean_name):
            try:
                # 确保设备目录不存在重复
                counter = 1
                original_dir = device_dir
                while device_dir.exists():
                    device_dir = Path(f"{original_dir}_{counter}")
                    counter += 1                # 创建设备目录
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
        生成报告URL（增强版本，支持相对路径处理）
        Args:
            device_dir: 设备报告目录路径
        Returns:
            包含各种报告URL的字典
        """
        try:
            # 标准化路径
            device_dir = PathUtils.normalize_path(device_dir)
            reports_root = PathUtils.normalize_path(self.reports_root)

            # 计算相对路径
            relative_path = PathUtils.make_relative_url(device_dir, reports_root)
            base_url = '/static/reports'

            return {
                'html_report': f"{base_url}/{relative_path}/log.html",
                'log_file': f"{base_url}/{relative_path}/log.txt",
                'screenshots': f"{base_url}/{relative_path}/log/",
                'directory': f"{base_url}/{relative_path}/"
            }
        except Exception as e:
            logger.warning(f"生成报告URL失败: {device_dir}, 错误: {e}")
            # 回退到简单的URL生成
            device_name = device_dir.name if hasattr(device_dir, 'name') else str(device_dir).split('/')[-1]
            return {
                'html_report': f"/static/reports/ui_run/WFGameAI.air/log/{device_name}/log.html",
                'log_file': f"/static/reports/ui_run/WFGameAI.air/log/{device_name}/log.txt",
                'screenshots': f"/static/reports/ui_run/WFGameAI.air/log/{device_name}/log/",
                'directory': f"/static/reports/ui_run/WFGameAI.air/log/{device_name}/"
            }

    def copy_static_resources(self, target_dir: Path, max_retries: Optional[int] = None) -> bool:
        """
        复制静态资源到目标目录（增强版本，支持重试）
        Args:
            target_dir: 目标目录路径
            max_retries: 最大重试次数，如果为None则使用配置值
        Returns:
            是否复制成功
        """
        if max_retries is None:
            max_retries = self.config.retry_count

        retry_delay = self.config.retry_delay_seconds

        for attempt in range(max_retries + 1):
            try:
                import airtest
                airtest_static = Path(airtest.__file__).parent / "report" / "static"

                if airtest_static.exists():
                    target_static = PathUtils.safe_join(target_dir, "static")

                    # 如果目标静态目录存在，先删除
                    if target_static.exists():
                        PathUtils.safe_remove(target_static)

                    # 复制整个静态目录
                    shutil.copytree(str(airtest_static), str(target_static))
                    logger.debug(f"静态资源复制成功: {target_static}")
                    return True
                else:
                    logger.warning(f"Airtest静态资源目录不存在: {airtest_static}")
                    return False

            except ImportError:
                logger.warning("未找到Airtest模块，无法复制静态资源")
                return False
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"复制静态资源失败（第{attempt + 1}次尝试）: {e}，{retry_delay}秒后重试")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"复制静态资源失败（已尝试{max_retries + 1}次）: {e}")
                    return False

        return False

    def cleanup_old_reports(self, days: Optional[int] = None, max_count: Optional[int] = None) -> Dict[str, int]:
        """
        清理旧的报告文件（增强版本，支持并发安全和详细统计）
        Args:
            days: 保留天数，如果为None则使用配置值
            max_count: 最大报告数量，如果为None则使用配置值
        Returns:
            清理统计信息字典
        """
        if days is None:
            days = self.config.report_retention_days
        if max_count is None:
            max_count = self.config.max_reports_count

        stats = {
            'device_reports_cleaned': 0,
            'summary_reports_cleaned': 0,
            'bytes_freed': 0,
            'errors': []
        }

        # 使用清理锁确保并发安全
        with self.lock_manager.cleanup_lock():
            try:
                cutoff_time = time.time() - (days * 86400)

                # 清理设备报告
                if self.device_reports_dir.exists():
                    device_reports = []
                    for device_dir in self.device_reports_dir.iterdir():
                        if device_dir.is_dir():
                            try:
                                mtime = device_dir.stat().st_mtime
                                size = PathUtils.get_size(device_dir)
                                device_reports.append((device_dir, mtime, size))
                            except Exception as e:
                                stats['errors'].append(f"获取设备报告信息失败 {device_dir}: {e}")

                    # 按修改时间排序
                    device_reports.sort(key=lambda x: x[1])

                    # 按时间和数量清理
                    reports_to_clean = []
                    for device_dir, mtime, size in device_reports:
                        if mtime < cutoff_time or len(device_reports) - len(reports_to_clean) > max_count:
                            reports_to_clean.append((device_dir, size))

                    # 执行清理
                    for device_dir, size in reports_to_clean:
                        try:
                            if PathUtils.safe_remove(device_dir):
                                stats['device_reports_cleaned'] += 1
                                stats['bytes_freed'] += size
                                logger.info(f"已清理设备报告: {device_dir}")
                            else:
                                stats['errors'].append(f"删除设备报告失败: {device_dir}")
                        except Exception as e:
                            stats['errors'].append(f"清理设备报告异常 {device_dir}: {e}")

                # 清理汇总报告
                if self.summary_reports_dir.exists():
                    summary_reports = []
                    for report_file in self.summary_reports_dir.glob("*.html"):
                        try:
                            mtime = report_file.stat().st_mtime
                            size = PathUtils.get_size(report_file)
                            summary_reports.append((report_file, mtime, size))
                        except Exception as e:
                            stats['errors'].append(f"获取汇总报告信息失败 {report_file}: {e}")

                    # 按修改时间排序
                    summary_reports.sort(key=lambda x: x[1])

                    # 按时间和数量清理
                    reports_to_clean = []
                    for report_file, mtime, size in summary_reports:
                        if mtime < cutoff_time or len(summary_reports) - len(reports_to_clean) > max_count:
                            reports_to_clean.append((report_file, size))

                    # 执行清理
                    for report_file, size in reports_to_clean:
                        try:
                            if PathUtils.safe_remove(report_file):
                                stats['summary_reports_cleaned'] += 1
                                stats['bytes_freed'] += size
                                logger.info(f"已清理汇总报告: {report_file}")
                            else:
                                stats['errors'].append(f"删除汇总报告失败: {report_file}")
                        except Exception as e:
                            stats['errors'].append(f"清理汇总报告异常 {report_file}: {e}")

                # 清理过期锁文件
                self.lock_manager.cleanup_stale_locks()

                logger.info(f"报告清理完成: {stats}")
                return stats

            except Exception as e:
                stats['errors'].append(f"清理操作异常: {e}")
                logger.error(f"报告清理失败: {e}")
                return stats

    def get_device_reports(self) -> List[Dict]:
        """
        获取所有设备报告信息
        Returns:
            设备报告信息列表
        """
        reports = []

        if not self.device_reports_dir.exists():
            return reports

        for device_dir in self.device_reports_dir.iterdir():
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
                'url': f'/static/reports/summary_reports/{report_file.name}',
                'created': created_time,
                'created_str': datetime.fromtimestamp(created_time).strftime('%Y-%m-%d %H:%M:%S'),
                'path': str(report_file)
            })        # 按创建时间倒序排序
        reports.sort(key=lambda x: x['created'], reverse=True)
        return reports

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

        if self.reports_root.exists():
            for file_path in self.reports_root.rglob("*"):
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
            'reports_root': str(self.reports_root),
            'last_updated': datetime.now().isoformat()
        }

    def list_summary_reports(self) -> List[str]:
        """
        获取所有汇总报告文件路径列表
        Returns:
            汇总报告文件路径列表
        """
        reports = []

        if self.summary_reports_dir.exists():
            for report_file in self.summary_reports_dir.glob("summary_report_*.html"):
                reports.append(str(report_file))

        return sorted(reports, key=lambda x: os.path.getctime(x), reverse=True)

    def list_device_reports(self, device_id: Optional[str] = None) -> List[str]:
        """
        获取设备报告目录列表
        Args:
            device_id: 设备ID，如果提供则只返回该设备的报告
        Returns:
            设备报告目录路径列表
        """
        reports = []

        if not self.device_reports_dir.exists():
            return reports

        if device_id:
            # 查找特定设备的报告
            device_pattern = f"*{device_id}*"
            for device_dir in self.device_reports_dir.glob(device_pattern):
                if device_dir.is_dir():
                    reports.append(str(device_dir))
        else:
            # 获取所有设备报告
            for device_dir in self.device_reports_dir.iterdir():
                if device_dir.is_dir():
                    reports.append(str(device_dir))

        return sorted(reports, key=lambda x: os.path.getctime(x), reverse=True)

    def get_summary_report_url(self, filename: str) -> str:
        """
        获取汇总报告的访问URL
        Args:
            filename: 报告文件名
        Returns:
            报告访问URL
        """
        return f'/static/reports/summary_reports/{filename}'

    def get_device_report_url(self, device_name: str, filename: str = 'log.html') -> str:
        """
        获取设备报告的访问URL
        Args:
            device_name: 设备名称
            filename: 报告文件名，默认为log.html
        Returns:
            报告访问URL
        """
        return f'/static/reports/ui_run/WFGameAI.air/log/{device_name}/{filename}'

    def normalize_device_report_url(self, relative_url: str) -> str:
        """
        将相对URL转换为绝对URL
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

        # 处理相对路径
        if url.startswith('../'):
            # ../ui_run/... -> /static/reports/ui_run/...
            path_suffix = url[3:]  # 移除 ../
            return f'/static/reports/{path_suffix}'
        elif url.startswith('./'):
            # ./ui_run/... -> /static/reports/ui_run/...
            path_suffix = url[2:]  # 移除 ./
            return f'/static/reports/{path_suffix}'
        elif url.startswith('ui_run/'):
            # ui_run/... -> /static/reports/ui_run/...
            return f'/static/reports/{url}'
        else:
            # 其他相对路径，假设相对于reports目录
            return f'/static/reports/{url}'

    def get_report_statistics(self) -> Dict:
        """
        获取报告统计信息
        Returns:
            报告统计信息字典
        """
        return self.get_report_stats()
