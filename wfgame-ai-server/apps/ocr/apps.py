"""
OCR模块应用配置
"""

from django import conf
from django.apps import AppConfig


class OCRConfig(AppConfig):
    """OCR应用配置类"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ocr"
    verbose_name = "OCR图片文字识别"

    def ready(self):
        """应用准备就绪时执行的操作"""

        # 确保 OCR 相关目录已配置并存在
        from utils.config_helper import config

        config.get_path("ocr_results_dir")
        config.get_path("ocr_uploads_dir")
        config.get_path("ocr_repos_dir")

        # 加载信号处理器
        # import apps.ocr.signals
