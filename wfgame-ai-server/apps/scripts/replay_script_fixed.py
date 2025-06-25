# -*- coding: utf-8 -*-
"""
重构后的 replay_script.py - 精简版本
负责核心流程控制，具体的action处理委托给ActionProcessor
"""

from airtest.core.api import set_logdir
import cv2
import numpy as np
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
import io
import re
import glob
from adbutils import adb
import traceback
from datetime import datetime
import random
from pathlib import Path

# 导入必要的模块
try:
    from account_manager import get_account_manager
except ImportError:
    try:
        from .account_manager import get_account_manager
    except ImportError:
        from apps.scripts.account_manager import get_account_manager

try:
    from enhanced_input_handler import DeviceScriptReplayer
except ImportError:
    try:
        from .enhanced_input_handler import DeviceScriptReplayer
    except ImportError:
        DeviceScriptReplayer = None

try:
    from app_permission_manager import integrate_with_app_launch
except ImportError:
    try:
        from .app_permission_manager import integrate_with_app_launch
    except ImportError:
        integrate_with_app_launch = None

try:
    from enhanced_device_preparation_manager import EnhancedDevicePreparationManager
except ImportError:
    try:
        from .enhanced_device_preparation_manager import EnhancedDevicePreparationManager
    except ImportError:
        EnhancedDevicePreparationManager = None

try:
    from action_processor import ActionProcessor, ActionContext, ActionResult
except ImportError:
    try:
        from .action_processor import ActionProcessor, ActionContext, ActionResult
    except ImportError:
        from apps.scripts.action_processor import ActionProcessor, ActionContext, ActionResult

# 定义实时输出函数，确保日志立即显示
def print_realtime(message):
    """打印消息并立即刷新输出缓冲区，确保实时显示"""
    print(message)
    sys.stdout.flush()

# 导入新的统一报告管理系统
try:
    # 方法1: 尝试使用Django应用导入
    try:
        from apps.reports.report_manager import ReportManager
        from apps.reports.report_generator import ReportGenerator
        print_realtime("✅ 已通过Django应用导入统一报告管理系统")
    except ImportError:
        # 方法2: 尝试相对路径导入
        reports_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'reports')
        if reports_path not in sys.path:
            sys.path.insert(0, reports_path)

        from report_manager import ReportManager
        from report_generator import ReportGenerator
        print_realtime("✅ 已通过相对路径导入统一报告管理系统")

except ImportError as e:
    print_realtime(f"⚠️ 无法导入统一报告管理系统: {e}")
    print_realtime(f"Debug: 当前工作目录: {os.getcwd()}")
    print_realtime(f"Debug: __file__路径: {__file__}")
    print_realtime(f"Debug: 尝试导入路径: {os.path.join(os.path.dirname(os.path.dirname(__file__)), 'reports')}")
    ReportManager = None
    ReportGenerator = None

# 全局修补shutil.copytree以解决Airtest静态资源复制问题
print_realtime("🔧 应用全局shutil.copytree修补，防止静态资源复制冲突")
_original_copytree = shutil.copytree

def _patched_copytree(src, dst, symlinks=False, ignore=None, copy_function=shutil.copy2,
                     ignore_dangling_symlinks=False, dirs_exist_ok=True):
    """全局修补的copytree函数，自动处理目录已存在的情况"""
    try:
        return _original_copytree(src, dst, symlinks=symlinks, ignore=ignore,
                                 copy_function=copy_function,
                                 ignore_dangling_symlinks=ignore_dangling_symlinks,
                                 dirs_exist_ok=True)
    except TypeError:
        try:
            if os.path.exists(dst):
                shutil.rmtree(dst)
            return _original_copytree(src, dst, symlinks=symlinks, ignore=ignore,
                                     copy_function=copy_function,
                                     ignore_dangling_symlinks=ignore_dangling_symlinks)
        except Exception as e:
            print_realtime(f"🔧 全局copytree修补失败，忽略错误继续执行: {src} -> {dst}, 错误: {e}")
            if os.path.exists(dst):
                return dst
            raise e
    except Exception as e:
        print_realtime(f"🔧 全局copytree处理异常: {src} -> {dst}, 错误: {e}")
        if os.path.exists(dst):
            return dst
        raise e

# 应用全局修补
shutil.copytree = _patched_copytree
print_realtime("✅ 全局shutil.copytree修补已应用")

# 初始化统一报告管理系统
REPORT_MANAGER = None
REPORT_GENERATOR = None

if ReportManager and ReportGenerator:
    try:
        # 获取项目根目录
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        REPORT_MANAGER = ReportManager(base_dir)
        REPORT_GENERATOR = ReportGenerator(REPORT_MANAGER)
        print_realtime("✅ 统一报告管理系统初始化成功")
    except Exception as e:
        print_realtime(f"⚠️ 统一报告管理系统初始化失败: {e}")

# 统一报告目录配置（向后兼容）
if REPORT_MANAGER:
    STATICFILES_REPORTS_DIR = str(REPORT_MANAGER.reports_root)
    DEVICE_REPORTS_DIR = str(REPORT_MANAGER.device_reports_dir)
    SUMMARY_REPORTS_DIR = str(REPORT_MANAGER.summary_reports_dir)
else:
    # 回退到旧的配置
    STATICFILES_REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "staticfiles", "reports")
    DEVICE_REPORTS_DIR = os.path.join(STATICFILES_REPORTS_DIR, "ui_run", "WFGameAI.air", "log")
    SUMMARY_REPORTS_DIR = os.path.join(STATICFILES_REPORTS_DIR, "summary_reports")

# 默认路径
DEFAULT_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TESTCASE_DIR = os.path.join(DEFAULT_BASE_DIR, "testcase")

# 全局锁
REPORT_GENERATION_LOCK = Lock()

# 导入配置管理
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from config_import import config_manager, ConfigManager
except ImportError as e:
    print_realtime(f"配置导入失败: {e}")
    config_manager = None

# 全局YOLO模型变量
model = None

# 导入YOLO和模型加载功能
try:
    from ultralytics import YOLO
    print_realtime("✅ 成功导入ultralytics YOLO")
except ImportError as e:
    print_realtime(f"⚠️ 导入ultralytics失败: {e}")
    YOLO = None

# 导入load_yolo_model函数
try:
    from utils import load_yolo_model
    print_realtime("✅ 成功导入load_yolo_model函数")
except ImportError:
    try:
        # 尝试从项目根目录导入
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        from utils import load_yolo_model
        print_realtime("✅ 从项目根目录成功导入load_yolo_model函数")
    except ImportError:
        print_realtime("⚠️ 无法导入load_yolo_model函数")
        load_yolo_model = None

def load_yolo_model_for_detection(model_path=None):
    """加载YOLO模型用于AI检测"""
    global model

    if YOLO is None:
        print_realtime("❌ 无法加载YOLO模型：ultralytics未正确导入")
        return False

    try:
        if model_path and os.path.exists(model_path):
            print_realtime(f"🔄 加载指定模型: {model_path}")
            model = YOLO(model_path)
        elif load_yolo_model is not None:
            # 使用项目的load_yolo_model函数
            base_dir = os.path.dirname(os.path.abspath(__file__))
            try:
                model = load_yolo_model(
                    base_dir=base_dir,
                    model_class=YOLO,
                    specific_model=None,
                    exit_on_failure=False
                )
                if model is not None:
                    print_realtime("✅ 成功使用load_yolo_model加载模型")
                else:
                    print_realtime("⚠️ load_yolo_model返回None")
                    return False
            except Exception as e:
                print_realtime(f"⚠️ load_yolo_model加载失败: {e}")
                return False
        else:
            # 尝试查找默认模型路径
            possible_paths = [
                os.path.join(os.path.dirname(__file__), "datasets", "train", "weights", "best.pt"),
                os.path.join(os.path.dirname(__file__), "best.pt"),
                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models", "best.pt")
            ]

            model_found = False
            for path in possible_paths:
                if os.path.exists(path):
                    print_realtime(f"🔄 找到并加载模型: {path}")
                    model = YOLO(path)
                    model_found = True
                    break

            if not model_found:
                print_realtime("⚠️ 未找到可用的YOLO模型文件")
                return False

        print_realtime(f"✅ YOLO模型加载成功: {type(model)}")
        if model is not None and hasattr(model, 'names'):
            print_realtime(f"📋 模型类别: {model.names}")
        return True

    except Exception as e:
        print_realtime(f"❌ YOLO模型加载失败: {e}")
        model = None
        return False

def detect_buttons(frame, target_class=None):
    """检测按钮，与legacy版本保持一致"""
    global model

    if model is None:
        print_realtime("❌ 错误：YOLO模型未加载，无法进行检测")
        return False, (None, None, None)

    try:
        frame_for_detection = cv2.resize(frame, (640, 640))
        print_realtime(f"🔍 开始检测目标类别: {target_class}")

        # 使用当前设备进行预测
        results = model.predict(source=frame_for_detection, imgsz=640, conf=0.6, verbose=False)

        # 检查预测结果是否有效
        if results is None or len(results) == 0:
            print_realtime("⚠️ 警告：模型预测结果为空")
            return False, (None, None, None)

        # 检查结果中是否有boxes
        if not hasattr(results[0], 'boxes') or results[0].boxes is None:
            print_realtime("⚠️ 警告：预测结果中没有检测框")
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
        print_realtime(f"按钮检测失败: {e}")
        return False, (None, None, None)


def normalize_script_path(path_input):
    """规范化脚本路径，支持相对路径和绝对路径"""
    try:
        if not path_input:
            return ""

        path_input = path_input.strip()

        # 如果是绝对路径，直接返回
        if os.path.isabs(path_input):
            return path_input

        # 获取testcase目录
        if config_manager:
            try:
                # 假设config_manager有get_testcase_dir或类似方法
                testcase_dir = getattr(config_manager, 'get_testcase_dir', lambda: None)()
                if not testcase_dir:
                    # 从配置文件读取
                    base_dir = getattr(config_manager, 'get_base_dir', lambda: os.path.dirname(os.path.abspath(__file__)))()
                    testcase_dir = os.path.join(base_dir, "testcase")
            except:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                testcase_dir = os.path.join(base_dir, "testcase")
        else:
            # 备用路径
            base_dir = os.path.dirname(os.path.abspath(__file__))
            testcase_dir = os.path.join(base_dir, "testcase")

        # 处理相对路径
        if path_input.startswith(('testcase/', 'testcase\\')):
            # 去掉testcase前缀
            relative_path = path_input[9:]  # 去掉 "testcase/" 或 "testcase\"
            full_path = os.path.join(testcase_dir, relative_path)
        elif os.sep not in path_input and '/' not in path_input:
            # 简单文件名，直接放在testcase目录
            full_path = os.path.join(testcase_dir, path_input)
        else:
            # 其他相对路径，基于当前脚本目录
            script_dir = os.path.dirname(os.path.abspath(__file__))
            full_path = os.path.join(script_dir, path_input)

        return os.path.normpath(full_path)

    except Exception as e:
        print_realtime(f"路径规范化失败: {path_input}, 错误: {e}")
        return path_input


def parse_script_arguments(args_list):
    """解析脚本参数，支持每个脚本独立的loop-count和max-duration配置"""
    scripts = []
    current_script = None
    current_loop_count = 1
    current_max_duration = None

    i = 0
    while i < len(args_list):
        arg = args_list[i]

        if arg == '--script':
            # 保存前一个脚本
            if current_script:
                scripts.append({
                    'path': normalize_script_path(current_script),
                    'loop_count': current_loop_count,
                    'max_duration': current_max_duration
                })

            # 开始新脚本
            if i + 1 < len(args_list):
                current_script = args_list[i + 1]
                i += 1
            else:
                print_realtime("错误: --script 参数后缺少脚本路径")
                break

        elif arg == '--loop-count':
            if i + 1 < len(args_list):
                try:
                    current_loop_count = int(args_list[i + 1])
                    i += 1
                except ValueError:
                    print_realtime(f"错误: 无效的循环次数: {args_list[i + 1]}")
            else:
                print_realtime("错误: --loop-count 参数后缺少数值")

        elif arg == '--max-duration':
            if i + 1 < len(args_list):
                try:
                    current_max_duration = int(args_list[i + 1])
                    i += 1
                except ValueError:
                    print_realtime(f"错误: 无效的最大持续时间: {args_list[i + 1]}")
            else:
                print_realtime("错误: --max-duration 参数后缺少数值")

        i += 1

    # 保存最后一个脚本
    if current_script:
        scripts.append({
            'path': normalize_script_path(current_script),
            'loop_count': current_loop_count,
            'max_duration': current_max_duration
        })

    return scripts


def get_device_screenshot(device):
    """获取设备截图的辅助函数"""
    try:
        screencap = device.shell("screencap -p", encoding=None)
        import io
        from PIL import Image

        # 使用io.BytesIO处理二进制数据
        screenshot_io = io.BytesIO(screencap)
        screenshot = Image.open(screenshot_io)

        return screenshot
    except Exception as e:
        print_realtime(f"获取设备截图失败: {e}")
        return None


def get_device_name(device):
    """获取设备的友好名称"""
    try:
        brand = device.shell("getprop ro.product.brand").strip()
        model = device.shell("getprop ro.product.model").strip()

        # 清理和规范化设备信息
        brand = "".join(c for c in brand if c.isalnum() or c in ('-', '_'))
        model = "".join(c for c in model if c.isalnum() or c in ('-', '_'))

        device_name = f"{brand}-{model}"
        return device_name
    except Exception as e:
        print_realtime(f"获取设备 {device.serial} 信息失败: {e}")
        return "".join(c for c in device.serial if c.isalnum() or c in ('-', '_'))


def setup_log_directory(device_name):
    """设置日志目录"""
    device_dir = "".join(c for c in device_name if c.isalnum() or c in ('-', '_'))
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

    log_dir = os.path.join(DEVICE_REPORTS_DIR, f"{device_dir}_{timestamp}")
    os.makedirs(log_dir, exist_ok=True)

    # 创建log子目录
    log_images_dir = os.path.join(log_dir, "log")
    os.makedirs(log_images_dir, exist_ok=True)

    # 创建空的log.txt文件
    log_file = os.path.join(log_dir, "log.txt")
    if not os.path.exists(log_file):
        with open(log_file, 'w', encoding='utf-8') as f:
            pass

    # 设置Airtest日志目录
    try:
        set_logdir(log_dir)
    except Exception as e:
        print_realtime(f"set_logdir失败: {e}")

    return log_dir


def check_device_status(device, device_name):
    """检查设备状态，确保设备可用且屏幕处于正确状态"""
    try:
        # 基本连接测试
        device.shell("echo test")

        # 检查屏幕状态
        display_state = device.shell("dumpsys power | grep 'mHoldingDisplaySuspendBlocker'")
        if "true" not in display_state.lower():
            print_realtime(f"设备 {device_name} 屏幕未打开，尝试唤醒")
            device.shell("input keyevent 26")  # 电源键唤醒
            time.sleep(1)

        print_realtime(f"设备 {device_name} 状态检查完成")
        return True
    except Exception as e:
        print_realtime(f"设备 {device_name} 状态检查失败: {e}")
        return False


def detection_service(screenshot_queue, click_queue, stop_event):
    """简化的检测服务"""
    print_realtime("🚀 检测服务已启动")
    while not stop_event.is_set():
        try:
            item = screenshot_queue.get(timeout=1)
            if len(item) != 5:
                print_realtime(f"⚠️ 跳过无效数据: {item}")
                continue

            device_name, step_num, frame, target_class, _ = item
            print_realtime(f"📸 设备 {device_name} 步骤 {step_num}: 检测 {target_class}")

            # 这里可以集成AI检测逻辑
            # 目前返回模拟结果
            success = False
            coords = (None, None, None)

            click_queue.put((success, coords))
        except queue.Empty:
            continue
        except Exception as e:
            print_realtime(f"❌ 检测服务错误: {e}")


def clear_log_dir():
    """清理日志目录"""
    if os.path.exists(DEVICE_REPORTS_DIR):
        shutil.rmtree(DEVICE_REPORTS_DIR)
    os.makedirs(DEVICE_REPORTS_DIR, exist_ok=True)


def load_json_data(run_all):
    """加载测试进度数据"""
    base_dir = DEFAULT_BASE_DIR
    if config_manager:
        try:
            # 使用config_manager获取基础目录
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        except:
            base_dir = DEFAULT_BASE_DIR

    json_file = os.path.join(base_dir, 'data.json')

    if not run_all and os.path.isfile(json_file):
        data = json.load(open(json_file))
        data['start'] = time.time()
        return data
    else:
        print_realtime(f"清理日志目录: {DEVICE_REPORTS_DIR}")
        clear_log_dir()
        return {
            'start': time.time(),
            'script': "replay_script",
            'tests': {}
        }


def try_log_screen(device, log_dir, quality=60, max_size=None):
    """
    截取屏幕截图并创建缩略图，用于日志记录

    Args:
        device: 设备对象
        log_dir: 日志目录
        quality: JPEG质量 (1-100)
        max_size: 最大尺寸限制 (width, height)

    Returns:
        dict: 包含screenshot文件名和分辨率信息
    """
    try:
        # 获取设备截图
        screenshot = get_device_screenshot(device)
        if not screenshot:
            return None

        # 转换为OpenCV格式
        frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

        # 应用最大尺寸限制
        if max_size:
            height, width = frame.shape[:2]
            max_width, max_height = max_size
            if width > max_width or height > max_height:
                scale = min(max_width / width, max_height / height)
                new_width = int(width * scale)
                new_height = int(height * scale)
                frame = cv2.resize(frame, (new_width, new_height))

        # 生成时间戳文件名
        timestamp = time.time()
        screenshot_timestamp = int(timestamp * 1000)
        screenshot_filename = f"{screenshot_timestamp}.jpg"
        screenshot_path = os.path.join(log_dir, screenshot_filename)

        # 保存主截图
        cv2.imwrite(screenshot_path, frame, [cv2.IMWRITE_JPEG_QUALITY, quality])

        # 创建缩略图
        thumbnail_filename = f"{screenshot_timestamp}_small.jpg"
        thumbnail_path = os.path.join(log_dir, thumbnail_filename)
        small_frame = cv2.resize(frame, (0, 0), fx=0.3, fy=0.3)
        cv2.imwrite(thumbnail_path, small_frame, [cv2.IMWRITE_JPEG_QUALITY, 60])

        # 获取分辨率
        height, width = frame.shape[:2]
        resolution = [width, height]

        return {
            "screen": screenshot_filename,
            "resolution": resolution
        }

    except Exception as e:
        print_realtime(f"try_log_screen失败: {e}")
        return None


def main():
    """主函数 - 支持README中的完整命令格式"""
    # 加载YOLO模型用于AI检测
    print_realtime("🔄 正在加载YOLO模型...")
    model_loaded = load_yolo_model_for_detection()
    if model_loaded:
        print_realtime("✅ YOLO模型加载成功，AI检测功能可用")
    else:
        print_realtime("⚠️ YOLO模型加载失败，AI检测功能不可用")

    # 使用自定义参数解析以支持复杂的脚本参数格式
    import sys

    # 检查是否有--script参数
    if '--script' not in sys.argv:
        print_realtime("❌ 错误: 必须指定 --script 参数")
        print_realtime("用法示例:")
        print_realtime("  python replay_script.py --script testcase/scene1.json")
        print_realtime("  python replay_script.py --show-screens --script testcase/scene1.json --loop-count 1")
        print_realtime("  python replay_script.py --script testcase/scene1.json --loop-count 1 --script testcase/scene2.json --max-duration 30")
        return

    # 解析脚本参数
    scripts = parse_script_arguments(sys.argv[1:])

    if not scripts:
        print_realtime("❌ 未找到有效的脚本参数")
        return

    # 解析其他参数
    show_screens = '--show-screens' in sys.argv

    print_realtime("🎬 启动精简版回放脚本")
    print_realtime(f"📝 将执行 {len(scripts)} 个脚本:")
    for i, script in enumerate(scripts, 1):
        print_realtime(f"  {i}. {script['path']} (循环:{script['loop_count']}, 最大时长:{script['max_duration']}s)")
    print_realtime(f"🖥️ 显示屏幕: {'是' if show_screens else '否'}")

    # 验证脚本文件存在
    missing_scripts = []
    for script in scripts:
        if not os.path.exists(script['path']):
            missing_scripts.append(script['path'])

    if missing_scripts:
        print_realtime("❌ 以下脚本文件不存在:")
        for path in missing_scripts:
            print_realtime(f"  - {path}")
        return

    # 获取连接的设备
    try:
        devices = adb.device_list()
        if not devices:
            print_realtime("❌ 未找到连接的设备")
            return

        print_realtime(f"📱 找到 {len(devices)} 个设备")

        # 最终检查模型状态
        global model
        if model is not None:
            print_realtime("✅ 模型状态检查通过，AI检测功能可用")
        else:
            print_realtime("⚠️ 模型状态检查失败，将使用备用检测模式")

        # 收集实际处理的设备名称列表，用于生成报告
        processed_device_names = []
        # 收集本次执行创建的设备报告目录路径
        current_execution_device_dirs = []

        # 检查是否启用多设备并发模式
        multi_device_mode = len(devices) > 1
        if multi_device_mode:
            print_realtime(f"🚀 启用多设备并发模式，将并发处理 {len(devices)} 台设备")

            # 使用独立的多设备并发回放器
            try:
                from multi_device_replayer import replay_scripts_on_devices

                # 提取设备序列号
                device_serials = [device.serial for device in devices]

                # 执行多设备并发回放
                results = replay_scripts_on_devices(device_serials, scripts, max_workers=4)

                # 收集结果
                for device_serial, result in results.items():
                    if result.get('success'):
                        processed_device_names.append(device_serial)
                        # 注意：简化版本不生成报告目录

                print_realtime(f"✅ 多设备并发回放完成，成功处理 {len([r for r in results.values() if r.get('success')])} 台设备")

            except ImportError as e:
                print_realtime(f"❌ 无法导入多设备回放器: {e}")
                print_realtime("⚠️ 回退到单设备模式")
                multi_device_mode = False

        # 如果多设备模式被禁用，回退到单设备模式
        if not multi_device_mode:
            # 单设备模式，保持原有逻辑
            print_realtime("📱 单设备模式，顺序执行")

            # 为每个设备执行回放
            for device in devices:
                device_name = get_device_name(device)

                print_realtime(f"🔧 设备 {device_name} 开始处理")

                # 检查设备状态
                if not check_device_status(device, device_name):
                    print_realtime(f"❌ 设备 {device_name} 状态检查失败，跳过")
                    continue

                # 记录成功处理的设备名称（提取基础名称，不包含时间戳）
                base_device_name = device_name.split('_')[0] if '_' in device_name else device_name
                processed_device_names.append(base_device_name)

                # 创建必要的队列和事件
                screenshot_queue = queue.Queue()
                action_queue = queue.Queue()
                click_queue = queue.Queue()
                stop_event = Event()

                # 启动检测服务
                detection_thread = Thread(
                    target=detection_service,
                    args=(screenshot_queue, click_queue, stop_event)
                )
                detection_thread.daemon = True
                detection_thread.start()

                # 使用 DeviceScriptReplayer 执行脚本回放（单设备模式的简化版本）
                try:
                    if DeviceScriptReplayer is None:
                        print_realtime(f"❌ 设备 {device_name} DeviceScriptReplayer 不可用")
                        continue

                    replayer = DeviceScriptReplayer(device.serial)

                    # 执行每个脚本
                    has_execution = False
                    for script_config in scripts:
                        script_path = script_config["path"]
                        script_loop_count = script_config.get("loop_count", 1)

                        print_realtime(f"📄 设备 {device_name} 开始执行脚本: {os.path.basename(script_path)}")

                        # 循环执行脚本
                        for loop in range(script_loop_count):
                            if script_loop_count > 1:
                                print_realtime(f"🔄 设备 {device_name} 第 {loop+1}/{script_loop_count} 次循环")

                            result = replayer.replay_single_script(script_path)
                            if result:
                                has_execution = True
                                print_realtime(f"✅ 设备 {device_name} 脚本执行成功")
                            else:
                                print_realtime(f"❌ 设备 {device_name} 脚本执行失败")

                            time.sleep(1.0)  # 循环间短暂等待

                    if has_execution:
                        print_realtime(f"✅ 设备 {device_name} 回放成功完成")
                    else:
                        print_realtime(f"⚠️ 设备 {device_name} 未执行任何操作")

                except Exception as e:
                    print_realtime(f"❌ 设备 {device_name} 回放失败: {e}")
                    traceback.print_exc()
                finally:
                    stop_event.set()

        print_realtime(f"🎉 所有设备处理完成，成功处理 {len(processed_device_names)} 台设备")

    except Exception as e:
        print_realtime(f"❌ 设备处理失败: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
