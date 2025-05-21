"""
WFGame AI自动化测试平台后端服务
"""

# 配置Celery
from __future__ import absolute_import, unicode_literals

# 确保在Django启动时Celery应用也被加载
from .celery import app as celery_app

__all__ = ('celery_app',) 