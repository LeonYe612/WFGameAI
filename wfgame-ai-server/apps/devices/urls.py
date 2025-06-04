"""
设备管理应用URL配置
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.decorators import api_view, permission_classes

from . import views

# 应用的URL模式
urlpatterns = [
    # 设备扫描API - 先定义具体路径
    path('devices/scan/', views.ScanDevicesView.as_view(), name='device-scan'),

    # 新增的设备管理API
    path('devices/usb-check/', views.USBConnectionCheckView.as_view(), name='device-usb-check'),
    path('devices/enhanced-report/', views.EnhancedDeviceReportView.as_view(), name='device-enhanced-report'),
    path('devices/<int:pk>/enhanced-report/', views.EnhancedDeviceReportView.as_view(), name='device-enhanced-report-detail'),

    # 自定义操作 - 确保所有API都支持POST
    path('devices/<int:pk>/connect/', views.ConnectDeviceView.as_view(), name='device-connect'),
    path('devices/<int:pk>/disconnect/', views.DisconnectDeviceView.as_view(), name='device-disconnect'),
    path('devices/<int:pk>/reserve/', views.ReserveDeviceView.as_view(), name='device-reserve'),
    path('devices/<int:pk>/release/', views.ReleaseDeviceView.as_view(), name='device-release'),

    # 创建路由器并注册视图集
    # 注意：路由器注册顺序放在最后，避免通配符路径覆盖具体路径
]

# 创建路由器并注册视图集 - 放在具体路径后面
router = DefaultRouter()
router.register(r'types', views.DeviceTypeViewSet)
router.register(r'devices', views.DeviceViewSet)
router.register(r'logs', views.DeviceLogViewSet)

# 添加路由器URL
urlpatterns += [
    # API路由 - ViewSet自动生成的路由
    path('', include(router.urls)),
]