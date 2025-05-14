"""
设备管理应用URL配置
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

# 创建路由器并注册视图集
router = DefaultRouter()
router.register(r'types', views.DeviceTypeViewSet)
router.register(r'devices', views.DeviceViewSet)
router.register(r'logs', views.DeviceLogViewSet)

# 应用的URL模式
urlpatterns = [
    # API路由
    path('', include(router.urls)),
    
    # 自定义操作
    path('devices/<int:pk>/connect/', views.ConnectDeviceView.as_view(), name='device-connect'),
    path('devices/<int:pk>/disconnect/', views.DisconnectDeviceView.as_view(), name='device-disconnect'),
    path('devices/<int:pk>/reserve/', views.ReserveDeviceView.as_view(), name='device-reserve'),
    path('devices/<int:pk>/release/', views.ReleaseDeviceView.as_view(), name='device-release'),
    path('devices/scan/', views.ScanDevicesView.as_view(), name='device-scan'),
] 