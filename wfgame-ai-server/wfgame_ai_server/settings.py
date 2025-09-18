# Proxy settings module
from wfgame_ai_server_main.settings import *

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    # "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.core.middleware.auth.AuthenticationMiddleware",  # 添加自定义认证中间件
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "wfgame_ai_server.middleware.JsonErrorHandlerMiddleware",  # 添加自定义中间件
]
