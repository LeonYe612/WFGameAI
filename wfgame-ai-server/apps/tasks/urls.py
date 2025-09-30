#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务管理应用的URL配置
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TaskGroupViewSet, TaskViewSet, task_bulk_operations, task_execution_logs


# 使用标准 RESTful 路由，主路由 /api/tasks/ 指向 TaskViewSet
router = DefaultRouter()
router.register(r'', TaskViewSet, basename='task')
router.register(r'groups', TaskGroupViewSet, basename='taskgroup')

urlpatterns = [
    path('', include(router.urls)),
    path('bulk-operations/', task_bulk_operations, name='task-bulk-operations'),
    path('<int:task_id>/logs/', task_execution_logs, name='task-execution-logs'),
]