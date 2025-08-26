"""
Celery配置
"""

from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from django.conf import settings

# 设置默认Django配置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wfgame_ai_server_main.settings')

# 创建Celery应用
AI_CELERY = Celery('wfgame_ai_server_main',backend=settings.CELERY_REDIS_CFG.redis_url, broker=settings.CELERY_REDIS_CFG.redis_url, broker_connection_retry_on_startup=True)

# 使用字符串表示，以避免将对象本身通过pickle序列化
AI_CELERY.config_from_object('django.conf:settings', namespace='CELERY')

# 自动从所有已注册的Django应用中加载任务
AI_CELERY.autodiscover_tasks()

@AI_CELERY.task(bind=True)
def debug_task(self):
    """测试任务，用于调试"""
    print(f'Request: {self.request!r}') 