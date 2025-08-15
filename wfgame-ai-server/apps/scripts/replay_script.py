# -*- coding: utf-8 -*-
"""
重构后的 replay_script.py - 精简版本
负责核心流程控制，具体的action处理委托给ActionProcessor
"""

# 🔧 新增：禁用第三方库DEBUG日志
import logging

logging.getLogger('airtest').setLevel(logging.WARNING)
logging.getLogger('airtest.core.android.adb').setLevel(logging.WARNING)
logging.getLogger('adbutils').setLevel(logging.WARNING)
from django.conf import settings


# 新增：FileLogger类和SafeOutputWrapper类用于处理二进制内容
class FileLogger:
    """安全的文件日志记录器，专门处理二进制和文本混合内容"""
    def __init__(self, log_dir, device_serial=None):
        self.log_file = os.path.join(log_dir, f"{device_serial or 'master'}.log")
        self.device_serial = device_serial
        # 确保日志目录存在
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

    def log(self, msg):
        """安全记录日志，处理二进制和文本混合内容"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

        # 处理不同类型的输入
        if isinstance(msg, bytes):
            # 处理纯二进制数据
            try:
                msg_str = msg.decode('utf-8', errors='replace')
            except Exception:
                msg_str = f"[二进制数据: {len(msg)} bytes]"
        elif isinstance(msg, str):
            # 处理字符串，但可能包含无法显示的字符
            msg_str = msg
        else:
            # 处理其他类型
            msg_str = str(msg)

        # 清理无法显示的字符
        msg_str = msg_str.replace('\ufffd', '[无法解码字符]')

        # 限制单行日志长度，防止过长的二进制内容
        if len(msg_str) > 1000:
            msg_str = msg_str[:1000] + f"...[截断,原长度:{len(msg_str)}]"

        try:
            with open(self.log_file, 'a', encoding='utf-8', errors='replace') as f:
                f.write(f"[{timestamp}] {msg_str}\n")
                f.flush()  # 确保实时写入
        except Exception as e:
            # 如果写入失败，尝试写入到标准错误输出
            try:
                sys.stderr.write(f"日志写入失败 {self.device_serial}: {e}\n")
            except:
                pass  # 静默失败，避免程序崩溃

    def log_binary_safe(self, data, description="数据"):
        """专门用于记录可能包含二进制的数据"""
        if isinstance(data, bytes):
            # 尝试解码，失败则记录为二进制
            try:
                decoded = data.decode('utf-8', errors='ignore')
                if decoded.strip():
                    self.log(f"{description}: {decoded}")
                else:
                    self.log(f"{description}: [二进制数据 {len(data)} bytes]")
            except:
                self.log(f"{description}: [二进制数据 {len(data)} bytes]")
        else:
            self.log(f"{description}: {data}")


class SafeOutputWrapper:
    """安全的输出包装器，重定向stdout/stderr到文件日志"""
    def __init__(self, file_logger, stream_type="stdout"):
        self.file_logger = file_logger
        self.stream_type = stream_type
        self.original_stream = sys.stdout if stream_type == "stdout" else sys.stderr

    def write(self, data):
        """写入数据到文件日志"""
        if data and data.strip():
            self.file_logger.log_binary_safe(data, self.stream_type)
        # 也输出到原始流（如果需要）
        try:
            self.original_stream.write(data)
            self.original_stream.flush()
        except:
            pass

    def flush(self):
        """刷新缓冲区"""
        try:
            self.original_stream.flush()
        except:
            pass


def write_result(log_dir, device_serial, result_data):
    """
    原子写入结果文件，确保数据完整性
    支持完整的状态分离记录：脚本执行状态、业务结果状态、报告生成状态
    """
    # 验证 result_data 格式
    if not isinstance(result_data, dict):
        result_data = {
            "error": "无效的结果数据格式",
            "exit_code": -1,
            "report_url": "",
            "execution_completed": False,
            "script_execution_success": False,
            "business_result_success": False,
            "report_generation_success": False
        }

    # 确保必要字段存在 - 按照新的状态分离格式
    required_fields = {
        "exit_code": -1,
        "report_url": "",
        "execution_completed": False,
        "script_execution_success": False,
        "business_result_success": False,
        "report_generation_success": False,
        "device": device_serial,
        "timestamp": time.time(),
        "message": "未知状态",
        "error_details": {"business_errors": [], "report_errors": []}
    }

    for field, default_value in required_fields.items():
        if field not in result_data:
            result_data[field] = default_value

    # Convert Path objects to strings for JSON serialization
    for key, value in result_data.items():
        if hasattr(value, '__fspath__'):  # Path-like object
            result_data[key] = str(value)
        elif isinstance(value, (type(Path()), Path)):  # Direct Path check
            result_data[key] = str(value)

    result_file = os.path.join(log_dir, f"{device_serial}.result.json")

    # 使用原子写入：先写临时文件，再重命名
    temp_file = f"{result_file}.tmp"
    try:
        # 预检 JSON 格式
        json_content = json.dumps(result_data, ensure_ascii=False, indent=4)

        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(json_content)
            f.flush()  # 确保写入磁盘
            os.fsync(f.fileno())  # 强制同步到磁盘

        # 原子重命名
        if os.path.exists(result_file):
            backup_file = f"{result_file}.backup"
            os.rename(result_file, backup_file)
        os.rename(temp_file, result_file)
    except Exception as e:
        # 清理临时文件
        if os.path.exists(temp_file):
            os.remove(temp_file)
        # 写入异常处理的结果
        fallback_data = {
            "exit_code": -1,
            "error": f"结果写入失败: {str(e)}",
            "report_url": ""
        }
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(fallback_data, f, ensure_ascii=False, indent=4)


from airtest.core.api import set_logdir, auto_setup
from airtest.core.settings import Settings as ST
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
import shutil
import io
import re
import glob
from adbutils import adb
import traceback
from datetime import datetime
import random
from pathlib import Path
import configparser

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
try:
    REPORTS_STATIC_DIR = str(REPORT_MANAGER.report_static_url)
    DEVICE_REPORTS_DIR = str(REPORT_MANAGER.device_replay_reports_dir)
    SUMMARY_REPORTS_DIR = str(REPORT_MANAGER.summary_reports_dir)
except Exception as e:
    print_realtime(f"⚠️ 无法获取统一报告管理系统配置 {e}")


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


def load_yolo_model_for_detection():
    """只从config.ini的[paths]段读取model_path加载YOLO模型，未找到直接抛异常。禁止使用绝对路径。"""
    global model
    if YOLO is None:
        print_realtime("❌ 无法加载YOLO模型：ultralytics未正确导入")
        raise RuntimeError("YOLO未正确导入")
    try:
        # 获取项目根目录并定位 config.ini
        from pathlib import Path
        project_root = Path(__file__).resolve().parents[3]
        config_path = project_root / 'config.ini'
        if not config_path.exists():
            raise FileNotFoundError(f"未找到配置文件: {config_path}")
        # 读取配置，必须用ExtendedInterpolation保证变量递归替换
        config = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
        config.read(str(config_path), encoding='utf-8')
        if 'paths' not in config or 'model_path' not in config['paths']:
            raise KeyError("config.ini的[paths]段未配置model_path")
        # 递归变量替换
        def resolve_var(val, section):
            import re
            pattern = re.compile(r'\$\{([^}]+)\}')
            while True:
                match = pattern.search(val)
                if not match:
                    break
                var = match.group(1)
                rep = config[section].get(var) or config['paths'].get(var) or ''
                val = val.replace(f'${{{var}}}', rep)
            return val
        # raw_path = resolve_var(config['paths']['model_path'], 'paths')
        # 修正为递归变量替换后，直接用configparser的get方法，自动展开变量
        raw_path = config.get('paths', 'model_path')
        # 构造模型文件绝对路径
        model_file = Path(raw_path)
        if not model_file.is_absolute():
            model_file = project_root / model_file
        if not model_file.exists():
            raise FileNotFoundError(f"[paths]段model_path指定的模型文件不存在: {model_file}")
        print_realtime(f"🔄 加载模型文件: {model_file}")
        model = YOLO(str(model_file))
        print_realtime(f"✅ YOLO模型加载成功: {type(model)}")
        if model is not None and hasattr(model, 'names'):
            print_realtime(f"📋 模型类别(过长，未打印)...")
        return True
    except Exception as e:
        print_realtime(f"❌ YOLO模型加载失败: {e}")
        model = None
        raise

def detect_buttons(frame, target_class=None, conf_threshold=None):
    """
    检测按钮，使用YOLO模型进行推理。
    坐标逆变换、类别匹配、置信度阈值等均支持灵活配置。
    - frame: 输入的原始图像（numpy数组）
    - target_class: 目标类别名（如'button'）
    - conf_threshold: 置信度阈值（可选，优先级高于配置文件）
    返回: (success, (x, y, detected_class))
    """
    global model

    if model is None:
        print_realtime("❌ 错误：YOLO模型未加载，无法进行检测")
        return False, (None, None, None)

    try:
        print_realtime(f"🔍 开始检测目标类别: {target_class}")
        import tempfile
        import os

        # 优先使用传入参数，否则从config读取
        if conf_threshold is None:
            conf_threshold = get_confidence_threshold_from_config()

        # 将frame保存为临时图片，供YOLO模型推理
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            temp_path = temp_file.name
            cv2.imwrite(temp_path, frame)

        try:
            # 选择推理设备
            device = "cuda" if hasattr(model, 'device') and 'cuda' in str(model.device) else "cpu"
            # 执行YOLO推理，传入图片路径和相关参数
            results = model.predict(
                source=temp_path,      # 输入图片路径，YOLO要求文件路径而非numpy数组
                device=device,         # 推理设备，'cuda'表示GPU，'cpu'表示CPU
                imgsz=640,             # 推理时图片缩放到的尺寸（YOLO常用640x640）
                conf=conf_threshold,   # 置信度阈值，低于该值的目标会被过滤
                iou=0.6,               # NMS（非极大值抑制）IoU阈值，控制重叠框的合并
                half=True if device == "cuda" else False,  # 是否使用半精度加速，仅GPU可用
                max_det=300,           # 最大检测目标数，防止极端场景下过多框
                verbose=False          # 是否输出详细推理日志
            )

            # 检查预测结果是否有效
            if results is None or len(results) == 0:
                # 如果模型推理结果为空，直接返回失败
                print_realtime("⚠️ 警告：模型预测结果为空")
                return False, (None, None, None)

            # 检查结果中是否有boxes属性且不为None
            if not hasattr(results[0], 'boxes') or results[0].boxes is None:
                # 如果没有检测框，返回失败
                print_realtime("⚠️ 警告：预测结果中没有检测框")
                return False, (None, None, None)

            # 获取原始图片的高和宽，用于坐标逆变换
            orig_h, orig_w = frame.shape[:2]
            print_realtime(f"📏 原始图片尺寸: {orig_w}x{orig_h}")


            # 遍历所有检测到的目标框
            for box in results[0].boxes:
                # print_realtime(f"🔍 检测到目标框: {box.xyxy[0].tolist()}, 置信度: {box.conf.item():.3f}, 类别ID: {int(box.cls.item())}")
                cls_id = int(box.cls.item())  # 获取类别ID
                # 检查模型是否有类别名映射
                if hasattr(model, 'names') and model.names is not None:
                    detected_class = model.names[cls_id]  # 获取类别名
                else:
                    detected_class = f"class_{cls_id}"
                # 判断检测到的类别是否为目标类别
                if detected_class == target_class:
                    # 取检测框的左上和右下坐标，计算中心点坐标
                    box_coords = box.xyxy[0].tolist()  # [x1, y1, x2, y2]
                    # print_realtime(f"🔍 检测到目标类别: {detected_class}, 坐标: {box_coords}")
                    x = (box_coords[0] + box_coords[2]) / 2  # 中心点x
                    y = (box_coords[1] + box_coords[3]) / 2  # 中心点y
                    # print_realtime(f"🔍 计算得到中心点坐标: ({x:.2f}, {y:.2f})")

                    # 打印检测到目标的日志，包括类别和置信度
                    print_realtime(f"✅ 找到目标类别 {target_class}，中心坐标: ({x:.2f}, {y:.2f})，置信度: {box.conf.item():.3f}")
                    # 返回检测成功和中心点坐标、类别名
                    return True, (x, y, detected_class)

            # 如果没有找到目标类别，返回失败
            print_realtime(f"❌ 未找到目标类别: {target_class} ❌")
            return False, (None, None, None)

        finally:
            # 清理临时文件
            try:
                os.unlink(temp_path)
            except:
                pass

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
    """解析脚本参数，支持每个脚本独立的loop-count和max-duration配置，以及多设备并发参数"""
    scripts = []
    current_script = None
    current_loop_count = 1
    current_max_duration = None

    # 新增：多设备并发回放参数
    log_dir = None
    device_serial = None
    account_user = None
    account_pass = None
    i = 0
    while i < len(args_list):
        arg = args_list[i]

        if arg == '--script':
            # 保存前一个脚本
            if current_script:
                normalized_path = normalize_script_path(current_script)
                print_realtime(f"🔧 保存脚本: {current_script} -> {normalized_path}")
                scripts.append({
                    'path': normalized_path,
                    'loop_count': current_loop_count,
                    'max_duration': current_max_duration
                })

            # 开始新脚本
            if i + 1 < len(args_list):
                current_script = args_list[i + 1]
                print_realtime(f"🔧 发现新脚本: {current_script}")
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

        # 新增：多设备并发回放参数
        elif arg == '--log-dir':
            if i + 1 < len(args_list):
                log_dir = args_list[i + 1]
                i += 1
            else:
                print_realtime("错误: --log-dir 参数后缺少目录路径")

        elif arg == '--device':
            if i + 1 < len(args_list):
                device_serial = args_list[i + 1]
                i += 1
            else:
                print_realtime("错误: --device 参数后缺少设备序列号")

        elif arg == '--account':
            if i + 1 < len(args_list):
                account = args_list[i + 1]
                i += 1
            else:
                print_realtime("错误: --account 参数后缺少用户名")

        elif arg == '--password':
            if i + 1 < len(args_list):
                password = args_list[i + 1]
                i += 1
            else:
                print_realtime("错误: --password 参数后缺少密码")

        i += 1

    # 保存最后一个脚本
    if current_script:
        scripts.append({
            'path': normalize_script_path(current_script),
            'loop_count': current_loop_count,
            'max_duration': current_max_duration
        })

    # 返回解析结果，包括新的多设备参数
    return scripts, {
        'log_dir': log_dir,
        'device_serial': device_serial,
        'account': account,
        'password': password
    }

    return scripts


def get_device_screenshot(device):
    """获取设备截图的辅助函数 - 增强版"""

    # 🔧 修复1: 多种截图方法，确保成功率
    methods = [
        ("subprocess_screencap", lambda: _screenshot_method_subprocess(device)),
        ("airtest_snapshot", lambda: _screenshot_method_airtest(device)),
        ("mock_screenshot", lambda: _screenshot_method_mock(device)),
        # ("adb_shell_screencap", lambda: _screenshot_method_adb_shell(device)) # 此方法会报错

    ]

    for method_name, method_func in methods:
        try:
            print_realtime(f"🔍 尝试截图方法: {method_name}")
            screenshot = method_func()
            if screenshot is not None:
                print_realtime(f"✅ 截图成功: {method_name}")
                return screenshot
        except Exception as e:
            print_realtime(f"⚠️ 截图方法 {method_name} 失败: {e}")
            continue

    print_realtime("❌ 所有截图方法都失败，返回None")
    return None

def _screenshot_method_adb_shell(device):
    """方法1: 使用device.shell"""
    screencap = device.shell("screencap -p", encoding=None)

    if not screencap or len(screencap) < 100:
        raise Exception("截图数据为空或过小")

    import io
    from PIL import Image

    # 处理可能的CRLF问题
    if b'\r\n' in screencap:
        screencap = screencap.replace(b'\r\n', b'\n')

    screenshot_io = io.BytesIO(screencap)
    screenshot_io.seek(0)

    # 验证是否为PNG格式
    magic = screenshot_io.read(8)
    screenshot_io.seek(0)

    if not magic.startswith(b'\x89PNG'):
        raise Exception("不是有效的PNG格式")

    screenshot = Image.open(screenshot_io)
    screenshot.load()  # 强制加载图像数据
    return screenshot

def _screenshot_method_subprocess(device):
    """方法2: 使用subprocess"""
    import subprocess
    import io
    from PIL import Image

    result = subprocess.run(
        f"adb -s {device.serial} exec-out screencap -p",
        shell=True,
        capture_output=True,
        timeout=10
    )

    if result.returncode != 0 or not result.stdout:
        raise Exception(f"subprocess命令失败: {result.stderr}")

    return Image.open(io.BytesIO(result.stdout))

def _screenshot_method_airtest(device):
    """方法3: 使用airtest"""
    try:
        from airtest.core.api import connect_device
        airtest_device = connect_device(f"Android:///{device.serial}")
        screenshot = airtest_device.snapshot()
        if screenshot is None:
            raise Exception("airtest返回None")
        return screenshot
    except ImportError:
        raise Exception("airtest未安装")

def _screenshot_method_mock(device):
    """方法4: 创建Mock截图用于测试"""
    try:
        from PIL import Image
        import numpy as np

        # 创建一个简单的测试图像 (1080x2400像素)
        width, height = 1080, 2400

        # 创建渐变背景
        image_array = np.zeros((height, width, 3), dtype=np.uint8)

        # 添加渐变效果
        for y in range(height):
            color_value = int((y / height) * 255)
            image_array[y, :] = [color_value, 50, 100]

        # 添加一些几何图形模拟UI元素
        # 顶部状态栏
        image_array[0:100, :] = [30, 30, 30]

        # 中间按钮区域
        image_array[800:1000, 300:780] = [0, 150, 255]  # 蓝色按钮
        image_array[1200:1400, 300:780] = [255, 100, 0]  # 橙色按钮

        # 底部导航栏
        image_array[2200:2400, :] = [50, 50, 50]

        mock_image = Image.fromarray(image_array, 'RGB')
        print_realtime("🎭 使用Mock截图进行测试")
        return mock_image

    except Exception as e:
        raise Exception(f"Mock截图创建失败: {e}")


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

    # 🔧 修复：不创建log子目录，直接在设备目录下存储所有文件
    # 根据文档要求，截图和log.txt应该直接存放在设备目录下

    # 创建空的log.txt文件
    log_file = os.path.join(log_dir, "log.txt")
    if not os.path.exists(log_file):
        with open(log_file, 'w', encoding='utf-8') as f:
            pass    # 设置Airtest日志目录
    try:
        set_logdir(log_dir)
    except Exception as e:
        print_realtime(f"set_logdir失败: {e}")

    return log_dir


def check_device_status(device, device_name):
    """检查设备状态，确保设备可用且屏幕处于正确状态"""
    try:
        # 基本连接测试
        device.shell("echo test")        # 检查屏幕状态
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


def process_priority_based_script(device, steps, meta, device_report_dir, action_processor,
                        screenshot_queue, click_queue, max_duration=None):
    """处理基于优先级的动态脚本 - 修复后版本"""
    print_realtime("🎯 开始执行优先级模式脚本")

    # 按优先级排序
    steps.sort(key=lambda s: s.get("Priority", 999))

    priority_start_time = time.time()
    cycle_count = 0  # 真正的循环次数计数
    detection_count = 0

    # 按优先级正确分类步骤
    ai_detection_steps = sorted([s for s in steps if s.get('action') == 'ai_detection_click'],
                               key=lambda x: x.get('Priority', 999))
    swipe_steps = sorted([s for s in steps if s.get('action') == 'swipe'],
                        key=lambda x: x.get('Priority', 999))
    fallback_steps = sorted([s for s in steps if s.get('action') == 'fallback_click'],
                           key=lambda x: x.get('Priority', 999))

    print_realtime(f"📋 步骤分类: AI检测={len(ai_detection_steps)}, 滑动={len(swipe_steps)}, 备选点击={len(fallback_steps)}")

    # 读取停滞控制参数
    stagnation_threshold = meta.get('stagnation_threshold')
    stagnation_tolerance = meta.get('stagnation_tolerance', 0.05)  # 默认0.05
    prev_screenshot = None
    stagnation_counter = 0

    while max_duration is None or (time.time() - priority_start_time) <= max_duration:
        cycle_count += 1
        print_realtime(f"🔄 第 {cycle_count} 轮检测循环开始")

        # 获取本轮通用截图用于AI检测和停滞检测
        try:
            base_screenshot = get_device_screenshot(device)
        except Exception:
            base_screenshot = None

        # ------------------ 界面停滞检测 ------------------
        current_screenshot = base_screenshot

        # 比较截图相似度，更新停滞计数器
        if prev_screenshot is not None and current_screenshot is not None and stagnation_threshold:
            gray_prev = cv2.cvtColor(np.array(prev_screenshot), cv2.COLOR_RGB2GRAY)
            gray_curr = cv2.cvtColor(np.array(current_screenshot), cv2.COLOR_RGB2GRAY)
            diff = cv2.absdiff(gray_prev, gray_curr)
            non_zero = np.count_nonzero(diff > 0)
            total_pixels = diff.size
            similarity = 1 - non_zero / total_pixels
            if similarity >= stagnation_tolerance:
                stagnation_counter += 1
            else:
                stagnation_counter = 0
        else:
            stagnation_counter = 0
        prev_screenshot = current_screenshot

        # 达到停滞阈值，执行特殊操作阶段
        if stagnation_threshold and stagnation_counter >= stagnation_threshold:
            special_steps = sorted([s for s in steps if s.get('marker')=='special'], key=lambda x: x.get('Priority', 999))
            base_screenshot = current_screenshot
            for step in special_steps:
                print_realtime(f"🚧 Stagnation 特殊操作: {step.get('action')} P{step.get('Priority')} - {step.get('remark')}")
                if step.get('action') == 'swipe':
                    result = action_processor._handle_swipe_priority_mode(step, cycle_count, device_report_dir)
                elif step.get('action') == 'fallback_click':
                    result = action_processor._handle_fallback_click_priority_mode(step, cycle_count, device_report_dir)
                else:
                    continue
                # 执行后检测界面变化
                try:
                    new_screenshot = get_device_screenshot(device)
                except Exception:
                    new_screenshot = None
                if base_screenshot is not None and new_screenshot is not None:
                    gray_base = cv2.cvtColor(np.array(base_screenshot), cv2.COLOR_RGB2GRAY)
                    gray_new = cv2.cvtColor(np.array(new_screenshot), cv2.COLOR_RGB2GRAY)
                    diff2 = cv2.absdiff(gray_base, gray_new)
                    non_zero2 = np.count_nonzero(diff2 > 0)
                    similarity2 = 1 - non_zero2 / diff2.size
                    if similarity2 < stagnation_tolerance:
                        print_realtime("🔄 界面已变化，重置停滞计数，重新进入常规循环")
                        stagnation_counter = 0
                        prev_screenshot = new_screenshot
                        matched_any_target = False
                        break
            continue  # 跳过本轮常规检测，进入下一轮

        # ------------------ Phase 1: AI 检测 ------------------
        print_realtime("🎯 [阶段1] 执行AI检测步骤")
        for step_idx, step in enumerate(ai_detection_steps):
            # 将截图转换并缓存
            if base_screenshot is None:
                screenshot = get_device_screenshot(device)
            else:
                screenshot = base_screenshot
            frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

            step_class = step.get('yolo_class')
            priority = step.get('Priority', 999)
            print_realtime(f"  [Replay] 尝试AI检测 P{priority}: {step_class}")
            try:
                # 使用批量检测或一次性调用detect_buttons
                success, detection_result = action_processor.detect_buttons(frame, target_class=step_class)
                detection_count += 1
                if success and detection_result[0] is not None:
                    # 命中，执行点击和日志记录
                    result = action_processor._handle_ai_detection_click_priority_mode(step, cycle_count, device_report_dir)
                    if result.success and result.executed:
                        matched_any_target = True
                        hit_step = step
                        print_realtime(f"  ✅ [Replay] AI检测命中:>>>>>>>>>>【 {step_class} 】<<<<<<<<<<")
                        time.sleep(1.0)
                        break
                else:
                    print_realtime(f"  ❌ [Replay] AI检测未命中: {step_class}")
            except Exception as e:
                print_realtime(f"  ❌ [Replay] AI检测异常: {e}")
                detection_count += 1

        # 如果AI检测有命中，记录日志并继续下一轮
        if matched_any_target and hit_step:
            continue

        # 第2阶段：如果AI全部未命中，尝试滑动操作
        print_realtime("🔄 [阶段2] 执行滑动操作")
        for step in swipe_steps:
            step_class = step.get('yolo_class')
            step_remark = step.get('remark', '')
            priority = step.get('Priority', 999)
            print_realtime(f"  尝试滑动 P{priority}: {step_class}")
            try:
                # 对于滑动，直接执行并记录
                result = action_processor._handle_swipe_priority_mode(step, cycle_count, device_report_dir)
                if result.success and result.executed:
                    matched_any_target = True
                    hit_step = step
                    print_realtime(f"  ✅ 滑动完成: {step_class}")
                    time.sleep(1.0)
                    break
                else:
                    print_realtime(f"  ❌ 滑动未执行: {step_class}")
            except Exception as e:
                print_realtime(f"  ❌ 滑动异常: {e}")

        # 如果滑动有执行，继续下一轮
        if matched_any_target and hit_step:
            continue

        # 第3阶段：如果滑动也未执行，尝试备选点击
        print_realtime("🔄 [阶段3] 执行备选点击")
        for step in fallback_steps:
            step_class = step.get('yolo_class')
            priority = step.get('Priority', 999)
            print_realtime(f"  尝试备选点击 P{priority}: {step_class}")
            try:
                # 对于备选点击，直接执行并记录
                result = action_processor._handle_fallback_click_priority_mode(step, cycle_count, device_report_dir)
                if result.success and result.executed:
                    matched_any_target = True
                    hit_step = step
                    print_realtime(f"  ✅ 备选点击成功: {step_class}")
                    time.sleep(1.0)
                    break
                else:
                    print_realtime(f"  ❌ 备选点击未成功: {step_class}")
            except Exception as e:
                print_realtime(f"  ❌ 备选点击异常: {e}")

        # 检查超时条件
        if time.time() - priority_start_time > 30 and cycle_count == 0:
            print_realtime("⏰ 连续30秒未检测到任何操作，停止优先级模式")
            break        # 如果这一轮完全没有任何操作成功，等待后继续下一轮
        if not matched_any_target:
            print_realtime("⚠️ 本轮所有操作都未成功，等待0.5秒后继续下一轮")

        time.sleep(0.5)

    print_realtime(f"优先级模式执行完成，共执行 {cycle_count} 个循环")
    return cycle_count > 0


def process_sequential_script(device, steps, device_report_dir, action_processor, max_duration=None):
    """处理顺序执行脚本"""
    print_realtime("📝 开始按顺序执行脚本")

    script_start_time = time.time()
    has_executed_steps = False

    for step_idx, step in enumerate(steps):        # 检查是否超过最大执行时间
        if max_duration is not None and (time.time() - script_start_time) > max_duration:
            print_realtime(f"脚本已达到最大执行时间 {max_duration}秒，停止执行")
            break
        step_class = step.get("class", "")
        step_action = step.get("action", "click")
        step_remark = step.get("remark", "")

        display_name = step_class if step_class else step_action
        # 增强的步骤执行日志
        step_start_time = time.time()
        print_realtime(f"🚀 [步骤 {step_idx+1}/{len(steps)}] 步骤开始执行: {display_name}")
        print_realtime(f"   └─ 动作类型: {step_action}")
        print_realtime(f"   └─ 目标类别: {step_class}")
        print_realtime(f"   └─ 备注说明: {step_remark}")
        print_realtime(f"   └─ 开始时间: {time.strftime('%H:%M:%S', time.localtime(step_start_time))}")

        # 使用ActionProcessor处理步骤
        try:
            result = action_processor.process_action(step, step_idx, device_report_dir)

            # 处理新的ActionResult格式
            if hasattr(result, 'success'):
                # 新的ActionResult对象
                success = result.success
                has_executed = result.executed
                should_continue = result.should_continue
                step_message = result.message
            else:
                # 兼容旧的元组格式
                if len(result) == 3:
                    success, has_executed, should_continue = result
                    step_message = "步骤执行完成"
                else:
                    success, has_executed, should_continue = False, False, False
                    step_message = "未知结果格式"

            step_end_time = time.time()
            step_duration = step_end_time - step_start_time

            if success and has_executed:
                has_executed_steps = True
                print_realtime(f"✅ [步骤 {step_idx+1}] 步骤执行完成 - 成功 (耗时: {step_duration:.2f}s)")
                print_realtime(f"   └─ 结果: {step_message}")
            else:
                print_realtime(f"❌ [步骤 {step_idx+1}] 步骤执行完成 - 失败 (耗时: {step_duration:.2f}s)")
                print_realtime(f"   └─ 原因: {step_message}")

            # 检查是否需要停止
            if not should_continue:
                print_realtime(f"⏹️ [步骤 {step_idx+1}] 要求停止执行")
                break

        except Exception as e:
            step_end_time = time.time()
            step_duration = step_end_time - step_start_time
            print_realtime(f"❌ [步骤 {step_idx+1}] 执行异常 (耗时: {step_duration:.2f}s): {e}")
            print_realtime(f"   └─ 异常详情: {str(e)[:100]}...")
            traceback.print_exc()# 短暂暂停让UI响应
        time.sleep(0.5)

    print_realtime(f"顺序执行完成，共处理 {len(steps)} 个步骤")
    return has_executed_steps


def replay_device(device, scripts, screenshot_queue, action_queue, click_queue, stop_event,
                 device_name, log_dir, loop_count=1, cmd_account=None, cmd_password=None):
    """
    重构后的设备回放函数
    主要负责流程控制，具体的action处理委托给ActionProcessor
    """
    print_realtime(f"🚀 开始回放设备: {device_name}, 脚本数量: {len(scripts)}")

    # 检查脚本列表
    if not scripts:
        raise ValueError("脚本列表为空，无法回放")    # 🔧 关键修复：分离方案3日志目录和报告系统目录
    # log_dir: 方案3传入的共享工作目录，用于任务管理（.result.json, .log）
    # device_report_dir: 报告系统的独立设备目录，用于HTML报告和截图

    device_report_dir = None
    if REPORT_MANAGER:
        try:
            device_report_dir = REPORT_MANAGER.create_device_report_dir(device_name)
            print_realtime(f"✅ 报告系统目录创建成功: {device_report_dir}")
        except Exception as e:
            print_realtime(f"⚠️ 报告系统目录创建失败: {e}")
            device_report_dir = None

    # 如果报告系统失败，使用fallback目录结构
    if not device_report_dir:
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        fallback_dir = os.path.join(DEVICE_REPORTS_DIR, f"{device_name}_{timestamp}")
        os.makedirs(fallback_dir, exist_ok=True)
        device_report_dir = Path(fallback_dir)
        print_realtime(f"⚠️ 使用fallback报告目录: {device_report_dir}")

    print_realtime(f"📁 方案3日志目录: {log_dir}")
    print_realtime(f"📁 报告系统目录: {device_report_dir}")    # 设置Airtest日志目录为报告系统目录
    try:
        set_logdir(str(device_report_dir))
        print_realtime(f"✅ 设置Airtest日志目录: {device_report_dir}")
    except Exception as e:
        print_realtime(f"⚠️ 设置Airtest日志目录失败: {e}")

    # 创建报告系统的log.txt文件（用于HTML报告生成）
    log_txt_path = os.path.join(str(device_report_dir), "log.txt")
    with open(log_txt_path, "w", encoding="utf-8") as f:
        f.write("")

    # 分配账号给设备 - 优先使用命令行参数中的账号
    device_account = None

    # 1. 首先尝试使用命令行参数中的账号
    if cmd_account and cmd_password:
        device_account = (cmd_account, cmd_password)
        print_realtime(f"✅ 使用命令行参数中的账号: {cmd_account}")

    # 2. 如果没有命令行参数，尝试从预分配文件中读取
    if not device_account:
        try:
            # 尝试从主进程预分配的账号文件中读取
            accounts_file = os.path.join(log_dir, "device_accounts.json")
            if os.path.exists(accounts_file):
                try:
                    with open(accounts_file, 'r', encoding='utf-8') as f:
                        device_accounts = json.load(f)
                        if device.serial in device_accounts:
                            username, password = device_accounts[device.serial]
                            device_account = (username, password)
                            print_realtime(f"✅ 从预分配文件中获取设备 {device_name} 的账号: {username}")
                except Exception as e:
                    print_realtime(f"❌ 读取账号预分配文件失败: {e}")

            # 3. 如果前两种方式都失败，尝试直接分配（备用方案）
            if not device_account:
                account_manager = get_account_manager()
                device_account = account_manager.allocate_account(device.serial)
                if device_account:
                    username, password = device_account
                    print_realtime(f"✅ 为设备 {device_name} 分配账号: {username} (备用方案)")
                else:
                    print_realtime(f"⚠️ 设备 {device_name} 账号分配失败")
        except Exception as e:
            print_realtime(f"❌ 账号分配过程中出错: {e}")

    global model
    if model is None:
        print_realtime("⚠️ 检测到模型未加载，尝试重新加载...")
        load_yolo_model_for_detection()

    # 检查检测函数是否可用
    if model is not None:
        print_realtime("✅ YOLO模型可用，AI检测功能启用")
        detect_func = detect_buttons
    else:
        print_realtime("❌ YOLO模型不可用，AI检测功能禁用")
        detect_func = lambda frame, target_class=None: (False, (None, None, None))    # 初始化ActionProcessor
    action_processor = ActionProcessor(device, device_name=device_name, log_txt_path=log_txt_path, detect_buttons_func=detect_func)# 设置设备账号
    if device_account:
        action_processor.set_device_account(device_account)

    # 记录测试开始
    start_time = time.time()
    start_entry = {
        "tag": "function",
        "depth": 1,
        "time": start_time,
        "data": {
            "name": "开始测试",
            "call_args": {"device": device_name, "scripts": [s['path'] for s in scripts]},
            "start_time": start_time - 0.001,
            "ret": True,
            "end_time": start_time
        }
    }
    with open(log_txt_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(start_entry, ensure_ascii=False) + "\n")    # 获取初始截图
    try:
        screenshot = get_device_screenshot(device)
        if screenshot:
            frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            timestamp = time.time()
            screenshot_timestamp = int(timestamp * 1000)
            screenshot_filename = f"{screenshot_timestamp}.jpg"
            # 🔧 修复：截图保存到报告系统目录，而不是方案3目录
            screenshot_path = os.path.join(str(device_report_dir), screenshot_filename)
            cv2.imwrite(screenshot_path, frame)

            # 创建缩略图
            thumbnail_filename = f"{screenshot_timestamp}_small.jpg"
            thumbnail_path = os.path.join(str(device_report_dir), thumbnail_filename)
            small_frame = cv2.resize(frame, (0, 0), fx=0.3, fy=0.3)
            cv2.imwrite(thumbnail_path, small_frame, [cv2.IMWRITE_JPEG_QUALITY, 60])

            print_realtime(f"保存初始截图到报告目录: {screenshot_path}")
            print_realtime(f"保存初始缩略图到报告目录: {thumbnail_path}")
    except Exception as e:
        print_realtime(f"获取初始截图失败: {e}")    # 执行所有脚本
    total_executed = 0
    has_any_execution = False
    total_scripts_processed = 0  # 新增：记录成功处理的脚本数量

    for script_config in scripts:
        script_path = script_config["path"]
        script_loop_count = script_config.get("loop_count", loop_count)
        max_duration = script_config.get("max_duration", None)

        print_realtime(f"📄 处理脚本: {script_path}, 循环: {script_loop_count}, 最大时长: {max_duration}")

        # 读取脚本步骤
        try:
            with open(script_path, "r", encoding="utf-8") as f:
                json_data = json.load(f)
                steps = json_data.get("steps", [])
                meta = json_data.get("meta", {})  # 提取脚本全局meta配置
        except Exception as e:
            print_realtime(f"❌ 读取脚本失败: {e}")
            continue

        if not steps:
            print_realtime(f"⚠️ 脚本 {script_path} 中未找到有效步骤，跳过")
            continue

        # 为步骤设置默认action
        for step in steps:
            if "action" not in step:
                step["action"] = "click"

        # 检查脚本类型
        is_priority_based = any("Priority" in step for step in steps)

        # 脚本成功解析并准备执行，计数+1
        total_scripts_processed += 1
        print_realtime(f"✅ 脚本解析成功，准备执行: {script_path}")

        # 循环执行脚本
        for loop in range(script_loop_count):
            print_realtime(f"🔄 第 {loop + 1}/{script_loop_count} 次循环")

            try:
                if is_priority_based:
                    executed = process_priority_based_script(
                        device, steps, meta, device_report_dir, action_processor,
                        screenshot_queue, click_queue, max_duration
                    )
                else:
                    executed = process_sequential_script(
                        device, steps, device_report_dir, action_processor, max_duration
                    )

                # 记录执行情况，但不影响脚本执行成功状态
                if executed:
                    print_realtime(f"✅ 脚本循环执行成功: 第{loop+1}次循环")
                    total_executed += 1
                else:
                    print_realtime(f"⚠️ 脚本循环执行完成但无成功步骤: 第{loop+1}次循环")

            except Exception as e:
                print_realtime(f"❌ 脚本循环执行异常: 第{loop+1}次循环 - {e}")    # 修改逻辑：采用状态分离原则
    # 1. 脚本执行完成状态：脚本是否正常执行完毕（无崩溃异常）
    # 2. 业务结果状态：脚本执行后的业务结果（是否找到目标、是否完成任务）

    # 脚本执行完成状态：只要没有发生异常，就认为执行完成
    script_execution_completed = True

    # 业务结果状态：基于实际的执行结果
    business_result_success = total_executed > 0

    # 脚本处理成功状态：基于脚本解析和处理
    script_processing_success = total_scripts_processed > 0

    # 🔧 关键修复：真正的状态分离
    # 脚本执行状态：只要函数正常运行到结束，就认为成功（不依赖业务结果）
    # 这是状态分离的核心：脚本执行状态与业务结果状态完全独立

    # 脚本执行状态：只要到达这里，就认为脚本执行成功
    has_any_execution = script_execution_completed  # 基于脚本是否正常完成

    if has_any_execution:
        print_realtime(f"✅ 脚本执行成功: 共处理 {total_scripts_processed} 个脚本，成功执行 {total_executed} 个循环")
    else:
        print_realtime(f"❌ 脚本执行失败: 脚本处理={script_processing_success}, 执行完成={script_execution_completed}")

    # 状态分离说明：
    # - has_any_execution: 脚本是否正常执行完毕
    # - business_result_success: 业务逻辑是否成功
    # - 这两个状态完全独立，互不影响

    print_realtime(f"📊 执行统计: 处理脚本数={total_scripts_processed}, 成功循环数={total_executed}")
    print_realtime(f"📊 状态统计: 脚本执行完成={script_execution_completed}, 业务结果成功={business_result_success}, 脚本处理成功={script_processing_success}")# 记录测试结束
    end_time = time.time()
    end_entry = {
        "tag": "function",
        "depth": 1,
        "time": end_time,
        "data": {
            "name": "结束测试",
            "call_args": {"device": device_name, "executed_scripts": total_executed},
            "start_time": end_time - 0.001,
            "ret": True,
            "end_time": end_time
        }
    }
    with open(log_txt_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(end_entry, ensure_ascii=False) + "\n")
        # 生成HTML报告 - 使用降级处理策略，确保报告生成失败不影响脚本执行状态
    report_generation_success = False
    try:
        print_realtime(f"📝 生成设备 {device_name} 的 HTML 报告...")

        if not REPORT_GENERATOR:
            print_realtime(f"⚠️ 统一报告生成器未初始化，跳过报告生成")
        elif not device_report_dir:
            print_realtime(f"⚠️ 设备报告目录未创建，跳过报告生成")
        elif not REPORT_MANAGER:
            print_realtime(f"⚠️ 报告管理器未初始化，跳过报告生成")
        else:
            # 使用新的统一报告生成器
            print_realtime(f"📝 使用统一报告生成器生成设备报告")
            success = REPORT_GENERATOR.generate_device_report(device_report_dir, scripts)
            if success:
                # 获取报告URL
                report_urls = REPORT_MANAGER.generate_report_urls(device_report_dir)
                print_realtime(f"✅ 设备 {device_name} 单设备报告生成成功: {report_urls['html_report']}")
                report_generation_success = True
            else:
                print_realtime(f"⚠️ 设备 {device_name} 统一报告生成失败，但不影响脚本执行状态")

    except Exception as e:
        print_realtime(f"⚠️ 设备 {device_name} HTML 报告生成失败: {e}，但不影响脚本执行状态")

    # 报告生成状态记录在日志中，不影响脚本执行的成功状态
    if not report_generation_success:
        print_realtime(f"ℹ️ 设备 {device_name} 报告生成失败，建议检查报告管理器配置")# 释放账号
    if device_account:
        try:
            account_manager = get_account_manager()
            account_manager.release_account(device.serial)
            print_realtime(f"✅ 设备 {device_name} 账号已释放")
        except Exception as e:
            print_realtime(f"❌ 账号释放失败: {e}")

    print_realtime(f"🎉 设备 {device_name} 回放完成，总执行脚本数: {total_executed}")
    stop_event.set()

    return has_any_execution, business_result_success, device_report_dir


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


# 注意：原来的generate_script_py和generate_summary_script_py函数已被删除
# 因为它们不再被使用，新的统一报告生成器有自己的实现


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

def log_step_progress(step_num, total_steps, message, device_name=None, is_multi_device=False):
    """
    统一的步骤进度日志记录函数
    适用于单设备和多设备场景
    """
    if is_multi_device and device_name:
        prefix = f"[设备:{device_name}]"
    else:
        prefix = "[单设备]" if not is_multi_device else "[多设备]"

    progress_indicator = f"步骤 {step_num}/{total_steps}"
    print_realtime(f"{prefix} {progress_indicator}: {message}")

def log_phase_start(phase_name, device_name=None, is_multi_device=False):
    """记录阶段开始"""
    if is_multi_device and device_name:
        prefix = f"[设备:{device_name}]"
    else:
        prefix = "[单设备]" if not is_multi_device else "[多设备]"

    print_realtime(f"{prefix} 🚀 开始阶段: {phase_name}")

def log_phase_complete(phase_name, device_name=None, is_multi_device=False, success=True):
    """记录阶段完成"""
    if is_multi_device and device_name:
        prefix = f"[设备:{device_name}]"
    else:
        prefix = "[单设备]" if not is_multi_device else "[多设备]"

    status = "✅ 完成" if success else "❌ 失败"
    print_realtime(f"{prefix} {status}阶段: {phase_name}")

def log_device_summary(device_results):
    """记录多设备执行汇总"""
    if not device_results:
        print_realtime("📊 [汇总] 无设备执行结果")
        return

    total_devices = len(device_results)
    successful_devices = sum(1 for result in device_results if result.get('exit_code', -1) == 0)
    failed_devices = total_devices - successful_devices

    print_realtime("=" * 60)
    print_realtime("📊 [执行汇总]")
    print_realtime(f"   总设备数: {total_devices}")
    print_realtime(f"   成功设备: {successful_devices}")
    print_realtime(f"   失败设备: {failed_devices}")
    print_realtime(f"   成功率: {(successful_devices/total_devices*100):.1f}%")

    for i, result in enumerate(device_results):
        device_name = result.get('device', f'设备{i+1}')
        status = "✅" if result.get('exit_code', -1) == 0 else "❌"
        print_realtime(f"   {status} {device_name}")
    print_realtime("=" * 60)

# 只保留流程调度、日志、报告、设备管理、模型加载等工具方法
# 所有action处理都通过ActionProcessor实现
def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='WFGameAI回放脚本')
    parser.add_argument('--device', type=str, help='设备序列号')
    parser.add_argument('--log-dir', type=str, help='日志目录')
    parser.add_argument('--multi-device', action='store_true', help='多设备模式')
    parser.add_argument('--use-preassigned-accounts', action='store_true', help='使用主进程预分配的账号')
    parser.add_argument('--script', type=str, help='脚本路径')
    parser.add_argument('--loop-count', type=int, default=1, help='循环次数')
    parser.add_argument('--max-duration', type=int, help='最大执行时间(秒)')
    parser.add_argument('--all', action='store_true', help='执行所有脚本')
    parser.add_argument('--account', type=str, help='账号')
    parser.add_argument('--password', type=str, help='密码')
    parser.add_argument('--confidence', type=float, help='置信度阈值')
    args = parser.parse_args()

    # 初始化全局变量
    global is_multi_device
    is_multi_device = args.multi_device or False  # 初始化多设备模式标志

    # 🔧 增加详细的启动调试信息
    print_realtime("=" * 60)
    print_realtime("🚀 replay_script.py 启动")
    print_realtime(f"📅 启动时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print_realtime(f"🐍 Python版本: {sys.version}")
    print_realtime(f"📁 工作目录: {os.getcwd()}")
    print_realtime(f"📝 脚本路径: {__file__ if '__file__' in globals() else 'unknown'}")
    print_realtime(f"🔧 命令行参数数量: {len(sys.argv)}")
    print_realtime("🔧 完整命令行参数:")
    for i, arg in enumerate(sys.argv):
        print_realtime(f"   argv[{i}]: {arg}")
    print_realtime("=" * 60)

    # 加载YOLO模型用于AI检测
    print_realtime("🔄 正在加载YOLO模型...")
    model_loaded = load_yolo_model_for_detection()
    if model_loaded:
        print_realtime("✅ YOLO模型加载成功，AI检测功能可用")
    else:
        print_realtime("⚠️ YOLO模型加载失败，AI检测功能不可用")

    # 检查是否有--script参数
    if '--script' not in sys.argv:
        print_realtime("❌ 错误: 必须指定 --script 参数")
        print_realtime("📋 当前接收到的参数:")
        for i, arg in enumerate(sys.argv):
            print_realtime(f"   参数 {i}: '{arg}'")
        print_realtime("")
        print_realtime("📖 用法示例:")
        print_realtime("  python replay_script.py --script testcase/scene1.json")
        print_realtime("  python replay_script.py --show-screens --script testcase/scene1.json --loop-count 1")
        print_realtime("  python replay_script.py --script testcase/scene1.json --loop-count 1 --script testcase/scene2.json --max-duration 30")
        print_realtime("  python replay_script.py --log-dir /path/to/logs --device serial123 --script testcase/scene1.json")
        print_realtime("❌ 脚本退出: 缺少必要的 --script 参数")
        return

    # 解析脚本参数和多设备参数
    print_realtime("🔧 开始解析命令行参数...")
    scripts, multi_device_params = parse_script_arguments(sys.argv[1:])

    if not scripts:
        print_realtime("❌ 未找到有效的脚本参数")
        print_realtime("🔧 解析结果:")
        print_realtime(f"   scripts: {scripts}")
        print_realtime(f"   multi_device_params: {multi_device_params}")
        print_realtime("❌ 脚本退出: 没有有效的脚本配置")
        return    print_realtime(f"✅ 解析成功，找到 {len(scripts)} 个脚本配置:")
    for i, script in enumerate(scripts):
        print_realtime(f"   脚本 {i+1}: {script}")
    print_realtime(f"🔧 多设备参数: {multi_device_params}")

    # 提取多设备参数
    log_dir = multi_device_params.get('log_dir')
    device_serial = multi_device_params.get('device_serial')
    account = multi_device_params.get('account')
    password = multi_device_params.get('password')

    # 添加调试日志，显示解析到的账号参数
    print_realtime(f"🔍 解析到的账号参数: account={account}, password={'*' * len(password) if password else 'None'}")

    # 如果指定了log_dir和device_serial，则启用文件日志模式
    file_logger = None
    original_stdout = None
    original_stderr = None

    if log_dir and device_serial:
        try:
            file_logger = FileLogger(log_dir, device_serial)
            file_logger.log(f"🎬 启动设备 {device_serial} 的脚本回放")
            file_logger.log(f"📝 将执行 {len(scripts)} 个脚本")
            # 重定向stdout和stderr到文件日志
            original_stdout = sys.stdout
            original_stderr = sys.stderr
            sys.stdout = SafeOutputWrapper(file_logger, "stdout")
            sys.stderr = SafeOutputWrapper(file_logger, "stderr")

            print_realtime(f"✅ 文件日志已启用: {log_dir}/{device_serial}.log")
        except Exception as e:
            print_realtime(f"⚠️ 文件日志启用失败: {e}")

    exit_code = 0
    report_url = ""

    # 状态分离跟踪变量
    system_error_occurred = False  # 是否发生了系统级错误
    business_execution_completed = False  # 是否完成了业务逻辑执行
    any_business_success = False  # 🔧 新增：跟踪是否有任何业务成功

    try:
        log_phase_start("脚本回放初始化", device_serial, len(scripts) > 1)
        print_realtime("🎬 启动精简版回放脚本")
        print_realtime(f"📝 将执行 {len(scripts)} 个脚本:")
        for i, script in enumerate(scripts, 1):
            print_realtime(f"  {i}. {script['path']} (循环:{script['loop_count']}, 最大时长:{script['max_duration']}s)")
        log_phase_complete("脚本回放初始化", device_serial, len(scripts) > 1, True)

        # 如果有账号信息，记录日志
        if account:
            print_realtime(f"�� 使用账号: {account}")

        # 验证脚本文件存在
        missing_scripts = []
        for script in scripts:
            if not os.path.exists(script['path']):
                missing_scripts.append(script['path'])

        if missing_scripts:
            print_realtime("❌ 以下脚本文件不存在:")
            for path in missing_scripts:
                print_realtime(f"  - {path}")
            exit_code = -1
        else:
            # 获取连接的设备
            try:
                devices = adb.device_list()
                if not devices:
                    print_realtime("❌ 未找到连接的设备")
                    exit_code = -1
                else:
                    print_realtime(f"📱 找到 {len(devices)} 个设备")

                    # 如果指定了特定设备，检查是否存在
                    if device_serial:
                        device_found = any(d.serial == device_serial for d in devices)
                        if not device_found:
                            print_realtime(f"❌ 指定的设备 {device_serial} 未找到")
                            exit_code = -1
                        else:
                            print_realtime(f"✅ 使用指定设备: {device_serial}")
                            # 过滤设备列表，只使用指定设备
                            devices = [d for d in devices if d.serial == device_serial]
                    if exit_code == 0:
                        # 最终检查模型状态
                        global model
                        if model is not None:
                            print_realtime("✅ 模型状态检查通过，AI检测功能可用")
                        else:
                            print_realtime("⚠️ 模型状态检查失败，将使用备用检测模式")

                        # 🔧 关键修复：区分单设备和多设备执行模式
                        if len(devices) > 1:
                            print_realtime(f"🔀 检测到多设备模式 ({len(devices)} 台设备)，使用多设备执行框架")

                            # 使用多设备执行框架
                            device_serials = [device.serial for device in devices]
                            try:
                                from multi_device_replayer import replay_scripts_on_devices

                                print_realtime(f"📱 准备并发执行设备: {device_serials}")
                                results, device_report_dirs = replay_scripts_on_devices(
                                    device_serials=device_serials,
                                    scripts=scripts,
                                    max_workers=min(len(devices), 4),  # 最大4个并发
                                    strategy="hybrid"
                                )

                                # 检查执行结果
                                successful_devices = [device for device, result in results.items() if result.get('success', False)]
                                failed_devices = [device for device, result in results.items() if not result.get('success', False)]

                                print_realtime(f"📊 多设备执行完成: 成功 {len(successful_devices)}/{len(devices)} 台设备")
                                if successful_devices:
                                    any_business_success = True
                                    business_execution_completed = True

                                # 收集设备报告目录用于汇总报告
                                current_execution_device_dirs = [str(path) for path in device_report_dirs if path]
                                processed_device_names = list(results.keys())

                                if failed_devices:
                                    print_realtime(f"⚠️ 失败设备: {failed_devices}")
                                    for device in failed_devices:
                                        error = results[device].get('error', 'Unknown error')
                                        print_realtime(f"  - {device}: {error}")

                            except ImportError as e:
                                print_realtime(f"❌ 多设备执行框架导入失败，回退到单设备模式: {e}")
                                # 回退到原有的单设备循环处理
                                processed_device_names = []
                                current_execution_device_dirs = []
                                for device in devices:
                                    device_name = device.serial
                                    processed_device_names.append(device_name)
                            except Exception as e:
                                print_realtime(f"❌ 多设备执行失败: {e}")
                                system_error_occurred = True
                                exit_code = -1
                        else:
                            print_realtime(f"📱 单设备模式，使用原有执行逻辑")
                            # 执行脚本回放的核心逻辑 - 使用现有的replay_device函数
                            processed_device_names = []
                            current_execution_device_dirs = []

                            # 为每个设备执行脚本
                            for device in devices:
                                device_name = device.serial
                                processed_device_names.append(device_name)

                            try:
                                print_realtime(f"🎯 开始处理设备: {device_name}")

                                # 确定日志目录
                                device_log_dir = log_dir if log_dir else None

                                # 使用现有的replay_device函数执行脚本
                                from threading import Event
                                import queue

                                # 创建必要的队列和事件
                                screenshot_queue = queue.Queue()
                                action_queue = queue.Queue()
                                click_queue = queue.Queue()
                                stop_event = Event()

                                # 调用replay_device函数
                                has_execution, business_success, device_report_dir = replay_device(
                                    device=device,
                                    scripts=scripts,
                                    screenshot_queue=screenshot_queue,
                                    action_queue=action_queue,
                                    click_queue=click_queue,
                                    stop_event=stop_event,
                                    device_name=device_name,
                                    log_dir=device_log_dir,
                                    loop_count=1,  # 每个脚本的循环次数已在scripts中指定
                                    cmd_account=account,  # 传递命令行参数中的账号
                                    cmd_password=password  # 传递命令行参数中的密码
                                )
                                if device_report_dir:
                                    current_execution_device_dirs.append(device_report_dir)

                                # 🔧 关键修复：彻底的状态分离处理
                                # 只要replay_device返回，就代表业务逻辑执行阶段已完成
                                business_execution_completed = True

                                # 状态分离处理：脚本执行状态与业务结果状态完全独立
                                if has_execution:
                                    print_realtime(f"✅ 设备 {device_name} 脚本执行成功")
                                else:
                                    print_realtime(f"⚠️ 设备 {device_name} 脚本执行失败")

                                # 业务结果状态处理：独立于脚本执行状态
                                if business_success:
                                    any_business_success = True  # 记录业务成功
                                    print_realtime(f"  -> 业务结果: 成功")
                                else:
                                    print_realtime(f"  -> 业务结果: 无匹配项")

                                # 🔧 关键修复：脚本执行失败也不影响整体状态
                                # 除非发生系统级异常，否则不设置exit_code = -1
                            except Exception as e:
                                print_realtime(f"❌ 设备 {device_name} 处理异常: {e}")
                                # 🔧 关键修复：任何在设备回放期间的异常都应视为系统错误
                                system_error_occurred = True
                                exit_code = -1
                                traceback.print_exc()  # 记录详细堆栈

                        # 删除子进程中的汇总报告生成代码，改为仅记录设备报告目录
                        # 子进程不应该生成汇总报告，只生成自己的设备报告
                        if current_execution_device_dirs and is_multi_device:
                            # 子进程只记录设备报告目录，不生成汇总报告
                            print_realtime("📊 设备测试完成，已记录报告目录")
                            # 只记录device_report_dir以供主进程使用
                            device_report_dir = current_execution_device_dirs[0] if current_execution_device_dirs else None
                            if device_report_dir:
                                # 将设备报告目录作为report_url返回，供主进程汇总
                                report_url = str(device_report_dir)
                                print_realtime(f"📂 设备报告目录: {device_report_dir}")
                        # 如果是单设备模式，则允许生成汇总报告
                        elif current_execution_device_dirs and not is_multi_device and REPORT_GENERATOR:
                            print_realtime("📊 单设备模式，生成汇总报告...")
                            # 转换字符串路径为Path对象
                            from pathlib import Path
                            device_report_paths = [Path(dir_path) for dir_path in current_execution_device_dirs]
                            summary_report_path = REPORT_GENERATOR.generate_summary_report(
                                device_report_paths,
                                scripts  # 传入脚本列表
                            )
                            if summary_report_path:
                                # Convert Path object to string for JSON serialization
                                report_url = str(summary_report_path)
                                print_realtime(f"✅ 汇总报告已生成: {summary_report_path}")
                            else:
                                print_realtime("⚠️ 汇总报告生成失败")

                        print_realtime("✅ 脚本回放执行完成")
                        # 更新状态：业务逻辑执行完成
                        business_execution_completed = True
            except Exception as e:
                print_realtime(f"❌ 设备列表获取失败: {e}")
                # 根据状态分离原则，区分系统异常和业务逻辑异常
                if isinstance(e, (FileNotFoundError, ConnectionError, PermissionError)):
                    exit_code = -1  # 只有系统级异常才影响脚本执行状态
                    system_error_occurred = True
                else:
                    print_realtime(f"⚠️ 设备获取失败但不影响脚本执行状态: {e}")

    except Exception as e:
        print_realtime(f"❌ 脚本回放过程出错: {e}")
        # 根据状态分离原则，区分系统异常和业务逻辑异常
        if isinstance(e, (FileNotFoundError, ConnectionError, PermissionError, ImportError)):
            exit_code = -1  # 只有系统级异常才影响脚本执行状态
            system_error_occurred = True
        else:
            print_realtime(f"⚠️ 脚本回放过程出错但不影响脚本执行状态: {e}")

    finally:
        # 资源清理和结果写入
        if file_logger and log_dir and device_serial:
            try:
                # 恢复原始输出流
                if original_stdout:
                    sys.stdout = original_stdout
                if original_stderr:
                    sys.stderr = original_stderr                # 写入结果文件，包含完整的状态分离记录
                # 关键修复：实现真正的状态分离，使用状态跟踪变量

                # 1. 脚本执行完成状态：脚本是否正常执行完毕（到达finally块表示正常执行）
                execution_completed = True

                # 2. 脚本执行成功状态：基于是否发生系统级异常
                script_execution_success = not system_error_occurred

                # 3. 业务结果状态：基于实际的业务逻辑执行结果
                # 🔧 关键修复：使用 any_business_success 变量，并确保业务执行阶段已完成
                business_result_success = business_execution_completed and any_business_success and not system_error_occurred

                # 🔧 调试日志：记录状态分离的详细信息
                print_realtime(f"📊 状态分离调试信息:")
                print_realtime(f"  -> 脚本执行完成: {execution_completed}")
                print_realtime(f"  -> 脚本执行成功: {script_execution_success}")
                print_realtime(f"  -> 业务执行完成: {business_execution_completed}")
                print_realtime(f"  -> 业务结果成功: {any_business_success}")
                print_realtime(f"  -> 系统错误发生: {system_error_occurred}")
                print_realtime(f"  -> 最终业务结果: {business_result_success}")
                print_realtime(f"  -> 最终退出代码: {0 if script_execution_success else -1}")

                # 4. 报告生成状态：基于报告是否成功生成
                report_generation_success = bool(report_url)

                # 构造结果数据
                result_data = {
                    # 关键修复：exit_code基于真实的执行状态，不再完全依赖脚本内部变量
                    # 只有在真正的系统异常时才设置为-1
                    "exit_code": 0 if script_execution_success else -1,
                    "report_url": report_url,
                    "device": device_serial,
                    "timestamp": time.time(),
                    # 状态分离字段
                    "execution_completed": execution_completed,
                    "script_execution_success": script_execution_success,
                    "business_result_success": business_result_success,
                    "report_generation_success": report_generation_success,
                    # 详细信息
                    "message": "脚本执行完成" if script_execution_success else "脚本执行失败",
                    "error_details": {
                        "business_errors": [],  # 业务逻辑错误列表
                        "report_errors": [] if report_generation_success else ["报告生成失败"]  # 报告错误列表
                    }
                }
                write_result(log_dir, device_serial, result_data)
                file_logger.log(f"✅ 结果已写入: {result_data}")
            except Exception as e:
                print_realtime(f"⚠️ 结果写入失败: {e}")

        print_realtime("🏁 脚本回放任务结束")


def get_confidence_threshold_from_config():
    """
    从config.ini的[settings]节读取AI检测置信度阈值。
    若未配置则返回默认值0.6。
    """
    # config = configparser.ConfigParser()
    # # 构造config.ini的绝对路径（假设本文件在wfgame-ai-server\apps\scripts下）
    # config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'config.ini')
    # config.read(config_path, encoding='utf-8')
    config = settings.CFG._config
    try:
        # 优先从[settings]读取confidence_threshold，没有则用默认值0.6
        return float(config.get('settings', 'confidence_threshold', fallback='0.6'))
    except Exception:
        return 0.6


if __name__ == "__main__":
    main()

