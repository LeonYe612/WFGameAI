from airtest.core.api import touch, exists, snapshot, set_logdir, connect_device, log
from airtest.report.report import LogToHtml
import cv2
import numpy as np
from ultralytics import YOLO
import json
import time
import os
import subprocess
from threading import Thread, Event, Lock
import queue
import sys
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import shutil
from adbutils import adb
from jinja2 import Environment, FileSystemLoader
import traceback
import io  # 确保导入 io 模块
import airtest  # 添加这行
from datetime import datetime
from app_lifecycle_manager import AppLifecycleManager
import random
import torch
import re
import torch
from datetime import datetime
import random

# 全局修补shutil.copytree以解决Airtest静态资源复制的FileExistsError问题
# 这必须在所有其他操作之前进行，确保Airtest使用修补后的函数
print("🔧 应用全局shutil.copytree修补，防止静态资源复制冲突")
_original_copytree = shutil.copytree

def _patched_copytree(src, dst, symlinks=False, ignore=None, copy_function=shutil.copy2,
                     ignore_dangling_symlinks=False, dirs_exist_ok=True):
    """全局修补的copytree函数，自动处理目录已存在的情况"""
    try:
        # Python 3.8+支持dirs_exist_ok参数
        return _original_copytree(src, dst, symlinks=symlinks, ignore=ignore,
                                 copy_function=copy_function,
                                 ignore_dangling_symlinks=ignore_dangling_symlinks,
                                 dirs_exist_ok=True)
    except TypeError:
        # Python 3.7及以下版本不支持dirs_exist_ok参数
        try:
            if os.path.exists(dst):
                shutil.rmtree(dst)
            return _original_copytree(src, dst, symlinks=symlinks, ignore=ignore,
                                     copy_function=copy_function,
                                     ignore_dangling_symlinks=ignore_dangling_symlinks)
        except Exception as e:
            print(f"🔧 全局copytree修补失败，忽略错误继续执行: {src} -> {dst}, 错误: {e}")
            # 如果目标目录已存在，直接返回成功
            if os.path.exists(dst):
                return dst
            raise e
    except Exception as e:
        print(f"🔧 全局copytree处理异常: {src} -> {dst}, 错误: {e}")
        # 如果目标目录已存在，直接返回成功
        if os.path.exists(dst):
            return dst
        raise e

# 应用全局修补
shutil.copytree = _patched_copytree
print("✅ 全局shutil.copytree修补已应用")

# 导入统一路径管理工具

# 统一报告目录配置 - 所有报告相关路径都基于staticfiles/reports
STATICFILES_REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "staticfiles", "reports")
DEVICE_REPORTS_DIR = os.path.join(STATICFILES_REPORTS_DIR, "ui_run", "WFGameAI.air", "log")
SUMMARY_REPORTS_DIR = os.path.join(STATICFILES_REPORTS_DIR, "summary_reports")

# 其他默认路径
DEFAULT_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TESTCASE_DIR = os.path.join(DEFAULT_BASE_DIR, "testcase")

# 全局锁，用于防止多设备同时复制静态资源时的竞争条件
REPORT_GENERATION_LOCK = Lock()

try:
    # 使用单独的配置导入文件
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from config_import import config_manager, ConfigManager

    # 将load_yolo_model也正确导入
    try:
        from utils import load_yolo_model
        print("成功导入load_yolo_model函数")
    except ImportError:
        print("警告: 无法导入utils.load_yolo_model，将尝试直接使用YOLO")
        # 如果导入失败，提供一个空函数
        def load_yolo_model(*args, **kwargs):
            print("警告: load_yolo_model 导入失败，返回None")
            return None

    if config_manager:
        print("成功导入ConfigManager模块")

        # 使用配置管理器获取路径
        BASE_DIR = config_manager.get_path('scripts_dir')
        if not BASE_DIR:
            BASE_DIR = DEFAULT_BASE_DIR

        TESTCASE_DIR = config_manager.get_path('testcase_dir')
        if not TESTCASE_DIR:
            TESTCASE_DIR = DEFAULT_TESTCASE_DIR

        # 统一使用新的报告目录结构
        REPORTS_DIR = DEVICE_REPORTS_DIR
        UI_REPORTS_DIR = DEVICE_REPORTS_DIR

        print(f"使用路径配置: BASE_DIR={BASE_DIR}, TESTCASE_DIR={TESTCASE_DIR}")
        print(f"统一报告目录: DEVICE_REPORTS_DIR={DEVICE_REPORTS_DIR}, SUMMARY_REPORTS_DIR={SUMMARY_REPORTS_DIR}")
    else:
        raise ImportError("ConfigManager导入失败")
except Exception as e:
    # 如果导入失败，使用默认路径
    print(f"配置管理器错误: {e}")
    BASE_DIR = DEFAULT_BASE_DIR
    TESTCASE_DIR = DEFAULT_TESTCASE_DIR
    # 统一使用新的报告目录结构
    REPORTS_DIR = DEVICE_REPORTS_DIR
    UI_REPORTS_DIR = DEVICE_REPORTS_DIR
    print("警告: 未找到配置管理工具，使用默认路径")
    print(f"统一报告目录: DEVICE_REPORTS_DIR={DEVICE_REPORTS_DIR}, SUMMARY_REPORTS_DIR={SUMMARY_REPORTS_DIR}")

# 禁用 Ultralytics 的日志输出
logging.getLogger("ultralytics").setLevel(logging.CRITICAL)

# 全局变量
model = None
devices = []
CURRENT_TIME = "_" + time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime(time.time()))
template_dir = os.path.join(BASE_DIR, "templates")  # 模板目录路径

# 统一报告目录配置 - 只使用staticfiles作为报告存储根目录
STATICFILES_REPORTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "staticfiles", "reports"
)

# 设备报告目录
DEVICE_REPORTS_DIR = os.path.join(STATICFILES_REPORTS_DIR, "ui_run", "WFGameAI.air", "log")

# 汇总报告目录
SUMMARY_REPORTS_DIR = os.path.join(STATICFILES_REPORTS_DIR, "summary_reports")

# 确保目录存在
os.makedirs(STATICFILES_REPORTS_DIR, exist_ok=True)
os.makedirs(DEVICE_REPORTS_DIR, exist_ok=True)
os.makedirs(SUMMARY_REPORTS_DIR, exist_ok=True)
os.makedirs(template_dir, exist_ok=True)

# 设置Airtest日志存储目录为设备报告目录
set_logdir(DEVICE_REPORTS_DIR)
# 尝试设置全局日志目录
try:
    import airtest.core.api as airtest_api
    # 使用更安全的方式设置LOG_DIR
    if hasattr(airtest_api, 'ST') and airtest_api.ST is not None:
        # 如果LOG_DIR属性可写，则设置它
        try:
            if hasattr(airtest_api.ST, 'LOG_DIR'):
                # 使用setattr来避免类型检查错误
                setattr(airtest_api.ST, 'LOG_DIR', DEVICE_REPORTS_DIR)
            else:
                print(f"警告：Airtest.ST没有LOG_DIR属性，使用set_logdir代替")
        except (AttributeError, TypeError) as e:
            # 如果无法设置，记录警告但继续执行
            print(f"警告：无法设置Airtest LOG_DIR ({e})，将使用默认设置")
except (ImportError, AttributeError) as e:
    print(f"设置Airtest全局日志目录时出错: {e}")

screenshot_queue = queue.Queue()
action_queue = queue.Queue()
click_queue = queue.Queue()  # 新增全局 click_queue

# 全局YOLO模型变量
model = None

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
    log_file = os.path.join(DEVICE_REPORTS_DIR, f"{device_name}_log.txt")
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

        # 组合设备名称（不包含分辨率）
        device_name = f"{brand}-{model}"
        return device_name
    except Exception as e:
        print(f"获取设备 {device.serial} 信息失败: {e}")
        # 返回清理后的序列号作为后备名称
        return "".join(c for c in device.serial if c.isalnum() or c in ('-', '_'))


# 检测按钮
def detect_buttons(frame, target_class=None):
    global model  # 声明model为全局变量
    frame_for_detection = cv2.resize(frame, (640, 640))
    try:
        # 检查模型是否可用
        if model is None:
            print("❌ 错误：YOLO模型未加载，无法进行检测")
            return False, (None, None, None)

        print(f"🔍 开始检测目标类别: {target_class}")
        # 使用当前设备进行预测
        results = model.predict(source=frame_for_detection, imgsz=640, conf=0.6, verbose=False)

        # 检查预测结果是否有效
        if results is None or len(results) == 0:
            print("⚠️ 警告：模型预测结果为空")
            return False, (None, None, None)

        # 检查结果中是否有boxes
        if not hasattr(results[0], 'boxes') or results[0].boxes is None:
            print("⚠️ 警告：预测结果中没有检测框")
            return False, (None, None, None)

        orig_h, orig_w = frame.shape[:2]
        scale_x, scale_y = orig_w / 640, orig_h / 640

        for box in results[0].boxes:
            cls_id = int(box.cls.item())
            # 检查模型是否有names属性
            if hasattr(model, 'names') and model.names is not None:
                detected_class = model.names[cls_id]
            else:
                detected_class = f"class_{cls_id}"

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

    # 使用新的统一目录结构
    log_dir = os.path.join(DEVICE_REPORTS_DIR, f"{device_dir}_{timestamp}")
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
    try:
        import airtest.core.api as airtest_api
        if hasattr(airtest_api, 'ST') and hasattr(airtest_api.ST, 'LOG_DIR'):
            try:
                setattr(airtest_api.ST, 'LOG_DIR', log_dir)
            except (AttributeError, TypeError) as e:
                print(f"设置设备日志目录时出错: {e}")
        else:
            print(f"警告：Airtest.ST没有LOG_DIR属性，跳过设置")
    except (ImportError, AttributeError) as e:
        print(f"设置设备日志目录时出错: {e}")

    # 使用set_logdir作为备用方法
    try:
        set_logdir(log_dir)
    except Exception as e:
        print(f"set_logdir失败: {e}")

    return log_dir


# 清理日志目录
def clear_log_dir():
    if os.path.exists(DEVICE_REPORTS_DIR):
        shutil.rmtree(DEVICE_REPORTS_DIR)
    os.makedirs(DEVICE_REPORTS_DIR, exist_ok=True)


# 加载测试进度数据
def load_json_data(run_all):
    # 确保BASE_DIR有效
    base_dir = BASE_DIR if BASE_DIR is not None else DEFAULT_BASE_DIR
    json_file = os.path.join(base_dir, 'data.json')
    if not run_all and os.path.isfile(json_file):
        data = json.load(open(json_file))
        data['start'] = time.time()
        return data
    else:
        print(f"清理日志目录: {DEVICE_REPORTS_DIR}")
        clear_log_dir()
        return {
            'start': time.time(),
            'script': "replay_script",
            'tests': {}
        }


def replay_device(device, scripts, screenshot_queue, action_queue, click_queue, stop_event, device_name, log_dir, show_screens=False,
                  loop_count=1):
    """
    回放设备脚本，记录日志并生成报告所需信息。

    参数:
        device: ADB 设备对象（adbutils 设备实例）。
        scripts (list): 脚本配置列表，例如 [{"path": "path/to/script.json", "loop_count": 1}]。
        screenshot_queue (queue.Queue): 截图队列，用于传递屏幕截图给检测服务。
        action_queue (queue.Queue): 动作队列，用于记录操作。
        click_queue (queue.Queue): 点击队列，用于处理点击操作。
        stop_event (threading.Event): 停止事件，用于控制检测服务。
        device_name (str): 设备名称，例如 "OnePlus-KB2000-1080x2400"。
        show_screens (bool): 是否显示屏幕（默认 False）。
        loop_count (int): 循环次数（默认 1，从 scripts 中获取优先）。
    """
    # 为当前设备设置日志目录
    try:
        set_logdir(log_dir)
    except Exception as e:
        print(f"set_logdir失败: {e}")

    # 直接设置全局日志目录，确保Airtest使用正确的日志目录
    try:
        import airtest.core.api as airtest_api
        if hasattr(airtest_api, 'ST') and hasattr(airtest_api.ST, 'LOG_DIR'):
            try:
                setattr(airtest_api.ST, 'LOG_DIR', log_dir)
            except (AttributeError, TypeError) as e:
                print(f"设置Airtest日志目录时出错: {e}")
        else:
            print(f"警告：Airtest.ST没有LOG_DIR属性，跳过设置")
    except (ImportError, AttributeError) as e:
        print(f"设置Airtest日志目录时出错: {e}")

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
        script_id = script_config.get("script_id")
        script_category = script_config.get("category")

        print(f"开始执行脚本: {script_path}, 循环次数: {script_loop_count}, 最大执行时间: {max_duration}秒")
        print(f"脚本ID: {script_id}, 脚本分类: {script_category}")

        # 特殊处理：启动程序和停止程序类别
        if script_category in ['启动程序', '停止程序']:
            print(f"检测到应用生命周期管理脚本，分类: {script_category}")

            try:
                # 从脚本文件中读取应用信息
                with open(script_path, "r", encoding="utf-8") as f:
                    json_data = json.load(f)
                    steps = json_data.get("steps", [])

                # 查找app_start或app_stop步骤中的应用信息
                app_name = None
                package_name = None

                for step in steps:
                    if step.get("class") in ["app_start", "app_stop"]:
                        params = step.get("params", {})
                        app_name = params.get("app_name", "")
                        package_name = params.get("package_name", "")
                        break

                if not app_name and not package_name:
                    print(f"警告: {script_category}脚本中未找到应用信息，跳过特殊处理")
                else:
                    # 使用AppLifecycleManager执行应用生命周期操作
                    app_lifecycle_manager = AppLifecycleManager()

                    if script_category == '启动程序':
                        print(f"执行应用启动: {app_name or package_name}")
                        app_identifier = app_name or package_name
                        if app_identifier:
                            success = app_lifecycle_manager.start_app(str(app_identifier), device.serial)
                        else:
                            success = False
                        operation_name = "start_app"

                    elif script_category == '停止程序':
                        print(f"执行应用停止: {app_name or package_name}")
                        if package_name:
                            success = app_lifecycle_manager.force_stop_by_package(str(package_name), device.serial)
                        else:
                            app_identifier = app_name
                            if app_identifier:
                                success = app_lifecycle_manager.stop_app(str(app_identifier), device.serial)
                            else:
                                success = False
                        operation_name = "stop_app"

                    print(f"{script_category}操作{'成功' if success else '失败'}")

                    # 记录生命周期管理操作日志
                    timestamp = time.time()
                    lifecycle_entry = {
                        "tag": "function",
                        "depth": 1,
                        "time": timestamp,
                        "data": {
                            "name": operation_name,
                            "call_args": {"app_name": app_name or package_name},
                            "start_time": timestamp,
                            "ret": success,
                            "end_time": timestamp + 1,
                            "category": script_category,
                            "is_lifecycle_operation": True
                        }
                    }
                    with open(log_txt_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps(lifecycle_entry, ensure_ascii=False) + "\n")

                    has_executed_steps = True
                    total_step_counter += 1

                    # 对于生命周期脚本，执行完后直接跳过正常的步骤处理
                    print(f"{script_category}脚本执行完成，跳过正常步骤处理")
                    continue

            except Exception as e:
                print(f"执行{script_category}脚本时出错: {e}")
                # 出错时继续执行正常的脚本处理流程

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

                        step_class = step.get("class", "")
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
                            print(f"正在等待AI检测结果: {step_class}")
                            success, (x, y, detected_class) = click_queue.get(timeout=10)  # 使用设备专用click_queue，超时10秒
                            print(f"AI检测完成 - success: {success}, detected_class: {detected_class}, expected_class: {step_class}")

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
                        print(f"[FALLBACK] 开始执行备选步骤")
                        print(f"[FALLBACK] - 所有优先级步骤都未检测到目标")
                        print(f"[FALLBACK] - 执行Priority {unknown_fallback_step.get('Priority', 999)}的备选步骤: {unknown_fallback_step.get('remark', '')}")
                        print(f"[FALLBACK] - 备选步骤配置: {json.dumps(unknown_fallback_step, ensure_ascii=False)}")

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
                    step_class = step.get("class", "")
                    step_remark = step.get("remark", "")

                    # 获取步骤的action类型，如果没有则默认为"click"
                    step_action = step.get("action", "click")

                    # 如果没有class字段，使用action作为显示名称
                    display_name = step_class if step_class else step_action
                    print(f"执行步骤 {step_idx+1}/{len(steps)}: {display_name}, 备注: {step_remark}")

                    # 处理特殊步骤类型
                    if step_class == "delay":
                        # 处理延时步骤
                        delay_seconds = step.get("params", {}).get("seconds", 1)
                        print(f"延时 {delay_seconds} 秒: {step_remark}")
                        time.sleep(delay_seconds)

                        # 记录延时日志
                        timestamp = time.time()
                        delay_entry = {
                            "tag": "function",
                            "depth": 1,
                            "time": timestamp,
                            "data": {
                                "name": "sleep",
                                "call_args": {"secs": delay_seconds},
                                "start_time": timestamp,
                                "ret": None,
                                "end_time": timestamp + delay_seconds
                            }
                        }
                        with open(log_txt_path, "a", encoding="utf-8") as f:
                            f.write(json.dumps(delay_entry, ensure_ascii=False) + "\n")
                        continue

                    elif step_class == "app_start":
                        # 处理应用启动步骤
                        app_name = step.get("params", {}).get("app_name", "")
                        package_name = step.get("params", {}).get("package_name", "")

                        if not app_name and not package_name:
                            print(f"错误: app_start 步骤缺少 app_name 或 package_name 参数")
                            continue

                        print(f"启动应用 {app_name or package_name}: {step_remark}")

                        # 使用 AppLifecycleManager 启动应用
                        app_lifecycle_manager = AppLifecycleManager()
                        success = False

                        if app_name:
                            try:
                                success = app_lifecycle_manager.start_app(str(app_name), device.serial)
                            except Exception as e:
                                print(f"使用模板启动失败: {e}")
                                success = False
                        elif package_name:
                            # 如果提供了包名但没有模板，尝试直接启动
                            print(f"直接启动包名: {package_name}")
                            try:
                                import subprocess
                                result = subprocess.run(
                                    f"adb -s {device.serial} shell am start -n {package_name}/.MainActivity".split(),
                                    capture_output=True,
                                    text=True,
                                    timeout=30
                                )
                                success = result.returncode == 0
                            except Exception as e:
                                print(f"直接启动失败: {e}")
                                success = False

                        print(f"应用启动{'成功' if success else '失败'}")

                        # 记录应用启动日志
                        timestamp = time.time()
                        app_start_entry = {
                            "tag": "function",
                            "depth": 1,
                            "time": timestamp,
                            "data": {
                                "name": "app_start",
                                "call_args": {"app_name": app_name or package_name},
                                "start_time": timestamp,
                                "ret": success,
                                "end_time": timestamp + 0.5
                            }
                        }
                        with open(log_txt_path, "a", encoding="utf-8") as f:
                            f.write(json.dumps(app_start_entry, ensure_ascii=False) + "\n")
                        continue

                    elif step_class == "app_stop":
                        # 处理应用停止步骤
                        app_name = step.get("params", {}).get("app_name", "")
                        package_name = step.get("params", {}).get("package_name", "")

                        if not app_name and not package_name:
                            print(f"错误: app_stop 步骤缺少 app_name 或 package_name 参数")
                            continue

                        print(f"停止应用 {app_name or package_name}: {step_remark}")

                        # 使用 AppLifecycleManager 停止应用
                        app_lifecycle_manager = AppLifecycleManager()
                        success = False

                        if app_name:
                            # 首先尝试使用模板名称
                            try:
                                success = app_lifecycle_manager.stop_app(str(app_name), device.serial)
                                if not success:
                                    # 如果模板停止失败，检查是否是包名格式，直接强制停止
                                    if "." in str(app_name):  # 包名通常包含点号
                                        print(f"模板停止失败，尝试使用包名直接停止: {app_name}")
                                        success = app_lifecycle_manager.force_stop_by_package(str(app_name), device.serial)
                            except Exception as e:
                                print(f"使用模板停止失败: {e}，尝试使用包名直接停止")
                                if "." in str(app_name):  # 包名通常包含点号
                                    success = app_lifecycle_manager.force_stop_by_package(str(app_name), device.serial)
                        else:
                            # 使用包名直接强制停止
                            success = app_lifecycle_manager.force_stop_by_package(package_name, device.serial)

                        print(f"应用停止{'成功' if success else '失败'}")

                        # 记录应用停止日志
                        timestamp = time.time()
                        app_stop_entry = {
                            "tag": "function",
                            "depth": 1,
                            "time": timestamp,
                            "data": {
                                "name": "app_stop",
                                "call_args": {"app_name": app_name or package_name},
                                "start_time": timestamp,
                                "ret": success,
                                "end_time": timestamp + 0.5
                            }
                        }
                        with open(log_txt_path, "a", encoding="utf-8") as f:
                            f.write(json.dumps(app_stop_entry, ensure_ascii=False) + "\n")
                        continue

                    elif step_class == "log":
                        # 处理日志步骤
                        log_message = step.get("params", {}).get("message", step_remark)
                        print(f"日志: {log_message}")

                        # 记录日志条目
                        timestamp = time.time()
                        log_entry = {
                            "tag": "function",
                            "depth": 1,
                            "time": timestamp,
                            "data": {
                                "name": "log",
                                "call_args": {"msg": log_message},
                                "start_time": timestamp,
                                "ret": None,
                                "end_time": timestamp
                            }
                        }
                        with open(log_txt_path, "a", encoding="utf-8") as f:
                            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
                        continue

                    elif step_action == "wait_if_exists":
                        # 处理条件等待步骤
                        element_class = step_class
                        polling_interval = step.get("polling_interval", 1000) / 1000.0  # 转换为秒
                        max_duration = step.get("max_duration", 30)  # 默认30秒超时
                        confidence = step.get("confidence", 0.7)  # 默认置信度

                        print(f"\n🚀 [步骤 {step_idx+1}] 开始执行 wait_if_exists 操作")
                        print(f"📋 元素类型: '{element_class}'")
                        print(f"⚙️ 轮询间隔: {polling_interval}秒")
                        print(f"⏰ 最大等待: {max_duration}秒")
                        print(f"🎯 置信度: {confidence}")
                        print(f"📝 备注: {step_remark}")
                        print(f"⏱️ 步骤开始时间: {time.strftime('%H:%M:%S', time.localtime())}")

                        wait_start_time = time.time()
                        element_found = False
                        wait_result = "not_found"  # not_found, disappeared, timeout

                        try:
                            # 第一步：检查元素是否存在
                            print(f"\n🔍 [阶段1] 检查元素 '{element_class}' 是否存在...")

                            # 获取当前屏幕截图
                            print(f"📱 正在获取屏幕截图...")
                            screenshot = device.screenshot()
                            if screenshot is None:
                                print(f"❌ 警告: 无法获取屏幕截图，跳过条件等待")
                                wait_result = "screenshot_failed"
                            else:
                                print(f"✅ 屏幕截图获取成功，尺寸: {screenshot.shape}")

                                # 使用YOLO模型检测元素（与detect_buttons函数一致）
                                print(f"🤖 正在使用YOLO模型检测元素 '{element_class}'...")
                                success, detection_result = detect_buttons(screenshot, target_class=element_class)
                                print(f"🔍 检测结果: success={success}, detection_result={detection_result}")

                                if success and detection_result[0] is not None:
                                    element_found = True
                                    x, y, detected_class = detection_result
                                    print(f"✅ [阶段1-成功] 元素 '{element_class}' 已找到!")
                                    print(f"📍 位置: ({x:.1f}, {y:.1f})")
                                    print(f"🏷️ 检测类别: {detected_class}")
                                    print(f"\n⏳ [阶段2] 开始等待元素消失...")

                                    loop_count = 0

                                    # 第二步：等待元素消失
                                    while (time.time() - wait_start_time) < max_duration:
                                        loop_count += 1
                                        elapsed_before_sleep = time.time() - wait_start_time
                                        print(f"🔄 [循环 {loop_count}] 等待 {polling_interval}秒... (已等待: {elapsed_before_sleep:.1f}秒)")

                                        time.sleep(polling_interval)

                                        elapsed_after_sleep = time.time() - wait_start_time
                                        print(f"⏰ [循环 {loop_count}] 睡眠结束，检查超时... (已等待: {elapsed_after_sleep:.1f}秒)")

                                        # 检查是否超过等待最大时间
                                        if (time.time() - wait_start_time) >= max_duration:
                                            print(f"⏰ [超时] 等待已达到最大时间 {max_duration}秒，停止等待")
                                            wait_result = "timeout"
                                            break

                                        # 重新获取截图检查元素是否还存在
                                        print(f"📱 [循环 {loop_count}] 重新获取截图...")
                                        current_screenshot = device.screenshot()
                                        if current_screenshot is not None:
                                            print(f"🤖 [循环 {loop_count}] 重新检测元素...")
                                            current_success, current_detection_result = detect_buttons(current_screenshot, target_class=element_class)
                                            print(f"🔍 [循环 {loop_count}] 重新检测结果: success={current_success}, result={current_detection_result}")

                                            if not current_success or current_detection_result[0] is None:
                                                wait_result = "disappeared"
                                                elapsed_time = time.time() - wait_start_time
                                                print(f"✅ [循环 {loop_count}] 元素 '{element_class}' 已消失! (等待时间: {elapsed_time:.1f}秒)")
                                                break
                                            else:
                                                elapsed_time = time.time() - wait_start_time
                                                curr_x, curr_y, curr_class = current_detection_result
                                                print(f"🔄 [循环 {loop_count}] 元素 '{element_class}' 仍然存在")
                                                print(f"📍 当前位置: ({curr_x:.1f}, {curr_y:.1f})")
                                                print(f"⏰ 已等待: {elapsed_time:.1f}秒")
                                        else:
                                            print(f"❌ [循环 {loop_count}] 无法获取当前截图")

                                    if wait_result == "not_found":  # 如果循环结束但没有设置结果，说明超时
                                        wait_result = "timeout"
                                        print(f"⏰ [超时-最终] 元素 '{element_class}' 在 {max_duration}秒内未消失")
                                else:
                                    print(f"✅ [阶段1-跳过] 元素 '{element_class}' 不存在，直接继续")
                                    wait_result = "not_found"

                        except Exception as e:
                            print(f"❌ 错误: 条件等待执行失败: {e}")
                            import traceback
                            print(f"📋 错误详情:\n{traceback.format_exc()}")
                            wait_result = "error"

                        # 计算总等待时间
                        timestamp = time.time()
                        total_wait_time = timestamp - wait_start_time

                        print(f"\n🏁 [步骤 {step_idx+1}] wait_if_exists 执行完成")
                        print(f"📊 最终结果:")
                        print(f"   - 元素发现: {element_found}")
                        print(f"   - 等待结果: {wait_result}")
                        print(f"   - 总等待时间: {total_wait_time:.1f}秒")
                        print(f"⏱️ 步骤结束时间: {time.strftime('%H:%M:%S', time.localtime())}")
                        print(f"{'='*60}")

                        # 记录条件等待日志
                        wait_entry = {
                            "tag": "function",
                            "depth": 1,
                            "time": timestamp,
                            "data": {
                                "name": "wait_if_exists",
                                "call_args": {
                                    "element_class": element_class,
                                    "polling_interval": polling_interval,
                                    "max_duration": max_duration,
                                    "confidence": confidence
                                },
                                "start_time": wait_start_time,
                                "ret": {
                                    "element_found": element_found,
                                    "wait_result": wait_result,
                                    "total_wait_time": total_wait_time
                                },
                                "end_time": timestamp,
                                "desc": step_remark or "条件等待操作",
                                "title": f"#{step_idx+1} {step_remark or '条件等待操作'}"
                            }
                        }
                        with open(log_txt_path, "a", encoding="utf-8") as f:
                            f.write(json.dumps(wait_entry, ensure_ascii=False) + "\n")

                        has_executed_steps = True
                        step_counter += 1
                        continue

                    elif step_action == "swipe":
                        # 处理滑动步骤
                        start_x = step.get("start_x")
                        start_y = step.get("start_y")
                        end_x = step.get("end_x")
                        end_y = step.get("end_y")
                        duration = step.get("duration", 300)

                        if start_x is None or start_y is None or end_x is None or end_y is None:
                            print(f"错误: swipe 步骤缺少必要的坐标参数")
                            continue

                        print(f"执行滑动操作: ({start_x}, {start_y}) -> ({end_x}, {end_y}), 持续{duration}ms: {step_remark}")

                        # 执行ADB滑动命令
                        device.shell(f"input swipe {int(start_x)} {int(start_y)} {int(end_x)} {int(end_y)} {int(duration)}")

                        # 记录滑动日志
                        timestamp = time.time()
                        swipe_entry = {
                            "tag": "function",
                            "depth": 1,
                            "time": timestamp,
                            "data": {
                                "name": "swipe",
                                "call_args": {
                                    "start": [int(start_x), int(start_y)],
                                    "end": [int(end_x), int(end_y)],
                                    "duration": int(duration)
                                },
                                "start_time": timestamp,
                                "ret": {
                                    "start_pos": [int(start_x), int(start_y)],
                                    "end_pos": [int(end_x), int(end_y)]
                                },
                                "end_time": timestamp + (duration / 1000.0),
                                "desc": step_remark or "滑动操作",
                                "title": f"#{step_idx+1} {step_remark or '滑动操作'}"
                            }
                        }
                        with open(log_txt_path, "a", encoding="utf-8") as f:
                            f.write(json.dumps(swipe_entry, ensure_ascii=False) + "\n")

                        has_executed_steps = True
                        step_counter += 1

                        # 滑动后等待一段时间让UI响应
                        time.sleep(duration / 1000.0 + 0.5)
                        continue

                    elif step_class == "app_start":
                        # 处理应用启动步骤
                        app_name = step.get("params", {}).get("app_name", "")
                        print(f"启动应用: {app_name} - {step_remark}")

                        try:
                            app_manager = AppLifecycleManager()
                            result = app_manager.start_app(app_name, device.serial)
                            print(f"应用启动结果: {result}")

                            # 记录应用启动日志
                            timestamp = time.time()
                            app_start_entry = {
                                "tag": "function",
                                "depth": 1,
                                "time": timestamp,
                                "data": {
                                    "name": "start_app",
                                    "call_args": {"app_name": app_name},
                                    "start_time": timestamp,
                                    "ret": result,
                                    "end_time": timestamp + 1
                                }
                            }
                            with open(log_txt_path, "a", encoding="utf-8") as f:
                                f.write(json.dumps(app_start_entry, ensure_ascii=False) + "\n")
                        except Exception as e:
                            print(f"启动应用失败: {e}")
                        continue

                    elif step_class == "app_stop":
                        # 处理应用停止步骤
                        params = step.get("params", {})
                        app_name = params.get("app_name", "")
                        package_name = params.get("package_name", "")

                        print(f"停止应用 - {step_remark}")

                        try:
                            app_manager = AppLifecycleManager()

                            if package_name:
                                # 直接使用包名停止应用
                                print(f"使用包名停止应用: {package_name}")
                                result = app_manager.force_stop_by_package(package_name, device.serial)
                                call_args = {"package_name": package_name}
                            elif app_name:
                                # 使用模板名停止应用
                                print(f"使用模板名停止应用: {app_name}")
                                result = app_manager.stop_app(app_name, device.serial)
                                call_args = {"app_name": app_name}
                            else:
                                print("错误: 未提供app_name或package_name参数")
                                continue

                            print(f"应用停止结果: {result}")

                            # 记录应用停止日志
                            timestamp = time.time()
                            app_stop_entry = {
                                "tag": "function",
                                "depth": 1,
                                "time": timestamp,
                                "data": {
                                    "name": "stop_app",
                                    "call_args": call_args,
                                    "start_time": timestamp,
                                    "ret": result,
                                    "end_time": timestamp + 1
                                }
                            }
                            with open(log_txt_path, "a", encoding="utf-8") as f:
                                f.write(json.dumps(app_stop_entry, ensure_ascii=False) + "\n")
                        except Exception as e:
                            print(f"停止应用失败: {e}")
                        continue

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
                    screenshot_queue.put((device_name, total_step_counter, frame, step_class, None))                        # 等待检测结果
                    try:
                        print(f"[DEBUG] 正在等待AI检测结果: 目标类别={step_class}, 优先级={priority}")
                        success, (x, y, detected_class) = click_queue.get(timeout=10)  # 使用设备专用click_queue，超时10秒
                        print(f"[DEBUG] AI检测完成 - success={success}, detected_class='{detected_class}', expected_class='{step_class}', 坐标=({x}, {y})")

                        if success:
                            print(f"[DEBUG] ✓ AI成功检测到目标，匹配成功！")
                        else:
                            print(f"[DEBUG] ✗ AI未能成功检测到目标: 期望'{step_class}', 实际检测到'{detected_class}'")

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
    print("🚀 检测服务已启动")
    while not stop_event.is_set():
        try:
            item = screenshot_queue.get(timeout=1)
            if len(item) != 5:
                print(f"⚠️ 跳过无效数据: {item}")
                continue
            device_name, step_num, frame, target_class, all_classes_or_special = item
            print(f"📸 设备 {device_name} 步骤 {step_num}: 检测 {target_class}")
            success, coords = detect_buttons(frame, target_class=target_class)
            print(f"✅ 检测结果: {success}, 坐标: {coords}")
            click_queue.put((success, coords))
        except queue.Empty:
            continue
        except Exception as e:
            print(f"❌ 检测服务错误: {e}")
            import traceback
            traceback.print_exc()


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
        # 修复：使用静态资源的绝对路径，避免Airtest在当前工作目录寻找资源
        static_root_path = os.path.join(report_dir, "static")
        rpt = LogToHtml(
            script_root=report_dir,         # 项目根目录
            log_root=log_report_dir,        # log子目录
            static_root=static_root_path,   # 使用绝对路径
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

        # 生成报告 - 使用线程锁防止多设备同时复制静态资源导致的竞争条件
        with REPORT_GENERATION_LOCK:
            print(f"📊 开始生成报告，设备占用锁中...")

            # 预处理：彻底清理script.log目录，避免Airtest copytree冲突
            script_log_dir = os.path.dirname(script_log_html_file)
            if os.path.exists(script_log_dir):
                try:
                    shutil.rmtree(script_log_dir)
                    print(f"🧹 已清理现有的script.log目录: {script_log_dir}")
                except Exception as e:
                    print(f"⚠️ 清理script.log目录时出错: {e}")

            # 直接生成报告，全局修补的shutil.copytree会自动处理目录冲突
            try:
                print(f"🚀 开始生成Airtest报告...")
                rpt.report()
                print(f"✅ Airtest报告生成完成")
            except Exception as e:
                print(f"⚠️ 报告生成时出现异常: {e}")
                # 即使出现异常也继续，因为可能只是复制资源的问题
                import traceback
                traceback.print_exc()

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
    同步单个设备报告目录到新的统一报告目录结构中，保证Web端可访问。
    现在直接生成到最终位置，无需同步操作。
    Args:
        device_report_dir (str): 设备报告目录的绝对路径
    Returns:
        None
    """
    # 由于现在使用统一的目录结构直接生成报告到staticfiles/reports/，无需同步操作
    print(f"设备报告已在统一目录中生成: {device_report_dir}")
    print("已使用统一报告目录结构，无需额外同步操作")


def _should_include_device_in_summary(report_path, test_session_start=None):
    """
    检查设备是否应该包含在汇总报告中
    基于当前测试会话的时间范围进行过滤

    :param report_path: 设备报告路径
    :param test_session_start: 测试会话开始时间戳
    :return: True 如果设备应该包含在汇总报告中，False 如果是之前测试会话的设备
    """
    if not report_path or not os.path.exists(report_path):
        print(f"[过滤] 设备报告路径无效或文件不存在: {report_path}")
        return False

    # 如果没有提供测试会话开始时间，包含所有设备（兼容旧版本）
    if test_session_start is None:
        print(f"[兼容] 未提供测试会话开始时间，包含设备: {os.path.basename(os.path.dirname(report_path))}")
        return True

    try:
        # 从报告路径中提取设备目录名称和时间戳
        device_dir_name = os.path.basename(os.path.dirname(report_path))

        # 提取时间戳部分 (格式: 设备名_YYYY-MM-DD-HH-MM-SS)
        import re
        timestamp_match = re.search(r'_(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2})$', device_dir_name)
        if not timestamp_match:
            print(f"[警告] 无法从设备目录名称中提取时间戳: {device_dir_name}")
            return True  # 如果无法提取时间戳，保守地包含该设备

        device_timestamp_str = timestamp_match.group(1)

        # 将设备时间戳转换为时间戳进行比较
        from datetime import datetime
        device_time = datetime.strptime(device_timestamp_str, '%Y-%m-%d-%H-%M-%S')
        device_timestamp = device_time.timestamp()

        # 将测试会话开始时间转换为datetime以便比较
        session_start_time = datetime.fromtimestamp(test_session_start)

        # 计算时间差（分钟）
        time_diff_minutes = abs(device_timestamp - test_session_start) / 60

        # 如果设备时间戳在测试会话开始前后5分钟内，认为是当前会话的设备
        is_current_session = time_diff_minutes <= 5

        if is_current_session:
            print(f"[包含] 设备 {device_dir_name} 属于当前测试会话 (时间差: {time_diff_minutes:.1f}分钟)")
        else:
            print(f"[排除] 设备 {device_dir_name} 不属于当前测试会话 (时间差: {time_diff_minutes:.1f}分钟)")
            print(f"        设备时间: {device_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"        会话开始: {session_start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        return is_current_session

    except Exception as e:
        print(f"[错误] 处理设备时间戳时出错: {e}, 设备: {device_dir_name if 'device_dir_name' in locals() else 'unknown'}")
        return True  # 出错时保守地包含该设备


# 生成汇总报告
def run_summary(data):
    """
    生成汇总报告（方案1：直接生成到静态目录）
    :param data: 测试数据，包含每个设备的测试结果
    :return: 汇总报告的路径
    """
    try:
        # 直接使用staticfiles目录作为生成目标，消除文件拷贝
        staticfiles_reports_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "staticfiles", "reports", "summary_reports"
        )
        os.makedirs(staticfiles_reports_dir, exist_ok=True)

        # 生成带时间戳的报告文件名
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        report_file = f"summary_report_{timestamp}.html"
        summary_report_path = os.path.join(staticfiles_reports_dir, report_file)

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
        test_session_start = data.get('start')  # 获取测试会话开始时间

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
            if report_generated and report_path:
                # 从绝对路径中提取设备目录名称
                device_dir_name = os.path.basename(os.path.dirname(str(report_path)))

                # 计算汇总报告目录到设备报告目录的相对路径
                # 汇总报告在 staticfiles/reports/summary_reports/
                # 设备报告现在在 staticfiles/reports/ui_run/WFGameAI.air/log/设备目录/
                # 相对路径只需要向上一级目录
                report_rel_path = f"../ui_run/WFGameAI.air/log/{device_dir_name}/log.html"
                print(f"设备 {dev_name} 报告相对路径: {report_rel_path}")

            # 检查设备是否包含在当前测试会话中
            # 基于设备报告时间戳和测试会话开始时间进行过滤
            should_include_in_summary = _should_include_device_in_summary(report_path, test_session_start)

            # 如果设备不属于当前测试会话，跳过该设备不计入汇总统计
            if not should_include_in_summary:
                print(f"设备 {dev_name} 不属于当前测试会话，从汇总报告中排除")
                continue

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
        latest_report_path = os.path.join(staticfiles_reports_dir, "latest_report.html")
        shutil.copy(summary_report_path, latest_report_path)

        print(f"汇总报告已生成: {summary_report_path}")
        print(f"最新报告快捷方式: {latest_report_path}")

        return summary_report_path
    except Exception as e:
        print(f"汇总报告生成失败: {e}")
        traceback.print_exc()
        return ""


# 处理脚本路径，确保使用配置系统中的路径
def normalize_script_path(script_path):
    """处理脚本路径，确保使用配置中的路径"""
    # 如果已经是绝对路径，直接使用
    if os.path.isabs(script_path) and os.path.exists(script_path):
        return script_path

    # 确保路径变量不为None
    testcase_dir = TESTCASE_DIR if TESTCASE_DIR is not None else DEFAULT_TESTCASE_DIR
    base_dir = BASE_DIR if BASE_DIR is not None else DEFAULT_BASE_DIR

    # 相对路径处理策略
    # 1. 首先尝试相对于TESTCASE_DIR的路径
    path_in_testcase = os.path.join(testcase_dir, os.path.basename(script_path))
    if os.path.exists(path_in_testcase):
        return path_in_testcase

    # 2. 尝试相对于BASE_DIR的路径
    path_in_base = os.path.join(base_dir, script_path)
    if os.path.exists(path_in_base):
        return path_in_base

    # 3. 尝试相对于BASE_DIR/testcase的路径
    path_in_base_testcase = os.path.join(base_dir, "testcase", os.path.basename(script_path))
    if os.path.exists(path_in_base_testcase):
        return path_in_base_testcase

    # 如果都不存在，返回原始路径并打印警告
    print(f"警告: 找不到脚本文件 {script_path}")
    print(f"已尝试以下路径:")
    print(f"  - {path_in_testcase}")
    print(f"  - {path_in_base}")
    print(f"  - {path_in_base_testcase}")
    return script_path


def parse_script_args():
    """
    使用 argparse 解析脚本参数，支持多脚本顺序执行，每个脚本可单独指定循环次数和最大执行时间
    支持多线程并发执行控制
    """
    parser = argparse.ArgumentParser(
        description='回放游戏操作脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 单个脚本
  replay_script.py --script test.json --loop-count 5

  # 多个脚本顺序执行，使用全局参数
  replay_script.py --loop-count 2 --script script1.json --script script2.json

  # 多个脚本顺序执行，每个脚本单独指定参数
  replay_script.py --script script1.json --loop-count 1 --script script2.json --max-duration 30

  # 使用脚本列表文件
  replay_script.py --script-list scripts.json

  # 多线程执行控制
  replay_script.py --script test.json --max-workers 4
  replay_script.py --script test.json --conservative
        """
    )

    # 脚本相关参数
    parser.add_argument('--script', '-s', action='append', dest='scripts',
                       help='脚本文件路径（可多次指定，支持顺序执行）')
    parser.add_argument('--script-list', '-l',
                       help='脚本列表文件路径')
    parser.add_argument('--loop-count', '-c', type=int, default=1,
                       help='循环次数（默认为1）')
    parser.add_argument('--max-duration', '-t', type=int,
                       help='最大执行时间（秒）')

    # 设备和显示参数
    parser.add_argument('--device', '-d',
                       help='指定设备序列号，不指定则使用所有已连接设备')
    parser.add_argument('--show-screens', action='store_true',
                       help='显示截图（默认为不显示）')

    # 多线程参数
    parser.add_argument('--max-workers', type=int, default=None,
                       help='最大工作线程数，不指定则无限制并发（默认：无限制）')
    parser.add_argument('--conservative', action='store_true',
                       help='保守模式：限制为4个并发线程（等同于 --max-workers 4）')

    # 其他参数
    parser.add_argument('--run-all', action='store_true',
                       help='忽略进度文件，全部重新测试')
    parser.add_argument('--clear', dest='clear_logs', action='store_true',
                       help='清空所有历史日志')
    parser.add_argument('--model', '-m', default='best.pt',
                       help='指定YOLO模型文件路径（默认为best.pt）')

    args = parser.parse_args()

    # 处理保守模式
    if args.conservative:
        args.max_workers = 4

    # 验证参数
    if not args.scripts and not args.script_list:
        parser.error("必须指定 --script 或 --script-list 参数")

    # 将简单的脚本列表转换为详细格式以保持兼容性
    if args.scripts:
        scripts_detailed = []
        for script_path in args.scripts:
            scripts_detailed.append({
                'path': script_path,
                'loop_count': args.loop_count,
                'max_duration': args.max_duration,
                'script_id': None,
                'category': None
            })
        args.scripts = scripts_detailed

    return vars(args)


def execute_device_replay_parallel(devices, scripts_to_run, screenshot_queue, action_queue, args, model, max_workers=None):
    """
    并行执行多设备回放，支持线程池控制

    :param devices: 设备列表
    :param scripts_to_run: 要运行的脚本列表
    :param screenshot_queue: 截图队列
    :param action_queue: 动作队列
    :param args: 命令行参数
    :param model: YOLO模型
    :param max_workers: 最大工作线程数，None表示无限制
    :return: dict 包含每个设备的执行结果
    """
    if not devices:
        print("没有可用的设备")
        return {}, {}

    device_count = len(devices)
    print(f"开始并行处理 {device_count} 个设备")

    # 确定实际的工作线程数
    if max_workers is None:
        actual_workers = device_count  # 无限制时，每个设备一个线程
        print(f"并发模式：无限制 ({actual_workers} 个并发线程)")
    else:
        actual_workers = min(max_workers, device_count)
        print(f"并发模式：限制为 {max_workers} 个工作线程 (实际 {actual_workers} 个)")

    device_results = {}
    device_reports = {}

    def process_device(device):
        """处理单个设备的回放 - 每个设备使用独立的检测队列和线程"""
        device_name = None
        device_screenshot_queue = queue.Queue()  # 立即初始化
        device_action_queue = queue.Queue()      # 立即初始化
        device_click_queue = queue.Queue()       # 立即初始化
        detection_thread = None
        stop_event = Event()                     # 立即初始化

        try:
            device_name = get_device_name(device)
            print(f"设备 {device_name} 开始初始化...")

            # 检查设备状态
            if not check_device_status(device, device_name):
                print(f"设备 {device_name} 状态异常，跳过")
                return device_name, {'success': False, 'error': '设备状态异常'}

            # 获取设备日志目录
            log_dir = get_log_dir(device_name)
            print(f"设备 {device_name} 日志目录: {log_dir}")

            print(f"设备 {device_name} 创建独立检测队列和线程...")

            # 为每个设备创建独立的检测服务线程
            detection_thread = Thread(
                target=detection_service,
                args=(device_screenshot_queue, device_click_queue, stop_event),
                daemon=True,
                name=f"detection_service_{device_name}"
            )
            detection_thread.start()
            print(f"设备 {device_name} 检测服务线程已启动")

            # 执行设备回放
            try:
                print(f"设备 {device_name} 开始执行回放...")
                replay_device(
                    device,
                    scripts_to_run,
                    device_screenshot_queue,  # 设备专用
                    device_action_queue,      # 设备专用
                    device_click_queue,       # 设备专用
                    stop_event,
                    device_name,
                    log_dir,
                    args['show_screens'],
                    1  # 传递默认循环次数，但实际使用脚本中的循环次数
                )

                print(f"设备 {device_name} 回放执行完成，正在清理资源...")

                # 停止检测线程
                stop_event.set()
                if detection_thread and detection_thread.is_alive():
                    detection_thread.join(timeout=5)
                    if detection_thread.is_alive():
                        print(f"警告：设备 {device_name} 检测线程未能在5秒内正常结束")

                print(f"设备 {device_name} 开始生成报告...")

                # 生成报告
                report_generated, test_passed = run_one_report(
                    log_dir=log_dir,
                    report_dir=log_dir,
                    script_path=[s['path'] for s in scripts_to_run]
                )

                result = {
                    'success': True,
                    'report_path': os.path.join(log_dir, "log.html") if report_generated else None,
                    'test_passed': test_passed,
                    'log_dir': log_dir
                }

                print(f"设备 {device_name} 完成 - 报告：{'成功' if report_generated else '失败'}, 测试：{'通过' if test_passed else '失败'}")
                return device_name, result

            except Exception as e:
                print(f"设备 {device_name} 回放执行失败: {e}")
                traceback.print_exc()
                return device_name, {'success': False, 'error': str(e)}

        except Exception as e:
            error_msg = f"设备 {device_name or 'unknown'} 处理失败: {e}"
            print(error_msg)
            traceback.print_exc()
            return device_name or str(device), {'success': False, 'error': str(e)}

        finally:
            # 确保资源被正确清理
            try:
                if stop_event:
                    stop_event.set()
                if detection_thread and detection_thread.is_alive():
                    detection_thread.join(timeout=3)
                # 清空队列
                if device_screenshot_queue:
                    while not device_screenshot_queue.empty():
                        try:
                            device_screenshot_queue.get_nowait()
                        except queue.Empty:
                            break
                if device_action_queue:
                    while not device_action_queue.empty():
                        try:
                            device_action_queue.get_nowait()
                        except queue.Empty:
                            break
                if device_click_queue:
                    while not device_click_queue.empty():
                        try:
                            device_click_queue.get_nowait()
                        except queue.Empty:
                            break
                print(f"设备 {device_name or 'unknown'} 资源清理完成")
            except Exception as cleanup_e:
                print(f"设备 {device_name or 'unknown'} 资源清理时出错: {cleanup_e}")

    # 使用ThreadPoolExecutor并行执行
    with ThreadPoolExecutor(max_workers=actual_workers) as executor:
        # 提交所有设备任务
        future_to_device = {executor.submit(process_device, device): device for device in devices}

        # 收集结果
        for future in as_completed(future_to_device):
            device = future_to_device[future]
            try:
                device_name, result = future.result()
                device_results[device_name] = result
                if result.get('success'):
                    device_reports[device_name] = {
                        'report_path': result.get('report_path'),
                        'log_dir': result.get('log_dir')
                    }
            except Exception as e:
                device_name = get_device_name(device) if hasattr(device, 'serial') else str(device)
                print(f"设备 {device_name} 执行异常: {e}")
                traceback.print_exc()
                device_results[device_name] = {'success': False, 'error': str(e)}

    print(f"所有设备处理完成。成功：{sum(1 for r in device_results.values() if r.get('success'))}/{len(device_results)}")
    return device_results, device_reports


if __name__ == "__main__":
    # 使用自定义参数解析
    args = parse_script_args()

    if args['clear_logs']:
        print("清空所有历史日志...")
        # 使用新的统一目录结构
        if os.path.exists(DEVICE_REPORTS_DIR):
            shutil.rmtree(DEVICE_REPORTS_DIR)
        if os.path.exists(SUMMARY_REPORTS_DIR):
            shutil.rmtree(SUMMARY_REPORTS_DIR)

        # 重新创建目录
        os.makedirs(DEVICE_REPORTS_DIR, exist_ok=True)
        os.makedirs(SUMMARY_REPORTS_DIR, exist_ok=True)
        print(f"已清空并重新创建统一报告目录")
        print(f"设备报告目录: {DEVICE_REPORTS_DIR}")
        print(f"汇总报告目录: {SUMMARY_REPORTS_DIR}")

    # 加载YOLO模型
    try:
        # 检查是否可以使用工具类中的load_yolo_model函数
        try:
            # 尝试从utils.py导入load_yolo_model
            sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
            from utils import load_yolo_model as utils_load_yolo_model

            # 使用工具类的函数加载模型
            print("使用统一的模型加载工具...")

            # 判断参数是否是绝对路径
            if os.path.isabs(args['model']):
                model = utils_load_yolo_model(model_path=args['model'], exit_on_failure=True)
            else:
                # 使用更健壮的扩展模式, 会自动搜索多个路径
                model = utils_load_yolo_model(
                    base_dir=BASE_DIR,
                    model_class=YOLO,
                    specific_model=args['model'],
                    exit_on_failure=True
                )
            print(f"模型加载成功")

        except (ImportError, AttributeError) as e:
            print(f"无法使用统一工具类加载模型: {e}")

            # 使用原来的加载逻辑作为备用
            # 从配置获取权重文件目录
            weights_dir = ""
            if config_manager:
                weights_dir = config_manager.get_path('weights_dir')

            if not weights_dir or not os.path.isdir(weights_dir):
                # 如果配置中的权重目录无效，设置默认路径
                project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
                weights_dir = os.path.join(project_root, "wfgame-ai-server", "apps", "scripts", "datasets", "train", "weights")
                print(f"从配置获取权重目录失败，使用默认目录: {weights_dir}")

            # 构建模型路径
            model_file = args['model']
            if os.path.isabs(model_file):
                model_path = model_file
            else:
                model_path = os.path.join(weights_dir, model_file)

            print(f"使用模型路径: {model_path}")

            # 检查文件是否存在
            if not os.path.exists(model_path):
                print(f"警告：模型文件不存在: {model_path}")
                print("尝试使用备用路径...")

                # 尝试在项目根目录查找模型文件
                project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
                candidate_paths = [
                    os.path.join(project_root, model_file),
                    os.path.join(project_root, "yolo11m.pt"),
                    os.path.join(weights_dir, "best.pt")
                ]

                found_model = False
                for alt_model_path in candidate_paths:
                    if os.path.exists(alt_model_path):
                        model_path = alt_model_path
                        print(f"找到备用模型: {model_path}")
                        found_model = True
                        break

                if not found_model:
                    print("错误：无法找到可用的模型文件")
                    sys.exit(1)

            print(f"加载模型: {model_path}")
            model = YOLO(model_path)
            print(f"✅ 模型加载成功: {type(model)}")
            print(f"📋 模型类别: {model.names if hasattr(model, 'names') else '未知'}")
        # print(f"模型加载成功: {model}")
    except Exception as e:
        print(f"模型加载失败: {e}")
        traceback.print_exc()
        sys.exit(1)

    # 准备脚本
    scripts_to_run = []

    if args['scripts']:
        # 处理多个 --script 参数（新的自定义解析逻辑）
        for script_info in args['scripts']:
            normalized_path = normalize_script_path(script_info['path'])
            if not os.path.exists(normalized_path):
                print(f"错误: 脚本文件不存在: {normalized_path}")
                sys.exit(1)

            scripts_to_run.append({
                "path": normalized_path,
                "loop_count": script_info['loop_count'],
                "max_duration": script_info['max_duration'],
                "script_id": script_info.get('script_id'),
                "category": script_info.get('category')
            })

        print(f"将运行 {len(scripts_to_run)} 个脚本（顺序执行）")

    elif args['script_list']:
        list_path = normalize_script_path(args['script_list'])
        if not os.path.exists(list_path):
            print(f"错误: 脚本列表文件不存在: {list_path}")
            sys.exit(1)

        try:
            with open(list_path, "r", encoding="utf-8") as f:
                script_list_data = json.load(f)

            for script_item in script_list_data:
                if isinstance(script_item, dict):
                    script_path = script_item.get("path")
                    # 处理 loop_count=null 的特殊情况，将其转换为无限循环（用 999999 表示）
                    loop_count = script_item.get("loop_count")
                    if loop_count is None and script_item.get("max_duration") is not None:
                        loop_count = 999999  # 当 loop_count 为 null 且设置了 max_duration 时，视为无限循环
                    else:
                        loop_count = loop_count if loop_count is not None else 1  # 默认循环次数
                    max_duration = script_item.get("max_duration", None)
                else:
                    script_path = script_item
                    loop_count = 1  # 默认循环次数
                    max_duration = None

                normalized_path = normalize_script_path(script_path)
                if os.path.exists(normalized_path):
                    scripts_to_run.append({
                        "path": normalized_path,
                        "loop_count": loop_count,
                        "max_duration": max_duration
                    })
                else:
                    print(f"警告: 跳过不存在的脚本: {normalized_path}")

            print(f"将运行 {len(scripts_to_run)} 个脚本")
        except Exception as e:
            print(f"读取脚本列表文件失败: {e}")
            traceback.print_exc()
            sys.exit(1)
    else:
        print("错误: 必须指定 --script 或 --script-list 参数")
        print("使用 --help 查看帮助信息")
        sys.exit(1)

    # 获取设备列表
    try:
        device_list = adb.device_list()
        if not device_list:
            print("错误: 未找到已连接的设备")
            sys.exit(1)

        if args['device']:
            # 使用指定的设备
            devices = [d for d in device_list if d.serial == args['device']]
            if not devices:
                print(f"错误: 未找到指定的设备: {args['device']}")
                print("可用设备:")
                for d in device_list:
                    print(f"  - {d.serial}")
                sys.exit(1)
        else:
            # 使用所有已连接设备
            devices = device_list

        print(f"使用设备: {', '.join([d.serial if d.serial else '' for d in devices])}")
    except Exception as e:
        print(f"获取设备列表失败: {e}")
        traceback.print_exc()
        sys.exit(1)

    # 加载测试进度数据
    data = load_json_data(args['run_all'])

    # 使用并行执行处理所有设备
    print("开始并行处理设备...")
    device_results, device_reports = execute_device_replay_parallel(
        devices=devices,
        scripts_to_run=scripts_to_run,
        screenshot_queue=screenshot_queue,
        action_queue=action_queue,
        args=args,
        model=model,
        max_workers=args.get('max_workers')
    )

    # 生成报告
    print("所有设备回放完成，生成报告...")

    test_results = {}
    for device_name, result in device_results.items():
        if result.get('success'):
            test_results[device_name] = {
                'report_path': result.get('report_path'),
                'test_passed': result.get('test_passed', False)
            }
            print(f"设备 {device_name} 报告生成 {'成功' if result.get('report_path') else '失败'}, 测试 {'通过' if result.get('test_passed') else '失败'}")
        else:
            test_results[device_name] = {
                'report_path': None,
                'test_passed': False
            }
            print(f"设备 {device_name} 处理失败: {result.get('error', '未知错误')}")

    # 更新测试进度数据
    data['tests'].update(test_results)
    data['end'] = time.time()
    data['duration'] = data['end'] - data.get('start', data['end'])

    # 保存测试进度数据
    try:
        with open(os.path.join(BASE_DIR, 'data.json'), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存测试进度数据失败: {e}")

    # 生成汇总报告
    summary_report_path = run_summary(data)
    if summary_report_path:
        print(f"汇总报告已生成: {summary_report_path}")
    else:
        print("汇总报告生成失败")

    print("所有操作完成")