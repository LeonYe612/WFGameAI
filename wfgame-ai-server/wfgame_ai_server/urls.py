"""
URL配置
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.views.generic.base import TemplateView
from django.http import JsonResponse
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from .views import index_view

# 导入脚本相关视图函数
from scripts.views import replay_script, get_scripts, import_script, get_python_envs, switch_python_env

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
    path('reports/', include('reports.urls')),
    
    # 尚未实现的应用
    # path('tasks/', include('tasks.urls')),
    # path('data/', include('data_source.urls')),
    # path('users/', include('users.urls')),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls')),
    
    # API接口
    path('api/scripts/', include('scripts.urls')),
    path('api/devices/', include('devices.urls')),
    path('api/reports/', include('reports.urls')),
    
    # 脚本相关接口 - api 路径
    path('api/scripts/replay/', replay_script, name='replay_script'),
    path('api/scripts/list/', get_scripts, name='get_scripts'),
    path('api/scripts/import/', import_script, name='import_script'),
    
    # 兼容旧版API路径，前端代码仍使用/api/v1/路径
    path('api/v1/scripts/replay/', replay_script, name='v1_replay_script'),
    path('api/v1/scripts/list/', get_scripts, name='v1_get_scripts'),
    path('api/v1/scripts/import/', import_script, name='v1_import_script'),
    
    # 报告相关接口
    path('api/v1/reports/', include('reports.urls')),
    
    # Python环境相关接口
    path('api/system/python-envs/', get_python_envs, name='get_python_envs'),
    path('api/system/switch-python-env/', switch_python_env, name='switch_python_env'),
    
    # 兼容旧版API路径，前端代码仍使用/api/v1/路径
    path('api/v1/settings/python_envs/', get_python_envs, name='v1_get_python_envs'),
    path('api/v1/settings/switch_python_env/', switch_python_env, name='v1_switch_python_env'),
]

# 页面路由 - 使用 TemplateView 直接渲染模板
page_routes = [
    path('', RedirectView.as_view(url='/dashboard/'), name='index'),
    path('dashboard/', TemplateView.as_view(template_name='pages/dashboard.html'), name='dashboard'),
    path('devices/', TemplateView.as_view(template_name='pages/devices.html'), name='devices'),
    path('scripts/', TemplateView.as_view(template_name='pages/scripts.html'), name='scripts'),
    path('tasks/', TemplateView.as_view(template_name='pages/tasks.html'), name='tasks'),
    path('reports/', TemplateView.as_view(template_name='pages/reports.html'), name='reports'),
    path('data/', TemplateView.as_view(template_name='pages/data.html'), name='data'),
    path('settings/', TemplateView.as_view(template_name='pages/settings.html'), name='settings'),
]

# 添加 /pages/ 路径的兼容性映射
pages_routes = [
    path('pages/dashboard.html', TemplateView.as_view(template_name='pages/dashboard.html'), name='dashboard_page'),
    path('pages/devices.html', TemplateView.as_view(template_name='pages/devices.html'), name='devices_page'),
    path('pages/scripts.html', TemplateView.as_view(template_name='pages/scripts.html'), name='scripts_page'),
    path('pages/tasks.html', TemplateView.as_view(template_name='pages/tasks.html'), name='tasks_page'),
    path('pages/reports.html', TemplateView.as_view(template_name='pages/reports.html'), name='reports_page'),
    path('pages/data.html', TemplateView.as_view(template_name='pages/data.html'), name='data_page'),
    path('pages/settings.html', TemplateView.as_view(template_name='pages/settings.html'), name='settings_page'),
]

urlpatterns += page_routes
urlpatterns += pages_routes

# 添加media文件的URL配置
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# 添加健康检查接口
def health_check(request):
    return JsonResponse({'status': 'ok'})

urlpatterns.append(path('health/', health_check, name='health_check'))

# API文档
urlpatterns += [
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

# 开发环境下的静态文件和媒体文件
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) 