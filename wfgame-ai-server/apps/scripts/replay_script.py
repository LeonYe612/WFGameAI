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
from account_manager import get_account_manager
from enhanced_input_handler import EnhancedInputHandler
from app_permission_manager import integrate_with_app_launch
from enhanced_device_preparation_manager import EnhancedDevicePreparationManager
from action_processor import ActionProcessor, ActionContext, ActionResult

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


def process_priority_based_script(device, steps, log_dir, action_processor, screenshot_queue, click_queue, max_duration=None):
    """处理基于优先级的动态脚本"""
    print_realtime("🎯 开始执行优先级模式脚本")

    # 按优先级排序
    steps.sort(key=lambda s: s.get("Priority", 999))

    priority_start_time = time.time()
    priority_step_counter = 0
    detection_count = 0

    # 持续检测直到超出最大时间
    while max_duration is None or (time.time() - priority_start_time) <= max_duration:
        cycle_count = detection_count // len(steps) + 1
        print_realtime(f"第 {cycle_count} 轮尝试检测，已检测 {detection_count} 次")

        matched_any_target = False
        unknown_fallback_step = None

        for step_idx, step in enumerate(steps):
            # 检查是否达到最大时间
            if max_duration is not None and (time.time() - priority_start_time) > max_duration:
                print_realtime(f"优先级模式已达到最大执行时间 {max_duration}秒，停止执行")
                break

            step_class = step.get("class", "")
            step_remark = step.get("remark", "")
            priority = step.get("Priority", 999)

            # 记录unknown步骤作为备选
            if step_class == "unknown":
                unknown_fallback_step = step
                continue

            print_realtime(f"尝试优先级步骤 P{priority}: {step_class}, 备注: {step_remark}")

            # 使用统一的ActionProcessor接口处理步骤
            try:
                # 为优先级模式设置特殊的action类型
                priority_step = dict(step)  # 复制步骤
                priority_step['action'] = 'ai_detection_click'

                success, has_executed, should_continue = action_processor.process_action(
                    priority_step, step_idx, log_dir
                )

                if success and has_executed:
                    matched_any_target = True
                    priority_step_counter += 1
                    detection_count += 1
                    print_realtime(f"✅ 成功执行优先级步骤: {step_remark}")
                    time.sleep(1.0)  # 让UI响应
                    break
                else:
                    print_realtime(f"❌ 优先级步骤未匹配: {step_class}")
                    detection_count += 1

            except Exception as e:
                print_realtime(f"❌ 优先级步骤执行异常: {e}")
                detection_count += 1

        # 如果所有目标都未匹配，执行备选步骤
        if not matched_any_target and unknown_fallback_step is not None:
            print_realtime("🔄 执行备选步骤")

            try:
                # 为备选步骤设置特殊的action类型
                fallback_step = dict(unknown_fallback_step)  # 复制步骤
                fallback_step['action'] = 'fallback_click'

                success, has_executed, should_continue = action_processor.process_action(
                    fallback_step, -1, log_dir
                )

                if success and has_executed:
                    priority_step_counter += 1
                    print_realtime(f"✅ 成功执行备选步骤")
                    time.sleep(1.0)

            except Exception as e:
                print_realtime(f"❌ 备选步骤执行异常: {e}")

        # 超时检查
        if time.time() - priority_start_time > 30 and priority_step_counter == 0:
            print_realtime("连续30秒未检测到任何优先级步骤，停止检测")
            break

        time.sleep(0.5)  # 短暂暂停

    print_realtime(f"优先级模式执行完成，成功执行步骤: {priority_step_counter}")
    return priority_step_counter > 0


def process_sequential_script(device, steps, log_dir, action_processor, max_duration=None):
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
        print_realtime(f"执行步骤 {step_idx+1}/{len(steps)}: {display_name}, 备注: {step_remark}")        # 使用ActionProcessor处理步骤
        try:
            success, has_executed, should_continue = action_processor.process_action(
                step, step_idx, log_dir
            )

            if success and has_executed:
                has_executed_steps = True
                print_realtime(f"✅ 步骤 {step_idx+1} 执行成功")
            else:
                print_realtime(f"❌ 步骤 {step_idx+1} 执行失败")

            # 检查是否需要停止
            if not should_continue:
                print_realtime(f"步骤 {step_idx+1} 要求停止执行")
                break

        except Exception as e:
            print_realtime(f"❌ 步骤 {step_idx+1} 执行异常: {e}")
            traceback.print_exc()        # 短暂暂停让UI响应
        time.sleep(0.5)

    print_realtime(f"顺序执行完成，共处理 {len(steps)} 个步骤")
    return has_executed_steps


def replay_device(device, scripts, screenshot_queue, action_queue, click_queue, stop_event,
                 device_name, log_dir, show_screens=False, loop_count=1):
    """
    重构后的设备回放函数 - 精简版本
    主要负责流程控制，具体的action处理委托给ActionProcessor
    """
    print_realtime(f"🚀 开始回放设备: {device_name}, 脚本数量: {len(scripts)}")

    # 检查脚本列表
    if not scripts:
        raise ValueError("脚本列表为空，无法回放")    # 使用新的报告管理器创建设备报告目录
    device_report_dir = None
    log_dir = None
    if REPORT_MANAGER:
        try:
            device_report_dir = REPORT_MANAGER.create_device_report_dir(device_name)
            log_dir = str(device_report_dir)
            print_realtime(f"✅ 使用统一报告管理器创建目录: {log_dir}")
        except Exception as e:
            print_realtime(f"⚠️ 统一报告管理器创建目录失败: {e}")
            device_report_dir = None
            log_dir = None

    # 如果统一报告系统失败，使用旧的目录结构
    if not log_dir:
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        log_dir = os.path.join(DEVICE_REPORTS_DIR, f"{device_name}_{timestamp}")
        os.makedirs(log_dir, exist_ok=True)
        print_realtime(f"⚠️ 回退到旧目录结构: {log_dir}")

    # 设置日志目录
    try:
        set_logdir(log_dir)
    except Exception as e:
        print_realtime(f"设置日志目录失败: {e}")

    # 创建log.txt文件
    log_txt_path = os.path.join(log_dir, "log.txt")
    with open(log_txt_path, "w", encoding="utf-8") as f:
        f.write("")

    # 分配账号给设备
    device_account = None
    try:
        account_manager = get_account_manager()
        device_account = account_manager.allocate_account(device.serial)

        if device_account:
            username, password = device_account
            print_realtime(f"✅ 为设备 {device_name} 分配账号: {username}")
        else:
            print_realtime(f"⚠️ 设备 {device_name} 账号分配失败")
    except Exception as e:
        print_realtime(f"❌ 账号分配过程中出错: {e}")

    # 初始化ActionProcessor
    action_processor = ActionProcessor(device, device_name, log_txt_path, lambda: None)    # 设置设备账号
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
        f.write(json.dumps(start_entry, ensure_ascii=False) + "\n")

    # 获取初始截图
    try:
        screenshot = get_device_screenshot(device)
        if screenshot:
            frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            timestamp = time.time()
            screenshot_timestamp = int(timestamp * 1000)
            screenshot_filename = f"{screenshot_timestamp}.jpg"
            screenshot_path = os.path.join(log_dir, screenshot_filename)
            cv2.imwrite(screenshot_path, frame)
            print_realtime(f"保存初始截图: {screenshot_path}")
    except Exception as e:
        print_realtime(f"获取初始截图失败: {e}")

    # 执行所有脚本
    total_executed = 0
    has_any_execution = False

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
        is_priority_based = any("Priority" in step for step in steps)        # 循环执行脚本
        for loop in range(script_loop_count):
            print_realtime(f"🔄 第 {loop + 1}/{script_loop_count} 次循环")

            if is_priority_based:
                executed = process_priority_based_script(
                    device, steps, log_dir, action_processor,
                    screenshot_queue, click_queue, max_duration
                )
            else:
                executed = process_sequential_script(
                    device, steps, log_dir, action_processor, max_duration
                )

            if executed:
                has_any_execution = True
                total_executed += 1    # 记录测试结束
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
        f.write(json.dumps(end_entry, ensure_ascii=False) + "\n")    # 生成HTML报告 - 强制使用新的统一报告生成器
    try:
        print_realtime(f"📝 生成设备 {device_name} 的 HTML 报告...")

        if not REPORT_GENERATOR:
            error_msg = f"❌ 统一报告生成器未初始化，无法生成报告"
            print_realtime(error_msg)
            raise RuntimeError(error_msg)

        if not device_report_dir:
            error_msg = f"❌ 设备报告目录未创建，无法生成报告"
            print_realtime(error_msg)
            raise RuntimeError(error_msg)

        if not REPORT_MANAGER:
            error_msg = f"❌ 报告管理器未初始化，无法生成报告"
            print_realtime(error_msg)
            raise RuntimeError(error_msg)

        # 使用新的统一报告生成器
        print_realtime(f"📝 使用统一报告生成器生成设备报告")
        success = REPORT_GENERATOR.generate_device_report(device_report_dir, scripts)
        if success:
            # 获取报告URL
            report_urls = REPORT_MANAGER.generate_report_urls(device_report_dir)
            print_realtime(f"✅ 设备 {device_name} 报告生成成功: {report_urls['html_report']}")
        else:
            error_msg = f"❌ 设备 {device_name} 统一报告生成失败"
            print_realtime(error_msg)
            raise RuntimeError(error_msg)

    except Exception as e:
        print_realtime(f"❌ 设备 {device_name} HTML 报告生成失败: {e}")
        raise e    # 释放账号
    if device_account:
        try:
            account_manager = get_account_manager()
            account_manager.release_account(device.serial)
            print_realtime(f"✅ 设备 {device_name} 账号已释放")
        except Exception as e:
            print_realtime(f"❌ 账号释放失败: {e}")

    print_realtime(f"🎉 设备 {device_name} 回放完成，总执行脚本数: {total_executed}")
    stop_event.set()

    return has_any_execution, device_report_dir


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


# 主要函数和命令行参数处理保持不变...
def main():
    """主函数 - 支持README中的完整命令格式"""
    # 使用自定义参数解析以支持复杂的脚本参数格式
    import sys    # 检查是否有--script参数
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
        return    # 解析其他参数
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
        return    # 获取连接的设备
    try:
        devices = adb.device_list()
        if not devices:
            print_realtime("❌ 未找到连接的设备")
            return        print_realtime(f"📱 找到 {len(devices)} 个设备")

        # 收集实际处理的设备名称列表，用于生成报告
        processed_device_names = []
        # 收集本次执行创建的设备报告目录路径
        current_execution_device_dirs = []# 为每个设备执行回放
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
            detection_thread.start()            # 执行设备回放
            try:
                has_execution, device_report_dir = replay_device(
                    device=device,
                    scripts=scripts,
                    screenshot_queue=screenshot_queue,
                    action_queue=action_queue,
                    click_queue=click_queue,
                    stop_event=stop_event,
                    device_name=device_name,
                    log_dir=None,  # 让replay_device函数内部的统一报告管理器来创建目录
                    show_screens=show_screens,
                    loop_count=1  # 这个参数在脚本级别配置中已被覆盖
                )

                if has_execution:
                    print_realtime(f"✅ 设备 {device_name} 回放成功完成")
                    # 记录本次执行创建的设备报告目录
                    if device_report_dir:
                        current_execution_device_dirs.append(device_report_dir)
                else:
                    print_realtime(f"⚠️ 设备 {device_name} 未执行任何操作")

            except Exception as e:
                print_realtime(f"❌ 设备 {device_name} 回放失败: {e}")
                traceback.print_exc()
            finally:
                stop_event.set()

        # 所有设备处理完成后，生成汇总报告
        print_realtime("🔄 脚本执行完成，开始生成汇总报告...")
        try:
            # 给Airtest日志一点时间完成写入
            time.sleep(2)

            # 使用新的统一报告生成器生成汇总报告
            if not REPORT_GENERATOR:
                error_msg = f"❌ 统一报告生成器未初始化，无法生成汇总报告"
                print_realtime(error_msg)
                raise RuntimeError(error_msg)

            if not REPORT_MANAGER:
                error_msg = f"❌ 报告管理器未初始化，无法生成汇总报告"
                print_realtime(error_msg)
                raise RuntimeError(error_msg)            # 使用本次执行创建的设备报告目录，而不是所有历史目录
            device_report_dirs = current_execution_device_dirs

            if not device_report_dirs:
                print_realtime("⚠️ 没有找到本次执行创建的设备报告目录，跳过汇总报告生成")
                return

            print_realtime(f"📊 将为 {len(device_report_dirs)} 个设备生成汇总报告")

            # 生成汇总报告
            summary_report_path = REPORT_GENERATOR.generate_summary_report(device_report_dirs, scripts)
            if summary_report_path:
                print_realtime(f"✅ 汇总报告生成成功: {summary_report_path}")
            else:
                error_msg = f"❌ 汇总报告生成失败"
                print_realtime(error_msg)
                raise RuntimeError(error_msg)

        except ImportError as e:
            print_realtime(f"❌ 无法导入报告生成模块: {e}")
        except Exception as e:
            print_realtime(f"❌ 报告生成异常: {e}")

    except Exception as e:
        print_realtime(f"❌ 设备处理失败: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
