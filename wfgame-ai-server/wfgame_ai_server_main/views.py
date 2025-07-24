#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================
Description:
主应用视图函数
Author: WFGame AI Team
CreateDate: 2025-05-15
Version: 1.0
===============================
"""

import os
import logging
from django.shortcuts import render, redirect
from django.http import Http404, HttpResponse, FileResponse
from django.conf import settings

# 配置日志
logger = logging.getLogger(__name__)


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


def static_page_view(request, template_name):
    """
    静态页面视图
    直接提供静态HTML文件，不使用Django模板引擎

    Args:
        request: HTTP请求
        template_name: 静态文件名

    Returns:
        HttpResponse: 静态文件响应

    Raises:
        Http404: 如果文件不存在
    """
    # 构建静态文件完整路径
    if not template_name.endswith('.html'):
        template_name += '.html'

    logger.info(f"访问静态页面: {template_name}")

    file_path = os.path.join(settings.BASE_DIR, 'staticfiles', 'pages', template_name)
    logger.info(f"查找文件路径: {file_path}")

    # 检查文件是否存在
    if os.path.exists(file_path):
        logger.info(f"文件存在，直接返回: {file_path}")
        # 读取文件内容并返回
        with open(file_path, 'rb') as f:
            content = f.read()
            return HttpResponse(content, content_type='text/html')

    # 文件不存在，尝试重定向到首页
    logger.warning(f"文件不存在: {file_path}")

    # 对于特定的模板，重定向到首页
    if template_name in ['dashboard_template.html', 'ocr_template.html',
                        'settings_template.html', 'reports_template.html']:
        logger.info("重定向到首页")
        return redirect('/pages/index_template.html')

    # 文件不存在，返回404
    raise Http404(f"找不到静态文件: {template_name}")