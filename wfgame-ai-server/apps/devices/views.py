"""
设备管理应用的视图
"""

import subprocess
import json
import os
import sys
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, views
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.conf import settings

from .models import DeviceType, Device, DeviceLog
from .serializers import (
    DeviceTypeSerializer,
    DeviceSerializer,
    DeviceDetailSerializer,
    DeviceLogSerializer
)

# 添加设备信息增强器的导入
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from device_info_enhancer import DeviceInfoEnhancer
    device_enhancer = DeviceInfoEnhancer()
except ImportError:
    device_enhancer = None
    print("警告: 在views.py中无法导入设备信息增强器")


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
    """连接设备（增强：连接前实时检测ADB状态并同步数据库）"""
    permission_classes = [AllowAny]  # 允许所有用户访问
    http_method_names = ['post']  # 只允许POST方法

    def post(self, request, pk):
        device = get_object_or_404(Device, pk=pk)

        # --- 增强：连接前实时检测ADB状态并同步数据库 ---
        try:
            adb_result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
            adb_lines = adb_result.stdout.strip().split('\n')[1:]
            adb_online_ids = set()
            for line in adb_lines:
                if not line.strip():
                    continue
                parts = line.split('\t')
                if len(parts) >= 2 and parts[1].strip() == 'device':
                    adb_online_ids.add(parts[0].strip())
            # 如果设备实际未连接但数据库为online，自动修正
            if device.device_id not in adb_online_ids and device.status == 'online':
                device.status = 'offline'
                device.save()
            # 如果设备实际已连接但数据库为offline，自动修正
            if device.device_id in adb_online_ids and device.status != 'online':
                device.status = 'online'
                device.last_online = timezone.now()
                device.save()
        except Exception as e:
            # ADB检测异常时写日志但不中断主流程
            DeviceLog.objects.create(
                device=device,
                level='warning',
                message=f"连接前ADB检测异常: {str(e)}"
            )

        # 检查设备是否已连接（以数据库状态为准，已同步）
        if device.status == 'online':
            return Response(
                {"detail": "设备已经处于连接状态"},
                status=status.HTTP_400_BAD_REQUEST
            )
        # 尝试连接设备
        try:
            # TODO: 这里可集成实际连接逻辑，如adb connect等，负责人: AI
            device.status = 'online'
            device.last_online = timezone.now()
            device.save()
            DeviceLog.objects.create(
                device=device,
                level='info',
                message=f"设备 '{device.name}' 已连接"
            )
            return Response(
                {"detail": "设备连接成功"},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            DeviceLog.objects.create(
                device=device,
                level='error',
                message=f"连接设备 '{device.name}' 失败: {str(e)}"
            )
            return Response(
                {"detail": f"设备连接失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DisconnectDeviceView(views.APIView):
    """断开设备连接（增强：断开前实时检测ADB状态并同步数据库）"""
    permission_classes = [AllowAny]  # 允许所有用户访问
    http_method_names = ['post']  # 只允许POST方法

    def post(self, request, pk):
        device = get_object_or_404(Device, pk=pk)

        # --- 增强：断开前实时检测ADB状态并同步数据库 ---
        try:
            adb_result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
            adb_lines = adb_result.stdout.strip().split('\n')[1:]
            adb_online_ids = set()
            for line in adb_lines:
                if not line.strip():
                    continue
                parts = line.split('\t')
                if len(parts) >= 2 and parts[1].strip() == 'device':
                    adb_online_ids.add(parts[0].strip())
            # 如果设备实际未连接但数据库为online，自动修正
            if device.device_id not in adb_online_ids and device.status == 'online':
                device.status = 'offline'
                device.save()
            # 如果设备实际已连接但数据库为offline，自动修正
            if device.device_id in adb_online_ids and device.status != 'online':
                device.status = 'online'
                device.last_online = timezone.now()
                device.save()
        except Exception as e:
            DeviceLog.objects.create(
                device=device,
                level='warning',
                message=f"断开前ADB检测异常: {str(e)}"
            )

        # 检查设备是否已断开（以数据库状态为准，已同步）
        if device.status == 'offline':
            return Response(
                {"detail": "设备已经处于断开状态"},
                status=status.HTTP_400_BAD_REQUEST
            )
        # 尝试断开设备连接
        try:
            # TODO: 这里可集成实际断开逻辑，如adb disconnect等，负责人: AI
            device.status = 'offline'
            device.save()
            DeviceLog.objects.create(
                device=device,
                level='info',
                message=f"设备 '{device.name}' 已断开连接"
            )
            return Response(
                {"detail": "设备已断开连接"},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            DeviceLog.objects.create(
                device=device,
                level='error',
                message=f"断开设备 '{device.name}' 连接失败: {str(e)}"
            )
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
    """扫描设备（集成：USB连接检查和设备状态扫描）"""
    permission_classes = [AllowAny]  # 允许所有用户访问
    http_method_names = ['post']  # 只允许POST方法

    def _process_device_from_cache(self, raw_device_id, cache_data):
        """从缓存中处理设备信息"""
        if ':' in raw_device_id:  # IP地址格式
            # 查找匹配IP的设备
            for device_id, info in cache_data.items():
                wireless = info.get('wireless_connection', {})
                if wireless and f"{wireless.get('ip')}:{wireless.get('port', 5555)}" == raw_device_id:
                    return {
                        'device_id': device_id,
                        'ip_address': raw_device_id,
                        'name': f"{info.get('model', '')} ({device_id})",
                        'brand': info.get('brand', ''),
                        'model': info.get('model', ''),
                        'android_version': info.get('android_version', '')
                    }
        else:  # 常规设备ID格式
            if raw_device_id in cache_data:
                info = cache_data[raw_device_id]
                wireless = info.get('wireless_connection', {})
                return {
                    'device_id': raw_device_id,
                    'ip_address': f"{wireless.get('ip')}:{wireless.get('port', 5555)}" if wireless else '',
                    'name': f"{info.get('model', '')} ({raw_device_id})",
                    'brand': info.get('brand', ''),
                    'model': info.get('model', ''),
                    'android_version': info.get('android_version', '')
                }
        return None

    def _enhance_device_info(self, device_info, device_status):
        """增强设备信息，填充缺失的品牌、型号信息"""
        if not device_enhancer:
            return device_info

        device_id = device_info.get('device_id', '')
        current_model = device_info.get('model', '')
        current_brand = device_info.get('brand', '')

        # 如果品牌或型号缺失，且设备在线，尝试通过ADB获取和增强
        if device_status == 'device' and (not current_brand or not current_model):
            try:
                enhanced_info = device_enhancer.enhance_device_info(
                    device_id, current_model, current_brand
                )

                # 更新设备信息
                if enhanced_info:
                    device_info.update({
                        'brand': enhanced_info.get('enhanced_brand', current_brand),
                        'model': enhanced_info.get('commercial_name', current_model) or current_model,
                        'name': enhanced_info.get('display_name', device_info.get('name', '')),
                        'series': enhanced_info.get('series', ''),
                        'category': enhanced_info.get('category', '')
                    })

            except Exception as e:
                print(f"设备信息增强失败 {device_id}: {e}")

        return device_info

    def _update_device_record(self, device_info, device_status):
        """创建或更新设备记录"""
        device, created = Device.objects.get_or_create(
            device_id=device_info['device_id'],
            defaults={
                'name': device_info.get('name', ''),
                'status': 'online' if device_status == 'device' else 'offline',
                'ip_address': device_info.get('ip_address', ''),
                'brand': device_info.get('brand', ''),
                'model': device_info.get('model', ''),
                'android_version': device_info.get('android_version', '')
            }
        )

        if not created:
            update_fields = []
            for field, value in [
                ('status', 'online' if device_status == 'device' else 'offline'),
                ('ip_address', device_info.get('ip_address', '')),
                ('brand', device_info.get('brand', '')),
                ('model', device_info.get('model', '')),
                ('android_version', device_info.get('android_version', ''))
            ]:
                if value and getattr(device, field) != value:
                    setattr(device, field, value)
                    update_fields.append(field)

            if update_fields and device_status == 'device':
                device.last_online = timezone.now()
                update_fields.append('last_online')
                device.save(update_fields=update_fields)

        return device, created

    def post(self, request):
        try:
            # 步骤1：先进行USB连接检查
            usb_check_result = self._perform_usb_check()

            # 步骤2：然后进行ADB设备扫描
            result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
            if result.returncode != 0:
                return Response(
                    {"detail": "扫描设备失败", "error": result.stderr},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # 从缓存文件加载设备信息
            cache_data = {}
            try:
                cache_file = os.path.join(settings.BASE_DIR, '..', 'device_preparation_cache.json')
                if os.path.exists(cache_file):
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
            except Exception as e:
                print(f"读取设备缓存文件失败: {e}")

            # 处理设备列表
            devices_found = []
            adb_ids = set()
            device_lines = result.stdout.strip().split('\n')[1:]  # 跳过第一行标题

            for line in device_lines:
                if not line.strip():
                    continue

                parts = line.split('\t')
                if len(parts) < 2:
                    continue

                raw_device_id = parts[0].strip()
                device_status = parts[1].strip()

                # 初始化设备信息
                device_info = {'status': 'online' if device_status == 'device' else 'offline'}                # 从缓存获取设备信息
                cached_info = self._process_device_from_cache(raw_device_id, cache_data)
                if cached_info:
                    device_info.update(cached_info)
                else:
                    # 使用基本信息
                    device_info.update({
                        'device_id': raw_device_id,
                        'name': f"Android设备 {raw_device_id}",
                        'ip_address': raw_device_id if ':' in raw_device_id else ''
                    })

                # 增强设备信息（填充缺失的品牌、型号等信息）
                device_info = self._enhance_device_info(device_info, device_status)

                # 更新数据库记录
                device, created = self._update_device_record(device_info, device_status)
                adb_ids.add(device_info['device_id'])

                # 获取USB检查信息
                usb_info = next((d for d in usb_check_result.get('devices', [])
                              if d.get('device_id') == device_info['device_id']), {})

                # 添加到结果列表
                devices_found.append({
                    'id': device.id,
                    'device_id': device.device_id,
                    'name': device.name,
                    'brand': getattr(device, 'brand', '') or '',
                    'model': getattr(device, 'model', '') or '',
                    'android_version': getattr(device, 'android_version', '') or '',
                    'occupied_personnel': getattr(device.current_user, 'username', '')
                            if hasattr(device, 'current_user') and device.current_user else '',
                    'status': device.status,
                    'created': created,
                    'connection_status': usb_info.get('connection_status', 'unknown'),
                    'authorization_status': usb_info.get('authorization_status', 'unknown'),
                    'usb_path': usb_info.get('usb_path', ''),
                    'ip_address': getattr(device, 'ip_address', '') or ''
                })

            # 将数据库中未在ADB列表的设备状态设为offline
            for db_device in Device.objects.all():
                if db_device.device_id not in adb_ids and db_device.status != 'offline':
                    db_device.status = 'offline'
                    db_device.save()
                    DeviceLog.objects.create(
                        device=db_device,
                        level='info',
                        message=f"扫描时自动将设备 '{db_device.name}' 状态设为离线"
                    )

            return Response({
                "detail": "扫描设备成功",
                "devices_found": devices_found,
                "usb_check_result": usb_check_result
            })
        except Exception as e:
            return Response(
                {"detail": "扫描设备失败", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    def _perform_usb_check(self):
        """执行USB连接检查"""
        try:
            # 尝试导入USB连接检查器
            scripts_path = os.path.join(settings.BASE_DIR, 'apps', 'scripts')
            if scripts_path not in sys.path:
                sys.path.append(scripts_path)

            result = None

            # 尝试所有检查方法
            checkers = [
                ('enhanced', lambda: self._check_with_enhanced_manager()),
                ('basic', lambda: self._check_with_usb_checker()),
                ('adb', lambda: self._check_with_adb())
            ]

            for name, checker in checkers:
                try:
                    result = checker()
                    if result:
                        result['check_method'] = name
                        break
                except Exception as checker_error:
                    print(f"{name} checker failed: {str(checker_error)}")
                    continue

            if not result:
                # 如果所有检查都失败，使用最基本的ADB检查
                result = self._check_with_adb()
                result['check_method'] = 'adb_fallback'

            return result

        except Exception as e:
            # 记录错误但不中断主流程
            print(f"USB检查错误: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'devices': [],
                'summary': {
                    'total_devices': 0,
                    'connected_devices': 0,
                    'authorized_devices': 0
                },
                'check_method': 'failed'
            }

    def _check_with_enhanced_manager(self):
        """使用增强版设备管理器检查"""
        try:
            from enhanced_device_preparation_manager import EnhancedDevicePreparationManager
            manager = EnhancedDevicePreparationManager()
            return manager.check_usb_connections()
        except Exception as e:
            raise Exception(f"Enhanced manager check failed: {str(e)}")

    def _check_with_usb_checker(self):
        """使用独立的USB检查器检查"""
        try:
            from usb_connection_checker import USBConnectionChecker
            checker = USBConnectionChecker()
            return checker.check_all_connections()
        except Exception as e:
            raise Exception(f"USB checker failed: {str(e)}")

    def _check_with_adb(self):
        """使用基础ADB命令检查"""
        try:
            adb_result = subprocess.run(
                ['adb', 'devices'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )

            if adb_result.returncode != 0:
                raise Exception(f"ADB command failed: {adb_result.stderr}")

            lines = adb_result.stdout.strip().split('\n')[1:]
            devices = []

            for line in lines:
                if not line.strip():
                    continue

                parts = line.split('\t')
                if len(parts) >= 2:                    devices.append({
                        'device_id': parts[0].strip(),
                        'connection_status': 'connected' if parts[1].strip() == 'device' else 'disconnected',
                        'authorization_status': 'authorized' if parts[1].strip() == 'device' else 'unauthorized'
                    })
            return {
                'success': True,
                'devices': devices,
                'summary': {
                    'total_devices': len(devices),
                    'connected_devices': len([d for d in devices if d['connection_status'] == 'connected']),
                    'authorized_devices': len([d for d in devices if d['authorization_status'] == 'authorized'])
                }
            }
        except Exception as e:
            raise Exception(f"ADB check failed: {str(e)}")


class USBConnectionCheckView(views.APIView):
    """USB连接检查API"""
    permission_classes = [AllowAny]
    http_method_names = ['post']

    def post(self, request):
        try:
            # Import the USB connection checker
            scripts_path = os.path.join(settings.BASE_DIR, 'apps', 'scripts')
            if scripts_path not in sys.path:
                sys.path.append(scripts_path)
                # Try to import and run USB connection check
            try:
                from usb_connection_checker import USBConnectionChecker
                checker = USBConnectionChecker()
                result = checker.check_all_connections()
            except ImportError:
                # Fallback to basic ADB scan if USB checker not available
                adb_result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
                if adb_result.returncode != 0:
                    raise Exception(f"ADB command failed: {adb_result.stderr}")

                lines = adb_result.stdout.strip().split('\n')[1:]
                devices = []
                for line in lines:
                    if line.strip():
                        parts = line.split('\t')
                        if len(parts) >= 2:
                            devices.append({
                                'device_id': parts[0].strip(),
                                'connection_status': 'connected' if parts[1].strip() == 'device' else 'disconnected',
                                'authorization_status': 'authorized' if parts[1].strip() == 'device' else 'unauthorized'
                            })

                result = {
                    'summary': {
                        'total_devices': len(devices),
                        'connected_devices': len([d for d in devices if d['connection_status'] == 'connected']),
                        'authorized_devices': len([d for d in devices if d['authorization_status'] == 'authorized'])
                    },
                    'devices': devices
                }

            # Update device statuses in database based on check results
            devices_updated = 0
            for device_info in result.get('devices', []):
                device_id = device_info.get('device_id')
                connection_status = device_info.get('connection_status', 'unknown')
                auth_status = device_info.get('authorization_status', 'unknown')

                try:
                    device = Device.objects.get(device_id=device_id)
                    old_status = device.status

                    # Update device status based on connection and authorization
                    if connection_status == 'connected' and auth_status == 'authorized':
                        device.status = 'online'
                        device.last_online = timezone.now()
                    elif connection_status == 'connected' and auth_status == 'unauthorized':
                        device.status = 'offline'  # Connected but not authorized
                    else:
                        device.status = 'offline'  # Not connected

                    # Save changes and create log if status changed
                    if device.status != old_status:
                        device.save()
                        devices_updated += 1

                        DeviceLog.objects.create(
                            device=device,
                            level='info',
                            message=f"USB检查更新设备状态: {old_status} -> {device.status}"
                        )

                except Device.DoesNotExist:
                    # Device not in database, could be a new device
                    continue
                except Exception as update_error:
                    print(f"更新设备 {device_id} 状态失败: {str(update_error)}")

            return Response({
                'success': True,
                'message': f'USB连接检查完成，更新了{devices_updated}台设备状态',
                'usb_check_result': result,
                'devices_updated': devices_updated
            })

        except Exception as e:
            return Response({
                'success': False,
                'message': f'USB连接检查失败: {str(e)}',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EnhancedDeviceReportView(views.APIView):
    """增强设备报告API"""
    permission_classes = [AllowAny]
    http_method_names = ['post']

    def post(self, request, pk=None):
        try:
            # Import the enhanced device preparation manager
            scripts_path = os.path.join(settings.BASE_DIR, 'apps', 'scripts')
            if scripts_path not in sys.path:
                sys.path.append(scripts_path)

            try:
                from enhanced_device_preparation_manager import EnhancedDevicePreparationManager
                manager = EnhancedDevicePreparationManager()
            except ImportError:
                # Fallback to basic device info if enhanced manager not available
                return Response({
                    'success': False,
                    'message': '增强设备管理模块未找到，请确保已正确安装',
                    'error_type': 'module_not_found'
                }, status=status.HTTP_404_NOT_FOUND)

            if pk:
                # Generate report for specific device
                device = get_object_or_404(Device, pk=pk)

                # Run comprehensive test for the specific device
                try:
                    report = manager.run_comprehensive_device_test(device.device_id)
                except Exception as test_error:
                    # Create basic report on test failure
                    report = {
                        'timestamp': timezone.now().isoformat(),
                        'device_tests': {
                            device.device_id: {
                                'overall_status': 'error',
                                'error_message': str(test_error)
                            }
                        }
                    }

                # Update device information in database
                if report and 'device_tests' in report:
                    device_test = report['device_tests'].get(device.device_id, {})

                    # Update device status based on test results
                    if device_test.get('overall_status') == 'healthy':
                        device.status = 'online'
                        device.last_online = timezone.now()
                    elif device_test.get('overall_status') in ['issues', 'error']:
                        device.status = 'offline'

                    device.save()

                    # Create device log entry
                    DeviceLog.objects.create(
                        device=device,
                        level='info' if device_test.get('overall_status') == 'healthy' else 'warning',
                        message=f"增强设备报告生成完成，状态: {device_test.get('overall_status', 'unknown')}"
                    )

                return Response({
                    'success': True,
                    'message': f'设备 {device.name} 的增强报告生成完成',
                    'data': report,
                    'device_id': device.device_id
                })
            else:
                # Generate report for all devices
                try:
                    report = manager.run_comprehensive_device_test()
                except Exception as test_error:
                    return Response({
                        'success': False,
                        'message': f'全设备测试失败: {str(test_error)}',
                        'error_type': 'test_failure'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                # Update all devices based on test results
                devices_updated = 0
                if report and 'device_tests' in report:
                    for device_id, device_test in report['device_tests'].items():
                        try:
                            device = Device.objects.get(device_id=device_id)
                            old_status = device.status

                            if device_test.get('overall_status') == 'healthy':
                                device.status = 'online'
                                device.last_online = timezone.now()
                            elif device_test.get('overall_status') in ['issues', 'error']:
                                device.status = 'offline'

                            device.save()
                            devices_updated += 1

                            # Create device log entry
                            DeviceLog.objects.create(
                                device=device,
                                level='info' if device_test.get('overall_status') == 'healthy' else 'warning',
                                message=f"增强设备报告更新: {old_status} -> {device.status}"
                            )
                        except Device.DoesNotExist:
                            continue
                        except Exception as update_error:
                            print(f"更新设备 {device_id} 状态失败: {str(update_error)}")

                return Response({
                    'success': True,
                    'message': f'增强设备报告生成完成，更新了{devices_updated}台设备状态',
                    'data': report,
                    'devices_updated': devices_updated
                })

        except Exception as e:
            return Response({
                'success': False,
                'message': f'增强设备报告生成失败: {str(e)}',
                'error_type': 'general_error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)