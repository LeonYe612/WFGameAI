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
        # config = configparser.ConfigParser()
        # config_path = settings.BASE_DIR.parent / 'config.ini'
        # config.read(config_path, encoding='utf-8')
        config = settings.CFG
        return config

    @staticmethod
    def _resolve_path_variables(path_str: str) -> str:
        """
        解析路径字符串中的变量，如${server_dir}等

        Args:
            path_str: 包含变量的路径字符串

        Returns:
            str: 解析后的路径字符串
        """
        if not path_str:
            return path_str

        # 定义变量映射
        variables = {
            '${project_root}': str(settings.BASE_DIR.parent),
            '${server_dir}': str(settings.BASE_DIR),
        }

        # 替换变量
        resolved_path = path_str
        for var, value in variables.items():
            if var in resolved_path:
                resolved_path = resolved_path.replace(var, value)
                logger.warning(f"路径变量替换: {var} -> {value}")

        return resolved_path

    @staticmethod
    def get_media_root():
        """获取媒体根目录"""
        return settings.MEDIA_ROOT

    @staticmethod
    def get_ocr_repos_dir():
        """获取OCR仓库目录"""
        config = PathUtils.load_config()
        path_str = config.get('paths', 'ocr_repos_dir', fallback=os.path.join(settings.MEDIA_ROOT, 'ocr', 'repositories'))
        resolved_path = PathUtils._resolve_path_variables(path_str)
        logger.debug(f"OCR仓库目录: {path_str} -> {resolved_path}")
        return resolved_path

    @staticmethod
    def get_ocr_uploads_dir():
        """获取OCR上传目录"""
        config = PathUtils.load_config()
        path_str = config.get('paths', 'ocr_uploads_dir', fallback=os.path.join(settings.MEDIA_ROOT, 'ocr', 'uploads'))
        resolved_path = PathUtils._resolve_path_variables(path_str)
        logger.debug(f"OCR上传目录: {path_str} -> {resolved_path}")
        return resolved_path

    @staticmethod
    def get_ocr_results_dir():
        """获取OCR结果目录"""
        config = PathUtils.load_config()
        path_str = config.get('paths', 'ocr_results_dir', fallback=os.path.join(settings.BASE_DIR.parent, 'output', 'ocr', 'results'))
        resolved_path = PathUtils._resolve_path_variables(path_str)
        logger.debug(f"OCR结果目录: {path_str} -> {resolved_path}")
        return resolved_path

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
        if not path:
            return path

        try:
            # 如果路径已经是相对路径（不包含盘符且不以/开头），直接返回
            if not os.path.isabs(path) and not path.startswith('/'):
                # 检查是否已经是正确的相对路径格式
                if path.startswith('ocr/repositories/') or path.startswith('ocr/uploads/'):
                    logger.debug(f"路径已经是正确的相对路径格式: {path}")
                    return path
                # 检查是否包含错误的路径格式
                if 'ocr/uploads/ocr/' in path:
                    corrected_path = path.replace('ocr/uploads/ocr/', 'ocr/')
                    logger.info(f"修正错误路径格式: {path} -> {corrected_path}")
                    return corrected_path
                return path

            # 获取媒体根目录
            media_root = PathUtils.get_media_root()

            # 如果路径以媒体根目录开头，转换为相对路径
            if path.startswith(media_root):
                rel_path = os.path.relpath(path, media_root)
                # 确保路径使用正斜杠，符合Web URL格式
                rel_path = rel_path.replace('\\', '/')

                # 修复路径，去掉多余的uploads目录
                if rel_path.startswith('ocr/uploads/ocr/'):
                    rel_path = rel_path.replace('ocr/uploads/ocr/', 'ocr/')
                    logger.info(f"修正路径中的重复目录: {path} -> {rel_path}")

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
        return os.path.join(settings.BASE_DIR.parent, "wfgame-ai-server", "media", "ocr", "repositories", "ocr_hit_5pics") # 专用于识别错误的测试目录
        # return os.path.join(settings.BASE_DIR.parent, "wfgame-ai-server", "media", "ocr", "repositories", "CardGame2", "Client", "assets", "designImg")
        return os.path.join(settings.BASE_DIR.parent, "wfgame-ai-server", "media", "ocr", "repositories", "ocr_test")
