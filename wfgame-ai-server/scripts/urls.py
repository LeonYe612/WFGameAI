"""
脚本管理应用URL配置
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

# 创建路由器并注册视图集
router = DefaultRouter()
router.register(r'categories', views.ScriptCategoryViewSet)
router.register(r'scripts', views.ScriptViewSet)
router.register(r'versions', views.ScriptVersionViewSet)

# 应用的URL模式
urlpatterns = [
    # API路由
    path('', include(router.urls)),
    
    # 自定义操作
    path('scripts/<int:pk>/clone/', views.CloneScriptView.as_view(), name='script-clone'),
    path('scripts/<int:pk>/export/', views.ExportScriptView.as_view(), name='script-export'),
    path('scripts/import/', views.ImportScriptView.as_view(), name='script-import'),
    path('scripts/<int:pk>/rollback/<str:version>/', views.RollbackScriptView.as_view(), name='script-rollback'),
] 