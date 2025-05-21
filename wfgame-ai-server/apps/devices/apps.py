"""
设备管理应用配置
"""

from django.apps import AppConfig


class DevicesConfig(AppConfig):
    """设备管理应用配置类"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.devices'
    verbose_name = '设备管理'

    def ready(self):
        """应用准备就绪时的初始化操作"""
        # 导入信号处理器
        import apps.devices.signals 