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
    replay_status,
    replay_cancel,
    debug_script,
    start_record,
    import_script,
    get_python_envs,
    switch_python_env,
    storage_status,
    storage_cleanup
)

# 应用生命周期管理API
from .app_lifecycle_api import (
    get_app_templates,
    create_app_template,
    start_app,
    stop_app,
    restart_app,
    get_app_status,
    get_connected_devices,
    batch_operation,
    health_check
)

# 创建路由器并注册视图集
router = DefaultRouter(trailing_slash=False)
router.register(r'categories', ScriptCategoryViewSet)
router.register(r'scripts', ScriptViewSet)
router.register(r'history', ScriptVersionViewSet)
router.register(r'executions', ScriptExecutionViewSet)

# API URL配置
urlpatterns = [
    # 只允许POST的主路由
    path('', ScriptViewSet.as_view({'post': 'create'})),
    # 包含路由器生成的其他URL
    path('', include(router.urls)),

    # 自定义API端点
    path('devices/', get_devices, name='get-devices'),
    path('list/', get_scripts, name='get-scripts'),
    path('reports/', get_reports, name='get-reports'),
    path('latest-report/', get_latest_report, name='get-latest-report'),
    path('record/', record_script, name='record-script'),
    path('replay/', replay_script, name='replay-script'),    # 新增API端点
    path('replay/status/', replay_status, name='replay-status'),
    path('replay/cancel/', replay_cancel, name='replay-cancel'),
    path('storage/status/', storage_status, name='storage-status'),
    path('storage/cleanup/', storage_cleanup, name='storage-cleanup'),    path('debug/', debug_script, name='debug-script'),
    path('start-record/', start_record, name='start-record'),
    path('import/', import_script, name='import-script'),

    # Python环境管理
    path('python-envs/', get_python_envs, name='get-python-envs'),
    path('switch-python-env/', switch_python_env, name='switch-python-env'),

    # 应用生命周期管理API
    path('app-lifecycle/templates/', get_app_templates, name='get-app-templates'),
    path('app-lifecycle/templates/create/', create_app_template, name='create-app-template'),
    path('app-lifecycle/start/', start_app, name='start-app'),
    path('app-lifecycle/stop/', stop_app, name='stop-app'),
    path('app-lifecycle/restart/', restart_app, name='restart-app'),
    path('app-lifecycle/status/', get_app_status, name='get-app-status'),
    path('app-lifecycle/devices/', get_connected_devices, name='get-connected-devices'),
    path('app-lifecycle/batch/', batch_operation, name='batch-app-operation'),
    path('app-lifecycle/health/', health_check, name='app-lifecycle-health'),
]