#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务管理应用的URL配置
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TaskGroupViewSet,
    TaskViewSet,
    task_bulk_operations,
    task_execution_logs
)

# 创建路由器并注册视图集
router = DefaultRouter(trailing_slash=False)
router.register(r'groups', TaskGroupViewSet)
router.register(r'tasks', TaskViewSet)

# API URL配置
urlpatterns = [
    # 只允许POST的主路由
    path('', TaskViewSet.as_view({'post': 'list'})),

    # 包含路由器生成的其他URL
    path('', include(router.urls)),

    # 自定义API端点
    path('bulk-operations/', task_bulk_operations, name='task-bulk-operations'),
    path('tasks/<int:task_id>/logs/', task_execution_logs, name='task-execution-logs'),
]
