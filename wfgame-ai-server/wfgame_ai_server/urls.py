"""
URL Configuration for wfgame_ai_server.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="WFGame AI API",
        default_version='v1',
        description="WFGame AI API Documentation",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # Swagger documentation
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

    # Application endpoints
    path('api/devices/', include('apps.devices.urls')),
    path('api/scripts/', include('apps.scripts.urls')),
    path('api/project-monitor/', include('apps.project_monitor.urls')),
    path('api/reports/', include('apps.reports.urls')),

    # OCR模块API
    path('api/ocr/', include('apps.ocr.urls')),
]

# 添加媒体文件URL
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
