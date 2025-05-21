"""
脚本管理应用配置
"""

from django.apps import AppConfig


class ScriptsConfig(AppConfig):
    """脚本管理应用配置类"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.scripts'
    verbose_name = '脚本管理'

    def ready(self):
        """应用准备就绪时的初始化操作"""
        # 导入信号处理器
        import apps.scripts.signals 