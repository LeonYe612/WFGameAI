"""
OCR模块应用配置
"""
from django.apps import AppConfig


class OCRConfig(AppConfig):
    """OCR应用配置类"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.ocr'
    verbose_name = 'OCR图片文字识别'

    def ready(self):
        """应用准备就绪时执行的操作"""
        import os
        from django.conf import settings
        import configparser

        # 确保OCR相关目录存在
        config = configparser.ConfigParser()
        config.read(settings.BASE_DIR.parent / 'config.ini', encoding='utf-8')

        results_dir = config.get('paths', 'ocr_results_dir', fallback='output/ocr/results')
        uploads_dir = config.get('paths', 'ocr_uploads_dir', fallback='media/ocr/uploads')
        repos_dir = config.get('paths', 'ocr_repos_dir', fallback='media/ocr/repositories')

        os.makedirs(results_dir, exist_ok=True)
        os.makedirs(uploads_dir, exist_ok=True)
        os.makedirs(repos_dir, exist_ok=True)

        # 加载信号处理器
        # import apps.ocr.signals