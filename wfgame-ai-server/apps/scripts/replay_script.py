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
import random
import torch
import re
from utils import load_yolo_model  # 导入模型加载公共函数

# 禁用 Ultralytics 的日志输出
logging.getLogger("ultralytics").setLevel(logging.CRITICAL)

# 全局变量
model = None
devices = []
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CURRENT_TIME = "_" + time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime(time.time()))
template_dir = os.path.join(BASE_DIR, "templates")  # 模板目录路径

# 定义报告基础目录
reports_base_dir = os.path.join(BASE_DIR, "outputs", "WFGameAI-reports")
# 定义UI报告目录
ui_reports_dir = os.path.join(reports_base_dir, "ui_reports")
# 定义运行代码目录
ui_run_dir = os.path.join(reports_base_dir, "ui_run")
# 定义项目目录
project_air_dir = os.path.join(ui_run_dir, "WFGameAI.air")
# 定义设备日志目录
device_log_dir = os.path.join(project_air_dir, "log")

# 确保目录存在
os.makedirs(reports_base_dir, exist_ok=True)
os.makedirs(ui_reports_dir, exist_ok=True)
os.makedirs(ui_run_dir, exist_ok=True)
os.makedirs(project_air_dir, exist_ok=True)
os.makedirs(device_log_dir, exist_ok=True)
os.makedirs(template_dir, exist_ok=True)

# 设置Airtest日志存储目录，避免在根目录生成日志文件
set_logdir(project_air_dir)
airtest.core.api.ST.LOG_DIR = project_air_dir  # 显式设置静态变量

# 旧目录结构（保留以兼容现有代码）
report_dir = os.path.join(BASE_DIR, "outputs/device_reports")
os.makedirs(report_dir, exist_ok=True)

screenshot_queue = queue.Queue()
action_queue = queue.Queue()
click_queue = queue.Queue()  # 新增全局 click_queue

# 固定种子
random.seed(42)
np.random.seed(42)
torch.manual_seed(42)

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
    """
    获取设备的友好名称
    :param device: adb设备对象
    :return: 设备友好名称
    """
    try:
        brand = device.shell("getprop ro.product.brand").strip()
        model = device.shell("getprop ro.product.model").strip()
        resolution = device.shell("wm size").strip().replace("Physical size: ", "")
        
        # 清理和规范化设备信息
        brand = "".join(c for c in brand if c.isalnum() or c in ('-', '_'))
        model = "".join(c for c in model if c.isalnum() or c in ('-', '_'))
        resolution = "".join(c for c in resolution if c.isalnum() or c in ('-', '_'))
        
        # 组合设备名称
        device_name = f"{brand}-{model}-{resolution}"
        return device_name
    except Exception as e:
        print(f"获取设备 {device.serial} 信息失败: {e}")
        # 返回清理后的序列号作为后备名称
        return "".join(c for c in device.serial if c.isalnum() or c in ('-', '_'))


# 检测按钮
def detect_buttons(frame, target_class=None):
    frame_for_detection = cv2.resize(frame, (640, 640))
    try:
        # 使用当前设备进行预测
        results = model.predict(source=frame_for_detection, imgsz=640, conf=0.3, verbose=False)
        orig_h, orig_w = frame.shape[:2]
        scale_x, scale_y = orig_w / 640, orig_h / 640

        for box in results[0].boxes:
            cls_id = int(box.cls.item())
            detected_class = model.names[cls_id]
            if detected_class == target_class:
                box_x, box_y = box.xywh[0][:2].tolist()
                x, y = box_x * scale_x, box_y * scale_y
                return True, (x, y, detected_class)
    except Exception as e:
        print(f"按钮检测失败: {e}")
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
    """获取日志目录"""
    # 清理设备名称，移除任何可能导致路径问题的字符
    device_dir = "".join(c for c in dev if c.isalnum() or c in ('-', '_'))
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    
    # 使用新目录结构
    log_dir = os.path.join(device_log_dir, f"{device_dir}_{timestamp}")
    os.makedirs(log_dir, exist_ok=True)
    
    # 创建log子目录
    log_images_dir = os.path.join(log_dir, "log")
    os.makedirs(log_images_dir, exist_ok=True)
    
    # 检查log文件是否存在，如果不存在则创建空文件
    log_file = os.path.join(log_dir, "log.txt")
    if not os.path.exists(log_file):
        with open(log_file, 'w', encoding='utf-8') as f:
            pass
    
    # 为每个设备单独设置日志目录，避免日志混乱
    airtest.core.api.ST.LOG_DIR = log_dir
    set_logdir(log_dir)
    
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
    # 为当前设备设置日志目录
    set_logdir(log_dir)
    airtest.core.api.ST.LOG_DIR = log_dir  # 确保Airtest使用正确的日志目录
    
    # 打印参数（用于调试）
    print(f"设备: {device_name}, 脚本: {scripts}, 日志目录: {log_dir}")
    print(f"show_screens: {show_screens}, loop_count: {loop_count}")

    # 模拟设备初始化
    print(f"开始回放设备: {device_name}, 脚本: {scripts}")

    # 检查脚本列表是否为空
    if not scripts:
        raise ValueError("脚本列表为空，无法回放")

    # 创建log.txt文件 - 确保存在正确位置
    log_txt_path = os.path.join(log_dir, "log.txt")
    with open(log_txt_path, "w", encoding="utf-8") as f:
        f.write("")  # 创建空文件

    # 记录测试开始日志 - 只记录用户明确指定的脚本
    start_time = time.time()
    script_paths = [s['path'] for s in scripts]
    start_entry = {
        "tag": "function", 
        "depth": 1,
        "time": start_time,
        "data": {
            "name": "开始测试",
            "call_args": {"device": device_name, "scripts": script_paths},
            "start_time": start_time - 0.001, 
            "ret": True,
            "end_time": start_time
        }
    }
    with open(log_txt_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(start_entry, ensure_ascii=False) + "\n")

    # 获取设备屏幕截图作为初始状态记录
    try:
        timestamp = time.time()
        screenshot = device.screenshot()
        frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        
        # 保存截图
        screenshot_timestamp = int(timestamp * 1000)
        screenshot_filename = f"{screenshot_timestamp}.jpg"
        screenshot_path = os.path.join(log_dir, screenshot_filename)
        cv2.imwrite(screenshot_path, frame)
        print(f"保存初始截图: {screenshot_path}")
        
        # 创建缩略图
        thumbnail_filename = f"{screenshot_timestamp}_small.jpg"
        thumbnail_path = os.path.join(log_dir, thumbnail_filename)
        small_frame = cv2.resize(frame, (0, 0), fx=0.3, fy=0.3)
        cv2.imwrite(thumbnail_path, small_frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
        
        # 获取屏幕分辨率
        height, width = frame.shape[:2]
        resolution = [width, height]
        
        # 记录初始截图
        snapshot_entry = {
            "tag": "function", 
            "depth": 3,
            "time": timestamp,
            "data": {
                "name": "try_log_screen",
                "call_args": {"screen": "array([[[...]]],dtype=uint8)", "quality": None, "max_size": None},
                "start_time": timestamp - 0.001, 
                "ret": {"screen": screenshot_filename, "resolution": resolution},
                "end_time": timestamp
            }
        }
        with open(log_txt_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(snapshot_entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"获取初始截图失败: {e}")

    # 执行所有脚本
    total_step_counter = 0
    has_executed_steps = False
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
            
            # 记录空脚本日志
            empty_script_entry = {
                "tag": "function", 
                "depth": 2,
                "time": time.time(),
                "data": {
                    "name": "empty_script",
                    "call_args": {"script_path": script_path},
                    "start_time": time.time() - 0.001, 
                    "ret": False,
                    "end_time": time.time()
                }
            }
            with open(log_txt_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(empty_script_entry, ensure_ascii=False) + "\n")
            
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
            
            if is_priority_based:
                priority_start_time = time.time()  # 记录优先级模式的实际开始时间
                print(f"优先级模式开始时间: {priority_start_time}, 最大执行时间: {max_duration}秒")
                
                # 优先级模式处理逻辑
                detection_count = 0
                priority_step_counter = 0
                start_check_time = time.time()
                
                # 持续检测直到超出最大时间
                while max_duration is None or (time.time() - priority_start_time) <= max_duration:
                    # 记录当前处理轮次
                    cycle_count = detection_count // len(steps) + 1
                    print(f"第 {cycle_count} 轮尝试检测，已检测 {detection_count} 次")
                    
                    # 检测是否有任何目标匹配
                    matched_any_target = False
                    unknown_fallback_step = None
                    
                    # 对于每一个优先级步骤，按优先级顺序尝试检测
                    for step_idx, step in enumerate(steps):
                        # 检查是否达到最大时间
                        if max_duration is not None and (time.time() - priority_start_time) > max_duration:
                            print(f"优先级模式已达到最大执行时间 {max_duration}秒，停止执行")
                            break

                        step_class = step["class"]
                        step_remark = step.get("remark", "")
                        priority = step.get("Priority", 999)
                        
                        # 记录unknown步骤作为备选
                        if step_class == "unknown":
                            unknown_fallback_step = step
                            continue
                        
                        print(f"尝试优先级步骤 P{priority}: {step_class}, 备注: {step_remark}")
                        
                        # 截取屏幕以检测目标
                        timestamp = time.time()
                        screenshot = device.screenshot()
                        frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                        if frame is None:
                            raise ValueError("无法获取设备屏幕截图")
                        
                        # 使用纯时间戳作为截图文件名 (是Airtest标准)
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
                        
                        # 将截图和检测任务放入队列
                        detection_count += 1
                        screenshot_queue.put((device_name, detection_count, frame, step_class, None))
                        
                        # 等待检测结果
                        try:
                            success, (x, y, detected_class) = click_queue.get(timeout=5)
                            
                            # 记录snapshot
                            snapshot_entry = {
                                "tag": "function", 
                                "depth": 3,
                                "time": timestamp,
                                "data": {
                                    "name": "try_log_screen",
                                    "call_args": {"screen": "array([[[...]]],dtype=uint8)", "quality": None, "max_size": None},
                                    "start_time": timestamp - 0.001, 
                                    "ret": {"screen": screenshot_filename, "resolution": resolution},
                                    "end_time": timestamp
                                }
                            }
                            
                            with open(log_txt_path, "a", encoding="utf-8") as f:
                                f.write(json.dumps(snapshot_entry, ensure_ascii=False) + "\n")
                            
                            if success:
                                matched_any_target = True
                                # 准备screen对象
                                screen_object = {
                                    "src": screenshot_filename,
                                    "_filepath": screenshot_filename,
                                    "thumbnail": thumbnail_filename,
                                    "resolution": resolution,
                                    "pos": [[int(x), int(y)]],
                                    "vector": [],
                                    "confidence": 0.85,
                                    "rect": [{"left": int(x)-50, "top": int(y)-50, "width": 100, "height": 100}]
                                }
                                
                                # 如果有相对位置设置，使用相对位置
                                if "relative_x" in step and "relative_y" in step:
                                    rel_x = float(step["relative_x"])
                                    rel_y = float(step["relative_y"])
                                    # 计算绝对坐标
                                    abs_x = int(width * rel_x)
                                    abs_y = int(height * rel_y)
                                    print(f"使用相对位置 ({rel_x}, {rel_y}) -> 绝对位置 ({abs_x}, {abs_y})")
                                    x, y = abs_x, abs_y
                                
                                # 执行点击操作
                                device.shell(f"input tap {int(x)} {int(y)}")
                                print(f"设备 {device_name} 执行优先级步骤 P{priority}: {detected_class}，点击位置: ({int(x)}, {int(y)})")
                                
                                # 准备显示文本 - 优先使用remark，如果为空则使用class
                                display_text = step.get("remark", "") or detected_class or "点击"
                                
                                # 记录touch操作
                                touch_entry = {
                                    "tag": "function", 
                                    "depth": 1,
                                    "time": timestamp + 0.001,
                                    "data": {
                                        "name": "touch",
                                        "call_args": {"v": [int(x), int(y)]},
                                        "start_time": timestamp + 0.0005,
                                        "ret": [int(x), int(y)],
                                        "end_time": timestamp + 0.001,
                                        "screen": screen_object,
                                        # 添加描述字段，优先使用remark，如果为空则使用class
                                        "desc": display_text,
                                        # 添加标题字段，用于左侧步骤列表显示
                                        "title": f"#{priority_step_counter} {display_text}",
                                        # 添加原始类别信息，确保报告可以获取
                                        "original_class": detected_class,
                                        "original_remark": step.get("remark", ""),
                                        # 添加自定义字段，确保在处理data模型时能识别这是自定义操作
                                        "is_custom_action": True,
                                        "custom_display_text": display_text,
                                        "custom_step_title": f"#{priority_step_counter} {display_text}",
                                        # 添加步骤信息，方便日志分析
                                        "step_number": step.get("step", priority_step_counter)
                                    }
                                }
                                
                                with open(log_txt_path, "a", encoding="utf-8") as f:
                                    f.write(json.dumps(touch_entry,ensure_ascii=False) + "\n")
                                
                                has_executed_steps = True
                                priority_step_counter += 1
                                step_counter += 1
                                total_step_counter += 1
                                
                                # 执行操作后暂停一段时间，让UI响应
                                time.sleep(1.0)
                                # 跳出循环，从第一个优先级步骤重新开始检测
                                break
                            else:
                                print(f"未检测到目标 {step_class}，尝试下一个优先级步骤")
                                
                                # 检查JSON步骤是否包含step字段，如果有则记录失败信息
                                if "step" in step:
                                    step_num = step.get("step", step_idx+1)
                                    step_remark = step.get("remark", "")
                                    
                                    # 创建screen对象，确保断言失败时也有截图
                                    screen_object = {
                                        "src": screenshot_filename,
                                        "_filepath": screenshot_filename,
                                        "thumbnail": thumbnail_filename,
                                        "resolution": resolution,
                                        "pos": [],  # 空位置表示没找到目标
                                        "vector": [],
                                        "confidence": 0,  # 置信度为0
                                        "rect": []  # 空区域
                                    }
                                    
                                    # 记录exists失败操作
                                    fail_entry = {
                                        "tag": "function", 
                                        "depth": 1,
                                        "time": timestamp + 0.001,
                                        "data": {
                                            "name": "exists",
                                            "call_args": {"v": step_class},
                                            "start_time": timestamp + 0.0005, 
                                            "ret": None,
                                            "end_time": timestamp + 0.001,
                                            "screen": screen_object
                                        }
                                    }
                                    
                                    with open(log_txt_path, "a", encoding="utf-8") as f:
                                        f.write(json.dumps(fail_entry, ensure_ascii=False) + "\n")
                                    
                                    # 为断言步骤生成自定义显示文本
                                    assertion_title = f"步骤{step_num}: {step_remark}"
                                    
                                    # 记录断言失败 - 确保包含screen字段
                                    fail_assert_entry = {
                                        "tag": "function", 
                                        "depth": 1,
                                        "time": timestamp + 0.002,
                                        "data": {
                                            "name": "assert_exists",
                                            "call_args": {"v": step_class, "msg": assertion_title},
                                            "start_time": timestamp + 0.0015, 
                                            "ret": {
                                                "result": False,
                                                "expected": "True", 
                                                "actual": "False",
                                                "reason": f"未找到元素: {step_class}"
                                            },
                                            "traceback": f"步骤{step_num}失败: 未检测到目标 {step_class}\n{step_remark}",
                                            "end_time": timestamp + 0.002,
                                            "screen": screen_object,  # 使用相同的screen对象
                                            # 添加自定义字段
                                            "custom_display_text": step_remark,
                                            "custom_step_title": f"#{step_num} 断言: {step_remark}",
                                            "is_custom_assertion": True,
                                            "step_number": step_num
                                        }
                                    }
                                    
                                    with open(log_txt_path, "a", encoding="utf-8") as f:
                                        f.write(json.dumps(fail_assert_entry, ensure_ascii=False) + "\n")
                                    
                                    print(f"已记录优先级步骤 {step_num} 失败: {step_remark}")
                        
                        except queue.Empty:
                            print(f"检测 {step_class} 超时，尝试下一个优先级步骤")
                            
                            # 检查JSON步骤是否包含step字段，如果有则记录失败信息
                            if "step" in step:
                                step_num = step.get("step", step_idx+1)
                                step_remark = step.get("remark", "")
                                
                                # 创建screen对象，确保超时情况也有截图
                                screen_object = {
                                    "src": screenshot_filename,
                                    "_filepath": screenshot_filename,
                                    "thumbnail": thumbnail_filename,
                                    "resolution": resolution,
                                    "pos": [],  # 空位置表示没找到目标
                                    "vector": [],
                                    "confidence": 0,  # 置信度为0
                                    "rect": []  # 空区域
                                }
                                
                                # 记录exists超时失败
                                timeout_entry = {
                                    "tag": "function", 
                                    "depth": 1,
                                    "time": timestamp + 0.001,
                                    "data": {
                                        "name": "exists",
                                        "call_args": {"v": step_class},
                                        "start_time": timestamp + 0.0005, 
                                        "ret": None,
                                        "end_time": timestamp + 0.001,
                                        "screen": screen_object
                                    }
                                }
                                
                                with open(log_txt_path, "a", encoding="utf-8") as f:
                                    f.write(json.dumps(timeout_entry, ensure_ascii=False) + "\n")
                                
                                # 为断言步骤生成自定义显示文本
                                timeout_title = f"步骤{step_num}超时: {step_remark}"
                                
                                # 记录assert_exists超时失败 - 确保包含screen字段
                                timeout_assert_entry = {
                                    "tag": "function", 
                                    "depth": 1,
                                    "time": timestamp + 0.002,
                                    "data": {
                                        "name": "assert_exists",
                                        "call_args": {"v": step_class, "msg": timeout_title},
                                        "start_time": timestamp + 0.0015, 
                                        "ret": {
                                            "result": False,
                                            "expected": "True", 
                                            "actual": "False",
                                            "reason": f"检测超时: {step_class}"
                                        },
                                        "traceback": f"步骤{step_num}失败: 检测超时 {step_class}\n{step_remark}",
                                        "end_time": timestamp + 0.002,
                                        "screen": screen_object,  # 使用相同的screen对象
                                        # 添加自定义字段
                                        "custom_display_text": step_remark,
                                        "custom_step_title": f"#{step_num} 断言超时: {step_remark}",
                                        "is_custom_assertion": True,
                                        "step_number": step_num
                                    }
                                }
                                
                                with open(log_txt_path, "a", encoding="utf-8") as f:
                                    f.write(json.dumps(timeout_assert_entry, ensure_ascii=False) + "\n")
                                
                                print(f"已记录优先级步骤 {step_num} 超时失败: {step_remark}")
                    
                    # 如果所有目标都未匹配，但有unknown备选步骤，则执行unknown步骤
                    if not matched_any_target and unknown_fallback_step is not None:
                        print(f"未检测到任何目标，执行备选步骤 class=unknown: {unknown_fallback_step.get('remark', '')}")
                        
                        # 获取最后一次截图的分辨率
                        height, width = frame.shape[:2]
                        
                        # 使用相对坐标
                        if "relative_x" in unknown_fallback_step and "relative_y" in unknown_fallback_step:
                            rel_x = float(unknown_fallback_step["relative_x"])
                            rel_y = float(unknown_fallback_step["relative_y"])
                            # 计算绝对坐标
                            abs_x = int(width * rel_x)
                            abs_y = int(height * rel_y)
                            print(f"使用unknown备选相对位置 ({rel_x}, {rel_y}) -> 绝对位置 ({abs_x}, {abs_y})")
                            
                            # 准备screen对象
                            screen_object = {
                                "src": screenshot_filename,
                                "_filepath": screenshot_filename,
                                "thumbnail": thumbnail_filename,
                                "resolution": resolution,
                                "pos": [[abs_x, abs_y]],
                                "vector": [],
                                "confidence": 0.85,
                                "rect": [{"left": abs_x-50, "top": abs_y-50, "width": 100, "height": 100}]
                            }
                            
                            # 执行点击操作
                            device.shell(f"input tap {abs_x} {abs_y}")
                            print(f"设备 {device_name} 执行unknown备选步骤，点击位置: ({abs_x}, {abs_y})")
                            
                            # 准备显示文本 - 优先使用remark，如果为空则使用类型
                            display_text = unknown_fallback_step.get("remark", "") or "备选点击"
                            
                            # 记录touch操作
                            touch_entry = {
                                "tag": "function", 
                                "depth": 1,
                                "time": timestamp + 0.001,
                                "data": {
                                    "name": "touch",
                                    "call_args": {"v": [abs_x, abs_y]},
                                    "start_time": timestamp + 0.0005,
                                    "ret": [abs_x, abs_y],
                                    "end_time": timestamp + 0.001,
                                    "screen": screen_object,
                                    # 添加描述字段，优先使用remark，如果为空则使用默认文本
                                    "desc": display_text,
                                    # 添加标题字段，用于左侧步骤列表显示
                                    "title": f"#{priority_step_counter} {display_text}",
                                    # 添加原始类别信息，确保报告可以获取
                                    "original_class": "unknown",
                                    "original_remark": unknown_fallback_step.get("remark", "")
                                }
                            }
                            
                            with open(log_txt_path, "a", encoding="utf-8") as f:
                                f.write(json.dumps(touch_entry,ensure_ascii=False) + "\n")
                            
                            has_executed_steps = True
                            priority_step_counter += 1
                            step_counter += 1
                            total_step_counter += 1
                            
                            # 执行操作后暂停一段时间，让UI响应
                            time.sleep(1.0)
                        else:
                            print("警告: unknown步骤未指定relative_x和relative_y，无法执行备选点击")
                    
                    # 如果已经超过30秒没有检测到任何步骤，则退出循环
                    if time.time() - start_check_time > 30 and priority_step_counter == 0:
                        print("连续30秒未检测到任何优先级步骤，停止检测")
                        break
                        
                    # 如果执行了某个步骤，重置计时器
                    if priority_step_counter > 0:
                        start_check_time = time.time()
                    
                    # 暂停一短暂时间再进行下一轮检测
                    time.sleep(0.5)
                
                print(f"优先级模式执行完成，检测次数: {detection_count}，成功执行步骤: {priority_step_counter}")
            else:
                # 普通脚本模式：按顺序执行每个步骤
                print(f"按顺序执行步骤，共 {len(steps)} 个步骤")
                for step_idx, step in enumerate(steps):
                    # 检查是否超过最大执行时间
                    if max_duration is not None and (time.time() - script_start_time) > max_duration:
                        print(f"脚本 {script_path} 已达到最大执行时间 {max_duration}秒，停止执行")
                        break
                        
                        step_counter += 1
                    total_step_counter += 1
                    step_class = step["class"]
                    step_remark = step.get("remark", "")
                    
                    print(f"执行步骤 {step_idx+1}/{len(steps)}: {step_class}, 备注: {step_remark}")
                    
                    # 截取屏幕以检测目标
                    timestamp = time.time()
                    screenshot = device.screenshot()
                    frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                    if frame is None:
                        raise ValueError("无法获取设备屏幕截图")
                    
                    # 使用纯时间戳作为截图文件名 (是Airtest标准)
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
                    
                    # 将截图和检测任务放入队列
                    screenshot_queue.put((device_name, total_step_counter, frame, step_class, None))
                    
                    # 等待检测结果
                    try:
                        success, (x, y, detected_class) = click_queue.get(timeout=5)
                        
                        # 记录snapshot
                        snapshot_entry = {
                            "tag": "function", 
                            "depth": 3,
                            "time": timestamp,
                            "data": {
                                "name": "try_log_screen",
                                "call_args": {"screen": "array([[[...]]],dtype=uint8)", "quality": None, "max_size": None},
                                "start_time": timestamp - 0.001, 
                                "ret": {"screen": screenshot_filename, "resolution": resolution},
                                "end_time": timestamp
                            }
                        }
                        
                        with open(log_txt_path, "a", encoding="utf-8") as f:
                            f.write(json.dumps(snapshot_entry, ensure_ascii=False) + "\n")
                        
                        if success:
                            # 准备screen对象
                            screen_object = {
                                "src": screenshot_filename,
                                "_filepath": screenshot_filename,
                                "thumbnail": thumbnail_filename,
                                "resolution": resolution,
                                "pos": [[int(x), int(y)]],
                                "vector": [],
                                "confidence": 0.85,
                                "rect": [{"left": int(x)-50, "top": int(y)-50, "width": 100, "height": 100}]
                            }
                            
                            # 执行点击操作
                            device.shell(f"input tap {int(x)} {int(y)}")
                            print(f"设备 {device_name} 执行步骤 {step_idx+1}: {detected_class}，点击位置: ({int(x)}, {int(y)})")
                            
                            # 准备显示文本 - 优先使用remark，如果为空则使用class
                            display_text = step.get("remark", "") or detected_class or "点击"
                            
                            # 记录touch操作
                            touch_entry = {
                                "tag": "function", 
                                "depth": 1,
                                "time": timestamp + 0.001,
                                "data": {
                                    "name": "touch",
                                    "call_args": {"v": [int(x), int(y)]},
                                    "start_time": timestamp + 0.0005,
                                    "ret": [int(x), int(y)],
                                    "end_time": timestamp + 0.001,
                                    "screen": screen_object,
                                    # 添加描述字段，优先使用remark，如果为空则使用class
                                    "desc": display_text,
                                    # 添加标题字段，用于左侧步骤列表显示
                                    "title": f"#{step_idx+1} {display_text}",
                                    # 添加原始类别信息，确保报告可以获取
                                    "original_class": detected_class,
                                    "original_remark": step.get("remark", ""),
                                    # 添加自定义字段，确保在处理data模型时能识别这是自定义操作
                                    "is_custom_action": True,
                                    "custom_display_text": display_text,
                                    "custom_step_title": f"#{step_idx+1} {display_text}",
                                    # 添加步骤信息，方便日志分析
                                    "step_number": step.get("step", step_idx+1)
                                }
                            }
                            
                            with open(log_txt_path, "a", encoding="utf-8") as f:
                                f.write(json.dumps(touch_entry,ensure_ascii=False) + "\n")
                            
                            has_executed_steps = True
                        else:
                            print(f"未检测到目标 {step_class}，跳过此步骤")
                            
                            # 检查JSON步骤是否包含step字段，如果有则记录失败信息
                            if "step" in step:
                                step_num = step.get("step", step_idx+1)
                                step_remark = step.get("remark", "")
                                
                                # 创建screen对象，确保断言失败时也有截图
                                screen_object = {
                                    "src": screenshot_filename,
                                    "_filepath": screenshot_filename,
                                    "thumbnail": thumbnail_filename,
                                    "resolution": resolution,
                                    "pos": [],  # 空位置表示没找到目标
                                    "vector": [],
                                    "confidence": 0,  # 置信度为0
                                    "rect": []  # 空区域
                                }
                                
                                # 记录exists失败操作
                                fail_entry = {
                                    "tag": "function", 
                                    "depth": 1,
                                    "time": timestamp + 0.001,
                                    "data": {
                                        "name": "exists",
                                        "call_args": {"v": step_class},
                                        "start_time": timestamp + 0.0005, 
                                        "ret": None,
                                        "end_time": timestamp + 0.001,
                                        "screen": screen_object
                                    }
                                }
                                
                                with open(log_txt_path, "a", encoding="utf-8") as f:
                                    f.write(json.dumps(fail_entry, ensure_ascii=False) + "\n")
                                
                                # 为断言步骤生成自定义显示文本
                                assertion_title = f"步骤{step_num}: {step_remark}"
                                
                                # 记录断言失败 - 确保包含screen字段
                                fail_assert_entry = {
                                    "tag": "function", 
                                    "depth": 1,
                                    "time": timestamp + 0.002,
                                    "data": {
                                        "name": "assert_exists",
                                        "call_args": {"v": step_class, "msg": assertion_title},
                                        "start_time": timestamp + 0.0015, 
                                        "ret": {
                                            "result": False,
                                            "expected": "True", 
                                            "actual": "False",
                                            "reason": f"未找到元素: {step_class}"
                                        },
                                        "traceback": f"步骤{step_num}失败: 未检测到目标 {step_class}\n{step_remark}",
                                        "end_time": timestamp + 0.002,
                                        "screen": screen_object,  # 使用相同的screen对象
                                        # 添加自定义字段
                                        "custom_display_text": step_remark,
                                        "custom_step_title": f"#{step_num} 断言: {step_remark}",
                                        "is_custom_assertion": True,
                                        "step_number": step_num
                                    }
                                }
                                
                                with open(log_txt_path, "a", encoding="utf-8") as f:
                                    f.write(json.dumps(fail_assert_entry, ensure_ascii=False) + "\n")
                                
                                print(f"已记录步骤 {step_num} 失败: {step_remark}")
                    
                    except queue.Empty:
                        print(f"检测 {step_class} 超时，跳过此步骤")
                        
                        # 检查JSON步骤是否包含step字段，如果有则记录失败信息
                        if "step" in step:
                            step_num = step.get("step", step_idx+1)
                            step_remark = step.get("remark", "")
                            
                            # 创建screen对象，确保超时情况也有截图
                            screen_object = {
                                "src": screenshot_filename,
                                "_filepath": screenshot_filename,
                                "thumbnail": thumbnail_filename,
                                "resolution": resolution,
                                "pos": [],  # 空位置表示没找到目标
                                "vector": [],
                                "confidence": 0,  # 置信度为0
                                "rect": []  # 空区域
                            }
                            
                            # 记录超时失败日志 - 使用exists和assert_exists组合
                            timeout_entry = {
                                "tag": "function", 
                                "depth": 1,
                                "time": timestamp + 0.001,
                                "data": {
                                    "name": "exists",  # 改为exists函数
                                    "call_args": {"v": step_class},
                                    "start_time": timestamp + 0.0005, 
                                    "ret": None,  # 设为None或False表示不存在
                                    "end_time": timestamp + 0.001,
                                    "screen": screen_object
                                }
                            }
                            
                            with open(log_txt_path, "a", encoding="utf-8") as f:
                                f.write(json.dumps(timeout_entry, ensure_ascii=False) + "\n")
                            
                            # 添加一个明确的失败日志条目
                            timeout_assert_entry = {
                                "tag": "function", 
                                "depth": 1,
                                "time": timestamp + 0.002,
                                "data": {
                                    "name": "assert_exists",  # 使用assert_exists
                                    "call_args": {"v": step_class, "msg": f"步骤{step_num}: {step_remark}"},
                                    "start_time": timestamp + 0.0015, 
                                    "ret": {
                                        "result": False,
                                        "expected": "True", 
                                        "actual": "False",
                                        "reason": f"检测超时: {step_class}"
                                    },
                                    "traceback": f"步骤{step_num}失败: 检测超时 {step_class}\n{step_remark}",
                                    "end_time": timestamp + 0.002,
                                    "screen": screen_object,  # 使用相同的screen对象
                                    # 添加自定义字段
                                    "custom_display_text": step_remark,
                                    "custom_step_title": f"#{step_num} 断言: {step_remark}",
                                    "is_custom_assertion": True,
                                    "step_number": step_num
                                }
                            }
                            
                            with open(log_txt_path, "a", encoding="utf-8") as f:
                                f.write(json.dumps(timeout_assert_entry, ensure_ascii=False) + "\n")
                            
                            print(f"已记录步骤 {step_num} 超时失败: {step_remark}")
                    
                    # 等待一段时间，让UI响应
                    time.sleep(0.5)
                
                # 执行完所有步骤
                print(f"已完成执行 {len(steps)} 个步骤")
            
            # 检查是否因最大执行时间而中断循环
            if max_duration is not None and (time.time() - script_start_time) > max_duration:
                print(f"脚本 {script_path} 已达到最大执行时间 {max_duration}秒，跳过剩余循环")
                break
        
        print(f"完成脚本 {script_path}，执行步骤数: {step_counter}，总步骤数: {total_step_counter}")

    # 记录测试结束日志
    end_time = time.time()
    end_entry = {
        "tag": "function", 
        "depth": 1,
        "time": end_time,
        "data": {
            "name": "结束测试",
            "call_args": {"device": device_name, "executed_steps": total_step_counter},
            "start_time": end_time - 0.001, 
            "ret": True,
            "end_time": end_time
        }
    }
    with open(log_txt_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(end_entry, ensure_ascii=False) + "\n")
    
    # 如果没有执行任何步骤，但需要确保报告不为空，则添加一个示例操作
    if not has_executed_steps:
        print(f"设备 {device_name} 未执行任何步骤，添加默认操作以确保报告不为空")
        try:
            # 再次截图
            timestamp = time.time()
            screenshot = device.screenshot()
            frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
            # 保存截图
            screenshot_timestamp = int(timestamp * 1000)
            screenshot_filename = f"{screenshot_timestamp}.jpg"
            screenshot_path = os.path.join(log_dir, screenshot_filename)
            cv2.imwrite(screenshot_path, frame)
            
            # 创建缩略图
            thumbnail_filename = f"{screenshot_timestamp}_small.jpg"
            thumbnail_path = os.path.join(log_dir, thumbnail_filename)
            small_frame = cv2.resize(frame, (0, 0), fx=0.3, fy=0.3)
            cv2.imwrite(thumbnail_path, small_frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
            
            # 获取屏幕分辨率
            height, width = frame.shape[:2]
            resolution = [width, height]
            
            # 中心点位置
            x, y = int(width / 2), int(height / 2)
            
            # 准备screen对象
            screen_object = {
                "src": screenshot_filename,
                "_filepath": screenshot_filename,
                "thumbnail": thumbnail_filename,
                "resolution": resolution,
                "pos": [[x, y]],
                "vector": [],
                "confidence": 0.85,
                "rect": [{"left": x-50, "top": y-50, "width": 100, "height": 100}]
            }
            
            # 记录snapshot
            snapshot_entry = {
                "tag": "function", 
                "depth": 3,
                "time": timestamp,
                "data": {
                    "name": "try_log_screen",
                    "call_args": {"screen": "array([[[...]]],dtype=uint8)", "quality": None, "max_size": None},
                    "start_time": timestamp - 0.001, 
                    "ret": {"screen": screenshot_filename, "resolution": resolution},
                    "end_time": timestamp
                }
            }
            with open(log_txt_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(snapshot_entry, ensure_ascii=False) + "\n")
            
            # 记录示例操作（仅作为日志记录，不实际执行）
            default_entry = {
                "tag": "function", 
                "depth": 1,
                "time": timestamp + 0.001,
                "data": {
                    "name": "touch",
                    "call_args": {"v": [x, y]},
                    "start_time": timestamp + 0.0005,
                    "ret": [x, y],
                    "end_time": timestamp + 0.001,
                    "screen": screen_object
                }
            }
            with open(log_txt_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(default_entry, ensure_ascii=False) + "\n")
                
        except Exception as e:
            print(f"添加默认操作失败: {e}")
    
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
    """
    获取Airtest报告模板的路径
    
    此函数尝试从多个可能的位置找到Airtest的HTML报告模板文件，
    按照优先级依次尝试不同位置。
    
    返回:
        str: Airtest报告模板的路径，如果找不到则返回None
    """
    try:
        # 尝试直接从airtest包中获取模板
        # 这是最常见的情况，即从已安装的airtest包中获取模板
        airtest_path = os.path.dirname(airtest.__file__)
        template_path = os.path.join(airtest_path, "report", "log_template.html")   #
        
        if os.path.exists(template_path):
            return template_path
        
        # 如果第一种方法失败，尝试从site-packages获取
        # 这是为了处理某些Python环境中包结构可能不同的情况
        site_packages = os.path.dirname(os.path.dirname(airtest_path))
        alt_path = os.path.join(site_packages, "airtest", "report", "log_template.html")
        
        if os.path.exists(alt_path):
            return alt_path
        
        # 如果前两种方法都失败，尝试从本地templates目录获取
        # 这是为了在airtest包不完整或结构异常时提供备选方案
        local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "log_template.html")
        
        if os.path.exists(local_path):
            return local_path
        
        # 如果所有方法都失败，返回None
        return None
    except Exception as e:
        print(f"获取Airtest模板路径时出错: {str(e)}")
        return None


def run_one_report(log_dir, report_dir, script_path=None):
    """
    为单个设备生成HTML报告
    
    此函数完成以下任务:
    1. 检查和修复日志文件的JSON格式
    2. 创建报告目录结构
    3. 复制并处理图片资源
    4. 复制静态资源(CSS/JS等)
    5. 生成HTML报告
    
    Args:
        log_dir: 包含日志文件的目录
        report_dir: 生成报告的目标目录
        script_path: 脚本文件路径，可以是单个路径字符串或路径列表
        
    Returns:
        tuple: (report_generated, test_passed) 
               report_generated - 是否成功生成报告
               test_passed - 测试是否全部通过(没有断言失败)
    """
    try:       
        # 检查日志文件是否存在
        log_file = os.path.join(log_dir, "log.txt")
        if not os.path.exists(log_file):
            print(f"❌ 日志文件不存在: {log_file}")
            return False, False
        
        # 检查是否有失败的断言步骤
        test_passed = True
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        log_entry = json.loads(line)
                        # 检查是否是断言步骤且失败
                        if (log_entry.get("tag") == "function" and 
                            log_entry.get("data", {}).get("name") == "assert_exists" and
                            log_entry.get("data", {}).get("traceback")):
                            test_passed = False
                            print(f"检测到失败的断言步骤: {log_entry.get('data', {}).get('traceback')}")
                            break
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"检查断言步骤状态时出错: {e}")
            # 发生错误时不影响报告生成，但保守地设为失败
            test_passed = False
            
        # 修复日志文件JSON格式
        print("检查并修复日志文件JSON格式...")
        try:
            # 读取原始日志内容
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 检查是否有不带换行符的JSON对象
            if '}{' in content:
                print(f"检测到不带换行符的JSON对象，开始修复: {log_file}")
                # 将连续的JSON对象分割开
                content = content.replace('}{', '}\n{')
                
                # 写回修复后的内容
                with open(log_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                    
            # 再次读取并验证每行
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            valid_lines = []
            fixed_count = 0
            
            # 逐行处理JSON数据
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    # 尝试解析JSON
                    json.loads(line)
                    valid_lines.append(line + '\n')
                except json.JSONDecodeError as e:
                    fixed_count += 1
                    print(f"修复无效的JSON行: {e}")
                    # 尝试修复缺少括号等问题
                    if line.endswith(','):
                        line = line[:-1]
                    if not line.endswith('}'):
                        line += '}'
                    if not line.startswith('{'):
                        line = '{' + line
                        
                    try:
                        # 再次验证
                        json.loads(line)
                        valid_lines.append(line + '\n')
                        print("修复成功!")
                    except json.JSONDecodeError:
                        print(f"无法修复的JSON行: {line}")
            
            # 重写日志文件
            with open(log_file, 'w', encoding='utf-8') as f:
                f.writelines(valid_lines)
                
            print(f"JSON格式修复完成: 总行数 {len(lines)}, 有效行数 {len(valid_lines)}, 修复 {fixed_count} 行")
        except Exception as e:
            print(f"修复JSON格式时出错: {e}")
            traceback.print_exc()
        
        # 创建报告目录结构
        log_report_dir = os.path.join(report_dir, "log")
        os.makedirs(log_report_dir, exist_ok=True)
        
        # 处理脚本文件(支持单个路径或路径列表)
        all_script_content = []
        if script_path:
            # 确保script_path是列表
            script_paths = script_path if isinstance(script_path, list) else [script_path]
            script_file = os.path.join(report_dir, "script.py")
            
            # 读取所有脚本内容并合并
            for idx, path in enumerate(script_paths):
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        script_content = f.read()
                        
                    # 为每个脚本添加区分注释
                    script_header = f"\n\n# ============ 脚本 {idx+1}: {os.path.basename(path)} ============\n"
                    script_header += f"# 此脚本文件是用户明确指定执行的，路径: {path}\n\n"
                    all_script_content.append(script_header + script_content)
                    print(f"处理脚本文件 {idx+1}: {path}")
            
            # 写入合并后的脚本内容
            if all_script_content:
                with open(script_file, 'w', encoding='utf-8') as f:
                    f.write("# 用户指定执行的脚本文件\n")
                    f.write("# 生成时间: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n")
                    f.write("\n".join(all_script_content))
                print(f"已合并 {len(script_paths)} 个脚本文件到: {script_file}")
        
        # 处理图片资源
        image_files = {}
        for img in os.listdir(log_dir):
            if img.endswith(".jpg") or img.endswith(".png"):
                if not img.endswith("_small.jpg") and not img.endswith("_small.png"):
                    # 复制原始图片
                    src = os.path.join(log_dir, img)
                    dst = os.path.join(log_report_dir, img)
                    shutil.copy2(src, dst)
                    image_files[img] = img
                    
                    # 检查或创建缩略图
                    small_img = img.replace(".", "_small.")
                    small_src = os.path.join(log_dir, small_img)
                    
                    if os.path.exists(small_src):
                        small_dst = os.path.join(log_report_dir, small_img)
                        shutil.copy2(small_src, small_dst)
                    else:
                        # 如果缩略图不存在，则创建一个
                        img_data = cv2.imread(src)
                        if img_data is not None:
                            h, w = img_data.shape[:2]
                            small_img_data = cv2.resize(img_data, (0, 0), fx=0.3, fy=0.3)
                            cv2.imwrite(os.path.join(log_report_dir, small_img), small_img_data, [cv2.IMWRITE_JPEG_QUALITY, 60])
                            print(f"创建缩略图: {small_img}")
        
        # 复制日志文件到报告目录
        log_txt_file = os.path.join(log_report_dir, "log.txt")
        shutil.copy2(log_file, log_txt_file)
        
        # 获取Airtest模板路径
        template_path = get_airtest_template_path()
        if not template_path:
            print("❌ 无法找到Airtest模板路径")
            return False, False

    # 复制静态资源
        static_dir = os.path.join(report_dir, "static")     
        if not os.path.exists(static_dir):
            # 获取Airtest安装路径
            import airtest
            airtest_dir = os.path.dirname(airtest.__file__)
            
            # 创建static目录及必要的子目录
            os.makedirs(static_dir, exist_ok=True)
            os.makedirs(os.path.join(static_dir, "css"), exist_ok=True)
            os.makedirs(os.path.join(static_dir, "js"), exist_ok=True)
            os.makedirs(os.path.join(static_dir, "image"), exist_ok=True)
            os.makedirs(os.path.join(static_dir, "fonts"), exist_ok=True)
            
            # 从airtest包复制静态资源
            report_dir_path = os.path.join(airtest_dir, "report")
            resource_copied = False
            
            try:
                # 复制CSS文件
                css_src = os.path.join(report_dir_path, "css")
                css_dst = os.path.join(static_dir, "css")
                if os.path.exists(css_src) and os.path.isdir(css_src):
                    for file in os.listdir(css_src):
                        src_file = os.path.join(css_src, file)
                        dst_file = os.path.join(css_dst, file)
                        if os.path.isfile(src_file):
                            shutil.copy2(src_file, dst_file)
                    resource_copied = True
                    print(f"复制CSS资源: {css_src} -> {css_dst}")
                
                # 复制JS文件
                js_src = os.path.join(report_dir_path, "js")
                js_dst = os.path.join(static_dir, "js")
                if os.path.exists(js_src) and os.path.isdir(js_src):
                    for file in os.listdir(js_src):
                        src_file = os.path.join(js_src, file)
                        dst_file = os.path.join(js_dst, file)
                        if os.path.isfile(src_file):
                            shutil.copy2(src_file, dst_file)
                        elif os.path.isdir(src_file):
                            dst_subdir = os.path.join(js_dst, file)
                            os.makedirs(dst_subdir, exist_ok=True)
                            for subfile in os.listdir(src_file):
                                src_subfile = os.path.join(src_file, subfile)
                                dst_subfile = os.path.join(dst_subdir, subfile)
                                if os.path.isfile(src_subfile):
                                    shutil.copy2(src_subfile, dst_subfile)
                    resource_copied = True
                    print(f"复制JS资源: {js_src} -> {js_dst}")
                
                # 复制图片资源
                image_src = os.path.join(report_dir_path, "image")
                image_dst = os.path.join(static_dir, "image")
                if os.path.exists(image_src) and os.path.isdir(image_src):
                    for file in os.listdir(image_src):
                        src_file = os.path.join(image_src, file)
                        dst_file = os.path.join(image_dst, file)
                        if os.path.isfile(src_file):
                            shutil.copy2(src_file, dst_file)
                    resource_copied = True
                    print(f"复制image资源: {image_src} -> {image_dst}")
                    
                # 复制字体文件
                fonts_src = os.path.join(report_dir_path, "fonts")
                fonts_dst = os.path.join(static_dir, "fonts")
                if os.path.exists(fonts_src) and os.path.isdir(fonts_src):
                    for file in os.listdir(fonts_src):
                        src_file = os.path.join(fonts_src, file)
                        dst_file = os.path.join(fonts_dst, file)
                        if os.path.isfile(src_file):
                            shutil.copy2(src_file, dst_file)
                    resource_copied = True
                    print(f"复制字体资源: {fonts_src} -> {fonts_dst}")
            except Exception as e:
                print(f"从airtest包复制资源时出错: {e}")
                traceback.print_exc()
                
                # 资源复制失败时，创建基础的资源文件
                try:
                    # 创建基础CSS文件
                    basic_css = os.path.join(static_dir, "css", "report.css")
                    with open(basic_css, "w", encoding="utf-8") as f:
                        f.write("""
                        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
                        .screen { max-width: 100%; border: 1px solid #ddd; }
                        .step { margin-bottom: 20px; border-bottom: 1px solid #eee; padding-bottom: 10px; }
                        .success { color: green; }
                        .fail { color: red; }
                        """)
                    
                    # 创建基础JS文件
                    basic_js = os.path.join(static_dir, "js", "report.js")
                    with open(basic_js, "w", encoding="utf-8") as f:
                        f.write("// Basic report functionality")
                    
                    resource_copied = True
                    print("✅ 创建了基础静态资源文件作为备份")
                except Exception as e_fallback:
                    print(f"创建基础资源文件失败: {e_fallback}")
            
            # 如果所有资源复制方法都失败，尝试从其他报告复制
            if not resource_copied:
                print("尝试从其他报告复制静态资源...")
                # 试图从其他报告中复制
                dirs = os.listdir(os.path.dirname(report_dir))
                for d in dirs:
                    other_static = os.path.join(os.path.dirname(report_dir), d, "static")
                    if os.path.exists(other_static) and d != os.path.basename(report_dir):
                        try:
                            # 使用递归复制目录树
                            for root, _, files in os.walk(other_static):
                                # 计算相对路径
                                rel_path = os.path.relpath(root, other_static)
                                # 创建目标目录
                                target_dir = os.path.join(static_dir, rel_path)
                                os.makedirs(target_dir, exist_ok=True)
                                # 复制文件
                                for file in files:
                                    src_file = os.path.join(root, file)
                                    dst_file = os.path.join(target_dir, file)
                                    shutil.copy2(src_file, dst_file)
                            
                            resource_copied = True
                            print(f"从其他报告复制静态资源: {other_static} -> {static_dir}")
                            break
                        except Exception as e:
                            print(f"复制静态资源时出现错误: {e}")
                
                if not resource_copied:
                    print("❌ 无法找到任何静态资源，但会继续尝试生成报告")
        
        # 复制模板文件
        print(f"复制模板文件: {template_path} -> {report_dir}")
        dest_template = os.path.join(report_dir, "log_template.html")
        print(f"复制模板文件: {dest_template}")
        shutil.copy2(template_path, dest_template)
        
        # 生成HTML报告
        rpt = LogToHtml(
            script_root=report_dir,         # 项目根目录
            log_root=log_report_dir,        # log子目录
            static_root="static",           # 静态资源目录名称（相对路径）
            export_dir=report_dir,          # 导出HTML的目录
            script_name="script.py",        # 脚本文件名
            logfile="log.txt",              # 日志文件名
            lang="zh"                       # 语言参数，使用中文
        )
        
        # 执行报告生成
        # 报告可能生成在report_dir/log.html或report_dir/script.log/log.html
        report_html_file = os.path.join(report_dir, "log.html")
        script_log_html_file = os.path.join(report_dir, "script.log", "log.html")
        print(f"report_html_file: {report_html_file}")
        print(f"script_log_html_file: {script_log_html_file}")

    # 生成报告
        rpt.report()
        
        # 确定实际生成的HTML文件路径
        actual_html_file = script_log_html_file if os.path.exists(script_log_html_file) else report_html_file
        print(f"HTML报告生成成功: {actual_html_file}")
        
        # 如果报告生成在script.log子目录，复制到report_dir根目录
        if os.path.exists(script_log_html_file) and not os.path.exists(report_html_file):
            try:
                shutil.copy2(script_log_html_file, report_html_file)
                print(f"复制报告: {script_log_html_file} -> {report_html_file}")
                actual_html_file = report_html_file
            except Exception as e:
                print(f"复制报告失败: {e}")
        
        # 修复HTML中的路径问题和增加测试结果状态
        if os.path.exists(actual_html_file):
            try:
                with open(actual_html_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # 修复路径引用
                dirname = os.path.dirname(actual_html_file)
                content = content.replace(dirname + "/static/", "static/")
                
                # 修改data对象，设置测试结果状态
                try:
                    # 查找data对象定义部分
                    data_pattern = re.compile(r"data\s*=\s*(\{.*?\});", re.DOTALL)
                    data_match = data_pattern.search(content)
                    if data_match:
                        data_str = data_match.group(1)
                        # 尝试通过安全解析
                        # 使用ast.literal_eval更安全
                        import ast
                        # 先将所有Unicode转义处理为Python字符串格式
                        python_data_str = data_str.replace("\\\\", "\\").replace('\\"', '"')
                        # 替换JS格式的true/false/null为Python格式
                        python_data_str = python_data_str.replace("true", "True").replace("false", "False").replace("null", "None")
                        # 尝试解析数据对象
                        data_obj = None
                        try:
                            data_obj = ast.literal_eval(python_data_str)
                        except Exception as parse_err:
                            print(f"无法解析data对象: {parse_err}")
                        if data_obj:
                            # 明确设置测试结果状态
                            data_obj["test_result"] = test_passed
                            # 将Python对象转换回JS对象字符串
                            json_str = json.dumps(data_obj, ensure_ascii=False)
                            # 替换Python布尔值为JavaScript格式
                            js_str = json_str.replace('True', 'true').replace('False', 'false').replace('None', 'null')
                            # 在HTML中替换原始的data对象
                            new_data_js = f"data = {js_str};"
                            content = re.sub(r"data\s*=\s*\{.*?\};", new_data_js, content, flags=re.DOTALL)
                            print(f"已更新测试结果状态为: {'通过' if test_passed else '失败'}")
                    
                except Exception as e:
                    print(f"查找或更新data对象失败: {e}")
                
                # 添加测试状态的视觉指示器
                status_css = """
<style>
.test-status {
    position: fixed;
    top: 10px;
    right: 10px;
    padding: 5px 15px;
    border-radius: 4px;
    font-weight: bold; 
    z-index: 1000;
}
.test-status.pass {
    background-color: #4caf50;
    color: white;
}
.test-status.fail {
    background-color: #f44336;
    color: white;
}
</style>
"""
                    
                status_js = f"""
                <script>
$(document).ready(function() {{
    // 添加测试状态指示器
    var statusClass = {str(test_passed).lower()} ? 'pass' : 'fail';
    var statusText = {str(test_passed).lower()} ? '通过' : '失败';
    $('body').append('<div class="test-status ' + statusClass + '">' + statusText + '</div>');
                        
    // 修改页面标题反映测试状态
    var originalTitle = document.title;
    document.title = '[' + statusText + '] ' + originalTitle;
}});
                </script>
                """
                
                # 在</body>标签前插入状态指示器代码
                content = content.replace('</head>', status_css + '</head>')
                content = content.replace('</body>', status_js + '</body>')
                
                # 写回修改后的内容
                with open(actual_html_file, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"HTML路径和显示修复成功: {actual_html_file}")
                
            except Exception as e:
                print(f"修复HTML路径失败: {e}")
                traceback.print_exc()

        # --- 新增：同步设备报告到staticfiles/ui_run/WFGameAI.air/log/ ---
        try:
            sync_device_report_to_staticfiles(report_dir)
        except Exception as sync_e:
            print(f"设备报告同步到静态目录失败: {sync_e}")
        # --- end ---

        return True, test_passed
    except Exception as e:
        print(f"生成HTML报告失败: {str(e)}")
        traceback.print_exc()
        return False, False


def sync_device_report_to_staticfiles(device_report_dir):
    """
    同步单个设备报告目录到staticfiles/ui_run/WFGameAI.air/log/下，保证Web端可访问。
    Args:
        device_report_dir (str): 设备报告目录的绝对路径
    Returns:
        None
    """
    import shutil
    static_ui_run_dir = os.path.join(os.path.dirname(__file__), "..", "staticfiles", "ui_run", "WFGameAI.air", "log")
    device_dir_name = os.path.basename(device_report_dir)
    dst_dir = os.path.join(static_ui_run_dir, device_dir_name)
    os.makedirs(dst_dir, exist_ok=True)
    # 递归复制整个设备报告目录
    for item in os.listdir(device_report_dir):
        s = os.path.join(device_report_dir, item)
        d = os.path.join(dst_dir, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True)
        else:
            shutil.copy2(s, d)
    print(f"设备报告已同步到静态目录: {dst_dir}")


# 生成汇总报告
def run_summary(data):
    """
    生成汇总报告
    :param data: 测试数据，包含每个设备的测试结果
    :return: 汇总报告的路径
    """
    try:
        # 确保汇总报告目录存在
        os.makedirs(ui_reports_dir, exist_ok=True)
        
        # 生成带时间戳的报告文件名
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        report_file = f"summary_report_{timestamp}.html"
        summary_report_path = os.path.join(ui_reports_dir, report_file)
        
        # 准备汇总数据
        summary = {
            "devices": [],
            "total": 0,
            "success": 0,  # 报告生成成功
            "passed": 0,   # 测试全部通过
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "duration": ""
        }
        
        # 收集各设备的测试结果
        for dev_name, test_result in data['tests'].items():
            # 处理新的测试结果数据结构
            if isinstance(test_result, dict):
                report_path = test_result.get('report_path')
                test_passed = test_result.get('test_passed', False)
            else:
                # 兼容旧格式数据
                report_path = test_result
                test_passed = False
            
            # 验证报告是否生成成功
            report_generated = report_path is not None and os.path.exists(report_path)
            
            # 获取设备报告的相对路径
            report_rel_path = None
            if report_generated:
                # 从绝对路径中提取设备目录名称
                device_dir_name = os.path.basename(os.path.dirname(report_path))
                
                # 计算汇总报告目录到设备报告目录的相对路径
                # 汇总报告在 outputs/WFGameAI-reports/ui_reports/
                # 设备报告在 outputs/WFGameAI-reports/ui_run/WFGameAI.air/log/设备目录/
                report_rel_path = f"../ui_run/WFGameAI.air/log/{device_dir_name}/log.html"
                print(f"设备 {dev_name} 报告路径: {report_rel_path}")
            
            device_data = {
                "name": dev_name,
                "report": report_rel_path,
                "success": report_generated,  # 报告是否生成成功
                "passed": test_passed,        # 测试是否全部通过
                "status": "通过" if test_passed else "失败" if report_generated else "错误"
            }
            summary["devices"].append(device_data)
            summary["total"] += 1
            if report_generated:
                summary["success"] += 1
            if test_passed:
                summary["passed"] += 1
        
        # 计算成功率和通过率
        summary["success_rate"] = f"{summary['success']}/{summary['total']}"
        summary["pass_rate"] = f"{summary['passed']}/{summary['total']}"
        summary["success_percent"] = f"{(summary['success'] / summary['total'] * 100) if summary['total'] > 0 else 0:.1f}%"
        summary["pass_percent"] = f"{(summary['passed'] / summary['total'] * 100) if summary['total'] > 0 else 0:.1f}%"
        
        # 使用模板生成汇总报告
        template_file = os.path.join(os.path.dirname(__file__), "templates", "summary_template.html")
        if not os.path.exists(template_file):
            print(f"模板文件不存在: {template_file}")
            template_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "summary_template.html")
        
        # 使用 Jinja2 渲染模板
        env = Environment(loader=FileSystemLoader(os.path.dirname(template_file)))
        template = env.get_template(os.path.basename(template_file))

        # 生成汇总报告 HTML
        with open(summary_report_path, "w", encoding="utf-8") as f:
            html_content = template.render(data=summary)
            f.write(html_content)
        
        # 同时创建一个latest_report.html作为最新报告的快捷方式
        latest_report_path = os.path.join(ui_reports_dir, "latest_report.html")
        shutil.copy(summary_report_path, latest_report_path)
        
        print(f"汇总报告已生成: {summary_report_path}")
        print(f"最新报告快捷方式: {latest_report_path}")

        # --- 新增：自动同步到Django静态目录，便于Web访问 ---
        try:
            static_reports_dir = os.path.join(os.path.dirname(__file__), "..", "staticfiles", "reports")
            os.makedirs(static_reports_dir, exist_ok=True)
            # 复制汇总报告
            shutil.copy2(summary_report_path, os.path.join(static_reports_dir, os.path.basename(summary_report_path)))
            # 复制latest_report.html
            shutil.copy2(latest_report_path, os.path.join(static_reports_dir, "latest_report.html"))
            print(f"报告已同步到静态目录: {static_reports_dir}")
        except Exception as sync_e:
            print(f"报告同步到静态目录失败: {sync_e}")
        # --- end ---
        
        return summary_report_path
    except Exception as e:
        print(f"汇总报告生成失败: {e}")
        traceback.print_exc()
        return ""


# 在多台设备上并行运行测试
def run_on_multi_device(devices, scripts, results, run_all, device_names, show_screens=False):
    tasks = []
    for i, device in enumerate(devices):
        serial = device.serial
        # 修复：从列表中获取设备名称，使用索引而不是字典
        device_name = device_names[i] if i < len(device_names) else serial
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
    
    # 显式记录实际要执行的脚本
    print(f"run函数将执行 {len(scripts)} 个脚本:")
    for idx, script in enumerate(scripts):
        print(f"  {idx+1}. {script['path']}")
    
    # 创建报告基础目录
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    os.makedirs(report_dir, exist_ok=True)
    
    # 在多设备上运行测试
    tasks = run_on_multi_device(devices, scripts, results, run_all, device_names, show_screens)
    success_count = 0
    test_pass_count = 0

    # 对每个设备生成报告
    for task in tasks:
        task['thread'].join()
        # 报告目录就是日志目录
        device_report_dir = task['log_dir']
        
        # 准备所有脚本文件路径
        script_paths = []
        if scripts:
            for script_config in scripts:
                if script_config.get('path') and os.path.exists(script_config.get('path')):
                    script_paths.append(script_config.get('path'))
            
        # 生成报告 - 传递所有脚本路径列表
        report_generated, test_passed = run_one_report(device_report_dir, device_report_dir, script_paths)
        
        # 更新报告路径为log.html的绝对路径
        report_path = os.path.join(device_report_dir, "log.html") if report_generated else None
        
        # 保存报告路径和测试通过状态
        results['tests'][task['dev']] = {
            'report_path': report_path,
            'test_passed': test_passed
        }
        
        print(f"设备 {task['dev']} 报告目录: {device_report_dir}")
        print(f"设备 {task['dev']} 报告路径: {report_path}")
        
        if report_generated:
            success_count += 1
            if test_passed:
                test_pass_count += 1
                print(f"设备 {task['dev']} 测试成功且全部通过")
            else:
                print(f"设备 {task['dev']} 测试成功但有断言失败")
        else:
            print(f"设备 {task['dev']} 测试报告生成失败")

    # 生成汇总报告
    print(f"开始生成汇总报告，成功率: {success_count}/{len(tasks)}，通过率: {test_pass_count}/{len(tasks)}")
    summary_report = run_summary(results)
    
    # 返回结果
    result_str = f"成功 {success_count}/{len(tasks)}，全部通过 {test_pass_count}/{len(tasks)}"
    return result_str, summary_report


# 回放步骤
def replay_steps(scripts, show_screens=False):
    global model, devices

    # 清空所有可能的缓存数据，确保只执行用户指定的脚本
    loaded_scripts = []
    print(f"准备执行用户指定的 {len(scripts)} 个脚本...")
    
    for script_config in scripts:
        script_path = script_config["path"]
        if not os.path.exists(script_path):
            print(f"文件 {script_path} 不存在，跳过")
            continue
        loaded_scripts.append(script_config)
        print(f"添加脚本: {script_path}")

    if not loaded_scripts:
        print("未加载任何有效脚本，回放终止")
        return False
        
    # 显式输出将要执行的脚本，方便调试
    print(f"最终将执行 {len(loaded_scripts)} 个脚本:")
    for idx, script in enumerate(loaded_scripts):
        print(f"  {idx+1}. {script['path']}" + 
              (f" (最大执行时间: {script.get('max_duration')}秒)" if 'max_duration' in script else "") +
              (f" (循环次数: {script.get('loop_count')})" if 'loop_count' in script else ""))

    # 设置默认日志目录为项目目录，避免在根目录生成日志
    set_logdir(project_air_dir)

    # 修改为列表
    device_names = []
    for device in devices:
        serial = device.serial
        try:
            airtest_device = connect_device(f"Android:///{serial}")
            friendly_name = get_device_name(airtest_device)
            device_names.append(friendly_name)
            airtest_device.serial = serial
            print(f"设备 {friendly_name} 连接成功")
        except Exception as e:
            print(f"设备 {serial} 连接失败: {e}")
            continue

    print(f"加载脚本: {', '.join(s['path'] for s in loaded_scripts)}")
    print(f"检测到 {len(devices)} 个设备: {device_names}")
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


# 修改函数位置。禁止使用或增加清理无用文件的函数！！！
def cleanup_unused_files():
    """清理生成的无用临时文件"""
    print("🧹 开始清理无用文件...")
    
    # 清理项目根目录下错误创建的静态资源目录
    root_static_dirs = ['static', 'static/css', 'static/js', 'static/image', 'static/fonts']
    for static_dir in root_static_dirs:
        if os.path.exists(static_dir) and os.path.abspath(static_dir).startswith(os.path.abspath(BASE_DIR)):
            try:
                if os.path.isdir(static_dir):
                    shutil.rmtree(static_dir)
                else:
                    os.remove(static_dir)
                print(f"✅ 已删除项目根目录下的静态资源: {static_dir}")
            except Exception as e:
                print(f"❌ 删除失败: {static_dir}, 错误: {e}")
    
    # 清理script.log目录中的冗余文件(保留log.html)
    for root, dirs, files in os.walk(reports_base_dir):
        if root.endswith("script.log"):
            for file in files:
                if file != "log.html":
                    file_path = os.path.join(root, file)
                    try:
                        os.remove(file_path)
                        print(f"✅ 已删除冗余文件: {file_path}")
                    except Exception as e:
                        print(f"❌ 删除失败: {file_path}, 错误: {e}")


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

    # 加载YOLO模型 - 使用统一的加载函数
    try:
        model = load_yolo_model(
            base_dir=BASE_DIR,
            model_class=YOLO,
            device="cuda"
        )
        if not model:
            print("错误：未能加载模型")
            exit(1)
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

    # 清理无用文件
    # cleanup_unused_files()


if __name__ == "__main__":
    main()

def generate_reports(results, script_path=None):
    """
    生成测试报告，按照Airtest标准结构
    
    参数:
        results: 包含测试结果的字典，格式如下:
                {'logs': {设备名: 日志目录}, 'tests': {设备名: 报告结果}, 'success_count': 成功数量}
        script_path: 脚本文件路径，可以是单个路径字符串或路径列表
        
    返回:
        bool: 是否成功生成报告
    """
    try:
        import traceback
        from datetime import datetime
        
        # 确保所有基础目录存在
        os.makedirs(reports_base_dir, exist_ok=True)
        os.makedirs(ui_reports_dir, exist_ok=True)
        os.makedirs(ui_run_dir, exist_ok=True)
        os.makedirs(project_air_dir, exist_ok=True)
        os.makedirs(device_log_dir, exist_ok=True)
        
        # 生成时间戳
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        
        # 初始化结果计数器
        if 'success_count' not in results:
            results['success_count'] = 0
        
        if 'passed_count' not in results:
            results['passed_count'] = 0
        
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
                results['tests'][device_name] = {
                    'report_path': None,
                    'test_passed': False
                }
                continue
                
            # 为每个设备创建标准目录路径
            device_timestamp = timestamp  # 使用相同的时间戳保持一致性
            device_report_dir = os.path.join(device_log_dir, f"{device_name}_{device_timestamp}")
            os.makedirs(device_report_dir, exist_ok=True)
            
            # 处理脚本路径，支持单个路径或路径列表
            script_paths = None
            if script_path:
                if isinstance(script_path, list):
                    # 过滤掉不存在的路径
                    script_paths = [path for path in script_path if os.path.exists(path)]
                    if script_paths:
                        print(f"为设备 {device_name} 使用 {len(script_paths)} 个脚本文件")
                    else:
                        print(f"警告: 设备 {device_name} 的所有脚本路径都不存在")
                else:
                    # 单个路径
                    if os.path.exists(script_path):
                        script_paths = [script_path]
                        print(f"为设备 {device_name} 使用脚本文件: {script_path}")
                    else:
                        print(f"警告: 设备 {device_name} 的脚本路径不存在: {script_path}")
            
            # 生成设备报告
            print(f"为设备 {device_name} 生成报告...")
            report_generated, test_passed = run_one_report(log_dir, device_report_dir, script_paths)
            
            # 更新测试结果
            if report_generated:
                report_path = os.path.join(device_report_dir, "log.html")
                results['tests'][device_name] = {
                    'report_path': report_path,
                    'test_passed': test_passed
                }
                results['success_count'] += 1
                if test_passed:
                    results['passed_count'] += 1
                device_reports[device_name] = report_path
                print(f"设备 {device_name} 报告生成成功，测试{'通过' if test_passed else '失败'}")
            else:
                results['tests'][device_name] = {
                    'report_path': None,
                    'test_passed': False
                }
                print(f"设备 {device_name} 报告生成失败")

        # 生成汇总报告
        total_tests = len(results['logs'])
        success_rate = (results['success_count'] / total_tests * 100) if total_tests > 0 else 0
        pass_rate = (results['passed_count'] / total_tests * 100) if total_tests > 0 else 0
        
        # 使用run_summary函数生成汇总报告
        summary_report = run_summary(results)
        
        print(f"报告生成完成，共测试 {total_tests} 个设备，成功生成报告 {results['success_count']} 个，测试全部通过 {results['passed_count']} 个")
        print(f"成功率: {success_rate:.1f}%，通过率: {pass_rate:.1f}%")
        print(f"报告目录: {reports_base_dir}")
        
        return True
    except Exception as e:
        print(f"报告生成失败: {str(e)}")
        traceback.print_exc()
        return False