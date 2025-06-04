#!/usr/bin/env python3
"""
同步设备缓存数据到数据库的脚本
"""
import os
import sys
import json
import django

# 设置Django环境
sys.path.append(os.path.join(os.path.dirname(__file__), 'wfgame-ai-server'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wfgame_ai_server_main.settings')
django.setup()

from apps.devices.models import Device

def sync_device_cache_to_db():
    """从设备缓存文件同步数据到数据库"""
    cache_file = 'device_preparation_cache.json'

    if not os.path.exists(cache_file):
        print(f"缓存文件 {cache_file} 不存在")
        return

    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)

        print(f"从缓存文件加载了 {len(cache_data)} 台设备数据")

        updated_count = 0
        for device_id, info in cache_data.items():
            try:
                # 查找设备（按device_id或IP地址查找）
                device = None

                # 首先尝试按device_id查找
                try:
                    device = Device.objects.get(device_id=device_id)
                except Device.DoesNotExist:
                    # 如果按device_id找不到，尝试按IP地址查找
                    wireless_info = info.get('wireless_connection', {})
                    if wireless_info:
                        ip_port = f"{wireless_info.get('ip', '')}:{wireless_info.get('port', 5555)}"
                        try:
                            device = Device.objects.get(device_id=ip_port)
                            # 如果找到了按IP地址存储的设备，更新其device_id为真实的ID
                            print(f"找到按IP地址存储的设备，将 {ip_port} 更新为 {device_id}")
                            device.device_id = device_id
                        except Device.DoesNotExist:
                            pass

                if device:
                    # 更新设备信息
                    old_name = device.name
                    old_brand = device.brand
                    old_model = device.model
                    old_android_version = device.android_version
                    old_ip_address = device.ip_address

                    # 从缓存获取品牌信息（如果有的话）
                    model_info = info.get('model', '')
                    brand = ''
                    model = model_info

                    # 尝试从model字段提取品牌信息
                    if model_info:
                        if 'OnePlus' in model_info or 'ONEPLUS' in model_info:
                            brand = 'OnePlus'
                            model = model_info.replace('ONEPLUS ', '').strip()
                        elif 'JAD-AL00' in model_info:
                            brand = 'Honor'
                        elif 'V2244A' in model_info:
                            brand = 'vivo'
                        elif '22041216C' in model_info:
                            brand = 'Xiaomi'
                        else:
                            brand = model_info.split(' ')[0] if ' ' in model_info else ''

                    device.name = f"{brand} {model}".strip() if brand and model else (model or device_id)
                    device.brand = brand
                    device.model = model
                    device.android_version = info.get('android_version', '')

                    # 设置IP地址
                    wireless_info = info.get('wireless_connection', {})
                    if wireless_info and wireless_info.get('ip'):
                        device.ip_address = f"{wireless_info['ip']}:{wireless_info.get('port', 5555)}"

                    device.save()
                    updated_count += 1

                    print(f"更新设备 {device_id}:")
                    print(f"  name: '{old_name}' -> '{device.name}'")
                    print(f"  brand: '{old_brand}' -> '{device.brand}'")
                    print(f"  model: '{old_model}' -> '{device.model}'")
                    print(f"  android_version: '{old_android_version}' -> '{device.android_version}'")
                    print(f"  ip_address: '{old_ip_address}' -> '{device.ip_address}'")
                    print()
                else:
                    print(f"未找到设备 {device_id} 在数据库中")

            except Exception as e:
                print(f"更新设备 {device_id} 时出错: {e}")

        print(f"成功更新了 {updated_count} 台设备的信息")

    except Exception as e:
        print(f"同步缓存数据时出错: {e}")

if __name__ == "__main__":
    sync_device_cache_to_db()
