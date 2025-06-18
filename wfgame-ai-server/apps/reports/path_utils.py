#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
跨平台路径处理工具
Author: WFGameAI Team
Date: 2025-06-17
"""

import os
import platform
from pathlib import Path
from typing import Union, List
import logging

logger = logging.getLogger(__name__)

class PathUtils:
    """跨平台路径处理工具类"""

    @staticmethod
    def safe_join(*args) -> Path:
        """
        安全的路径拼接，自动处理不同操作系统的路径分隔符
        Args:
            *args: 路径组件
        Returns:
            Path对象
        """
        if not args:
            return Path()

        # 将所有参数转换为字符串
        str_args = [str(arg) for arg in args if arg]

        # 使用Path自动处理路径分隔符
        result = Path(str_args[0])
        for part in str_args[1:]:
            result = result / part

        return result

    @staticmethod
    def normalize_path(path: Union[str, Path]) -> Path:
        """
        标准化路径，解析相对路径和符号链接
        Args:
            path: 路径
        Returns:
            标准化后的Path对象
        """
        if isinstance(path, str):
            path = Path(path)

        try:
            # 解析路径，处理相对路径和符号链接
            return path.resolve()
        except (OSError, RuntimeError) as e:
            logger.warning(f"路径标准化失败: {path}, 错误: {e}")
            return path.absolute()

    @staticmethod
    def ensure_dir(path: Union[str, Path], mode: int = 0o755) -> bool:
        """
        确保目录存在，如果不存在则创建
        Args:
            path: 目录路径
            mode: 目录权限（仅在Unix系统有效）        Returns:
            是否成功
        """
        try:
            path = Path(path)
            if platform.system() == 'Windows':
                path.mkdir(parents=True, exist_ok=True)
            else:
                path.mkdir(parents=True, exist_ok=True, mode=mode)
            return True
        except Exception as e:
            logger.error(f"创建目录失败: {path}, 错误: {e}")
            return False

    @staticmethod
    def safe_remove(path: Union[str, Path]) -> bool:
        """
        安全删除文件或目录
        Args:
            path: 文件或目录路径
        Returns:
            是否成功
        """
        try:
            path = Path(path)
            if not path.exists():
                return True

            if path.is_file():
                path.unlink()
            elif path.is_dir():
                import shutil
                shutil.rmtree(path)

            return True
        except Exception as e:
            logger.error(f"删除路径失败: {path}, 错误: {e}")
            return False

    @staticmethod
    def get_size(path: Union[str, Path]) -> int:
        """
        获取文件或目录大小（字节）
        Args:
            path: 文件或目录路径
        Returns:
            大小（字节），失败返回0
        """
        try:
            path = Path(path)
            if path.is_file():
                return path.stat().st_size
            elif path.is_dir():
                total_size = 0
                for file_path in path.rglob('*'):
                    if file_path.is_file():
                        try:
                            total_size += file_path.stat().st_size
                        except (OSError, PermissionError):
                            continue
                return total_size
            return 0
        except Exception as e:
            logger.warning(f"获取路径大小失败: {path}, 错误: {e}")
            return 0

    @staticmethod
    def is_safe_path(path: Union[str, Path], base_path: Union[str, Path]) -> bool:
        """
        检查路径是否在基础路径内（防止路径穿越攻击）
        Args:
            path: 要检查的路径
            base_path: 基础路径
        Returns:
            是否安全
        """
        try:
            path = PathUtils.normalize_path(path)
            base_path = PathUtils.normalize_path(base_path)

            # 检查路径是否以base_path开头
            try:
                path.relative_to(base_path)
                return True
            except ValueError:
                return False
        except Exception as e:
            logger.warning(f"路径安全检查失败: {path}, 错误: {e}")
            return False

    @staticmethod
    def make_relative_url(file_path: Union[str, Path], base_path: Union[str, Path]) -> str:
        """
        生成相对URL路径（使用正斜杠）
        Args:
            file_path: 文件路径
            base_path: 基础路径
        Returns:
            相对URL路径
        """
        try:
            file_path = PathUtils.normalize_path(file_path)
            base_path = PathUtils.normalize_path(base_path)

            # 计算相对路径
            rel_path = file_path.relative_to(base_path)

            # 转换为URL格式（使用正斜杠）
            return rel_path.as_posix()
        except Exception as e:
            logger.warning(f"生成相对URL失败: {file_path}, 错误: {e}")
            return str(file_path)

    @staticmethod
    def list_files(directory: Union[str, Path], pattern: str = '*', recursive: bool = True) -> List[Path]:
        """
        列出目录中的文件
        Args:
            directory: 目录路径
            pattern: 文件模式（如 '*.html'）
            recursive: 是否递归搜索
        Returns:
            文件路径列表
        """
        try:
            directory = Path(directory)
            if not directory.exists() or not directory.is_dir():
                return []

            if recursive:
                return list(directory.rglob(pattern))
            else:
                return list(directory.glob(pattern))
        except Exception as e:
            logger.warning(f"列出文件失败: {directory}, 错误: {e}")
            return []

    @staticmethod
    def copy_file_safe(src: Union[str, Path], dst: Union[str, Path]) -> bool:
        """
        安全复制文件
        Args:
            src: 源文件路径
            dst: 目标文件路径
        Returns:
            是否成功
        """
        try:
            src = Path(src)
            dst = Path(dst)

            if not src.exists():
                logger.warning(f"源文件不存在: {src}")
                return False

            # 确保目标目录存在
            PathUtils.ensure_dir(dst.parent)

            # 复制文件
            import shutil
            shutil.copy2(src, dst)
            return True
        except Exception as e:
            logger.error(f"复制文件失败: {src} -> {dst}, 错误: {e}")
            return False
