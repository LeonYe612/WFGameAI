#!/usr/bin/env python3
"""
Priority检测流程调试脚本
用于诊断为什么AI检测到了目标但Priority系统执行了fallback
"""

import json
import cv2
import numpy as np
import time
from ultralytics import YOLO

def simulate_detection_flow():
    """模拟检测流程，验证数据传递问题"""

    # 1. 加载分析数据
    with open("wfgame-ai-server/apps/scripts/analysis_data_5c41023b_20250606_153152.json", "r", encoding="utf-8") as f:
        analysis_data = json.load(f)

    print("=== 分析数据验证 ===")
    print(f"设备ID: {analysis_data['device_id']}")
    print(f"总检测数: {analysis_data['total_detections']}")

    # 查找navigation-fight检测结果
    nav_fight_detections = [d for d in analysis_data['detections'] if d['class_name'] == 'navigation-fight']

    if nav_fight_detections:
        detection = nav_fight_detections[0]
        print(f"✅ 找到navigation-fight检测:")
        print(f"   置信度: {detection['confidence']:.4f}")
        print(f"   边界框: {detection['bbox']}")

        # 计算中心点坐标
        bbox = detection['bbox']
        center_x = (bbox[0] + bbox[2]) / 2
        center_y = (bbox[1] + bbox[3]) / 2
        print(f"   中心坐标: ({center_x:.1f}, {center_y:.1f})")

    else:
        print("❌ 未找到navigation-fight检测结果")
        return

    print("\n=== 模拟detect_buttons函数 ===")

    # 2. 模拟detect_buttons函数的返回值
    def mock_detect_buttons(target_class):
        """模拟detect_buttons函数"""
        if target_class == "navigation-fight":
            # 返回格式: (success, (x, y, detected_class))
            return True, (center_x, center_y, "navigation-fight")
        else:
            return False, (None, None, None)

    # 测试检测函数
    success, coords = mock_detect_buttons("navigation-fight")
    print(f"detect_buttons返回: success={success}, coords={coords}")

    print("\n=== 模拟检测服务 ===")

    # 3. 模拟检测服务的处理
    # 检测服务中的代码: click_queue.put((success, coords))
    queue_data = (success, coords)
    print(f"放入队列的数据: {queue_data}")

    print("\n=== 模拟主循环接收 ===")

    # 4. 模拟主循环的接收
    try:
        # 主循环中的代码: success, (x, y, detected_class) = click_queue.get(timeout=10)
        success_received, (x, y, detected_class) = queue_data
        print(f"主循环接收到:")
        print(f"   success: {success_received}")
        print(f"   x: {x}")
        print(f"   y: {y}")
        print(f"   detected_class: {detected_class}")

        # 检查条件判断
        if success_received:
            print("✅ success为True，应该执行点击操作")
        else:
            print("❌ success为False，会跳过当前步骤")

    except Exception as e:
        print(f"❌ 数据解包失败: {e}")
        print("这可能是数据结构不匹配的问题")

    print("\n=== Priority匹配验证 ===")

    # 5. 加载Priority配置
    try:
        with open("wfgame-ai-server/apps/scripts/testcase/scene2_guide_steps_2025-04-07.json", "r", encoding="utf-8") as f:
            priority_config = json.load(f)

        steps = priority_config.get("steps", [])
        print(f"Priority配置文件包含 {len(steps)} 个步骤")

        # 查找navigation-fight步骤
        nav_fight_steps = [s for s in steps if s.get("class") == "navigation-fight"]

        if nav_fight_steps:
            step = nav_fight_steps[0]
            print(f"✅ 找到navigation-fight Priority配置:")
            print(f"   Priority: {step.get('Priority', 'N/A')}")
            print(f"   class: {step.get('class')}")
            print(f"   remark: {step.get('remark', '')}")

            # 模拟匹配逻辑
            target_class = step.get("class", "")
            if detected_class == target_class:
                print(f"✅ 类别匹配成功: {detected_class} == {target_class}")
            else:
                print(f"❌ 类别匹配失败: {detected_class} != {target_class}")

        else:
            print("❌ Priority配置中未找到navigation-fight步骤")

    except Exception as e:
        print(f"❌ 加载Priority配置失败: {e}")

def analyze_detection_service_issue():
    """分析检测服务的具体问题"""

    print("\n" + "="*50)
    print("检测服务问题分析")
    print("="*50)

    # 从分析数据中提取实际检测结果
    with open("wfgame-ai-server/apps/scripts/analysis_data_5c41023b_20250606_153152.json", "r", encoding="utf-8") as f:
        analysis_data = json.load(f)

    all_detections = analysis_data['detections']
    print(f"AI检测到的所有类别:")

    classes_found = {}
    for det in all_detections:
        class_name = det['class_name']
        confidence = det['confidence']

        if class_name not in classes_found:
            classes_found[class_name] = []
        classes_found[class_name].append(confidence)

    for class_name, confidences in classes_found.items():
        max_conf = max(confidences)
        count = len(confidences)
        print(f"   - {class_name}: {count}个检测, 最高置信度 {max_conf:.4f}")

    print(f"\n🔍 关键发现:")
    if "navigation-fight" in classes_found:
        max_conf = max(classes_found["navigation-fight"])
        print(f"✅ navigation-fight 被成功检测到，置信度 {max_conf:.4f}")
        print(f"   这说明AI检测功能正常")
    else:
        print(f"❌ navigation-fight 未被检测到")

    # 分析可能的问题
    print(f"\n🔧 可能的问题点:")
    print(f"1. 检测服务队列通信问题")
    print(f"2. 数据结构解包不匹配")
    print(f"3. Priority步骤配置问题")
    print(f"4. 检测超时或异常处理")

if __name__ == "__main__":
    print("开始Priority检测流程调试...")
    simulate_detection_flow()
    analyze_detection_service_issue()
    print("\n调试完成！")
