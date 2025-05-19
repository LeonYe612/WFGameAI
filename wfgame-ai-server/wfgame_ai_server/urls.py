"""
URL配置
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView, TemplateView
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from .views import index_view

# 导入脚本相关视图函数
from scripts.views import (
    get_scripts, edit_script, replay_script, import_script, debug_script, 
    get_devices, get_reports, get_latest_report, record_script, get_python_envs
)

from reports.views import get_report_list, get_device_performance

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

def template_view(request, template_name):
    """
    通用模板视图，用于渲染页面模板
    
    Args:
        request: HTTP请求对象
        template_name: 要渲染的模板名称
    """
    try:
        # 添加.html后缀如果没有
        if not template_name.endswith('.html'):
            template_name += '.html'
        
        return render(request, f'pages/{template_name}')
    except Exception as e:
        return HttpResponse(f'模板加载失败: {template_name}, 错误: {str(e)}')

def health_check(request):
    """健康检查API，返回系统状态"""
    return JsonResponse({"status": "ok"})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls')),
    
    # 首页
    path('', index_view, name='index'),
    
    # SPA路由
    path('pages/<path:template_name>', template_view, name='template_view'),
    
    # API接口 - 所有API使用POST方法
    path('api/devices/', get_devices, name='api-devices'),
    path('api/scripts/', get_scripts, name='api-scripts'),
    path('api/scripts/edit/', edit_script, name='api-script-edit'),
    path('api/scripts/replay/', replay_script, name='api-script-replay'),
    path('api/scripts/import/', import_script, name='api-script-import'),
    path('api/scripts/debug/', debug_script, name='api-script-debug'),
    path('api/scripts/record/', record_script, name='api-script-record'),
    path('api/reports/', get_reports, name='api-reports'),
    path('api/reports/latest/', get_latest_report, name='api-latest-report'),
    path('api/reports/performance/', get_device_performance, name='api-device-performance'),
    path('api/env/python/', get_python_envs, name='api-python-envs'),
    
    # 健康检查
    path('health/', health_check, name='health_check'),
    
    # API文档
    path('api/docs/', TemplateView.as_view(
        template_name='swagger-ui.html',
        extra_context={'schema_url': 'openapi-schema'}
    ), name='swagger-ui'),
    path('api/redoc/', TemplateView.as_view(
        template_name='redoc.html',
        extra_context={'schema_url': 'openapi-schema'}
    ), name='redoc'),
]

# 开发环境下的静态文件和媒体文件
if settings.DEBUG:
    # urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) 