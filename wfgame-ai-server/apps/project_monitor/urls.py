"""
项目监控系统URL配置
"""
from django.urls import path
from . import django_api

app_name = 'project_monitor'

urlpatterns = [
    # 项目管理API
    path('projects/list/', django_api.get_projects, name='get_projects'),
    path('projects/create/', django_api.create_project, name='create_project'),

    # 项目数据API
    path('dashboard/', django_api.get_project_dashboard, name='get_project_dashboard'),
    path('statistics/', django_api.get_project_statistics, name='get_project_statistics'),
    path('executions/log/', django_api.log_execution, name='log_execution'),
    path('trend/', django_api.get_class_trend, name='get_class_trend'),

    # 监控仪表板页面
    path('dashboard/page/', django_api.get_dashboard_page, name='dashboard_page'),
]
