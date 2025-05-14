"""
ASGI配置

它暴露了ASGI可调用对象作为模块级变量 ``application``。

更多信息请参考
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wfgame_ai_server.settings')

# 获取基本的ASGI应用
django_asgi_app = get_asgi_application()

# 导入WebSocket路由
from wfgame_ai_server.routing import websocket_urlpatterns

# 配置ASGI应用，支持HTTP和WebSocket
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
}) 