"""扫描视图的临时文件，用于检查格式"""
from django.utils import timezone
from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
import subprocess
import json
import os
from django.conf import settings

class ScanDevicesView(views.APIView):
    """扫描设备（集成：USB连接检查和设备状态扫描）"""
    permission_classes = [AllowAny]
    http_method_names = ['post']

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

            lines = result.stdout.strip().split('\n')
            device_lines = lines[1:]  # 跳过第一行的"List of devices attached"
            devices_found = []
            adb_ids = set()

            # 读取设备缓存文件
            cache_data = {}
            try:
                cache_file = os.path.join(settings.BASE_DIR, '..', 'device_preparation_cache.json')
                if os.path.exists(cache_file):
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
            except Exception as e:
                print(f"读取设备缓存文件失败: {e}")

            for line in device_lines:
                if not line.strip():
                    continue

                parts = line.split('\t')
                if len(parts) >= 2:
                    raw_device_id = parts[0].strip()
                    device_status = parts[1].strip()

                    # 处理设备ID和IP地址
                    device_id = raw_device_id
                    ip_address = ''

                    if ':' in raw_device_id:  # IP地址格式（如 172.20.19.147:5555）
                        ip_address = raw_device_id
                        # 从缓存中查找真实设备ID
                        for cached_id, info in cache_data.items():
                            wireless = info.get('wireless_connection', {})
                            if wireless and f"{wireless.get('ip')}:{wireless.get('port', 5555)}" == raw_device_id:
                                device_id = cached_id
                                break
                    else:  # 正常设备ID格式
                        # 从缓存中查找IP地址
                        if device_id in cache_data:
                            wireless = cache_data[device_id].get('wireless_connection', {})
                            if wireless:
                                ip_address = f"{wireless.get('ip')}:{wireless.get('port', 5555)}"

                    adb_ids.add(device_id)

                    # 从缓存获取设备详细信息
                    device_info = cache_data.get(device_id, {})
                    model = device_info.get('model', '')
                    android_version = device_info.get('android_version', '')

                    # 根据型号推断品牌
                    brand = ''
                    if model:
                        if 'OnePlus' in model or 'ONEPLUS' in model:
                            brand = 'OnePlus'
                            model = model.replace('ONEPLUS ', '').strip()
                        elif 'JAD-AL00' in model:
                            brand = 'Honor'
                        elif 'V2244A' in model:
                            brand = 'vivo'
                        elif '22041216C' in model:
                            brand = 'Xiaomi'
                        else:
                            brand = model.split(' ')[0] if ' ' in model else ''

                    # 获取或创建设备记录
                    device, created = Device.objects.get_or_create(
                        device_id=device_id,
                        defaults={
                            'name': f"{brand} {model}".strip() if brand and model else device_id,
                            'brand': brand,
                            'model': model,
                            'android_version': android_version,
                            'status': 'online' if device_status == 'device' else 'offline',
                            'ip_address': ip_address
                        }
                    )

                    # 如果设备已存在，更新信息
                    if not created:
                        update_fields = []
                        if device.brand != brand:
                            device.brand = brand
                            update_fields.append('brand')
                        if device.model != model:
                            device.model = model
                            update_fields.append('model')
                        if device.android_version != android_version:
                            device.android_version = android_version
                            update_fields.append('android_version')
                        if device.ip_address != ip_address:
                            device.ip_address = ip_address
                            update_fields.append('ip_address')
                        if device.name != (f"{brand} {model}".strip() if brand and model else device_id):
                            device.name = f"{brand} {model}".strip() if brand and model else device_id
                            update_fields.append('name')
                        if device.status != ('online' if device_status == 'device' else 'offline'):
                            device.status = 'online' if device_status == 'device' else 'offline'
                            update_fields.append('status')
                            if device.status == 'online':
                                device.last_online = timezone.now()
                                update_fields.append('last_online')

                        if update_fields:
                            device.save(update_fields=update_fields)

                    # 查找USB检查结果中的额外信息
                    usb_info = {}
                    for usb_device in usb_check_result.get('devices', []):
                        if usb_device.get('device_id') == device_id:
                            usb_info = usb_device
                            break

                    # 添加到设备列表
                    devices_found.append({
                        'id': device.id,
                        'device_id': device.device_id,
                        'name': device.name,
                        'brand': device.brand,
                        'model': device.model,
                        'android_version': device.android_version,
                        'occupied_personnel': getattr(device.current_user, 'username', '') if device.current_user else '',
                        'status': device.status,
                        'created': created,
                        'connection_status': usb_info.get('connection_status', 'unknown'),
                        'authorization_status': usb_info.get('authorization_status', 'unknown'),
                        'usb_path': usb_info.get('usb_path', ''),
                        'ip_address': device.ip_address
                    })

            # 将未连接的设备设为离线
            Device.objects.filter(status='online').exclude(device_id__in=adb_ids).update(
                status='offline'
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
