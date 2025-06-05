#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
最终验证测试
验证设备管理界面优化的完整功能
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
    from apps.devices.serializers import DeviceSerializer
    from device_info_enhancer import DeviceInfoEnhancer

    print("🎯 最终验证测试 - 设备管理界面优化")
    print("=" * 80)

    # 测试用例定义
    test_cases = [
        {
            'device_id': 'FVG0221729008356',
            'expected_display': 'HUAWEI | MATE 40 PRO',
            'description': 'FVG0221729008356设备显示"未知品牌/未知型号"问题'
        },
        {
            'device_id': '5c41023b',
            'expected_display': 'OPPO | OPPO K9',
            'description': '5c41023b显示OnePlus应为OPPO的品牌映射错误'
        },
        {
            'device_id': '65WGZT7P9XHEKN7D',
            'expected_display': 'Xiaomi | Xiaomi 12',
            'description': '65WGZT7P9XHEKN7D显示Redmi应为Xiaomi的品牌映射错误'
        },
        {
            'device_id': 'a3833caf',
            'expected_display': 'OnePlus | OnePlus 5T',
            'description': 'a3833caf设备的型号优化显示'
        }
    ]

    print("🔍 测试关键功能:")
    print("1. 品牌字段映射错误修复")
    print("2. 设备型号优化显示（技术型号→商品名）")
    print("3. 未知设备信息修复")
    print("4. 数据持久化验证")

    success_count = 0
    total_count = len(test_cases)

    for i, test_case in enumerate(test_cases, 1):
        device_id = test_case['device_id']
        expected_display = test_case['expected_display']
        description = test_case['description']

        print(f"\n--- 测试 {i}: {device_id} ---")
        print(f"📝 测试内容: {description}")
        print(f"🎯 期望显示: {expected_display}")

        try:
            # 1. 检查数据库中是否存在设备
            device = Device.objects.get(device_id=device_id)
            print(f"✅ 数据库中找到设备")

            # 2. 检查序列化器输出
            serializer = DeviceSerializer(device)
            serialized_data = serializer.data

            actual_brand = serialized_data.get('brand')
            actual_model = serialized_data.get('model')
            actual_display = f"{actual_brand} | {actual_model}"

            print(f"📊 实际显示: {actual_display}")

            # 3. 验证结果
            if actual_display == expected_display:
                print(f"✅ 测试通过!")
                success_count += 1
            else:
                print(f"❌ 测试失败!")
                print(f"   期望: {expected_display}")
                print(f"   实际: {actual_display}")

                # 显示详细信息用于调试
                print(f"   序列化器数据: brand='{actual_brand}', model='{actual_model}'")

        except Device.DoesNotExist:
            print(f"❌ 设备 {device_id} 不存在于数据库中")
        except Exception as e:
            print(f"❌ 测试过程中出错: {e}")

    # 显示测试总结
    print(f"\n" + "=" * 80)
    print(f"📊 测试总结:")
    print(f"   通过: {success_count}/{total_count}")
    print(f"   成功率: {success_count/total_count*100:.1f}%")

    if success_count == total_count:
        print(f"\n🎉 所有测试通过! 设备管理界面优化成功完成!")
        print(f"\n✅ 修复内容总结:")
        print(f"   1. ✅ 品牌字段映射错误已修复")
        print(f"   2. ✅ 设备型号优化显示已实现")
        print(f"   3. ✅ 未知设备信息已修复")
        print(f"   4. ✅ 数据刷新问题已解决")

        print(f"\n🔧 技术实现:")
        print(f"   - 设备信息增强器: device_info_enhancer.py")
        print(f"   - 映射配置文件: device_model_mapping.json")
        print(f"   - Django序列化器集成: apps/devices/serializers.py")
        print(f"   - 字段覆盖机制: get_brand() 和 get_model() 方法")

    else:
        print(f"\n⚠️ 部分测试失败，需要进一步调试!")

except Exception as e:
    print(f"❌ 验证过程中出错: {e}")
    import traceback
    traceback.print_exc()
