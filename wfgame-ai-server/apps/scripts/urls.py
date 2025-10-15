#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================
Description:
脚本管理应用的URL配置
Author: WFGame AI Team
CreateDate: 2025-05-15
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
    storage_cleanup,
    edit_script,  # 添加编辑脚本视图函数
    delete_script  # 添加删除脚本视图函数
)

from .apis.category import CategoryListView, CategoryDetailView, CategoryTreeView
from .apis.action import (
    ActionTypeListView,
    ActionTypeDetailView,
    ActionParamListView,
    ActionParamDetailView,
    ActionTypeWithParamsView,
    ActionSortView
)
from .apis.script import (
    ScriptListView,
    ScriptDetailView,
    ScriptDeleteView,
    ScriptMoveView,
    ScriptCopyView
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
    # 只允许POST的主路由，修改为list而非create
    path('', ScriptViewSet.as_view({'post': 'list'})),
    # 包含路由器生成的其他URL
    path('', include(router.urls)),

    # 脚本分类 api
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('categories/<int:pk>/', CategoryDetailView.as_view(), name='category-detail'),
    path('categories/tree/', CategoryTreeView.as_view()),

    # 脚本管理 api
    path('scripts/', ScriptListView.as_view(), name='script-list'),
    path('scripts/<int:pk>/', ScriptDetailView.as_view(), name='script-detail'),
    path('scripts/delete/', ScriptDeleteView.as_view(), name='script-delete'),
    path('scripts/move/', ScriptMoveView.as_view(), name='script-move'),
    path('scripts/copy/', ScriptCopyView.as_view(), name='script-copy'),

    # 操作类型和参数 api
    path('action-types/', ActionTypeListView.as_view(), name='action-type-list'),
    path('action-types/<int:pk>/', ActionTypeDetailView.as_view(), name='action-type-detail'),
    path('action-types/with-params/', ActionTypeWithParamsView.as_view(), name='action-type-with-params'),
    path('action-params/', ActionParamListView.as_view(), name='action-param-list'),
    path('action-params/<int:pk>/', ActionParamDetailView.as_view(), name='action-param-detail'),
    path('action-sort/', ActionSortView.as_view(), name='action-sort'),

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
    path('storage/cleanup/', storage_cleanup, name='storage-cleanup'),
    path('debug/', debug_script, name='debug-script'),
    path('start-record/', start_record, name='start-record'),
    path('import/', import_script, name='import-script'),
    path('edit/', edit_script, name='edit-script'),  # 添加编辑脚本路由
    path('delete/', delete_script, name='delete-script'),  # 添加删除脚本路由

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