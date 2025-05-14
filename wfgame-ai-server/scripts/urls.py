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

from . import views

# 创建路由器并注册视图集
router = DefaultRouter()
router.register(r'categories', views.ScriptCategoryViewSet)
router.register(r'scripts', views.ScriptViewSet)
router.register(r'executions', views.ScriptExecutionViewSet)

urlpatterns = [
    # 使用自动生成的路由
    path('', include(router.urls)),
    
    # 自定义API路径
    path('scripts/<int:pk>/execute/', views.ScriptViewSet.as_view({'post': 'execute'}), name='script-execute'),
    path('scripts/<int:pk>/executions/', views.ScriptViewSet.as_view({'get': 'executions'}), name='script-executions'),
    path('scripts/<int:pk>/toggle-active/', views.ScriptViewSet.as_view({'post': 'toggle_active'}), name='script-toggle-active'),
] 