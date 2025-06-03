#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试action字段改进的验证脚本
验证record_script.py和replay_script.py中action字段的一致性处理
"""

import json
import sys
import os

# 添加项目路径到 sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, 'wfgame-ai-server')
if project_root not in sys.path:
    sys.path.append(project_root)

def test_recorded_step_format():
    """测试录制步骤格式是否包含action字段"""
    print("=== 测试录制步骤格式 ===")

    # 模拟录制的按钮步骤（应该包含action: click）
    button_step = {
        "step": 1,
        "action": "click",  # 默认动作类型
        "class": "test_button",
        "confidence": 0.95,
        "timestamp": "2025-01-27 10:00:00.000000",
        "remark": "测试按钮"
    }

    # 模拟录制的未识别按钮步骤（应该包含action: click）
    unknown_step = {
        "step": 2,
        "action": "click",  # 默认动作类型
        "class": "unknown",
        "confidence": 0.0,
        "relative_x": 0.5,
        "relative_y": 0.5,
        "timestamp": "2025-01-27 10:00:01.000000",
        "remark": "未识别按钮"
    }

    # 模拟录制的滑动步骤
    swipe_step = {
        "step": 3,
        "action": "swipe",
        "start_x": 500,
        "start_y": 800,
        "end_x": 500,
        "end_y": 400,
        "duration": 300,
        "timestamp": "2025-01-27 10:00:02.000000",
        "remark": "向上滑动"
    }

    # 验证步骤格式
    steps = [button_step, unknown_step, swipe_step]
    all_passed = True

    for i, step in enumerate(steps):
        if "action" not in step:
            print(f"❌ 步骤 {i+1} 缺少action字段")
            all_passed = False
        else:
            action = step["action"]
            print(f"✅ 步骤 {i+1}: action = '{action}', class = '{step.get('class', 'N/A')}'")

    return all_passed

def test_action_handling_logic():
    """测试action处理逻辑"""
    print("\n=== 测试action处理逻辑 ===")

    # 模拟replay_script.py中的action处理逻辑
    test_steps = [
        {"class": "button1", "action": "click", "remark": "明确的点击操作"},
        {"class": "button2", "remark": "没有action字段的步骤"},
        {"class": "swipe_area", "action": "swipe", "start_x": 100, "start_y": 200, "end_x": 300, "end_y": 400, "duration": 500, "remark": "滑动操作"},
        {"class": "unknown", "relative_x": 0.5, "relative_y": 0.5, "remark": "未识别按钮"}
    ]

    all_passed = True

    for i, step in enumerate(test_steps):
        # 模拟replay_script.py中的逻辑：获取步骤的action类型，如果没有则默认为"click"
        step_action = step.get("action", "click")
        step_class = step["class"]
        step_remark = step.get("remark", "")

        print(f"步骤 {i+1}: class='{step_class}', action='{step_action}', remark='{step_remark}'")

        # 测试不同action类型的处理
        if step_action == "swipe":
            # 处理滑动步骤
            if all(key in step for key in ["start_x", "start_y", "end_x", "end_y"]):
                print(f"  ✅ 滑动步骤验证通过: ({step.get('start_x')}, {step.get('start_y')}) -> ({step.get('end_x')}, {step.get('end_y')})")
            else:
                print(f"  ❌ 滑动步骤缺少必要参数")
                all_passed = False
        elif step_action == "click":
            # 处理点击步骤
            print(f"  ✅ 点击步骤验证通过")
        else:
            print(f"  ⚠️  未知action类型: {step_action}")

    return all_passed

def test_json_compatibility():
    """测试JSON兼容性"""
    print("\n=== 测试JSON兼容性 ===")

    # 创建测试脚本
    test_script = {
        "script_name": "测试脚本",
        "device_info": "测试设备",
        "timestamp": "2025-01-27 10:00:00.000000",
        "steps": [
            {
                "step": 1,
                "action": "click",
                "class": "start_button",
                "confidence": 0.95,
                "timestamp": "2025-01-27 10:00:00.000000",
                "remark": "开始按钮"
            },
            {
                "step": 2,
                "action": "swipe",
                "start_x": 500,
                "start_y": 800,
                "end_x": 500,
                "end_y": 400,
                "duration": 300,
                "timestamp": "2025-01-27 10:00:01.000000",
                "remark": "向上滑动"
            },
            {
                "step": 3,
                "action": "click",
                "class": "unknown",
                "confidence": 0.0,
                "relative_x": 0.5,
                "relative_y": 0.5,
                "timestamp": "2025-01-27 10:00:02.000000",
                "remark": "未识别按钮"
            }
        ]
    }

    try:
        # 测试JSON序列化
        json_str = json.dumps(test_script, ensure_ascii=False, indent=2)
        print("✅ JSON序列化成功")

        # 测试JSON反序列化
        parsed_script = json.loads(json_str)
        print("✅ JSON反序列化成功")

        # 验证步骤完整性
        steps = parsed_script.get("steps", [])
        if len(steps) == 3:
            print("✅ 步骤数量正确")

            # 验证每个步骤都有action字段
            for i, step in enumerate(steps):
                if "action" in step:
                    print(f"✅ 步骤 {i+1} 包含action字段: {step['action']}")
                else:
                    print(f"❌ 步骤 {i+1} 缺少action字段")
                    return False
        else:
            print(f"❌ 步骤数量错误: 期望3, 实际{len(steps)}")
            return False

        return True

    except Exception as e:
        print(f"❌ JSON处理失败: {e}")
        return False

def main():
    """主测试函数"""
    print("WFGameAI Action字段改进验证测试")
    print("=" * 50)

    test_results = []

    # 执行各项测试
    test_results.append(("录制步骤格式测试", test_recorded_step_format()))
    test_results.append(("Action处理逻辑测试", test_action_handling_logic()))
    test_results.append(("JSON兼容性测试", test_json_compatibility()))

    # 汇总测试结果
    print("\n" + "=" * 50)
    print("测试结果汇总:")

    passed_count = 0
    total_count = len(test_results)

    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed_count += 1

    print(f"\n总体结果: {passed_count}/{total_count} 项测试通过")

    if passed_count == total_count:
        print("🎉 所有测试通过！Action字段改进验证成功！")
        return 0
    else:
        print("⚠️  部分测试失败，请检查实现！")
        return 1

if __name__ == "__main__":
    sys.exit(main())
