"""
URL配置。
主路由入口，统一分发到各App。
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView, TemplateView
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
import os

from .views import index_view

# 导入脚本相关视图函数
from apps.scripts.views import (
    get_scripts, edit_script, replay_script, import_script, debug_script,
    get_reports, get_latest_report, record_script, get_python_envs
)

from apps.reports.views import get_report_list, get_device_performance, summary_list

# API文档配置
schema_view = get_schema_view(
    openapi.Info(
        title="WFGame AI自动化测试平台 API",
        default_version='v1',
        description="WFGame AI自动化测试平台API文档",
        contact=openapi.Contact(email="admin@example.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

def static_page_view(request, template_name):
    """
    静态页面视图，使用staticfiles/pages目录下的HTML文件

    Args:
        request: HTTP请求对象
        template_name: 页面名称
    """
    try:
        # 添加.html后缀如果没有
        if not template_name.endswith('.html'):
            template_name += '.html'

        # 构建静态文件路径
        static_file_path = os.path.join(settings.BASE_DIR, 'staticfiles', 'pages', template_name)

        # 检查静态文件是否存在
        if os.path.exists(static_file_path):
            # 重定向到静态文件URL
            return redirect(f'/static/pages/{template_name}')
        else:
            # 如果请求的文件不存在，尝试查找对应的模板文件
            template_name_parts = template_name.split('.')
            template_file = f"{template_name_parts[0]}_template.{template_name_parts[1]}"
            template_path = os.path.join(settings.BASE_DIR, 'staticfiles', 'pages', template_file)

            if os.path.exists(template_path):
                return redirect(f'/static/pages/{template_file}')
            else:
                return HttpResponse(f'页面未找到: {template_name}', status=404)
    except Exception as e:
        return HttpResponse(f'页面加载失败: {template_name}, 错误: {str(e)}', status=500)

def health_check(request):
    """健康检查API，返回系统状态"""
    return JsonResponse({"status": "ok"})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls')),    # 首页
    path('', index_view, name='index'),

    # 页面路由 - 使用静态页面视图
    path('pages/<path:template_name>', static_page_view, name='static_page_view'),    # 设备管理API - 包含所有设备相关的端点
    path('api/', include('apps.devices.urls')),    # 脚本管理API
    path('api/scripts/', include('apps.scripts.urls')),

    # 任务管理API
    path('api/tasks/', include('apps.tasks.urls')),

    # 报告管理API
    path('api/reports/', include('apps.reports.urls')),

    # 保留原有的直接API访问路径，以确保兼容性
    path('api/reports/summary_list/', summary_list),

    # API接口 - 所有API使用POST方法
    path('api/scripts/record/', record_script, name='api-script-record'),
    path('api/reports/', get_reports, name='api-reports'),
    path('api/reports/latest/', get_latest_report, name='api-latest-report'),
    path('api/reports/performance/', get_device_performance, name='api-device-performance'),
    path('api/env/python/', get_python_envs, name='api-python-envs'),    # 健康检查
    path('health/', health_check, name='health_check'),    # API文档
    path('api/docs/', TemplateView.as_view(
        template_name='swagger-ui.html',
        extra_context={'schema_url': 'openapi-schema'}
    ), name='swagger-ui'),
    path('api/redoc/', TemplateView.as_view(
        template_name='redoc.html',
        extra_context={'schema_url': 'openapi-schema'}
    ), name='redoc'),

    # OpenAPI schema URLs
    path('api/schema/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('api/schema/swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/schema/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

# 开发环境下的静态文件和媒体文件
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)