#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的设备屏幕分析器 - 用于快速测试和演示

这是一个简化版本的设备屏幕分析器，专注于核心功能：
1. 连接设备并截图
2. 使用best.pt模型进行YOLO推理
3. 显示识别结果
"""

import os
import sys
import cv2
import numpy as np
import time
import json
from datetime import datetime
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

def find_best_model():
    """查找best.pt模型文件"""
    potential_paths = [
        "datasets/train/weights/best.pt",
        "apps/scripts/datasets/train/weights/best.pt",
        "wfgame-ai-server/apps/scripts/datasets/train/weights/best.pt",
        str(project_root / "wfgame-ai-server/apps/scripts/datasets/train/weights/best.pt"),
        "best.pt"
    ]

    for path in potential_paths:
        full_path = Path(path)
        if full_path.exists():
            print(f"✅ 找到模型文件: {full_path}")
            return str(full_path.absolute())

    print("❌ 未找到best.pt模型文件")
    return None

def test_adb_devices():
    """测试ADB设备连接"""
    try:
        from adbutils import adb
        devices = adb.device_list()

        print(f"发现 {len(devices)} 个ADB设备:")
        active_devices = []

        for device in devices:
            try:
                status = device.get_state()
                print(f"  - {device.serial}: {status}")
                if status == "device":
                    active_devices.append(device.serial)
            except Exception as e:
                print(f"  - {device.serial}: 检查状态失败 ({e})")

        return active_devices

    except ImportError:
        print("❌ adbutils 未安装")
        return []
    except Exception as e:
        print(f"❌ ADB连接测试失败: {e}")
        return []

def capture_device_screenshot(device_id):
    """捕获设备截图"""
    try:
        from airtest.core.api import connect_device

        # 连接设备
        device_uri = f"android:///{device_id}"
        print(f"正在连接设备: {device_uri}")
        device = connect_device(device_uri)

        if device:
            print(f"✅ 设备连接成功: {device_id}")

            # 截图
            print("正在截图...")
            screenshot = device.snapshot()

            if screenshot is not None:
                # 转换为OpenCV格式
                frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                print(f"✅ 截图成功，尺寸: {frame.shape}")
                return frame
            else:
                print("❌ 截图失败")
                return None
        else:
            print(f"❌ 设备连接失败: {device_id}")
            return None

    except ImportError:
        print("❌ airtest 未安装")
        return None
    except Exception as e:
        print(f"❌ 截图异常: {e}")
        return None

def analyze_with_yolo(frame, model_path, confidence=0.6):
    """使用YOLO模型分析截图"""
    try:
        from ultralytics import YOLO

        print(f"正在加载YOLO模型: {model_path}")
        model = YOLO(model_path)

        # 调整图像尺寸
        inference_frame = cv2.resize(frame, (640, 640))

        print("正在进行YOLO推理...")
        results = model.predict(
            source=inference_frame,
            conf=confidence,
            verbose=False
        )

        if not results or len(results) == 0:
            print("⚠️ 未检测到任何对象")
            return []

        # 解析结果
        detections = []
        result = results[0]

        if hasattr(result, 'boxes') and result.boxes is not None:
            boxes = result.boxes
            orig_h, orig_w = frame.shape[:2]
            scale_x, scale_y = orig_w / 640, orig_h / 640

            print(f"✅ 检测到 {len(boxes)} 个对象:")

            for i, box in enumerate(boxes):
                cls_id = int(box.cls.item())
                class_name = "unknown"
                if hasattr(model, 'names') and cls_id in model.names:
                    class_name = model.names[cls_id]

                confidence_score = float(box.conf.item())

                # 获取边界框
                xyxy = box.xyxy[0].tolist()
                x1 = int(xyxy[0] * scale_x)
                y1 = int(xyxy[1] * scale_y)
                x2 = int(xyxy[2] * scale_x)
                y2 = int(xyxy[3] * scale_y)

                detection = {
                    'class_name': class_name,
                    'confidence': confidence_score,
                    'bbox': (x1, y1, x2, y2)
                }

                detections.append(detection)
                print(f"  {i+1}. {class_name}: {confidence_score:.2f} at ({x1},{y1},{x2},{y2})")

        return detections

    except ImportError:
        print("❌ ultralytics 未安装")
        return []
    except Exception as e:
        print(f"❌ YOLO分析失败: {e}")
        return []

def visualize_results(frame, detections, save_path=None):
    """可视化检测结果"""
    result_frame = frame.copy()

    for detection in detections:
        x1, y1, x2, y2 = detection['bbox']
        class_name = detection['class_name']
        confidence = detection['confidence']

        # 绘制边界框
        cv2.rectangle(result_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # 绘制标签
        label = f"{class_name}: {confidence:.2f}"
        label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]

        cv2.rectangle(
            result_frame,
            (x1, y1 - label_size[1] - 10),
            (x1 + label_size[0], y1),
            (0, 255, 0),
            -1
        )

        cv2.putText(
            result_frame,
            label,
            (x1, y1 - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 0),
            2
        )

    if save_path:
        cv2.imwrite(save_path, result_frame)
        print(f"✅ 结果图像已保存: {save_path}")

    return result_frame

def main():
    """主函数"""
    print("=" * 60)
    print("简单设备屏幕分析器")
    print("=" * 60)

    # 1. 检查模型文件
    print("\n1. 检查YOLO模型文件...")
    model_path = find_best_model()
    if not model_path:
        print("请确保best.pt模型文件存在")
        return False

    # 2. 检查设备连接
    print("\n2. 检查ADB设备连接...")
    devices = test_adb_devices()
    if not devices:
        print("请确保至少有一个设备处于'device'状态")
        return False

    # 选择第一个可用设备
    target_device = devices[0]
    print(f"\n选择设备进行分析: {target_device}")

    # 3. 截图
    print(f"\n3. 从设备 {target_device} 获取截图...")
    frame = capture_device_screenshot(target_device)
    if frame is None:
        print("截图失败，请检查设备连接和权限")
        return False

    # 4. YOLO分析
    print(f"\n4. 使用YOLO模型分析截图...")
    detections = analyze_with_yolo(frame, model_path)    # 5. 保存结果
    print(f"\n5. 保存分析结果...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 确保结果目录存在
    results_dir = os.path.join(os.path.dirname(__file__), "screen_analysis_results")
    os.makedirs(results_dir, exist_ok=True)

    # 保存原始截图
    original_path = os.path.join(results_dir, f"screenshot_{target_device}_{timestamp}.jpg")
    cv2.imwrite(original_path, frame)
    print(f"✅ 原始截图已保存: {original_path}")

    # 保存分析结果图像
    if detections:
        result_path = os.path.join(results_dir, f"analysis_result_{target_device}_{timestamp}.jpg")
        visualize_results(frame, detections, result_path)

        # 保存JSON数据
        json_path = os.path.join(results_dir, f"analysis_data_{target_device}_{timestamp}.json")
        result_data = {
            "device_id": target_device,
            "timestamp": timestamp,
            "screenshot_shape": frame.shape,
            "total_detections": len(detections),
            "detections": detections
        }

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        print(f"✅ 分析数据已保存: {json_path}")
    else:
        print("⚠️ 未检测到任何对象，跳过结果可视化")

    print(f"\n🎉 分析完成！总共检测到 {len(detections)} 个UI元素")
    return True

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n✅ 设备屏幕分析器工作正常！")
        else:
            print("\n❌ 分析过程中遇到问题")
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"\n❌ 程序执行失败: {e}")
        import traceback
        traceback.print_exc()
