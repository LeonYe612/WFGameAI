#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================
Description:
主应用视图函数
Author: WFGame AI Team
CreateDate: 2024-05-15
Version: 1.0
===============================
"""

from django.shortcuts import render
from django.conf import settings


def index_view(request):
    """
    首页视图

    渲染主页模板

    Args:
        request: HTTP请求对象

    Returns:
        HttpResponse: 渲染后的HTML页面
    """
    context = {
        'title': 'WFGame AI自动化测试平台',
        'description': '集成AI视觉识别、多设备管理和自动化测试的一体化解决方案',
        'version': settings.VERSION
    }
    return render(request, 'index_template.html', context)