from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.notifications'
    verbose_name = '通知系统'

    def ready(self):
        """
        应用启动时执行的初始化操作
        """
        # 只在主进程中执行，避免在runserver的重载进程中重复执行
        import os
        if os.environ.get('RUN_MAIN') != 'true':
            return
            
        try:
            # 导入并执行清理函数
            from .services import clear_all_sse_connections_on_startup
            clear_all_sse_connections_on_startup()
            
        except Exception as e:
            logger.error(f"Error during notifications app startup cleanup: {e}")
