#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================
Description:
脚本管理应用的URL配置
Author: WFGame AI Team
CreateDate: 2024-05-15
Version: 1.0
===============================
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ScriptCategoryViewSet,
    ScriptViewSet,
    ScriptVersionViewSet,
    ScriptExecutionViewSet,
    get_devices,
    get_scripts,
    get_reports,
    get_latest_report,
    record_script,
    replay_script,
    debug_script,
    start_record,
    import_script,
    edit_script,
    get_python_envs,
    switch_python_env
)

# 创建路由器并注册视图集
router = DefaultRouter()
router.register(r'categories', ScriptCategoryViewSet)
router.register(r'scripts', ScriptViewSet)
router.register(r'history', ScriptVersionViewSet)
router.register(r'executions', ScriptExecutionViewSet)

# API URL配置
urlpatterns = [
    # 包含路由器生成的URL
    path('', include(router.urls)),
    
    # 自定义API端点
    path('devices/', get_devices, name='get-devices'),
    path('list/', get_scripts, name='get-scripts'),
    path('reports/', get_reports, name='get-reports'),
    path('latest-report/', get_latest_report, name='get-latest-report'),
    path('record/', record_script, name='record-script'),
    path('replay/', replay_script, name='replay-script'),
    
    # 新增API端点
    path('debug/', debug_script, name='debug-script'),
    path('start-record/', start_record, name='start-record'),
    path('import/', import_script, name='import-script'),
    path('edit/', edit_script, name='edit-script'),
    path('edit/<path:script_path>/', edit_script, name='edit-script-with-path'),
    
    # Python环境管理
    path('python-envs/', get_python_envs, name='get-python-envs'),
    path('switch-python-env/', switch_python_env, name='switch-python-env'),
] 