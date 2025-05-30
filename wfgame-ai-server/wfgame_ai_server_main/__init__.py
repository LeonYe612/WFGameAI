"""
WFGame AI自动化测试平台后端服务
"""

# 配置Celery
from __future__ import absolute_import, unicode_literals

# 确保在Django启动时Celery应用也被加载
from .celery import app as celery_app

import pymysql


# 设置pymysql版本信息，避免某些依赖检查失败
pymysql.version_info = (1, 4, 8, "final", 0)

# 使用pymysql作为MySQLdb的替代品
pymysql.install_as_MySQLdb()

# Celery应用实例
__all__ = ('celery_app',)

