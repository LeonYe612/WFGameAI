"""
WebSocket路由配置
"""

from django.urls import re_path

# 临时注释掉尚未实现的任务消费者
# from tasks.consumers import TaskConsumer
from apps.devices.consumers import DeviceConsumer

# WebSocket URL模式
websocket_urlpatterns = [
    # 临时注释掉尚未实现的任务WebSocket路由
    # path('ws/tasks/', TaskConsumer.as_asgi()),
    re_path(r'ws/devices/$', DeviceConsumer.as_asgi()),
] 