#!/usr/bin/env python3
"""
真实设备屏幕截取与AI检测分析器
"""

import cv2
import numpy as np
import os
import sys
import subprocess
import json
import configparser
import tempfile
from ultralytics import YOLO
from pathlib import Path
import time
import shutil
import traceback
import datetime
import argparse
import glob

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='真实设备屏幕AI检测分析器')
    parser.add_argument('--clean', action='store_true', help='清空历史生成的文件')
    return parser.parse_args()

def _letterbox_inverse_transform(x, y, orig_w, orig_h, yolo_size=640):
    """
    YOLO letterbox逆变换函数
    """
    # 计算缩放比例 - 取最小值保持长宽比
    scale = min(yolo_size / orig_w, yolo_size / orig_h)

    # 计算缩放后的图像尺寸
    scaled_w = orig_w * scale
    scaled_h = orig_h * scale

    # 计算padding（黑边）
    pad_x = (yolo_size - scaled_w) / 2
    pad_y = (yolo_size - scaled_h) / 2

    # 逆变换：从640x640空间转换回原始图像空间
    transformed_x = (x - pad_x) / scale
    transformed_y = (y - pad_y) / scale

    # 确保坐标在有效范围内
    transformed_x = max(0, min(transformed_x, orig_w - 1))
    transformed_y = max(0, min(transformed_y, orig_h - 1))

    return transformed_x, transformed_y

def check_adb_devices():
    """检查ADB设备连接"""
    try:
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, timeout=10)
        lines = result.stdout.strip().split('\n')
        devices = []
        for line in lines[1:]:  # 跳过第一行标题
            if line.strip() and '\tdevice' in line:
                device_id = line.split('\t')[0]
                devices.append(device_id)
        return devices
    except Exception as e:
        print(f"❌ 检查ADB设备失败: {e}")
        return []

def capture_device_screen(device_id=None, output_dir=None, file_prefix=None):
    """截取设备屏幕"""
    try:
        # 构建adb命令
        if device_id:
            cmd = ['adb', '-s', device_id, 'exec-out', 'screencap', '-p']
        else:
            cmd = ['adb', 'exec-out', 'screencap', '-p']

        print(f"📷 正在截取设备屏幕...")
        result = subprocess.run(cmd, capture_output=True, timeout=30)

        if result.returncode == 0:
            # 使用设备ID和日期时间作为文件名
            current_datetime = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            screenshot_filename = f"{file_prefix}_screenshot_{current_datetime}.png"

            # 使用指定的输出目录，如果有的话
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                screenshot_path = os.path.join(output_dir, screenshot_filename)
            else:
                screenshot_path = screenshot_filename

            with open(screenshot_path, 'wb') as f:
                f.write(result.stdout)

            print(f"✅ 截图保存: {screenshot_path}")
            return screenshot_path, current_datetime
        else:
            print(f"❌ 截图失败: {result.stderr.decode()}")
            return None, None

    except Exception as e:
        print(f"❌ 截图异常: {e}")
        return None, None

def get_screen_resolution(device_id=None):
    """获取设备屏幕分辨率"""
    try:
        if device_id:
            cmd = ['adb', '-s', device_id, 'shell', 'wm', 'size']
        else:
            cmd = ['adb', 'shell', 'wm', 'size']

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        if result.returncode == 0:
            # 解析输出：Physical size: 1080x2400
            output = result.stdout.strip()
            if 'Physical size:' in output:
                size_str = output.split('Physical size:')[1].strip()
                width, height = map(int, size_str.split('x'))
                return width, height

        print(f"⚠️ 无法获取屏幕分辨率，使用默认值")
        return 1080, 2400

    except Exception as e:
        print(f"❌ 获取分辨率失败: {e}")
        return 1080, 2400

def read_config():
    """从配置文件读取设置"""
    config = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())

    # 尝试读取不同位置的配置文件
    config_paths = [
        os.path.join(project_root, "config.ini"),
    ]

    for config_path in config_paths:
        if os.path.exists(config_path):
            try:
                config.read(config_path, encoding='utf-8')
                print(f"✅ 成功读取配置文件: {config_path}")

                # 尝试读取paths和Model部分
                try:
                    # 配置段名小写
                    if 'paths' in config and 'model_path' in config['paths']:
                        # 构建完整的模型路径，自动解析变量
                        model_path = config['paths']['model_path']
                        print(f"📑 配置文件指定的模型路径: {model_path}")
                        return model_path
                    else:
                        print("❌ 配置文件中缺少 paths.model_path 配置")
                        sys.exit(1)  # 终止程序
                except Exception as e:
                    print(f"❌ 读取配置部分失败: {e}")
                    print("❌ 配置文件中缺少 paths.model_path 配置")
                    sys.exit(1)  # 终止程序
            except Exception as e:
                print(f"❌ 读取配置文件 {config_path} 失败: {e}")

    # 如果没有找到配置文件，报错并终止
    print("❌ 未找到配置文件，程序终止")
    sys.exit(1)  # 终止程序

def load_model(model_path):
    """加载YOLO模型"""
    print(f"🔍 尝试加载模型: {model_path}")

    if os.path.exists(model_path):
        print(f"✅ 找到模型文件: {model_path}")
        try:
            model = YOLO(model_path)
            print(f"✅ 成功加载模型: {model_path}")
            return model
        except Exception as e:
            print(f"❌ 加载模型失败: {e}")
            print(traceback.format_exc())
            print("❌ 模型加载失败，程序终止")
            sys.exit(1)  # 终止程序
    else:
        print(f"❌ 指定的模型文件不存在: {model_path}")
        print("❌ 模型文件不存在，程序终止")
        sys.exit(1)  # 终止程序

def clean_output_directory(output_dir):
    """清空输出目录的所有生成文件"""
    if not os.path.exists(output_dir):
        return

    print(f"🧹 正在清空输出目录: {output_dir}")
    count = 0

    # 查找并删除所有设备生成的文件
    file_patterns = [
        "*.png",
        "*.json"
    ]

    for pattern in file_patterns:
        files = glob.glob(os.path.join(output_dir, pattern))
        for file in files:
            try:
                os.remove(file)
                count += 1
            except Exception as e:
                print(f"⚠️ 无法删除文件 {file}: {e}")

    print(f"✅ 清空完成，共删除 {count} 个文件")

def analyze_real_device_screenshot(args):
    """分析真实设备截图的AI检测结果"""
    print("🔍 开始真实设备屏幕分析...")

    # 检查设备连接
    devices = check_adb_devices()
    if not devices:
        print("❌ 未找到连接的Android设备")
        print("💡 请确保:")
        print("   1. 设备已连接并开启USB调试")
        print("   2. 已安装ADB工具")
        print("   3. 授权了电脑的调试权限")
        print("❌ 未检测到设备，程序终止")
        sys.exit(1)  # 终止程序

    print(f"📱 检测到 {len(devices)} 个设备")
    for idx, device_id in enumerate(devices):
        print(f"📱 设备 {idx+1}: {device_id}")

    # 创建结果输出目录
    output_dir = os.path.join(project_root, "ai_capture_and_analyze_result")
    os.makedirs(output_dir, exist_ok=True)
    print(f"📁 使用输出目录: {output_dir}")

    # 如果指定了--clean参数，清空输出目录
    if args.clean:
        clean_output_directory(output_dir)

    # 从配置文件读取模型路径
    try:
        model_path = read_config()
        print(f"📑 配置文件指定的模型路径: {model_path}")
    except Exception as e:
        print(f"❌ 读取配置文件失败: {e}")
        print(traceback.format_exc())
        print("❌ 配置读取失败，程序终止")
        sys.exit(1)  # 终止程序

    # 加载模型 - 如果失败，load_model会终止程序
    model = load_model(model_path)

    # 处理每个连接的设备
    for device_id in devices:
        print(f"\n🔄 正在处理设备: {device_id}")

        # 获取屏幕分辨率
        screen_w, screen_h = get_screen_resolution(device_id)
        print(f"📐 设备分辨率: {screen_w}x{screen_h}")

        # 使用设备ID作为文件前缀
        file_prefix = device_id

        # 截取屏幕
        screenshot_result = capture_device_screen(device_id, output_dir, file_prefix)
        if screenshot_result[0] is None:
            print(f"❌ 截取设备 {device_id} 屏幕失败，跳过该设备")
            continue

        screenshot_path, current_datetime = screenshot_result

        # 验证截图文件
        image = cv2.imread(screenshot_path)
        if image is None:
            print(f"❌ 无法读取设备 {device_id} 的截图文件: {screenshot_path}")
            print(f"❌ 跳过设备 {device_id}")
            continue

        actual_h, actual_w = image.shape[:2]
        print(f"📏 实际图像尺寸: {actual_w}x{actual_h}")

        # 定义输出文件路径
        labeled_image_path = os.path.join(output_dir, f"{file_prefix}_labeled_{current_datetime}.png")
        json_result_path = os.path.join(output_dir, f"{file_prefix}_detection_{current_datetime}.json")

        # 创建临时目录用于YOLO结果
        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"🔍 临时目录: {temp_dir}")

            try:
                # 运行AI检测
                print("🔍 开始AI检测...")
                print(f"🔍 检测源图像: {screenshot_path}")

                # 设置置信度阈值为0.7
                results = model.predict(
                    source=screenshot_path,
                    save=True,
                    project=temp_dir,
                    name="detection",
                    conf=0.7  # 明确设置置信度阈值
                )
                print(f"📊 检测结果数量: {len(results)}")

                # 创建JSON结果
                detection_results = []

                if len(results) > 0:
                    result = results[0]  # 获取第一个结果，因为只有一张图片

                    # 处理YOLO结果
                    if hasattr(result, 'boxes') and result.boxes is not None and len(result.boxes) > 0:
                        boxes = result.boxes
                        print(f"📦 检测到 {len(boxes)} 个目标")

                        # 分析每个检测结果
                        for i, box in enumerate(boxes):
                            cls_id = int(box.cls.item())
                            confidence = box.conf.item()
                            class_name = model.names[cls_id] if hasattr(model, 'names') else f"class_{cls_id}"

                            # 获取原始YOLO坐标 (640x640空间)
                            box_coords = box.xyxy[0].tolist()  # [x1, y1, x2, y2]
                            yolo_x = (box_coords[0] + box_coords[2]) / 2  # 中心点x
                            yolo_y = (box_coords[1] + box_coords[3]) / 2  # 中心点y

                            # 使用实际图像尺寸进行坐标转换
                            screen_x, screen_y = _letterbox_inverse_transform(yolo_x, yolo_y, actual_w, actual_h)

                            # 计算Y坐标在屏幕中的位置百分比
                            y_percentage = (screen_y / actual_h) * 100

                            detection_info = {
                                'id': i + 1,
                                'class': class_name,
                                'confidence': float(confidence),
                                'yolo_coords': [float(yolo_x), float(yolo_y)],
                                'screen_coords': [float(screen_x), float(screen_y)],
                                'y_percentage': float(y_percentage),
                                'box_xyxy': [float(x) for x in box_coords]
                            }
                            detection_results.append(detection_info)

                            # print(f"🎯 检测 {i+1}:")
                            # print(f"   类别: {class_name} (ID: {cls_id})")
                            # print(f"   置信度: {confidence:.3f}")
                            # print(f"   YOLO坐标: ({yolo_x:.1f}, {yolo_y:.1f})")
                            # print(f"   屏幕坐标: ({screen_x:.1f}, {screen_y:.1f})")

                # 复制标记后的图像
                temp_result_dir = os.path.join(temp_dir, "detection")

                # 检查原始扩展名和YOLO可能生成的扩展名
                screenshot_basename = os.path.basename(screenshot_path)
                screenshot_name, screenshot_ext = os.path.splitext(screenshot_basename)

                possible_extensions = ['.jpg', '.png', '.jpeg']
                found_labeled_image = False

                # 检查所有可能的标记图像名称
                for ext in possible_extensions:
                    temp_labeled_image = os.path.join(temp_result_dir, f"{screenshot_name}{ext}")
                    print(f"🔍 检查标记图像: {temp_labeled_image}")

                    if os.path.exists(temp_labeled_image):
                        found_labeled_image = True
                        shutil.copy2(temp_labeled_image, labeled_image_path)
                        print(f"✅ 标记图像已保存: {labeled_image_path}")
                        break

                if not found_labeled_image:
                    print(f"⚠️ 未找到标记后的图像，检查目录内容:")
                    for root, dirs, files in os.walk(temp_dir):
                        print(f"   目录: {root}")
                        for d in dirs:
                            print(f"     - {d}/")
                        for f in files:
                            print(f"     - {f}")
                            # 如果找到任何图像文件，尝试使用它
                            if f.endswith(('.jpg', '.png', '.jpeg')):
                                temp_labeled_image = os.path.join(root, f)
                                shutil.copy2(temp_labeled_image, labeled_image_path)
                                print(f"✅ 找到并使用图像: {temp_labeled_image}")
                                found_labeled_image = True
                                break
                        if found_labeled_image:
                            break

                    # 如果仍然找不到标记后的图像，复制原始图像
                    if not found_labeled_image:
                        shutil.copy2(screenshot_path, labeled_image_path)
                        print(f"✅ 已复制原始图像（无标记）: {labeled_image_path}")

                # 保存JSON结果
                json_data = {
                    'timestamp': int(time.time()),
                    'date': current_datetime,
                    'device_id': device_id,
                    'screen_resolution': [screen_w, screen_h],
                    'image_size': [actual_w, actual_h],
                    'screenshot_path': os.path.basename(screenshot_path),
                    'labeled_image_path': os.path.basename(labeled_image_path),
                    'detection_count': len(detection_results),
                    'detections': detection_results
                }

                with open(json_result_path, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, indent=2, ensure_ascii=False)

                print(f"✅ 检测结果已保存为JSON: {json_result_path}")

                # 打印文件摘要
                print("\n📁 结果文件摘要:")
                print(f"   原始截图: {screenshot_path}")
                print(f"   标记图像: {labeled_image_path}")
                print(f"   检测结果: {json_result_path}")
                print(f"   检测到的元素数量: {len(detection_results)}")

            except Exception as e:
                print(f"❌ 检测失败: {e}")
                print(traceback.format_exc())

                # 保存错误信息到JSON
                json_data = {
                    'timestamp': int(time.time()),
                    'date': current_datetime,
                    'device_id': device_id,
                    'screen_resolution': [screen_w, screen_h],
                    'image_size': [actual_w, actual_h],
                    'screenshot_path': os.path.basename(screenshot_path),
                    'detection_count': 0,
                    'detections': [],
                    'error': str(e),
                    'traceback': traceback.format_exc()
                }

                with open(json_result_path, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, indent=2, ensure_ascii=False)

                print(f"✅ 错误信息已保存为JSON: {json_result_path}")

                # 如果标记图像未生成，复制原始图像
                if not os.path.exists(labeled_image_path):
                    shutil.copy2(screenshot_path, labeled_image_path)
                    print(f"✅ 已复制原始图像（无标记）: {labeled_image_path}")

def main():
    """主函数"""
    print("🚀 真实设备屏幕AI检测分析器")
    print("=" * 50)

    # 解析命令行参数
    args = parse_arguments()

    analyze_real_device_screenshot(args)

if __name__ == "__main__":
    main()
