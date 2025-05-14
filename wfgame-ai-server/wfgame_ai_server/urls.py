"""
URL配置
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from .views import index_view

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

# API路由
api_v1_patterns = [
    # 已实现的应用
    path('devices/', include('devices.urls')),
    path('scripts/', include('scripts.urls')),
    
    # 尚未实现的应用
    # path('tasks/', include('tasks.urls')),
    # path('reports/', include('reports.urls')),
    # path('data/', include('data_source.urls')),
    # path('users/', include('users.urls')),
]

urlpatterns = [
    # 根路径指向首页视图
    path('', index_view, name='index'),
    
    # 管理后台
    path('admin/', admin.site.urls),
    
    # API文档
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
    # API v1
    path('api/v1/', include(api_v1_patterns)),
    
    # 身份验证
    path('api-auth/', include('rest_framework.urls')),
    
    # 前端页面
    path('pages/dashboard.html', TemplateView.as_view(template_name='pages/dashboard.html'), name='dashboard'),
    path('pages/devices.html', TemplateView.as_view(template_name='pages/devices.html'), name='devices'),
    path('pages/scripts.html', TemplateView.as_view(template_name='pages/scripts.html'), name='scripts'),
    path('pages/tasks.html', TemplateView.as_view(template_name='pages/tasks.html'), name='tasks'),
    path('pages/reports.html', TemplateView.as_view(template_name='pages/reports.html'), name='reports'),
    path('pages/data.html', TemplateView.as_view(template_name='pages/data.html'), name='data'),
    path('pages/settings.html', TemplateView.as_view(template_name='pages/settings.html'), name='settings'),
]

# 开发环境下的静态文件和媒体文件
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) 