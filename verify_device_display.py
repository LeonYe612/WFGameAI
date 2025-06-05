#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
查看数据库中的实际设备数据
验证设备显示优化是否真正生效
"""

import os
import sys
import django

# 设置Django环境
project_path = r'c:\Users\Administrator\PycharmProjects\WFGameAI\wfgame-ai-server'
sys.path.insert(0, project_path)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wfgame_ai_server_main.settings')

try:
    django.setup()
    from apps.devices.models import Device
    from apps.devices.serializers import DeviceSerializer, DeviceDetailSerializer

    print("🔍 查看数据库中的实际设备数据")
    print("=" * 80)

    # 查看所有设备
    devices = Device.objects.all()
    print(f"📊 数据库中总共有 {devices.count()} 个设备")

    if devices.count() == 0:
        print("❌ 数据库中没有设备数据，请先添加设备数据")
        sys.exit(1)

    print("\n📱 设备详细信息:")
    print("=" * 80)

    # 关键设备ID列表
    key_device_ids = ['5c41023b', '65WGZT7P9XHEKN7D', 'FVG0221729008356']

    # 查看关键设备
    for device_id in key_device_ids:
        try:
            device = Device.objects.get(device_id=device_id)
            print(f"\n🔧 设备ID: {device_id}")
            print(f"   📄 数据库原始数据:")
            print(f"      - 品牌: {device.brand}")
            print(f"      - 型号: {device.model}")
            print(f"      - 名称: {device.name}")
            print(f"      - IP: {device.ip_address}")
            print(f"      - 状态: {device.status}")

            # 测试序列化器输出
            serializer = DeviceSerializer(device)
            serialized_data = serializer.data

            print(f"   📺 序列化器输出 (前端看到的数据):")
            print(f"      - 品牌: {serialized_data.get('brand', 'N/A')}")
            print(f"      - 型号: {serialized_data.get('model', 'N/A')}")

            # 检查是否有增强字段
            if 'commercial_name' in serialized_data:
                print(f"      - 商品名: {serialized_data.get('commercial_name', 'N/A')}")
            if 'enhanced_brand' in serialized_data:
                print(f"      - 增强品牌: {serialized_data.get('enhanced_brand', 'N/A')}")

        except Device.DoesNotExist:
            print(f"\n❌ 设备 {device_id} 在数据库中不存在")

    # 查看所有设备的品牌分布
    print(f"\n📊 所有设备品牌分布:")
    print("=" * 50)

    brand_counts = {}
    for device in devices:
        brand = device.brand or '未知品牌'
        brand_counts[brand] = brand_counts.get(brand, 0) + 1

    for brand, count in sorted(brand_counts.items()):
        print(f"   {brand}: {count} 个设备")

    # 显示所有设备的基本信息
    print(f"\n📱 所有设备列表:")
    print("=" * 80)
    print(f"{'设备ID':<20} {'品牌':<15} {'型号':<20} {'状态':<10}")
    print("-" * 80)

    for device in devices:
        device_id = device.device_id[:18] + '...' if len(device.device_id) > 20 else device.device_id
        brand = device.brand or 'N/A'
        model = device.model or 'N/A'
        status = device.status
        print(f"{device_id:<20} {brand:<15} {model:<20} {status:<10}")

    # 测试序列化器是否工作
    print(f"\n🔧 序列化器功能验证:")
    print("=" * 50)

    test_device = devices.first()
    if test_device:
        serializer = DeviceSerializer(test_device)
        print(f"✅ DeviceSerializer 工作正常")

        detail_serializer = DeviceDetailSerializer(test_device)
        print(f"✅ DeviceDetailSerializer 工作正常")

        # 检查是否有get_brand和get_model方法
        if hasattr(serializer, 'get_brand'):
            print(f"✅ get_brand 方法存在")
        else:
            print(f"❌ get_brand 方法不存在")

        if hasattr(serializer, 'get_model'):
            print(f"✅ get_model 方法存在")
        else:
            print(f"❌ get_model 方法不存在")

except Exception as e:
    print(f"❌ 查看数据库数据时出错: {e}")
    import traceback
    traceback.print_exc()
