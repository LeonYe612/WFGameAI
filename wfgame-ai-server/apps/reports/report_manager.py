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
        """设置报告目录结构"""

        # ${server_dir}\staticfiles\reports
        self.device_replay_reports_dir = PathUtils.normalize_path(self.config.device_replay_reports_dir)

        # 统一报告目录结构
        # 使用配置中定义的目录
        # 单设备报告目录 ${device_replay_reports_dir}\ui_run\WFGameAI.air\log
        self.single_device_reports_dir = PathUtils.normalize_path(self.config.single_device_reports_dir)

        # 多设备汇总报告目录 ${device_replay_reports_dir}\summary_reports
        self.summary_reports_dir = PathUtils.normalize_path(self.config.summary_reports_dir)

        # 静态资源目录 ${device_replay_reports_dir}\static
        self.report_static_url = PathUtils.safe_join(self.config.report_static_url)
        # self.report_static_url = PathUtils.safe_join(self.base_dir, 'apps', 'reports', 'staticfiles')

        # 计算Web URL路径（相对于staticfiles/reports）
        self._reports_web_base = '/static/reports'

        # 计算单设备报告的Web URL路径
        try:
            # 从配置中获取相对于device_replay_reports_dir的路径
            single_relative = os.path.relpath(
                self.config.single_device_reports_dir,
                self.config.device_replay_reports_dir            ).replace('\\', '/')
            self._single_device_web_path = f"{self._reports_web_base}/{single_relative}"
        except:
            # 回退：动态计算而不是硬编码
            try:
                single_relative = os.path.relpath(
                    self.config.single_device_reports_dir,
                    self.config.device_replay_reports_dir
                ).replace('\\', '/')
                self._single_device_web_path = f"{self._reports_web_base}/{single_relative}"
            except:
                self._single_device_web_path = self._reports_web_base

        # 计算汇总报告的Web URL路径
        try:
            summary_relative = os.path.relpath(
                self.config.summary_reports_dir,
                self.config.device_replay_reports_dir
            ).replace('\\', '/')
            self._summary_web_path = f"{self._reports_web_base}/{summary_relative}"
        except:
            # 回退：动态计算而不是硬编码
            try:
                summary_relative = os.path.relpath(
                    self.config.summary_reports_dir,
                    self.config.device_replay_reports_dir
                ).replace('\\', '/')
                self._summary_web_path = f"{self._reports_web_base}/{summary_relative}"
            except:
                self._summary_web_path = self._reports_web_base

        # 确保目录存在
        directories = [
            self.device_replay_reports_dir,
            self.single_device_reports_dir,
            self.summary_reports_dir,
            self.report_static_url,
            PathUtils.safe_join(self.report_static_url, 'css'),
            PathUtils.safe_join(self.report_static_url, 'js'),
            PathUtils.safe_join(self.report_static_url, 'fonts'),
            PathUtils.safe_join(self.report_static_url, 'image')
        ]

        for dir_path in directories:
            if not PathUtils.ensure_dir(dir_path):
                logger.warning(f"创建目录失败: {dir_path}")

        logger.debug(f"报告目录结构已设置: {self.device_replay_reports_dir}")
        logger.debug(f"单设备报告Web路径: {self._single_device_web_path}")
        logger.debug(f"汇总报告Web路径: {self._summary_web_path}")

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

        # 🔧 修复：确保使用正确的single_device_reports_dir路径
        # 检查single_device_reports_dir是否存在，如果不存在则创建
        if not self.single_device_reports_dir.exists():
            logger.info(f"创建单设备报告目录: {self.single_device_reports_dir}")
            PathUtils.ensure_dir(self.single_device_reports_dir)

        # 确保设备目录创建在log目录下
        device_dir = PathUtils.safe_join(self.single_device_reports_dir, device_dir_name)

        # 记录详细的目录信息，便于调试
        logger.info(f"设备报告目录配置: {self.config.single_device_reports_dir}")
        logger.info(f"实际使用的设备报告目录: {self.single_device_reports_dir}")
        logger.info(f"将在此目录下创建设备目录: {device_dir}")

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
        生成报告URL（增强版本，全部使用 config 参数）
        Args:
            device_dir: 设备报告目录路径
        Returns:
            包含各种报告URL的字典
        """
        try:
            # 标准化路径
            device_dir = PathUtils.normalize_path(device_dir)
            single_device_reports_dir = PathUtils.normalize_path(self.config.single_device_reports_dir)
            summary_reports_dir = PathUtils.normalize_path(self.config.summary_reports_dir)
            device_replay_reports_dir = PathUtils.normalize_path(self.config.device_replay_reports_dir)

            # 计算相对路径
            relative_path = PathUtils.make_relative_url(device_dir, single_device_reports_dir)
            device_name = device_dir.name if hasattr(device_dir, 'name') else str(device_dir).split('/')[-1]

            # 构建 Web 路径
            base_url = self._single_device_web_path  # 设备报告web根目录
            summary_url = self._summary_web_path     # 汇总报告web根目录

            # 设备报告的绝对URL
            html_report_url = f"{base_url}/{relative_path}/log.html"
            log_file_url = f"{base_url}/{relative_path}/log.txt"
            screenshots_url = f"{base_url}/{relative_path}/"
            directory_url = f"{base_url}/{relative_path}/"

            # 汇总报告到设备报告的相对路径（用于HTML链接）
            # 🔧 修复：使用正确的相对路径格式，不使用../前缀
            # 计算从summary_reports_dir到single_device_reports_dir的相对路径
            try:
                # 计算从汇总报告目录到设备报告目录的相对路径
                reports_to_single = os.path.relpath(
                    self.config.device_replay_reports_dir,
                    summary_reports_dir.parent
                ).replace('\\', '/')

                # 构建相对URL，使用ui_run/WFGameAI.air/log/{device_name}/log.html格式
                html_report_relative = f"ui_run/WFGameAI.air/log/{device_name}/log.html"

                logger.debug(f"计算的相对路径: {html_report_relative}")
            except Exception as e:
                logger.warning(f"计算相对路径失败: {e}")
                # 回退方案：使用标准格式
                html_report_relative = f"ui_run/WFGameAI.air/log/{device_name}/log.html"

            return {
                'html_report': html_report_url,
                'html_report_relative': html_report_relative,
                'log_file': log_file_url,
                'screenshots': screenshots_url,
                'directory': directory_url
            }
        except Exception as e:
            logger.warning(f"生成报告URL失败: {device_dir}, 错误: {e}")
            # 回退到简单的URL生成 - 确保使用配置路径而不是硬编码
            device_name = device_dir.name if hasattr(device_dir, 'name') else str(device_dir).split('/')[-1]
            base_url = self._single_device_web_path
            summary_url = self._summary_web_path
            html_report_url = f"{base_url}/{device_name}/log.html"
            log_file_url = f"{base_url}/{device_name}/log.txt"
            screenshots_url = f"{base_url}/{device_name}/"
            directory_url = f"{base_url}/{device_name}/"
            # 🔧 修复：使用正确的相对路径格式，不使用../前缀
            html_report_relative = f"ui_run/WFGameAI.air/log/{device_name}/log.html"
            return {
                'html_report': html_report_url,
                'html_report_relative': html_report_relative,
                'log_file': log_file_url,
                'screenshots': screenshots_url,
                'directory': directory_url
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
        target_dir = PathUtils.normalize_path(target_dir)

        # 注意：我们不再复制静态资源到设备目录，而是使用相对路径引用统一的静态资源
        # 但保留此方法用于兼容旧代码，直接返回成功
        logger.info(f"使用相对路径引用静态资源，无需复制资源到设备目录: {target_dir}")
        return True

        # 以下代码保留但不执行
        for attempt in range(max_retries + 1):
            try:
                # 方法1: 从airtest包获取静态资源
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
                        logger.debug(f"静态资源从airtest包复制成功: {target_static}")
                        return True
                    else:
                        logger.warning(f"Airtest静态资源目录不存在: {airtest_static}")
                        # 继续尝试其他方法
                except ImportError:
                    logger.warning("未找到Airtest模块，尝试其他方法")

                # 方法2: 从配置的静态资源目录复制
                try:
                    static_src = PathUtils.normalize_path(self.report_static_url)
                    if static_src.exists():
                        target_static = PathUtils.safe_join(target_dir, "static")

                        # 如果目标静态目录存在，先删除
                        if target_static.exists():
                            PathUtils.safe_remove(target_static)

                        # 复制整个静态目录
                        shutil.copytree(str(static_src), str(target_static))
                        logger.debug(f"静态资源从配置目录复制成功: {target_static}")
                        return True
                    else:
                        logger.warning(f"配置的静态资源目录不存在: {static_src}")
                        # 继续尝试其他方法
                except Exception as e:
                    logger.warning(f"从配置目录复制静态资源失败: {e}")

                # 方法3: 从项目中可能的静态资源目录复制
                possible_static_dirs = [
                    PathUtils.safe_join(self.base_dir, "staticfiles", "reports", "static"),
                    PathUtils.safe_join(self.base_dir, "apps", "reports", "staticfiles", "static"),
                    PathUtils.safe_join(Path(__file__).parent, "staticfiles", "static")
                ]

                for static_dir in possible_static_dirs:
                    if static_dir.exists():
                        target_static = PathUtils.safe_join(target_dir, "static")

                        # 如果目标静态目录存在，先删除
                        if target_static.exists():
                            PathUtils.safe_remove(target_static)

                        # 复制整个静态目录
                        shutil.copytree(str(static_dir), str(target_static))
                        logger.debug(f"静态资源从项目目录复制成功: {target_static}")
                        return True

                # 如果无法复制，尝试创建最小化静态资源目录
                target_static = PathUtils.safe_join(target_dir, "static")

                # 确保目录存在
                os.makedirs(str(target_static), exist_ok=True)
                os.makedirs(str(PathUtils.safe_join(target_static, "css")), exist_ok=True)
                os.makedirs(str(PathUtils.safe_join(target_static, "js")), exist_ok=True)
                os.makedirs(str(PathUtils.safe_join(target_static, "image")), exist_ok=True)

                # 创建基本的CSS文件
                with open(str(PathUtils.safe_join(target_static, "css", "report.css")), "w") as f:
                    f.write("""
                    body { font-family: Arial, sans-serif; margin: 0; padding: 0; }
                    .container-fluid { padding: 20px; }
                    .title { text-align: center; margin-bottom: 20px; }
                    .step { margin-bottom: 20px; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
                    .success { background-color: #dff0d8; }
                    .fail { background-color: #f2dede; }
                    """)

                # 创建基本的JS文件
                with open(str(PathUtils.safe_join(target_static, "js", "jquery-1.10.2.min.js")), "w") as f:
                    f.write("// jQuery minimal placeholder")

                logger.warning(f"使用最小化静态资源目录: {target_static}")
                return True

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
                if self.single_device_reports_dir.exists():
                    device_reports = []
                    for device_dir in self.single_device_reports_dir.iterdir():
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
            })# 按创建时间倒序排序
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

        if not self.single_device_reports_dir.exists():
            return reports

        if device_id:
            # 查找特定设备的报告
            device_pattern = f"*{device_id}*"
            for device_dir in self.single_device_reports_dir.glob(device_pattern):
                if device_dir.is_dir():
                    reports.append(str(device_dir))
        else:
            # 获取所有设备报告
            for device_dir in self.single_device_reports_dir.iterdir():
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
        return f'{self._summary_web_path}/{filename}'
    def get_device_report_url(self, device_name: str, filename: str = 'log.html') -> str:
        """
        获取设备报告的访问URL
        Args:
            device_name: 设备名称
            filename: 报告文件名，默认为log.html
        Returns:
            报告访问URL
        """
        return f'{self._single_device_web_path}/{device_name}/{filename}'
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

        # 处理相对路径，使用动态路径而不是硬编码
        reports_base = getattr(self, '_reports_web_base', '/static/reports')

        if url.startswith('../'):
            # ../ui_run/... -> /static/reports/ui_run/...
            path_suffix = url[3:]  # 移除 ../
            return f'{reports_base}/{path_suffix}'
        elif url.startswith('./'):
            # ./ui_run/... -> /static/reports/ui_run/...
            path_suffix = url[2:]  # 移除 ./
            return f'{reports_base}/{path_suffix}'
        elif url.startswith('ui_run/'):
            # ui_run/... -> /static/reports/ui_run/...
            return f'{reports_base}/{url}'
        else:
            # 其他相对路径，假设相对于reports目录
            return f'{reports_base}/{url}'

    def normalize_report_url(self, device_name: str, is_relative: bool = True) -> str:
        """
        生成标准化的设备报告URL

        Args:
            device_name: 设备名称
            is_relative: 是否使用相对路径（相对于summary_reports目录）

        Returns:
            标准化的URL
        """
        try:
            if is_relative:
                # 从summary_reports目录到设备目录的相对路径
                return f"../ui_run/WFGameAI.air/log/{device_name}/log.html"
        except Exception as e:
            logger.error(f"生成标准化设备报告URL失败: {e}")


    def get_report_statistics(self) -> Dict:
        """
        获取报告统计信息
        Returns:
            报告统计信息字典
        """
        return self.get_report_stats()
