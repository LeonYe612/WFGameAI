#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================
Description:
Django主配置文件
Author: WFGame AI Team
CreateDate: 2025-05-15
Version: 1.0
===============================
"""

import os
import sys
from pathlib import Path
from utils.config_helper import *
from utils.redis_helper import RedisHelper
from utils.minio_helper import MinioService

# 添加项目根路径至 sys.path
sys.path.insert(0, get_project_root())

# 构建路径，以项目目录为起点
BASE_DIR = (
    Path(__file__).resolve().parent.parent
)  # wfgame-ai-server/wfgame_ai_server_main

# 密钥设置
SECRET_KEY = "django-insecure-key-for-development-only"

AUTH_USER_MODEL = "users.AuthUser"  # 使用自定义用户模型
APPEND_SLASH = False  # 自动追加斜杠

# 调试模式
DEBUG = True

ALLOWED_HOSTS = ["*"]

# 应用定义
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",  # Django静态文件处理
    "django_extensions",
    # 第三方应用
    "rest_framework",
    "drf_yasg",
    "corsheaders",
    # 本地应用
    "apps.devices",
    "apps.scripts",
    "apps.users",
    "apps.tasks",
    "apps.reports",
    "apps.data_source",
    "apps.ocr",  # OCR模块
    "apps.notifications", # SSE 通知应用
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    # 'django.middleware.csrf.CsrfViewMiddleware',  # 暂时注释掉CSRF中间件，仅用于测试环境
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.core.middleware.auth.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "wfgame_ai_server.middleware.JsonErrorHandlerMiddleware",  # 添加自定义中间件，确保API错误返回JSON
]

ROOT_URLCONF = "wfgame_ai_server_main.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "staticfiles", "pages")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "wfgame_ai_server_main.wsgi.application"

# 全局CONFIG单例对象
CFG = ConfigManager()

# 根据环境标识（由 AI_ENV 或启动脚本注入）
ENV_NAME = (os.environ.get("AI_ENV", "dev") or "dev").strip()

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": CFG.get("database", "dbname", fallback="gogotest_data"),
        "USER": CFG.get("database", "username", fallback="root"),
        "PASSWORD": CFG.get("database", "password", fallback="qa123456"),
        "HOST": CFG.get("database", "host", fallback="127.0.0.1"),
        "PORT": CFG.get("database", "port", fallback="3306"),
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# 密码校验
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# 国际化
LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_L10N = True
USE_TZ = False

# 静态文件设置
STATIC_URL = "/static/"
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "staticfiles"),
    os.path.join(BASE_DIR, "apps", "reports"),
]
# 重要：在开发模式下不要设置STATIC_ROOT，否则Django无法提供staticfiles目录中的文件
# STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')  # 已注释掉，确保开发模式下直接使用staticfiles目录

# 媒体文件设置
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# 默认主键类型
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# REST Framework设置
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        # 不使用 DRF SessionAuthentication，避免 CSRF问题
        # "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_SCHEMA_CLASS": "rest_framework.schemas.coreapi.AutoSchema",
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
}

# CORS设置
# 生产环境建议指定具体的允许域名
CORS_ALLOW_ALL_ORIGINS = True  # 开发环境默认放开
CORS_ALLOW_CREDENTIALS = True

# 根据环境收紧CORS/CSRF（从配置读取前端来源）
try:
    FRONT_ORIGIN = CFG.get('auth', 'sso_web_host', fallback='').strip()
except Exception:
    FRONT_ORIGIN = ''

if ENV_NAME == 'prod':
    CORS_ALLOW_ALL_ORIGINS = False
    CORS_ALLOWED_ORIGINS = [FRONT_ORIGIN] if FRONT_ORIGIN else []
    # CSRF 信任来源需包含 scheme
    CSRF_TRUSTED_ORIGINS = [FRONT_ORIGIN] if FRONT_ORIGIN else []
    # HTTPS 环境下开启安全Cookie
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# 生产环境使用以下配置替代 CORS_ALLOW_ALL_ORIGINS = True
# CORS_ALLOWED_ORIGINS = [
#     "https://your-frontend.example.com",
# ]

# CORS额外配置
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'x-frontend-version',  # 添加前端版本标识请求头
    'x-api-version',       # 添加API版本请求头
    'x-request-id',        # 添加请求ID请求头
]

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

# 预检请求的缓存时间
CORS_PREFLIGHT_MAX_AGE = 86400

# 日志配置
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": os.path.join(BASE_DIR, "logs/django.log"),
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": True,
        },
        "scripts": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "devices": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "ocr": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# 确保logs目录存在
os.makedirs(os.path.join(BASE_DIR, "logs"), exist_ok=True)

# Session配置
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = 86400  # 1天
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_SECURE = False
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# 应用版本
VERSION = "1.0.0"

# YOLO模型设置
YOLO_MODEL_PATH = os.path.join(BASE_DIR.parent, "yolo11m.pt")
YOLO_CONFIDENCE_THRESHOLD = 0.5

# TODO redis 相关
# ai业务接口
REDIS_CFG = get_redis_conn("redis")
REDIS = RedisHelper(REDIS_CFG)


# ai_celery配置（基于环境隔离）
# 优先尝试 [celery_{ENV_NAME}]（如 celery_dev/celery_prod），不存在再回退 [celery]
CELERY_SECTION = f"celery_{ENV_NAME}"
try:
    CELERY_REDIS_CFG = get_redis_conn(CELERY_SECTION)
except Exception as e:
    print(f"警告: 未找到 {CELERY_SECTION} 配置，回退到 [celery] 配置: {e}")
    CELERY_REDIS_CFG = get_redis_conn("celery")

# 任务默认队列名带环境后缀，确保与 worker -Q 一致
CELERY_TASK_DEFAULT_QUEUE = f"ai_queue_{ENV_NAME}"

 # === Celery 同步执行模式（Eager）按配置文件启用 ===
 # 按环境读取 [celery_dev] 或 [celery_prod] 中的 task_always_eager / task_eager_propogates
 # 仅支持 True / False，其他值视为 False
_celery_section = f"celery_{ENV_NAME}" if ENV_NAME != 'prod' else 'celery_prod'
try:
    # 注意：开发配置文件键名为 task_eager_propogates（原拼写），保持兼容读取
    CELERY_TASK_ALWAYS_EAGER = str(CFG.get(_celery_section, 'task_always_eager', fallback='False')).strip() == 'true'
    CELERY_TASK_EAGER_PROPAGATES = str(CFG.get(_celery_section, 'task_eager_propogates', fallback='True')).strip() == 'true'
    # 工作者健康检查超时时间（秒）
    try:
        CELERY_WORKER_HEALTHCHECK_TIMEOUT = float(str(CFG.get(_celery_section, 'worker_health_check_timeout', fallback='2')).strip())
    except Exception:
        CELERY_WORKER_HEALTHCHECK_TIMEOUT = 2.0
except Exception:
    CELERY_TASK_ALWAYS_EAGER = False
    CELERY_TASK_EAGER_PROPAGATES = True
    CELERY_WORKER_HEALTHCHECK_TIMEOUT = 2.0


# MinIO 全局服务实例（在应用启动时即加载，可直接 from django.conf import settings 后使用 settings.MINIO ）
try:
    MINIO: MinioService = MinioService()
except Exception as _e:
    # 避免启动中断，保留占位；后续使用前可检测是否有 client
    print(f"[WARN] MinIOService 初始化失败: {_e}")
    MINIO = None
