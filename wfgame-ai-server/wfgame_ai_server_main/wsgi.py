"""
WSGI配置

它暴露了WSGI可调用对象作为模块级变量 ``application``。

更多信息请参考
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wfgame_ai_server_main.settings')

application = get_wsgi_application() 