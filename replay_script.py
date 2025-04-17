from airtest.core.api import touch, exists, snapshot, set_logdir, connect_device, log
from airtest.report.report import LogToHtml
import cv2
import numpy as np
from ultralytics import YOLO
import json
import time
import os
import subprocess
from threading import Thread, Event
import queue
import sys
import argparse
import logging
import shutil
from adbutils import adb
from jinja2 import Environment, FileSystemLoader
import traceback
import io  # 确保导入 io 模块
import airtest  # 添加这行
from datetime import datetime

# 禁用 Ultralytics 的日志输出
logging.getLogger("ultralytics").setLevel(logging.CRITICAL)

# 全局变量
model = None
devices = []
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CURRENT_TIME = "_" + time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime(time.time()))
report_dir = os.path.join(BASE_DIR, "outputs/replay_reports")
template_dir = os.path.join(BASE_DIR, "templates")  # 模板目录路径

# 确保所有必要的目录都存在
os.makedirs(report_dir, exist_ok=True)
os.makedirs(template_dir, exist_ok=True)

screenshot_queue = queue.Queue()
action_queue = queue.Queue()
click_queue = queue.Queue()  # 新增全局 click_queue


# Airtest 兼容的 JSON 日志格式化器
class AirtestJsonFormatter(logging.Formatter):
    def format(self, record):
        timestamp = record.created
        log_entry = {
            "tag": getattr(record, 'tag', 'function'),
            "depth": getattr(record, 'depth', 0),
            "time": timestamp,
            "data": {
                "name": getattr(record, 'operation_name', 'unknown'),
                "call_args": getattr(record, 'call_args', {"message": record.getMessage()}),
                "start_time": timestamp - 0.001,
                "ret": getattr(record, 'ret', None),
                "end_time": timestamp
            }
        }
        return json.dumps(log_entry, ensure_ascii=False)


# 日志函数
def setup_device_logger(device_name):
    log_file = os.path.join(report_dir, f"{device_name}_log.txt")
    logger = logging.getLogger(device_name)
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(log_file, encoding="utf-8")
    formatter = AirtestJsonFormatter()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


# 获取设备名称
def get_device_name(device):
    try:
        brand = device.shell("getprop ro.product.brand").strip()
        model = device.shell("getprop ro.product.model").strip()
        resolution = device.shell("wm size").strip().replace("Physical size: ", "")
        return f"{brand}-{model}-{resolution}"
    except Exception as e:
        print(f"获取设备 {device.serial} 信息失败: {e}")
        return device.serial


# 检测按钮
def detect_buttons(frame, target_class=None):
    frame_for_detection = cv2.resize(frame, (640, 640))
    results = model.predict(source=frame_for_detection, device="mps", imgsz=640, conf=0.3, verbose=False)
    orig_h, orig_w = frame.shape[:2]
    scale_x, scale_y = orig_w / 640, orig_h / 640

    for box in results[0].boxes:
        cls_id = int(box.cls.item())
        detected_class = model.names[cls_id]
        if detected_class == target_class:
            box_x, box_y = box.xywh[0][:2].tolist()
            x, y = box_x * scale_x, box_y * scale_y
            return True, (x, y, detected_class)
    return False, (None, None, None)


# 验证目标消失
def verify_target_disappeared(device, target_class, max_attempts=5, delay=0.5):
    for attempt in range(max_attempts):
        screenshot = device.screenshot()
        frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        success, result = detect_buttons(frame, target_class=target_class)
        if not success or result[0] is None:
            return True
        time.sleep(delay)
    return False


# 检查设备状态
def check_device_status(device, device_name):
    try:
        device.shell("echo test")
        device.shell("input keyevent 82")
        time.sleep(1)
        device.shell("input swipe 500 1000 500 500")
        time.sleep(1)
        display_state = device.shell("dumpsys power | grep 'mHoldingDisplaySuspendBlocker'")
        if "true" not in display_state.lower():
            print(f"设备 {device_name} 屏幕未打开，尝试唤醒")
            device.shell("input keyevent 26")
            time.sleep(1)
        print(f"设备 {device_name} 状态检查完成")
        return True
    except Exception as e:
        print(f"设备 {device_name} 状态检查失败: {e}")
        return False


# 获取设备日志目录
def get_log_dir(dev):
    device_dir = dev.replace(".", "_").replace(":", "_") + CURRENT_TIME
    log_dir = os.path.normpath(os.path.join(report_dir, device_dir))
    
    # 创建必要的目录结构
    os.makedirs(log_dir, exist_ok=True)
    
    # 确保日志文件存在
    log_file = os.path.join(log_dir, "log.txt")
    if not os.path.exists(log_file):
        with open(log_file, "w", encoding="utf-8") as f:
            pass
            
    return log_dir


# 清理日志目录
def clear_log_dir():
    if os.path.exists(report_dir):
        shutil.rmtree(report_dir)
    os.makedirs(report_dir, exist_ok=True)


# 加载测试进度数据
def load_json_data(run_all):
    json_file = os.path.join(BASE_DIR, 'data.json')
    if not run_all and os.path.isfile(json_file):
        data = json.load(open(json_file))
        data['start'] = time.time()
        return data
    else:
        print(f"清理日志目录: {report_dir}")
        clear_log_dir()
        return {
            'start': time.time(),
            'script': "replay_script",
            'tests': {}
        }


def replay_device(device, scripts, screenshot_queue, action_queue, stop_event, device_name, log_dir, show_screens=False,
                  loop_count=1):
    """
    回放设备脚本，记录日志并生成报告所需信息。

    参数:
        device: ADB 设备对象（adbutils 设备实例）。
        scripts (list): 脚本配置列表，例如 [{"path": "path/to/script.json", "loop_count": 1}]。
        screenshot_queue (queue.Queue): 截图队列，用于传递屏幕截图给检测服务。
        action_queue (queue.Queue): 动作队列，用于记录操作。
        stop_event (threading.Event): 停止事件，用于控制检测服务。
        device_name (str): 设备名称，例如 "OnePlus-KB2000-1080x2400"。
        log_dir (str): 日志目录，例如 "outputs/replaylogs/OnePlus-KB2000-1080x2400_2025-04-15-14-34-35"。
        show_screens (bool): 是否显示屏幕（默认 False）。
        loop_count (int): 循环次数（默认 1，从 scripts 中获取优先）。
    """
    # 打印参数（用于调试）
    print(f"设备: {device_name}, 脚本: {scripts}, 日志目录: {log_dir}")
    print(f"show_screens: {show_screens}, loop_count: {loop_count}")

    # 模拟设备初始化
    print(f"开始回放设备: {device_name}, 脚本: {scripts}")

    # 检查脚本列表是否为空
    if not scripts:
        raise ValueError("脚本列表为空，无法回放")

    # 创建log.txt文件
    log_txt_path = os.path.join(log_dir, "log.txt")
    with open(log_txt_path, "w", encoding="utf-8") as f:
        f.write("")  # 创建空文件

    # 执行所有脚本
    total_step_counter = 0
    for script_config in scripts:
        script_path = script_config["path"]
        script_loop_count = script_config.get("loop_count", loop_count)  # 优先使用脚本配置中的 loop_count
        max_duration = script_config.get("max_duration", None)  # 获取最大执行时间（如果有）
        
        print(f"开始执行脚本: {script_path}, 循环次数: {script_loop_count}, 最大执行时间: {max_duration}秒")
        
        # 从 script_path 读取步骤
        with open(script_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)
            steps = json_data.get("steps", [])  # 确保获取 steps 列表

        # 检查 steps 是否为空
        if not steps:
            print(f"警告: 脚本 {script_path} 中未找到有效的步骤，跳过此脚本")
            continue

        # 检查脚本类型：是否是基于优先级的动态脚本
        is_priority_based = any("Priority" in step for step in steps)
        if is_priority_based:
            print(f"检测到基于优先级的动态脚本: {script_path}")
            # 按优先级排序（如果未指定Priority，则默认为最低优先级999）
            steps.sort(key=lambda s: s.get("Priority", 999))
            
        script_start_time = time.time()  # 记录脚本开始执行的时间
        
        # 循环执行（根据 script_loop_count）
        for loop in range(script_loop_count):
            print(f"第 {loop + 1}/{script_loop_count} 次循环")
            step_counter = 0
            
            # 如果是基于优先级的脚本，则一直循环执行直到达到最大执行时间
            if is_priority_based:
                priority_start_time = time.time()  # 记录优先级模式的实际开始时间
                print(f"优先级模式开始时间: {priority_start_time}, 最大执行时间: {max_duration}秒")
                
                while True:
                    # 检查是否超过最大执行时间
                    current_time = time.time()
                    elapsed_time = current_time - priority_start_time
                    if max_duration is not None and elapsed_time > max_duration:
                        print(f"脚本 {script_path} 已达到最大执行时间 {max_duration}秒，实际运行了{elapsed_time:.2f}秒，停止执行")
                        break
                    
                    # 截取屏幕以检测目标
                    timestamp = time.time()
                    screenshot = device.screenshot()
                    frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                    if frame is None:
                        raise ValueError("无法获取设备屏幕截图")
                        
                    # 使用纯时间戳作为截图文件名
                    screenshot_timestamp = int(timestamp * 1000)
                    screenshot_filename = f"{screenshot_timestamp}.jpg"
                    screenshot_path = os.path.join(log_dir, screenshot_filename)
                    cv2.imwrite(screenshot_path, frame)
                    print(f"保存截图: {screenshot_path}")
                    
                    # 创建缩略图
                    thumbnail_filename = f"{screenshot_timestamp}_small.jpg"
                    thumbnail_path = os.path.join(log_dir, thumbnail_filename)
                    small_frame = cv2.resize(frame, (0, 0), fx=0.3, fy=0.3)
                    cv2.imwrite(thumbnail_path, small_frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
                    
                    # 获取屏幕分辨率
                    height, width = frame.shape[:2]
                    resolution = [width, height]
                    
                    # 按优先级检测所有可能的目标
                    highest_priority_detected = None
                    highest_priority_coords = None
                    
                    for step in steps:
                        step_class = step["class"]
                        if step_class == "unknown":  # 默认操作
                            # 如果所有优先级都未检测到，则使用默认操作
                            relative_x = step.get("relative_x", 0.5)
                            relative_y = step.get("relative_y", 0.9)
                            x = int(width * relative_x)
                            y = int(height * relative_y)
                            highest_priority_detected = step
                            highest_priority_coords = (x, y, "unknown")
                            print(f"未检测到任何目标，使用默认操作: 点击位置 ({x}, {y})")
                            break
                        
                        # 将截图和检测任务放入队列
                        screenshot_queue.put((device_name, total_step_counter+1, frame, step_class, None))
                        
                        # 等待检测结果
                        try:
                            success, (x, y, detected_class) = click_queue.get(timeout=5)
                            if success:
                                highest_priority_detected = step
                                highest_priority_coords = (x, y, detected_class)
                                print(f"检测到优先级目标: {step_class}，优先级: {step.get('Priority', 999)}")
                                break
                        except queue.Empty:
                            print(f"检测 {step_class} 超时，尝试下一个优先级")
                            continue
                    
                    # 如果没有检测到任何目标且没有默认操作
                    if highest_priority_detected is None:
                        print("没有检测到任何目标，且没有默认操作，等待1秒后重试")
                        time.sleep(1)
                        continue
                    
                    # 执行检测到的最高优先级操作
                    step_counter += 1
                    total_step_counter += 1
                    step_num = total_step_counter
                    x, y, detected_class = highest_priority_coords
                    step_remark = highest_priority_detected.get("remark", "")
                    
                    # 准备screen对象
                    screen_object = {
                        "src": f"log/{screenshot_filename}",
                        "_filepath": f"log/{screenshot_filename}",
                        "thumbnail": f"log/{thumbnail_filename}",
                        "resolution": resolution,
                        "pos": [[int(x), int(y)]] if x is not None and y is not None else [],
                        "vector": [],
                        "confidence": 0.85,
                        "rect": [{"left": int(x)-50, "top": int(y)-50, "width": 100, "height": 100}] if x is not None and y is not None else []
                    }
                    
                    # 1. 记录snapshot操作
                    snapshot_entry = {
                        "tag": "function",
                        "depth": 0,
                        "time": timestamp,
                        "data": {
                            "name": "snapshot",
                            "call_args": {},
                            "start_time": timestamp - 0.002,
                            "ret": screenshot_filename,
                            "end_time": timestamp,
                            "screen": screen_object
                        }
                    }
                    
                    with open(log_txt_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps(snapshot_entry, ensure_ascii=False) + "\n")
                    
                    # 执行点击操作
                    device.shell(f"input tap {int(x)} {int(y)}")
                    print(f"设备 {device_name} 执行优先级操作: {detected_class}，点击位置: ({int(x)}, {int(y)})")
                    
                    # 2. 记录touch操作
                    touch_entry = {
                        "tag": "function",
                        "depth": 0,
                        "time": timestamp + 0.001,
                        "data": {
                            "name": "touch",
                            "call_args": {
                                "v": [int(x), int(y)]
                            },
                            "start_time": timestamp + 0.001,
                            "ret": [int(x), int(y)],
                            "end_time": timestamp + 0.002,
                            "screen": screen_object
                        }
                    }
                    
                    with open(log_txt_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps(touch_entry, ensure_ascii=False) + "\n")
                    
                    # 等待一段时间，让UI响应
                    time.sleep(0.5)
                    
                    # 再次检查是否超过最大执行时间
                    if max_duration is not None:
                        current_time = time.time()
                        elapsed_time = current_time - priority_start_time
                        print(f"已运行时间: {elapsed_time:.2f}秒, 最大执行时间: {max_duration}秒")
                        if elapsed_time > max_duration:
                            print(f"脚本 {script_path} 已达到最大执行时间 {max_duration}秒，实际运行了{elapsed_time:.2f}秒，停止执行")
                            break
            else:
                # 常规脚本，按顺序执行固定步骤
                for step in steps:
                    # 检查是否超过最大执行时间
                    if max_duration is not None and (time.time() - script_start_time) > max_duration:
                        print(f"脚本 {script_path} 已达到最大执行时间 {max_duration}秒，停止执行")
                        break
                    
                    step_class = step["class"]
                    step_remark = step.get("remark", "")
                    step_counter += 1
                    total_step_counter += 1
                    step_num = total_step_counter
                    timestamp = time.time()  # 更新时间戳

                    # 获取设备屏幕截图
                    screenshot = device.screenshot()  # 使用 adbutils 获取截图
                    frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                    if frame is None:
                        raise ValueError("无法获取设备屏幕截图")

                    # 使用纯时间戳作为截图文件名，符合ka2-reports-demo的命名约定
                    screenshot_timestamp = int(timestamp * 1000)
                    screenshot_filename = f"{screenshot_timestamp}.jpg"
                    screenshot_path = os.path.join(log_dir, screenshot_filename)
                    cv2.imwrite(screenshot_path, frame)
                    print(f"保存截图: {screenshot_path}")

                    # 创建缩略图
                    thumbnail_filename = f"{screenshot_timestamp}_small.jpg"
                    thumbnail_path = os.path.join(log_dir, thumbnail_filename)
                    small_frame = cv2.resize(frame, (0, 0), fx=0.3, fy=0.3)
                    cv2.imwrite(thumbnail_path, small_frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
                    print(f"保存缩略图: {thumbnail_path}")

                    # 获取屏幕分辨率
                    height, width = frame.shape[:2]
                    resolution = [width, height]

                    # 将截图和检测任务放入队列
                    screenshot_queue.put((device_name, step_num, frame, step_class, None))

                    # 等待检测结果，添加超时机制
                    try:
                        success, (x, y, detected_class) = click_queue.get(timeout=10)  # 等待最多 10 秒
                    except queue.Empty:
                        print(f"设备 {device_name} 检测超时，未收到目标按钮 {step_class} 的检测结果")
                        success, (x, y, detected_class) = False, (None, None, None)

                    # 准备screen对象，格式与ka2-reports-demo一致
                    screen_object = {
                        "src": f"log/{screenshot_filename}",
                        "_filepath": f"log/{screenshot_filename}",
                        "thumbnail": f"log/{thumbnail_filename}",
                        "resolution": resolution,
                        "pos": [[int(x), int(y)]] if success and x is not None and y is not None else [],
                        "vector": [],
                        "confidence": 0.85 if success else None,
                        "rect": [{"left": int(x)-50, "top": int(y)-50, "width": 100, "height": 100}] if success and x is not None and y is not None else []
                    }

                    # 1. 记录snapshot操作（作为底层操作，记录截图）
                    snapshot_entry = {
                        "tag": "function",
                        "depth": 0,
                        "time": timestamp,
                        "data": {
                            "name": "snapshot",
                            "call_args": {},
                            "start_time": timestamp - 0.002,
                            "ret": screenshot_filename,  # 返回文件名
                            "end_time": timestamp,
                            "screen": screen_object  # 包含完整的screen对象
                        }
                    }
                    
                    with open(log_txt_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps(snapshot_entry, ensure_ascii=False) + "\n")

                    # 处理检测结果
                    if success:
                        print(f"设备 {device_name} 检测到目标按钮 {step_class}，执行点击操作")
                        
                        # 执行点击操作
                        device.shell(f"input tap {int(x)} {int(y)}")
                        
                        # 2. 记录touch操作（点击成功）- 使用与ka2-reports-demo一致的格式
                        touch_entry = {
                            "tag": "function",
                            "depth": 0,
                            "time": timestamp + 0.001,
                            "data": {
                                "name": "touch",
                                "call_args": {
                                    "v": [int(x), int(y)]
                                },
                                "start_time": timestamp + 0.001,
                                "ret": [int(x), int(y)],
                                "end_time": timestamp + 0.002,
                                "screen": screen_object  # 直接引用相同的screen对象
                            }
                        }
                        
                        with open(log_txt_path, "a", encoding="utf-8") as f:
                            f.write(json.dumps(touch_entry, ensure_ascii=False) + "\n")
                            
                        # 等待一段时间，让UI响应
                        time.sleep(0.5)
                        
                    else:
                        print(f"设备 {device_name} 未检测到目标按钮 {step_class}，标记为失败")
                        
                        # 3. 记录assert_exists操作（检测失败）
                        assert_exists_entry = {
                            "tag": "function",
                            "depth": 0,
                            "time": timestamp + 0.001,
                            "data": {
                                "name": "assert_exists",
                                "call_args": {
                                    "v": f"Target {step_class}",
                                    "msg": f"Step {step_num}: 断言目标图片存在"
                                },
                                "start_time": timestamp + 0.001,
                                "traceback": f"AssertionError: Target {step_class} does not exist in screen for Step {step_num}",
                                "end_time": timestamp + 0.002,
                                "screen": screen_object  # 包含相同的screen对象
                            }
                        }
                        
                        with open(log_txt_path, "a", encoding="utf-8") as f:
                            f.write(json.dumps(assert_exists_entry, ensure_ascii=False) + "\n")
            
            # 检查是否因最大执行时间而中断循环
            if is_priority_based:
                # 优先级模式已经在内部循环中处理了时间限制
                pass
            elif max_duration is not None and (time.time() - script_start_time) > max_duration:
                print(f"脚本 {script_path} 已达到最大执行时间 {max_duration}秒，跳过剩余循环")
                break
        
        print(f"完成脚本 {script_path}，执行步骤数: {step_counter}，总步骤数: {total_step_counter}")

    print(f"设备 {device_name} 回放完成，完成总步骤数: {total_step_counter}")
    stop_event.set()  # 停止检测服务


# 检测服务
def detection_service(screenshot_queue, click_queue, stop_event):
    while not stop_event.is_set():
        try:
            item = screenshot_queue.get(timeout=1)
            if len(item) != 5:
                print(f"跳过无效数据: {item}")
                continue
            device_name, step_num, frame, target_class, all_classes_or_special = item
            success, coords = detect_buttons(frame, target_class=target_class)
            click_queue.put((success, coords))
        except queue.Empty:
            continue
        except Exception as e:
            print(f"检测服务错误: {e}")


def get_airtest_template_path():
    """获取 Airtest 默认模板路径"""
    import airtest
    airtest_path = os.path.dirname(airtest.__file__)
    template_path = os.path.join(airtest_path, "report", "log_template.html")
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"找不到 Airtest 模板文件: {template_path}")
    return template_path


def run_one_report(log_dir, report_dir, script_path=None):
    """
    为单个设备生成HTML报告，遵循Airtest标准结构
    
    参数:
        log_dir: 包含日志文件的目录
        report_dir: 生成报告的目标目录（现在与log_dir相同）
        script_path: 可选的脚本文件路径，如果提供则会复制到报告目录
        
    返回:
        bool: 是否成功生成报告
    """
    try:
        import traceback
        from airtest.report.report import LogToHtml
        
        # 检查日志文件是否存在
        log_file = os.path.join(log_dir, "log.txt")
        if not os.path.exists(log_file):
            print(f"找不到日志文件: {log_file}")
            return False
        
        # 创建log子目录，符合Airtest标准结构
        log_report_dir = os.path.join(log_dir, "log")
        os.makedirs(log_report_dir, exist_ok=True)
        
        # 1. 创建标准Airtest项目结构：script.py
        script_file = os.path.join(log_dir, "script.py")
        if not os.path.exists(script_file):
            with open(script_file, 'w', encoding='utf-8') as f:
                f.write("# Generated script for YOLO-based automation\n")
        
        # 2. 移动截图和缩略图到log子目录
        image_files = []
        for img in os.listdir(log_dir):
            if (img.endswith(".jpg") or img.endswith(".png")) and not img.endswith("_small.jpg") and not img.endswith("_small.png"):
                # 移动主图片
                src = os.path.join(log_dir, img)
                dst = os.path.join(log_report_dir, img)
                if src != dst:  # 如果源和目标不同，则移动文件
                    shutil.move(src, dst)
                image_files.append(img)
                
                # 对应的缩略图
                small_img = img.replace(".", "_small.")
                small_src = os.path.join(log_dir, small_img)
                if os.path.exists(small_src):
                    small_dst = os.path.join(log_report_dir, small_img)
                    if small_src != small_dst:  # 如果源和目标不同，则移动文件
                        shutil.move(small_src, small_dst)
                else:
                    # 如果没有缩略图，尝试创建一个
                    try:
                        import cv2
                        if os.path.exists(dst):
                            img_data = cv2.imread(dst)
                            if img_data is not None:
                                small_img_data = cv2.resize(img_data, (0, 0), fx=0.3, fy=0.3)
                                cv2.imwrite(os.path.join(log_report_dir, small_img), small_img_data, [cv2.IMWRITE_JPEG_QUALITY, 60])
                                print(f"创建缩略图: {small_img}")
                    except Exception as e:
                        print(f"创建缩略图失败: {e}")
        
        # 3. 将日志移动到log子目录下的log.txt
        with open(log_file, "r", encoding="utf-8") as f:
            log_content = f.read()
        
        log_txt_file = os.path.join(log_report_dir, "log.txt")
        with open(log_txt_file, "w", encoding="utf-8") as f:
            f.write(log_content)
        
        # 如果原始日志文件不在log子目录，则删除它
        if log_file != log_txt_file:
            os.remove(log_file)
        
        # 4. 复制脚本文件（如果提供）
        if script_path and os.path.exists(script_path):
            if script_path != script_file:  # 避免复制到同一个文件
                shutil.copy2(script_path, script_file)
        
        # 5. 创建static目录和资源
        # 获取Airtest资源路径
        airtest_path = os.path.dirname(airtest.__file__)
        report_path = os.path.join(airtest_path, "report")
        
        # 创建static目录及子目录
        static_dir = os.path.join(log_dir, "static")
        for resource in ["css", "js", "image", "fonts"]:
            os.makedirs(os.path.join(static_dir, resource), exist_ok=True)
        
        # 复制静态资源
        for resource in ["css", "js", "image", "fonts"]:
            src = os.path.join(report_path, resource)
            dst = os.path.join(static_dir, resource)
            if os.path.exists(src):
                for item in os.listdir(src):
                    s = os.path.join(src, item)
                    d = os.path.join(dst, item)
                    if os.path.isdir(s):
                        try:
                            shutil.copytree(s, d, dirs_exist_ok=True)
                        except Exception as e:
                            print(f"复制目录 {s} 到 {d} 时出错: {e}")
                            # 尝试复制单个文件
                            for subitem in os.listdir(s):
                                sub_s = os.path.join(s, subitem)
                                sub_d = os.path.join(d, subitem)
                                if os.path.isfile(sub_s):
                                    os.makedirs(d, exist_ok=True)
                                    shutil.copy2(sub_s, sub_d)
                    else:
                        shutil.copy2(s, d)
        else:
                print(f"警告: 找不到静态资源目录 {src}")
        
        # 6. 复制模板文件
        template_file = os.path.join(report_path, "log_template.html")
        if not os.path.exists(template_file):
            raise FileNotFoundError(f"找不到模板文件: {template_file}")
        
        dest_template = os.path.join(log_dir, "log_template.html")
        shutil.copy2(template_file, dest_template)
        
        # 7. 使用Airtest的LogToHtml生成报告
        rpt = LogToHtml(
            script_root=log_dir,           # 项目根目录
            log_root=log_report_dir,       # log子目录
            static_root="static/",         # 静态资源目录
            export_dir=None,
            logfile="log.txt",             # log.txt在log子目录中
            script_name="script.py",       # 脚本名称
            lang="zh"
        )
        
        # 生成报告
        report_html_file = os.path.join(log_dir, "log.html")
        rpt.report(template_name="log_template.html", output_file=report_html_file)
        
        # 修复HTML文件中的资源路径和截图引用
        fix_html_report(report_html_file, image_files)
        
        print(f"报告生成成功: {report_html_file}")
        return True
    except Exception as e:
        print(f"报告生成失败: {str(e)}")
        traceback.print_exc()
        return False


def fix_html_paths(html_file):
    """修复HTML文件中的资源路径，将绝对路径转换为相对路径"""
    try:
        with open(html_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 提取资源文件所在目录的绝对路径
        dirname = os.path.dirname(html_file)
        
        # 替换绝对路径为相对路径
        content = content.replace(dirname + "/static/", "static/")
        
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        print(f"修复HTML路径失败: {str(e)}")
        traceback.print_exc()


def fix_html_report(html_file, image_files):
    """修复HTML文件中的资源路径，并确保截图正确关联"""
    try:
        with open(html_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 提取资源文件所在目录的绝对路径
        dirname = os.path.dirname(html_file)
        
        # 替换绝对路径为相对路径
        content = content.replace(dirname + "/static/", "static/")
        
        # 尝试修复截图引用
        start_idx = content.find('data =')
        if start_idx > 0:
            # 找到data = {开始的位置
            json_start = content.find('{', start_idx)
            json_end = content.find('};', json_start) + 1
            
            if json_start > 0 and json_end > 0:
                # 提取JSON数据
                json_str = content[json_start:json_end]
                
                # 构建截图文件映射
                img_map = {}
                for img in image_files:
                    if img.endswith('.jpg') and not img.endswith('_small.jpg'):
                        img_map[img] = img
                
                # 分析steps数组，确保每一步正确关联到对应截图
                import json
                import re
                
                try:
                    # 解析JSON以便于修改
                    data_obj = json.loads(json_str)
                    
                    # 打开日志文件，读取原始日志条目
                    log_file = os.path.join(dirname, "log", "log.txt")
                    if os.path.exists(log_file):
                        log_entries = []
                        with open(log_file, "r", encoding="utf-8") as f:
                            for line in f:
                                try:
                                    entry = json.loads(line.strip())
                                    log_entries.append(entry)
                                except:
                                    continue
                    
                    if 'steps' in data_obj and log_entries:
                        # 收集日志中的截图信息
                        for i, step in enumerate(data_obj['steps']):
                            # 查找对应的日志条目
                            for entry in log_entries:
                                if entry.get("tag") == "function" and entry.get("data", {}):
                                    # 检查操作名称是否匹配
                                    log_op_name = entry.get("data", {}).get("name", "")
                                    html_op_name = step.get("code", {}).get("name", "")
                                    
                                    if log_op_name == html_op_name:
                                        # 检查时间戳是否接近
                                        if abs(entry.get("time", 0) - step.get("time", 0)) < 0.1:
                                            # 找到匹配的日志条目，提取screen信息
                                            if "screen" in entry.get("data", {}):
                                                step["screen"] = entry["data"]["screen"]
                                                print(f"修复步骤 {i} ({html_op_name}) 的截图引用")
                                                break
                    
                    # 写回修改后的JSON字符串
                    json_str = json.dumps(data_obj)
                    
                except json.JSONDecodeError:
                    print("JSON解析失败，使用正则表达式方法")
                    # 使用正则表达式方法作为备选
                    for img_file in img_map.values():
                        # 查找touch操作但没有截图的步骤
                        pattern = r'"name":\s*"touch".*?"screen":\s*null'
                        replacement = f'"name": "touch", "screen": {{"src": "log/{img_file}", "_filepath": "log/{img_file}", "thumbnail": "log/{img_file.replace(".", "_small.")}", "resolution": [1080, 2400], "pos": [], "vector": [], "rect": []}}'
                        json_str = re.sub(pattern, replacement, json_str)
                
                # 替换原始的JSON字符串
                modified_content = content[:json_start] + json_str + content[json_end:]
                content = modified_content
                
        # 写回修复后的内容
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(content)
            
        print(f"成功修复HTML报告的截图引用")
    except Exception as e:
        print(f"修复HTML报告失败: {str(e)}")
        traceback.print_exc()


# 生成汇总报告（保持不变）
def run_summary(data):
    """
    生成汇总报告 summary_report_YYYY-MM-DD-HH-MM-SS.html
    此报告包含所有测试设备的结果概览和链接到详细报告
    
    参数:
        data: 包含测试结果的字典，包括 'start', 'tests' 等字段
    
    返回:
        生成的汇总报告的文件路径，或者出错时返回空字符串
    """
    report_url = f"summary_report{CURRENT_TIME}.html"
    report_url_dir = os.path.join(report_dir, report_url)

    try:
        # 计算测试运行统计信息
        success_count = 0
        total_count = len(data['tests'])
        
        # 处理每个设备的报告信息
        for device, report_info in data['tests'].items():
            if report_info:  # 如果报告生成成功
                success_count += 1
                # 计算相对路径
                abs_report_path = report_info
                device_dir = os.path.dirname(abs_report_path)
                device_name = os.path.basename(device_dir).split('_')[0]
                # 由于报告和设备报告都在同一目录下，直接使用basename即可
                rel_path = f"{os.path.basename(device_dir)}/log.html"
                data['tests'][device] = {
                    'status': 0,  # 成功
                    'path': rel_path
                }
            else:  # 如果报告生成失败
                data['tests'][device] = {
                    'status': -1,  # 失败
                    'path': '#'
                }
        
        summary = {
            'time': "%.3f" % (time.time() - data['start']),
            'success': success_count,
            'count': total_count
        }
        summary.update(data)
        summary['start'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(data['start']))

        # 确保模板目录存在
        os.makedirs(template_dir, exist_ok=True)
        template_file = os.path.join(template_dir, 'report_tpl.html')
        
        # 检查模板文件是否存在
        if not os.path.exists(template_file):
            raise FileNotFoundError(f"汇总报告模板文件不存在: {template_file}")

        # 使用 Jinja2 渲染模板
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template('report_tpl.html')

        # 生成汇总报告 HTML
        with open(report_url_dir, "w", encoding="utf-8") as f:
            html_content = template.render(data=summary)
            f.write(html_content)
        print(f"汇总报告生成成功: {report_url_dir}")
        return report_url_dir
    except Exception as e:
        print(f"汇总报告生成失败: {e}")
        traceback.print_exc()
        return ""


# 在多台设备上并行运行测试
def run_on_multi_device(devices, scripts, results, run_all, device_names, show_screens=False):
    tasks = []
    for device in devices:
        serial = device.serial
        device_name = device_names[serial]
        print(f"⚠️ 当前测试设备: {device_name}")
        if not run_all and device_name in results['tests'] and results['tests'][device_name]['status'] == 0:
            print(f"❌ 跳过设备 {device_name}")
            continue

        log_dir = get_log_dir(device_name)
        t = Thread(target=replay_device, args=(
            device, scripts, screenshot_queue, action_queue, Event(), device_name, log_dir),
                   kwargs={"show_screens": show_screens})
        t.daemon = True
        t.start()
        tasks.append({
            'thread': t,
            'dev': device_name,
            'log_dir': log_dir
        })
    return tasks


# 主测试流程
def run(devices, scripts, device_names, show_screens=False, run_all=False):
    """运行主测试流程"""
    # 加载测试进度数据
    results = load_json_data(run_all)
    
    # 创建报告基础目录
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    os.makedirs(report_dir, exist_ok=True)
    
    # 在多设备上运行测试
    tasks = run_on_multi_device(devices, scripts, results, run_all, device_names, show_screens)
    success_count = 0

    # 对每个设备生成报告
    for task in tasks:
        task['thread'].join()
        # 报告目录就是日志目录
        device_report_dir = task['log_dir']
        
        # 复制脚本文件到报告目录
        script_path = None
        if scripts and scripts[0].get('path'):
            script_path = scripts[0]['path']
            
        # 生成报告
        device_report = run_one_report(device_report_dir, device_report_dir, script_path)
        # 更新报告路径为log.html的绝对路径
        report_path = os.path.join(device_report_dir, "log.html") if device_report else None
        results['tests'][task['dev']] = report_path
        
        if device_report:
            success_count += 1
            print(f"设备 {task['dev']} 测试成功")
        else:
            print(f"设备 {task['dev']} 测试失败")

    # 生成汇总报告
    print(f"开始生成汇总报告，成功率: {success_count}/{len(tasks)}")
    summary_report = run_summary(results)
    
    # 返回结果
    result_str = f"成功 {success_count}/{len(tasks)}"
    return result_str, summary_report


# 回放步骤
def replay_steps(scripts, show_screens=False):
    global model, devices

    loaded_scripts = []
    for script_config in scripts:
        script_path = script_config["path"]
        if not os.path.exists(script_path):
            print(f"文件 {script_path} 不存在，跳过")
            continue
        loaded_scripts.append(script_config)

    if not loaded_scripts:
        print("未加载任何有效脚本，回放终止")
        return False

    device_names = {}
    for device in devices:
        serial = device.serial
        try:
            airtest_device = connect_device(f"Android:///{serial}")
            device_names[serial] = get_device_name(airtest_device)
            airtest_device.serial = serial
            print(f"设备 {device_names[serial]} 连接成功")
        except Exception as e:
            print(f"设备 {serial} 连接失败: {e}")
            continue

    print(f"加载脚本: {', '.join(s['path'] for s in loaded_scripts)}")
    print(f"检测到 {len(devices)} 个设备: {[device_names[d.serial] for d in devices]}")
    print("开始回放")
    log({"msg": "Start replay", "success": True})

    # 启动检测服务线程
    stop_event = Event()
    detection_thread = Thread(target=detection_service, args=(screenshot_queue, click_queue, stop_event))
    detection_thread.daemon = True
    detection_thread.start()

    try:
        result, report_url = run(devices, loaded_scripts, device_names, show_screens=show_screens, run_all=False)
        print(f"执行结果: {result}, 报告地址: {report_url}")
        return True
    except Exception as e:
        print(f"回放失败: {e}")
        return False
    finally:
        # 停止检测服务线程
        stop_event.set()
        detection_thread.join()


# 主程序
def main():
    parser = argparse.ArgumentParser(description="设备回放脚本")
    parser.add_argument("--show-screens", action="store_true", help="显示所有设备画面并同步回放")
    parser.add_argument("--script", action="append", help="指定回放步骤文件，可多次使用")
    parser.add_argument("--loop-count", type=int, action="append", help="指定循环次数，逐脚本应用")
    parser.add_argument("--max-duration", type=float, action="append", help="指定最大运行时间（秒），逐脚本应用")

    args = parser.parse_args()
    scripts = []

    if args.script:
        # 解析命令行参数，按照顺序重建脚本配置
        arg_values = sys.argv[1:]
        script_configs = []
        current_config = None
        
        i = 0
        while i < len(arg_values):
            arg = arg_values[i]
            
            if arg == "--script":
                # 如果已有配置，保存它
                if current_config is not None:
                    script_configs.append(current_config)
                
                # 创建新的脚本配置
                if i + 1 < len(arg_values) and not arg_values[i + 1].startswith("--"):
                    script_path = arg_values[i + 1]
                    current_config = {"path": script_path}
                    i += 2
                else:
                    print("警告: --script 参数缺少值")
                    i += 1
            
            elif arg == "--loop-count" and current_config is not None:
                # 将循环次数应用于当前配置
                if i + 1 < len(arg_values) and not arg_values[i + 1].startswith("--"):
                    try:
                        current_config["loop_count"] = int(arg_values[i + 1])
                        i += 2
                    except ValueError:
                        print(f"警告: 无效的循环次数值: {arg_values[i + 1]}")
                        i += 2
                else:
                    print("警告: --loop-count 参数缺少值")
                    i += 1
            
            elif arg == "--max-duration" and current_config is not None:
                # 将最大执行时间应用于当前配置
                if i + 1 < len(arg_values) and not arg_values[i + 1].startswith("--"):
                    try:
                        current_config["max_duration"] = float(arg_values[i + 1])
                        i += 2
                    except ValueError:
                        print(f"警告: 无效的最大执行时间值: {arg_values[i + 1]}")
                        i += 2
                else:
                    print("警告: --max-duration 参数缺少值")
                    i += 1
            
            else:
                # 跳过其他参数
                i += 1
        
        # 添加最后一个配置
        if current_config is not None:
            script_configs.append(current_config)
        
        # 将解析出的配置传递给脚本
        scripts = script_configs
        
        # 打印解析结果以便调试
        print("解析命令行参数结果:")
        for i, config in enumerate(scripts):
            print(f"脚本 {i+1}: {config}")

    if not scripts:
        parser.error("必须使用 --script 指定至少一个脚本文件")

    global devices, model
    devices = adb.device_list()
    if not devices:
        print("错误: 未检测到 ADB 设备")
        exit(1)

    try:
        model = YOLO("/Users/helloppx/PycharmProjects/GameAI/outputs/train/weights/best.pt")
    except Exception as e:
        print(f"模型加载失败: {e}")
        exit(1)

    try:
        success = replay_steps(scripts, show_screens=args.show_screens)
        if not success:
            print("回放失败，请检查日志")
        else:
            print("回放成功")
    except Exception as e:
        print(f"回放失败: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()

def generate_reports(results, script_path=None):
    """
    生成测试报告，按照Airtest标准结构
    
    参数:
        results: 包含测试结果的字典，格式如下:
                {'logs': {设备名: 日志目录}, 'tests': {设备名: 报告结果}, 'success_count': 成功数量}
        script_path: 可选的脚本文件路径，如果提供则会复制到报告目录
        
    返回:
        bool: 是否成功生成报告
    """
    try:
        import traceback
        from datetime import datetime
        
        # 创建标准Airtest结构的报告目录
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        
        # 根目录
        base_dir = os.path.dirname(os.getcwd())
        project_name = os.path.basename(os.getcwd())  # 使用当前目录名作为项目名称
        
        # 按ka2-reports-demo创建标准结构
        # project_name-reports-demo/
        #   - ui_reports/  (汇总报告)
        #   - ui_run/      (代码目录)
        #     - project_name.air/  (项目目录)
        #       - log/             (设备报告目录)
        
        # 创建报告根目录
        reports_base = os.path.join(os.getcwd(), "outputs", project_name + "-reports")
        os.makedirs(reports_base, exist_ok=True)
        
        # 创建ui_reports目录 - 存放汇总报告
        ui_reports_dir = os.path.join(reports_base, "ui_reports")
        os.makedirs(ui_reports_dir, exist_ok=True)
        
        # 创建ui_run目录 - 运行代码目录
        ui_run_dir = os.path.join(reports_base, "ui_run")
        os.makedirs(ui_run_dir, exist_ok=True)
        
        # 创建项目目录 - project_name.air
        project_air_dir = os.path.join(ui_run_dir, f"{project_name}.air")
        os.makedirs(project_air_dir, exist_ok=True)
        
        # 创建log目录 - 存放设备报告
        project_log_dir = os.path.join(project_air_dir, "log")
        os.makedirs(project_log_dir, exist_ok=True)
        
        # 初始化结果计数器
        if 'success_count' not in results:
            results['success_count'] = 0
        
        if 'tests' not in results:
            results['tests'] = {}
            
        # 确保logs字段存在
        if 'logs' not in results:
            print("错误: results中缺少logs字段")
            return False
            
        # 为每个设备生成报告
        device_reports = {}
        for device_name, log_dir in results['logs'].items():
            if not os.path.exists(log_dir):
                print(f"警告: 设备 {device_name} 的日志目录不存在: {log_dir}")
                results['tests'][device_name] = False
                continue
                
            # 为每个设备创建单独的报告目录
            device_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            device_report_dir = os.path.join(project_log_dir, f"{device_name}_{device_timestamp}")
            os.makedirs(device_report_dir, exist_ok=True)
            
            # 生成设备报告
            print(f"为设备 {device_name} 生成报告...")
            device_report = run_one_report(log_dir, device_report_dir, script_path)
            results['tests'][device_name] = device_report
            
            if device_report:
                results['success_count'] += 1
                device_reports[device_name] = os.path.join(device_report_dir, "log.html")
                print(f"设备 {device_name} 报告生成成功")
            else:
                print(f"设备 {device_name} 报告生成失败")

        # 生成汇总报告到ui_reports目录
        total_tests = len(results['logs'])
        success_rate = (results['success_count'] / total_tests * 100) if total_tests > 0 else 0
        
        summary_report = os.path.join(ui_reports_dir, f"summary_report_{timestamp}.html")
        with open(summary_report, "w", encoding="utf-8") as f:
            f.write(f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>回放测试报告汇总</title>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
                    h1 {{ color: #333; border-bottom: 1px solid #ddd; padding-bottom: 10px; }}
                    .summary {{ background-color: #f8f8f8; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                    .devices {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px; }}
                    .device {{ padding: 15px; border: 1px solid #ddd; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                    .device h2 {{ margin-top: 0; color: #444; font-size: 1.2em; }}
                    .success {{ color: green; }}
                    .failure {{ color: red; }}
                    a {{ color: #0066cc; text-decoration: none; }}
                    a:hover {{ text-decoration: underline; }}
                    .progress-bar {{ 
                        height: 20px; 
                        background-color: #e0e0e0; 
                        border-radius: 10px; 
                        margin-bottom: 10px;
                        overflow: hidden;
                    }}
                    .progress {{ 
                        height: 100%; 
                        background-color: #4CAF50; 
                        border-radius: 10px; 
                        width: {success_rate}%;
                    }}
                </style>
            </head>
            <body>
                <h1>回放测试报告汇总</h1>
                
                <div class="summary">
                    <p><strong>生成时间:</strong> {timestamp.replace('-', '年' if timestamp.count('-') == 1 else '月' if timestamp.count('-') == 2 else '-').replace('-', '日', 1).replace('-', '时', 1).replace('-', '分', 1)}秒</p>
                    <p><strong>总测试设备数:</strong> {total_tests}</p>
                    <p><strong>成功生成报告数:</strong> {results['success_count']}</p>
                    <p><strong>成功率:</strong> {success_rate:.1f}%</p>
                    <div class="progress-bar">
                        <div class="progress"></div>
                    </div>
                </div>
                
                <div class="devices">
                    {''.join([
                        f'''
                        <div class="device">
                            <h2>设备: {dev}</h2>
                            <p class="{'success' if success else 'failure'}">
                                状态: {'成功' if success else '失败'}
                            </p>
                            {f'<p><a href="../ui_run/{project_name}.air/log/{dev}_{device_timestamp}/log.html" target="_blank">查看详细报告</a></p>' if dev in device_reports else '<p>无法生成报告</p>'}
                        </div>
                        '''
                        for dev, success in results['tests'].items()
                    ])}
                </div>
            </body>
            </html>
            """)
        
        print(f"汇总报告已生成: {summary_report}")
        print(f"共测试 {total_tests} 个设备，成功生成 {results['success_count']} 个报告，成功率: {success_rate:.1f}%")
        print(f"报告结构已保存在: {reports_base}")
        
        return True
    except Exception as e:
        print(f"报告生成失败: {str(e)}")
        traceback.print_exc()
        return False