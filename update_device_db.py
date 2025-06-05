#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
更新数据库中的设备信息
根据设备信息增强器的映射规则更新数据库中的品牌和型号字段
"""

import os
import sys
import django

# 设置Django环境
project_path = r'c:\Users\Administrator\PycharmProjects\WFGameAI\wfgame-ai-server'
sys.path.insert(0, project_path)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wfgame_ai_server_main.settings')

# 添加项目根路径以导入设备信息增强器
root_path = r'c:\Users\Administrator\PycharmProjects\WFGameAI'
sys.path.insert(0, root_path)

try:
    django.setup()
    from apps.devices.models import Device
    from device_info_enhancer import DeviceInfoEnhancer

    print("🔄 开始更新数据库中的设备信息")
    print("=" * 80)

    # 初始化设备信息增强器
    enhancer = DeviceInfoEnhancer()

    # 获取所有设备
    devices = Device.objects.all()
    print(f"📊 找到 {devices.count()} 个设备需要检查")

    updated_count = 0

    for device in devices:
        print(f"\n🔧 检查设备: {device.device_id}")
        print(f"   当前品牌: {device.brand}")
        print(f"   当前型号: {device.model}")

        # 获取原始数据用于增强
        original_brand = device.brand
        original_model = device.model

        # 从缓存中获取设备信息（如果没有原始信息）
        if not original_brand or not original_model:
            cached_info = enhancer._get_cached_device_info(device.device_id)
            if cached_info:
                original_brand = cached_info.get('brand', original_brand)
                original_model = cached_info.get('model', original_model)
                print(f"   从缓存获取: {original_brand} | {original_model}")

        # 获取增强的设备信息
        try:
            enhanced_info = enhancer.enhance_device_info(
                device.device_id,
                original_model or device.model,
                original_brand or device.brand
            )

            # 检查是否需要更新
            new_brand = enhanced_info.get('enhanced_brand', device.brand)
            new_model = enhanced_info.get('commercial_name', device.model)

            needs_update = False

            # 检查品牌是否需要更新
            if device.brand != new_brand:
                print(f"   🔄 品牌需要更新: {device.brand} → {new_brand}")
                device.brand = new_brand
                needs_update = True

            # 检查型号是否需要更新
            if device.model != new_model:
                print(f"   🔄 型号需要更新: {device.model} → {new_model}")
                device.model = new_model
                needs_update = True

            # 保存更新
            if needs_update:
                device.save()
                updated_count += 1
                print(f"   ✅ 设备信息已更新")
            else:
                print(f"   ✅ 设备信息已是最新")

        except Exception as e:
            print(f"   ❌ 更新设备信息失败: {e}")

    print(f"\n" + "=" * 80)
    print(f"📊 更新完成统计:")
    print(f"   总设备数: {devices.count()}")
    print(f"   更新设备数: {updated_count}")
    print(f"   未更新设备数: {devices.count() - updated_count}")

    if updated_count > 0:
        print(f"\n🎉 已成功更新 {updated_count} 个设备的信息！")
    else:
        print(f"\n✅ 所有设备信息都已是最新状态")

    # 再次验证更新结果
    print(f"\n🔍 验证更新结果:")
    print("=" * 50)

    for device in Device.objects.all():
        print(f"   {device.device_id}: {device.brand} | {device.model}")

except Exception as e:
    print(f"❌ 更新数据库时出错: {e}")
    import traceback
    traceback.print_exc()
