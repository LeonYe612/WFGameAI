"""
URL Configuration for wfgame_ai_server_main.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
import os

from .views import static_page_view

schema_view = get_schema_view(
    openapi.Info(
        title="WFGame AI API",
        default_version='v1',
        description="WFGame AI API Documentation",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

# 静态页面映射 - 修复路径处理
staticfiles_dir = os.path.join(settings.BASE_DIR, 'staticfiles')
pages_dir = os.path.join(staticfiles_dir, 'pages')

urlpatterns = [
    # 根路径使用主页模板
    path('', RedirectView.as_view(url='/pages/index_template.html', permanent=False), name='index'),

    # API文档
    path('admin/', admin.site.urls),
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

    # 常用页面的便捷访问路径
    path('dashboard/', RedirectView.as_view(url='/pages/dashboard_template.html', permanent=False)),
    path('ocr/', RedirectView.as_view(url='/pages/ocr_template.html', permanent=False)),
    path('reports/', RedirectView.as_view(url='/pages/reports_template.html', permanent=False)),
    path('settings/', RedirectView.as_view(url='/pages/settings_template.html', permanent=False)),

    # 静态页面模板访问
    path('pages/<path:template_name>', static_page_view, name='static_pages'),

    # Application endpoints
    path("api/users/", include("apps.users.urls")),
    path('api/devices/', include('apps.devices.urls')),
    path('api/scripts/', include('apps.scripts.urls')),
    path('api/project-monitor/', include('apps.project_monitor.urls')),
    path('api/reports/', include('apps.reports.urls')),
    path('api/notifications/', include('apps.notifications.urls')),

    # OCR模块API
    path('api/ocr/', include('apps.ocr.urls')),
]

# 添加静态文件目录
urlpatterns += static(settings.STATIC_URL, document_root=staticfiles_dir)

# 添加媒体文件URL
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)