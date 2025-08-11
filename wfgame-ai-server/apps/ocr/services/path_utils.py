"""
路径工具类
提供OCR模块中路径处理的通用功能
"""

import os
import logging
import configparser
from django.conf import settings

logger = logging.getLogger(__name__)

class PathUtils:
    """路径工具类"""

    @staticmethod
    def load_config():
        """加载配置文件"""
        config = configparser.ConfigParser()
        config_path = settings.BASE_DIR.parent / 'config.ini'
        config.read(config_path, encoding='utf-8')
        return config

    @staticmethod
    def get_media_root():
        """获取媒体根目录"""
        return settings.MEDIA_ROOT

    @staticmethod
    def get_ocr_repos_dir():
        """获取OCR仓库目录"""
        config = PathUtils.load_config()
        return config.get('paths', 'ocr_repos_dir', fallback=os.path.join(settings.MEDIA_ROOT, 'ocr', 'repositories'))

    @staticmethod
    def get_ocr_uploads_dir():
        """获取OCR上传目录"""
        config = PathUtils.load_config()
        return config.get('paths', 'ocr_uploads_dir', fallback=os.path.join(settings.MEDIA_ROOT, 'ocr', 'uploads'))

    @staticmethod
    def get_ocr_results_dir():
        """获取OCR结果目录"""
        config = PathUtils.load_config()
        return config.get('paths', 'ocr_results_dir', fallback=os.path.join(settings.BASE_DIR.parent, 'output', 'ocr', 'results'))

    @staticmethod
    def get_ocr_reports_dir():
        """获取OCR报告目录"""
        return os.path.join(settings.MEDIA_ROOT, 'ocr', 'reports')

    @staticmethod
    def normalize_path(path):
        """
        规范化路径，将绝对路径转换为相对路径

        Args:
            path: 原始路径

        Returns:
            str: 规范化后的路径
        """
        if not path or not os.path.isabs(path):
            return path

        try:
            # 获取媒体根目录
            media_root = PathUtils.get_media_root()

            # 如果路径以媒体根目录开头，转换为相对路径
            if path.startswith(media_root):
                rel_path = os.path.relpath(path, media_root)

                # 修复路径，去掉多余的uploads目录
                if rel_path.startswith('ocr/uploads/ocr/'):
                    rel_path = rel_path.replace('ocr/uploads/ocr/', 'ocr/')

                return rel_path
            else:
                # 如果不在媒体目录下，记录警告并返回原路径
                logger.warning(f"路径不在媒体目录下: {path}")
                return path
        except Exception as e:
            logger.error(f"路径规范化失败: {str(e)}")
            return path

    @staticmethod
    def get_debug_dir():
        """获取调试目录"""
        return os.path.join(settings.BASE_DIR.parent, "wfgame-ai-server", "media", "ocr", "repositories", "29c0ced8", "Client", "assets", "designImg")