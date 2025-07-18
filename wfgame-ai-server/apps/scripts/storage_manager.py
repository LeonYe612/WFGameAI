"""
存储管理系统 - 方案3实现
负责自动文件清理、磁盘空间监控和日志轮转
"""

import os
import shutil
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import threading
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class StorageStatus(Enum):
    """存储状态枚举"""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class CleanupStats:
    """清理统计信息"""
    files_deleted: int = 0
    directories_deleted: int = 0
    space_freed_mb: float = 0.0
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


@dataclass
class DiskSpaceInfo:
    """磁盘空间信息"""
    total_gb: float
    used_gb: float
    free_gb: float
    usage_percent: float
    status: StorageStatus


class StorageManager:
    """存储管理器 - 自动清理和监控磁盘空间"""

    def __init__(self, reports_dir: str):
        """
        初始化存储管理器

        Args:
            reports_dir: 报告根目录路径
        """
        self.reports_dir = Path(reports_dir)
        self.lock = threading.Lock()

        # 配置参数
        self.log_retention_days = 30  # 日志保留天数
        self.report_retention_days = 90  # 报告保留天数
        self.max_log_size_mb = 50  # 单个日志文件最大大小(MB)
        self.disk_warning_threshold = 0.80  # 磁盘使用率警告阈值(80%)
        self.disk_critical_threshold = 0.85  # 磁盘使用率严重阈值(85%)

        # 清理任务配置
        self.cleanup_schedule_hours = 24  # 每24小时执行一次清理
        self.last_cleanup_time = None

        logger.info(f"存储管理器初始化完成，监控目录: {self.reports_dir}")

    def get_disk_space_info(self) -> DiskSpaceInfo:
        """获取磁盘空间信息"""
        try:
            stat = shutil.disk_usage(self.reports_dir)
            total_gb = stat.total / (1024**3)
            free_gb = stat.free / (1024**3)
            used_gb = total_gb - free_gb
            usage_percent = used_gb / total_gb

            # 确定状态
            if usage_percent >= self.disk_critical_threshold:
                status = StorageStatus.CRITICAL
            elif usage_percent >= self.disk_warning_threshold:
                status = StorageStatus.WARNING
            else:
                status = StorageStatus.NORMAL

            return DiskSpaceInfo(
                total_gb=round(total_gb, 2),
                used_gb=round(used_gb, 2),
                free_gb=round(free_gb, 2),
                usage_percent=round(usage_percent * 100, 1),
                status=status
            )
        except Exception as e:
            logger.error(f"获取磁盘空间信息失败: {e}")
            return DiskSpaceInfo(0, 0, 0, 0, StorageStatus.CRITICAL)

    def cleanup_old_logs(self, days: Optional[int] = None) -> CleanupStats:
        """清理过期日志文件"""
        days = days or self.log_retention_days
        cutoff_date = datetime.now() - timedelta(days=days)
        stats = CleanupStats()

        try:
            with self.lock:
                log_patterns = ['*.log', '*.txt']

                for pattern in log_patterns:
                    for log_file in self.reports_dir.rglob(pattern):
                        try:
                            if log_file.is_file():
                                # 检查文件修改时间
                                file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                                if file_mtime < cutoff_date:
                                    file_size = log_file.stat().st_size / (1024*1024)  # MB
                                    log_file.unlink()
                                    stats.files_deleted += 1
                                    stats.space_freed_mb += file_size
                                    logger.debug(f"删除过期日志文件: {log_file}")
                        except Exception as e:
                            error_msg = f"删除日志文件 {log_file} 失败: {e}"
                            logger.error(error_msg)
                            stats.errors.append(error_msg)

        except Exception as e:
            error_msg = f"清理日志文件时出错: {e}"
            logger.error(error_msg)
            stats.errors.append(error_msg)

        logger.info(f"日志清理完成: 删除 {stats.files_deleted} 个文件，释放 {stats.space_freed_mb:.2f} MB")
        return stats

    def cleanup_old_reports(self, days: Optional[int] = None) -> CleanupStats:
        """清理过期报告目录"""
        days = days or self.report_retention_days
        cutoff_date = datetime.now() - timedelta(days=days)
        stats = CleanupStats()

        try:
            with self.lock:
                # 查找设备报告目录
                for report_dir in self.reports_dir.iterdir():
                    if not report_dir.is_dir():
                        continue

                    try:
                        # 检查目录修改时间
                        dir_mtime = datetime.fromtimestamp(report_dir.stat().st_mtime)
                        if dir_mtime < cutoff_date:
                            # 计算目录大小
                            dir_size = self._get_directory_size(report_dir) / (1024*1024)  # MB

                            # 删除整个目录
                            shutil.rmtree(report_dir)
                            stats.directories_deleted += 1
                            stats.space_freed_mb += dir_size
                            logger.debug(f"删除过期报告目录: {report_dir}")

                    except Exception as e:
                        error_msg = f"删除报告目录 {report_dir} 失败: {e}"
                        logger.error(error_msg)
                        stats.errors.append(error_msg)

        except Exception as e:
            error_msg = f"清理报告目录时出错: {e}"
            logger.error(error_msg)
            stats.errors.append(error_msg)

        logger.info(f"报告清理完成: 删除 {stats.directories_deleted} 个目录，释放 {stats.space_freed_mb:.2f} MB")
        return stats

    def rotate_large_logs(self) -> CleanupStats:
        """轮转过大的日志文件"""
        stats = CleanupStats()
        max_size_bytes = self.max_log_size_mb * 1024 * 1024

        try:
            with self.lock:
                for log_file in self.reports_dir.rglob('*.log'):
                    try:
                        if log_file.is_file() and log_file.stat().st_size > max_size_bytes:
                            # 创建轮转文件名
                            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                            rotated_name = f"{log_file.stem}_{timestamp}.log"
                            rotated_path = log_file.parent / rotated_name

                            # 重命名当前文件
                            log_file.rename(rotated_path)

                            # 创建新的空日志文件
                            log_file.touch()

                            stats.files_deleted += 1  # 实际是轮转，但计入处理的文件数
                            logger.info(f"轮转大日志文件: {log_file} -> {rotated_path}")

                    except Exception as e:
                        error_msg = f"轮转日志文件 {log_file} 失败: {e}"
                        logger.error(error_msg)
                        stats.errors.append(error_msg)

        except Exception as e:
            error_msg = f"日志轮转时出错: {e}"
            logger.error(error_msg)
            stats.errors.append(error_msg)

        logger.info(f"日志轮转完成: 处理 {stats.files_deleted} 个文件")
        return stats

    def emergency_cleanup(self) -> CleanupStats:
        """紧急清理 - 磁盘空间严重不足时执行"""
        logger.warning("执行紧急清理 - 磁盘空间严重不足")

        total_stats = CleanupStats()

        # 1. 先清理最老的日志文件
        log_stats = self.cleanup_old_logs(days=7)  # 只保留7天
        self._merge_stats(total_stats, log_stats)

        # 2. 清理最老的报告目录
        report_stats = self.cleanup_old_reports(days=30)  # 只保留30天
        self._merge_stats(total_stats, report_stats)

        # 3. 轮转所有大日志文件
        rotate_stats = self.rotate_large_logs()
        self._merge_stats(total_stats, rotate_stats)

        logger.info(f"紧急清理完成: 释放 {total_stats.space_freed_mb:.2f} MB")
        return total_stats

    def auto_cleanup(self) -> Optional[CleanupStats]:
        """自动清理 - 定期执行"""
        # 检查是否需要执行清理
        if self.last_cleanup_time:
            time_since_last = datetime.now() - self.last_cleanup_time
            if time_since_last.total_seconds() < self.cleanup_schedule_hours * 3600:
                return None

        logger.info("执行定期自动清理")

        total_stats = CleanupStats()

        # 检查磁盘空间
        disk_info = self.get_disk_space_info()

        if disk_info.status == StorageStatus.CRITICAL:
            # 磁盘空间严重不足，执行紧急清理
            emergency_stats = self.emergency_cleanup()
            self._merge_stats(total_stats, emergency_stats)

        elif disk_info.status == StorageStatus.WARNING:
            # 磁盘空间警告，执行积极清理
            log_stats = self.cleanup_old_logs(days=15)  # 保留15天
            report_stats = self.cleanup_old_reports(days=60)  # 保留60天
            rotate_stats = self.rotate_large_logs()

            self._merge_stats(total_stats, log_stats)
            self._merge_stats(total_stats, report_stats)
            self._merge_stats(total_stats, rotate_stats)

        else:
            # 正常情况下的常规清理
            log_stats = self.cleanup_old_logs()
            report_stats = self.cleanup_old_reports()
            rotate_stats = self.rotate_large_logs()

            self._merge_stats(total_stats, log_stats)
            self._merge_stats(total_stats, report_stats)
            self._merge_stats(total_stats, rotate_stats)

        self.last_cleanup_time = datetime.now()
        logger.info(f"自动清理完成: 释放 {total_stats.space_freed_mb:.2f} MB")
        return total_stats

    def get_storage_status(self) -> Dict:
        """获取存储状态信息"""
        disk_info = self.get_disk_space_info()

        # 统计文件数量
        log_count = len(list(self.reports_dir.rglob('*.log')))
        report_dirs = len([d for d in self.reports_dir.iterdir() if d.is_dir()])

        return {
            'disk_space': {
                'total_gb': disk_info.total_gb,
                'used_gb': disk_info.used_gb,
                'free_gb': disk_info.free_gb,
                'usage_percent': disk_info.usage_percent,
                'status': disk_info.status.value
            },
            'file_counts': {
                'log_files': log_count,
                'report_directories': report_dirs
            },
            'retention_policy': {
                'log_retention_days': self.log_retention_days,
                'report_retention_days': self.report_retention_days,
                'max_log_size_mb': self.max_log_size_mb
            },
            'last_cleanup': self.last_cleanup_time.isoformat() if self.last_cleanup_time else None
        }

    def _get_directory_size(self, directory: Path) -> int:
        """获取目录总大小（字节）"""
        total_size = 0
        try:
            for file_path in directory.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except Exception as e:
            logger.error(f"计算目录大小失败 {directory}: {e}")
        return total_size

    def _merge_stats(self, target: CleanupStats, source: CleanupStats):
        """合并清理统计信息"""
        target.files_deleted += source.files_deleted
        target.directories_deleted += source.directories_deleted
        target.space_freed_mb += source.space_freed_mb
        target.errors.extend(source.errors)


# 全局存储管理器实例
storage_manager = None


def get_storage_manager() -> StorageManager:
    """获取存储管理器实例"""
    global storage_manager
    if storage_manager is None:
        try:
            # 获取报告目录配置
            from .views import DEVICE_REPORTS_DIR
            storage_manager = StorageManager(DEVICE_REPORTS_DIR)
        except Exception as e:
            logger.error(f"初始化存储管理器失败: {e}")
            # 使用默认路径
            default_reports_dir = os.path.join(os.path.dirname(__file__), '../../staticfiles/reports')
            storage_manager = StorageManager(default_reports_dir)

    return storage_manager
