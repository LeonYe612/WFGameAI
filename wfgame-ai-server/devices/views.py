"""
设备管理应用的视图
"""

import subprocess
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, views
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import DeviceType, Device, DeviceLog
from .serializers import (
    DeviceTypeSerializer,
    DeviceSerializer,
    DeviceDetailSerializer,
    DeviceLogSerializer
)


class DeviceTypeViewSet(viewsets.ModelViewSet):
    """设备类型视图集"""
    queryset = DeviceType.objects.all()
    serializer_class = DeviceTypeSerializer
    permission_classes = [AllowAny]  # 允许所有用户访问
    http_method_names = ['post']  # 只允许POST方法


class DeviceViewSet(viewsets.ModelViewSet):
    """设备视图集"""
    queryset = Device.objects.all()
    permission_classes = [AllowAny]  # 允许所有用户访问
    filterset_fields = ['status', 'type']
    search_fields = ['name', 'device_id', 'ip_address']
    http_method_names = ['post']  # 只允许POST方法
    
    def get_serializer_class(self):
        """根据操作选择适当的序列化器"""
        if self.action == 'retrieve' or self.action == 'create' or self.action == 'update':
            return DeviceDetailSerializer
        return DeviceSerializer
    
    @action(detail=True, methods=['post'])
    def logs(self, request, pk=None):
        """获取指定设备的日志"""
        device = self.get_object()
        logs = DeviceLog.objects.filter(device=device)
        page = self.paginate_queryset(logs)
        if page is not None:
            serializer = DeviceLogSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = DeviceLogSerializer(logs, many=True)
        return Response(serializer.data)


class DeviceLogViewSet(viewsets.ReadOnlyModelViewSet):
    """设备日志视图集 - 只读"""
    queryset = DeviceLog.objects.all()
    serializer_class = DeviceLogSerializer
    permission_classes = [AllowAny]  # 允许所有用户访问
    filterset_fields = ['device', 'level']
    http_method_names = ['post']  # 只允许POST方法


class ConnectDeviceView(views.APIView):
    """连接设备"""
    permission_classes = [AllowAny]  # 允许所有用户访问
    http_method_names = ['post']  # 只允许POST方法
    
    def post(self, request, pk):
        device = get_object_or_404(Device, pk=pk)
        
        # 检查设备是否已连接
        if device.status == 'online':
            return Response(
                {"detail": "设备已经处于连接状态"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 尝试连接设备
        try:
            # 这里可以添加实际连接设备的代码
            # 例如使用adbutils连接Android设备
            
            # 更新设备状态
            device.status = 'online'
            device.last_online = timezone.now()
            device.save()
            
            # 创建日志
            DeviceLog.objects.create(
                device=device,
                level='info',
                message=f"设备 '{device.name}' 已连接"
            )
            
            # 返回成功响应
            return Response(
                {"detail": "设备连接成功"},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            # 创建错误日志
            DeviceLog.objects.create(
                device=device,
                level='error',
                message=f"连接设备 '{device.name}' 失败: {str(e)}"
            )
            
            # 返回错误响应
            return Response(
                {"detail": f"设备连接失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DisconnectDeviceView(views.APIView):
    """断开设备连接"""
    permission_classes = [AllowAny]  # 允许所有用户访问
    http_method_names = ['post']  # 只允许POST方法
    
    def post(self, request, pk):
        device = get_object_or_404(Device, pk=pk)
        
        # 检查设备是否已连接
        if device.status == 'offline':
            return Response(
                {"detail": "设备已经处于断开状态"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 尝试断开设备连接
        try:
            # 这里可以添加实际断开设备连接的代码
            
            # 更新设备状态
            device.status = 'offline'
            device.save()
            
            # 创建日志
            DeviceLog.objects.create(
                device=device,
                level='info',
                message=f"设备 '{device.name}' 已断开连接"
            )
            
            # 返回成功响应
            return Response(
                {"detail": "设备已断开连接"},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            # 创建错误日志
            DeviceLog.objects.create(
                device=device,
                level='error',
                message=f"断开设备 '{device.name}' 连接失败: {str(e)}"
            )
            
            # 返回错误响应
            return Response(
                {"detail": f"断开设备连接失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ReserveDeviceView(views.APIView):
    """预约设备"""
    permission_classes = [AllowAny]  # 允许所有用户访问
    http_method_names = ['post']  # 只允许POST方法
    
    def post(self, request, pk):
        device = get_object_or_404(Device, pk=pk)
        
        # 检查设备是否已被预约
        if device.status == 'busy' and device.current_user != request.user:
            return Response(
                {"detail": "设备已被其他用户预约"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 预约设备
        device.status = 'busy'
        device.current_user = request.user if request.user.is_authenticated else None
        device.save()
        
        # 创建日志
        DeviceLog.objects.create(
            device=device,
            level='info',
            message=f"设备 '{device.name}' 已被预约"
        )
        
        # 返回成功响应
        return Response(
            {"detail": "设备预约成功"},
            status=status.HTTP_200_OK
        )


class ReleaseDeviceView(views.APIView):
    """释放设备"""
    permission_classes = [AllowAny]  # 允许所有用户访问
    http_method_names = ['post']  # 只允许POST方法
    
    def post(self, request, pk):
        device = get_object_or_404(Device, pk=pk)
        
        # 检查设备是否已被预约
        if device.status != 'busy':
            return Response(
                {"detail": "设备未被预约"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 检查是否有权限释放设备
        if device.current_user != request.user and not request.user.is_staff:
            return Response(
                {"detail": "无权释放此设备"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 释放设备
        old_user = device.current_user
        device.status = 'online' if device.last_online and (timezone.now() - device.last_online).total_seconds() < 3600 else 'offline'
        device.current_user = None
        device.save()
        
        # 创建日志
        DeviceLog.objects.create(
            device=device,
            level='info',
            message=f"设备 '{device.name}' 已被用户 '{request.user.username}' 释放，之前由用户 '{old_user.username if old_user else 'unknown'}' 使用"
        )
        
        # 返回成功响应
        return Response(
            {"detail": "设备释放成功"},
            status=status.HTTP_200_OK
        )


class ScanDevicesView(views.APIView):
    """扫描设备"""
    permission_classes = [AllowAny]  # 允许所有用户访问
    http_method_names = ['post']  # 只允许POST方法
    
    def post(self, request):
        # 扫描Android设备
        try:
            # 使用adb命令扫描设备
            result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
            
            if result.returncode != 0:
                return Response(
                    {"detail": "扫描设备失败", "error": result.stderr},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # 解析adb输出
            lines = result.stdout.strip().split('\n')
            
            # 跳过第一行（标题行）
            device_lines = lines[1:]
            
            # 处理每个设备
            devices_found = []
            for line in device_lines:
                if not line.strip():
                    continue
                    
                parts = line.split('\t')
                if len(parts) >= 2:
                    device_id = parts[0].strip()
                    device_status = parts[1].strip()
                    
                    # 检查设备是否已存在
                    device, created = Device.objects.get_or_create(
                        device_id=device_id,
                        defaults={
                            'name': f"Android设备 {device_id}",
                            'status': 'online' if device_status == 'device' else 'offline'
                        }
                    )
                    
                    # 如果设备已存在但状态不同，更新状态
                    if not created and (
                        (device_status == 'device' and device.status != 'online') or
                        (device_status != 'device' and device.status == 'online')
                    ):
                        device.status = 'online' if device_status == 'device' else 'offline'
                        device.save()
                    
                    devices_found.append({
                        'id': device.id,
                        'device_id': device.device_id,
                        'name': device.name,
                        'status': device.status,
                        'created': created
                    })
            
            return Response({
                "detail": "扫描设备成功",
                "devices_found": devices_found
            })
        
        except Exception as e:
            return Response(
                {"detail": "扫描设备失败", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            ) 