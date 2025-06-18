#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件锁和并发安全模块
Author: WFGameAI Team
Date: 2025-06-17
"""

import os
import time
import threading
import platform
from pathlib import Path
from typing import Optional, Union
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

class FileLock:
    """文件锁实现，支持跨平台"""

    def __init__(self, lock_file: Union[str, Path], timeout: float = 30.0):
        """
        初始化文件锁
        Args:
            lock_file: 锁文件路径
            timeout: 超时时间（秒）
        """
        self.lock_file = Path(lock_file)
        self.timeout = timeout
        self.is_locked = False
        self._lock = threading.Lock()

    def acquire(self) -> bool:
        """
        获取锁
        Returns:
            是否成功获取锁
        """
        with self._lock:
            if self.is_locked:
                return True

            start_time = time.time()

            while time.time() - start_time < self.timeout:
                try:
                    # 确保锁文件目录存在
                    self.lock_file.parent.mkdir(parents=True, exist_ok=True)                    # 尝试创建锁文件
                    if platform.system() == 'Windows':
                        # Windows平台使用排他性文件创建
                        fd = os.open(self.lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                        os.close(fd)
                    else:
                        # Unix平台使用文件锁
                        try:
                            import fcntl
                            self._lock_fd = open(self.lock_file, 'w')
                            # 使用fcntl.flock进行文件锁定
                            fcntl.flock(self._lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)  # type: ignore
                        except (ImportError, AttributeError):
                            # 如果fcntl不可用或属性不存在，回退到Windows方式
                            if hasattr(self, '_lock_fd'):
                                self._lock_fd.close()
                                delattr(self, '_lock_fd')
                            fd = os.open(self.lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                            os.close(fd)

                    # 写入锁信息
                    with open(self.lock_file, 'w', encoding='utf-8') as f:
                        f.write(f"PID: {os.getpid()}\n")
                        f.write(f"Time: {time.time()}\n")
                        f.write(f"Thread: {threading.current_thread().ident}\n")

                    self.is_locked = True
                    logger.debug(f"获取文件锁成功: {self.lock_file}")
                    return True

                except (OSError, IOError):
                    # 锁文件已存在或其他错误，等待后重试
                    time.sleep(0.1)
                    continue

            logger.warning(f"获取文件锁超时: {self.lock_file}")
            return False

    def release(self) -> bool:
        """
        释放锁
        Returns:
            是否成功释放锁
        """
        with self._lock:
            if not self.is_locked:
                return True

            try:
                # 关闭文件描述符（Unix平台）
                if hasattr(self, '_lock_fd'):
                    self._lock_fd.close()
                    delattr(self, '_lock_fd')

                # 删除锁文件
                if self.lock_file.exists():
                    self.lock_file.unlink()

                self.is_locked = False
                logger.debug(f"释放文件锁成功: {self.lock_file}")
                return True

            except Exception as e:
                logger.error(f"释放文件锁失败: {self.lock_file}, 错误: {e}")
                return False

    def __enter__(self):
        """上下文管理器入口"""
        if not self.acquire():
            raise TimeoutError(f"无法获取文件锁: {self.lock_file}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.release()

    def __del__(self):
        """析构函数，确保锁被释放"""
        if self.is_locked:
            self.release()

@contextmanager
def file_lock(lock_file: Union[str, Path], timeout: float = 30.0):
    """
    文件锁上下文管理器
    Args:
        lock_file: 锁文件路径
        timeout: 超时时间（秒）
    """
    lock = FileLock(lock_file, timeout)
    try:
        if not lock.acquire():
            raise TimeoutError(f"无法获取文件锁: {lock_file}")
        yield lock
    finally:
        lock.release()

class ReportLockManager:
    """报告操作锁管理器"""

    def __init__(self, base_dir: Union[str, Path]):
        """
        初始化锁管理器
        Args:
            base_dir: 基础目录
        """
        self.base_dir = Path(base_dir)
        self.locks_dir = self.base_dir / '.locks'
        self.locks_dir.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def device_report_lock(self, device_name: str, timeout: float = 30.0):
        """
        设备报告操作锁
        Args:
            device_name: 设备名称
            timeout: 超时时间（秒）
        """
        lock_file = self.locks_dir / f"device_{device_name}.lock"
        with file_lock(lock_file, timeout) as lock:
            yield lock

    @contextmanager
    def summary_report_lock(self, timeout: float = 30.0):
        """
        汇总报告操作锁
        Args:
            timeout: 超时时间（秒）
        """
        lock_file = self.locks_dir / "summary_report.lock"
        with file_lock(lock_file, timeout) as lock:
            yield lock

    @contextmanager
    def cleanup_lock(self, timeout: float = 60.0):
        """
        清理操作锁
        Args:
            timeout: 超时时间（秒）
        """
        lock_file = self.locks_dir / "cleanup.lock"
        with file_lock(lock_file, timeout) as lock:
            yield lock

    def cleanup_stale_locks(self, max_age_hours: float = 24.0):
        """
        清理过期的锁文件
        Args:
            max_age_hours: 锁文件最大存在时间（小时）
        """
        try:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600

            for lock_file in self.locks_dir.glob("*.lock"):
                try:
                    # 检查文件年龄
                    file_age = current_time - lock_file.stat().st_mtime

                    if file_age > max_age_seconds:
                        # 尝试读取锁文件信息
                        try:
                            with open(lock_file, 'r', encoding='utf-8') as f:
                                content = f.read()
                                logger.info(f"清理过期锁文件: {lock_file}\n内容: {content}")
                        except:
                            pass

                        # 删除过期锁文件
                        lock_file.unlink()
                        logger.info(f"已删除过期锁文件: {lock_file}")

                except Exception as e:
                    logger.warning(f"处理锁文件失败: {lock_file}, 错误: {e}")

        except Exception as e:
            logger.error(f"清理过期锁文件失败: {e}")

# 全局锁管理器实例
_global_lock_manager = None

def get_lock_manager(base_dir: Optional[Union[str, Path]] = None) -> ReportLockManager:
    """获取全局锁管理器实例"""
    global _global_lock_manager
    if _global_lock_manager is None:
        if base_dir is None:
            # 使用默认基础目录
            from .path_utils import PathUtils
            base_dir = PathUtils.safe_join(Path(__file__).parent.parent.parent, 'staticfiles', 'reports')
        _global_lock_manager = ReportLockManager(base_dir)
    return _global_lock_manager
