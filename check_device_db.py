#!/usr/bin/env python3
"""
检查数据库中设备信息的当前状态
"""

import os
import sys
import django

# 设置Django环境
sys.path.append('c:\\Users\\Administrator\\PycharmProjects\\WFGameAI\\wfgame-ai-server')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wfgame_ai_server_main.settings')
django.setup()

from apps.devices.models import Device

def check_database_devices():
    """检查数据库中的设备信息"""
    print("=== 检查数据库中的设备信息 ===")

    # 获取所有设备
    devices = Device.objects.all()
    print(f"数据库中总共有 {devices.count()} 个设备")

    # 检查关键设备
    test_device_ids = ['5c41023b', 'FVG0221729008356', '65WGZT7P9XHEKN7D']

    for device_id in test_device_ids:
        try:
            device = Device.objects.get(device_id=device_id)
            print(f"\n设备 {device_id}:")
            print(f"  品牌: {device.brand}")
            print(f"  型号: {device.model}")
            print(f"  名称: {device.name}")
            print(f"  状态: {device.status}")
            print(f"  更新时间: {device.updated_at}")

            # 验证修复结果
            if device_id == '5c41023b':
                if device.brand == 'OPPO' and 'K9' in device.model:
                    print(f"  ✅ 5c41023b 数据库记录正确")
                else:
                    print(f"  ❌ 5c41023b 数据库记录需要修复")

            elif device_id == 'FVG0221729008356':
                if 'MATE 40 PRO' in device.model:
                    print(f"  ✅ FVG0221729008356 数据库记录正确")
                else:
                    print(f"  ❌ FVG0221729008356 数据库记录需要修复")

            elif device_id == '65WGZT7P9XHEKN7D':
                if device.brand == 'Xiaomi':
                    print(f"  ✅ 65WGZT7P9XHEKN7D 数据库记录正确")
                else:
                    print(f"  ❌ 65WGZT7P9XHEKN7D 数据库记录需要修复")

        except Device.DoesNotExist:
            print(f"\n设备 {device_id}: 在数据库中不存在")

if __name__ == "__main__":
    check_database_devices()
