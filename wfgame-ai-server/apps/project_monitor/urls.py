"""
项目监控URL配置
"""
from django.urls import path
from . import views

app_name = 'project_monitor'

urlpatterns = [
    # 项目管理API
    path('projects/list/', views.projects_list, name='projects_list'),
    path('projects/create/', views.projects_create, name='projects_create'),

    # 仪表板API
    path('dashboard/', views.dashboard, name='dashboard'),

    # 执行数据记录API
    path('log/', views.log_execution, name='log_execution'),

    # 健康检查API
    path('health/', views.health_check, name='health_check'),
]