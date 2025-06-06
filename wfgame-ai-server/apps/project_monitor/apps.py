"""
项目监控应用配置
"""
from django.apps import AppConfig


class ProjectMonitorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.project_monitor'
    verbose_name = '项目性能监控'

    def ready(self):
        """应用准备就绪后的初始化"""
        pass
