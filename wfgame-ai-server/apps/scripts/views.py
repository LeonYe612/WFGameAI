#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================
Description:
脚本管理应用的视图函数
Author: WFGame AI Team
CreateDate: 2024-05-15
Version: 1.0
===============================
"""

import logging
from datetime import datetime
import traceback
import atexit
import shlex
import json
import uuid
import os
import subprocess
import glob
import re
import threading
import sys
import platform
import signal
import shutil
import configparser # 新增：用于读取配置文件
import time
import psutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import concurrent.futures

# =====================
# 强制设置UTF-8编码环境
# =====================
# 设置环境变量确保所有子进程使用UTF-8
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

# 在Windows系统上设置控制台代码页为UTF-8
if platform.system() == "Windows":
    try:
        # 尝试设置控制台为UTF-8编码
        import subprocess
        subprocess.run(['chcp', '65001'], shell=True, capture_output=True, check=False)
        os.environ['PYTHONLEGACYWINDOWSSTDIO'] = '0'
    except Exception:
        pass  # 如果设置失败，继续执行

# 确保标准流使用UTF-8编码
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from django.shortcuts import get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from rest_framework import viewsets, status, views, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .models import (
    ScriptCategory, Script, ScriptVersion, ScriptExecution, ScriptFile, SystemConfig
)
from .serializers import (
    ScriptCategorySerializer,
    ScriptListSerializer,
    ScriptDetailSerializer,
    ScriptVersionSerializer,
    ScriptImportSerializer,
    ScriptExecutionSerializer,
    ScriptCreateSerializer,
    ScriptUpdateSerializer,
    ScriptSerializer,
    ScriptFileSerializer
)

logger = logging.getLogger(__name__)

# 配置logger以正确处理中文编码
class UTF8StreamHandler(logging.StreamHandler):
    """强化的UTF-8流处理器，确保所有中文和emoji字符正确显示"""

    def __init__(self, stream=None):
        super().__init__(stream)
        self.stream = stream or sys.stdout

    def emit(self, record):
        try:
            msg = self.format(record)

            # 确保消息是Unicode字符串
            if isinstance(msg, bytes):
                msg = msg.decode('utf-8', errors='replace')

            # 强制使用UTF-8编码输出
            if hasattr(self.stream, 'buffer'):
                # 直接写入底层buffer，绕过可能的编码问题
                self.stream.buffer.write(msg.encode('utf-8') + b'\n')
                self.stream.buffer.flush()
            else:
                # 如果没有buffer属性，直接写入流
                try:
                    self.stream.write(msg + '\n')
                    self.stream.flush()
                except UnicodeEncodeError:
                    # 如果编码失败，强制替换不可编码的字符
                    safe_msg = msg.encode('utf-8', errors='replace').decode('utf-8')
                    self.stream.write(safe_msg + '\n')
                    self.stream.flush()
        except Exception as e:
            # 如果所有方法都失败，使用最基本的错误处理
            try:
                fallback_msg = f"[编码错误] {repr(record.getMessage())}"
                if hasattr(self.stream, 'buffer'):
                    self.stream.buffer.write(fallback_msg.encode('utf-8') + b'\n')
                    self.stream.buffer.flush()
                else:
                    self.stream.write(fallback_msg + '\n')
                    self.stream.flush()
            except:
                self.handleError(record)

# 清理并重新配置所有日志处理器
def setup_utf8_logging():
    """设置UTF-8日志系统"""

    # 获取根日志器
    root_logger = logging.getLogger()

    # 移除所有现有处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 获取当前模块的日志器
    current_logger = logging.getLogger(__name__)

    # 移除当前模块日志器的所有处理器
    for handler in current_logger.handlers[:]:
        current_logger.removeHandler(handler)

    # 创建新的UTF-8处理器
    handler = UTF8StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)

    # 添加到当前模块日志器
    current_logger.addHandler(handler)
    current_logger.setLevel(logging.INFO)
    current_logger.propagate = False  # 防止重复输出

    # 同时为根日志器添加处理器，处理其他模块的日志
    root_handler = UTF8StreamHandler(sys.stdout)
    root_handler.setFormatter(formatter)
    root_handler.setLevel(logging.INFO)
    root_logger.addHandler(root_handler)
    root_logger.setLevel(logging.INFO)

    return current_logger

# 立即设置UTF-8日志系统
logger = setup_utf8_logging()

# 测试日志输出
logger.info("✅ UTF-8日志系统初始化完成")
logger.info("🔧 中文和emoji字符应该能正常显示")

# =====================
# UTF-8 subprocess 封装函数
# =====================
def run_subprocess_utf8(cmd, **kwargs):
    """
    统一的UTF-8 subprocess封装函数
    确保所有子进程调用都使用正确的UTF-8编码
    """
    # 强制设置UTF-8相关参数
    utf8_kwargs = {
        'encoding': 'utf-8',
        'errors': 'replace',
        'text': True,
        'env': dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
    }

    # 合并用户提供的参数，但UTF-8设置优先
    final_kwargs = {**kwargs, **utf8_kwargs}

    try:
        return subprocess.run(cmd, **final_kwargs)
    except Exception as e:
        logger.error(f"subprocess执行失败: {cmd}, 错误: {e}")
        raise

def create_subprocess_utf8(cmd, **kwargs):
    """
    统一的UTF-8 subprocess.Popen封装函数
    确保所有子进程创建都使用正确的UTF-8编码
    """
    # 强制设置UTF-8相关参数
    utf8_kwargs = {
        'encoding': 'utf-8',
        'errors': 'replace',
        'text': True,
        'env': dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
    }

    # 合并用户提供的参数，但UTF-8设置优先
    final_kwargs = {**kwargs, **utf8_kwargs}

    try:
        return subprocess.Popen(cmd, **final_kwargs)
    except Exception as e:
        logger.error(f"subprocess.Popen创建失败: {cmd}, 错误: {e}")
        raise

# =====================
# 路径变量统一修正（强制依赖config.ini）
# =====================
# 加载项目根目录下的config.ini
CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../config.ini'))
config = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())

# 确保config.ini文件存在
if not os.path.exists(CONFIG_PATH):
    raise FileNotFoundError(f'配置文件未找到: {CONFIG_PATH}')

# 读取配置文件
if not config.read(CONFIG_PATH, encoding='utf-8'):
    raise IOError(f'无法读取配置文件: {CONFIG_PATH}')

# 确保paths部分存在
if 'paths' not in config:
    raise KeyError(f'配置文件中缺少[paths]部分: {CONFIG_PATH}')

paths = config['paths']

# 记录加载的关键路径
logger.info(f'已加载配置文件: {CONFIG_PATH}')
logger.info(f'SCRIPTS_DIR将被设置为: {paths["scripts_dir"]}')
logger.info(f'TESTCASE_DIR将被设置为: {paths["testcase_dir"]}')
logger.info(f'REPORTS_DIR将被设置为: {paths["reports_dir"]}')

# 所有目录变量均以config.ini为准
SCRIPTS_DIR = os.path.abspath(paths['scripts_dir'])
TESTCASE_DIR = os.path.abspath(paths['testcase_dir'])
REPORTS_DIR = os.path.abspath(paths['reports_dir'])

if 'devices_report_paths' not in config:
    raise KeyError(f'配置文件中缺少[devices_report_paths]部分: {CONFIG_PATH}')

devices_report_paths = config['devices_report_paths']

# 使用新的统一报告目录结构
STATICFILES_REPORTS_DIR = os.path.abspath(devices_report_paths['device_replay_reports_dir'])
DEVICE_REPORTS_DIR = os.path.abspath(devices_report_paths['single_device_reports_dir'])
SUMMARY_REPORTS_DIR = os.path.abspath(devices_report_paths['summary_reports_dir'])

# 为兼容性保留UI_REPORTS_DIR变量，但指向新的设备报告目录
UI_REPORTS_DIR = DEVICE_REPORTS_DIR

# 确保统一报告目录存在
os.makedirs(STATICFILES_REPORTS_DIR, exist_ok=True)
os.makedirs(DEVICE_REPORTS_DIR, exist_ok=True)
os.makedirs(SUMMARY_REPORTS_DIR, exist_ok=True)

# 其余所有涉及目录引用的地方，全部使用上述变量，不允许静态拼接。
# 例如：
# record_script_path = os.path.join(SCRIPTS_DIR, "record_script.py")
# replay_script_path = os.path.join(SCRIPTS_DIR, "replay_script.py")
# 用例文件、报告文件等均以 TESTCASE_DIR、REPORTS_DIR、UI_REPORTS_DIR 为基准。
# =====================

# =====================
# 删除所有 configparser、load_config、CONFIG、PATHS、PYTHON_PATH 相关动态路径推导代码
# =====================

# 获取当前python解释器路径（仅返回sys.executable）
def get_persistent_python_path():
    """
    获取当前python解释器路径，已静态化
    """
    return sys.executable

def find_script_path(script_name):
    """查找脚本文件的完整路径"""
    # 在当前目录查找
    current_dir_path = os.path.join(os.path.dirname(__file__), script_name)
    if os.path.exists(current_dir_path):
        return current_dir_path

    # 在SCRIPTS_DIR查找
    scripts_dir_path = os.path.join(SCRIPTS_DIR, script_name)
    if os.path.exists(scripts_dir_path):
        return scripts_dir_path

    # 返回默认路径（可能不存在）
    return current_dir_path

# 存储当前使用的Python环境路径
CURRENT_PYTHON_ENV = {"path": get_persistent_python_path(), "initialized": True}

# 用于管理子进程的全局变量
CHILD_PROCESSES = {}

# 初始化时，设置进程结束的处理函数
def cleanup_processes():
    """清理所有子进程"""
    for pid, process in list(CHILD_PROCESSES.items()):
        try:
            if process.poll() is None:  # 进程仍在运行
                process.terminate()
                logger.info(f"已终止进程: {pid}")
        except Exception as e:
            logger.error(f"终止进程 {pid} 时出错: {e}")

    CHILD_PROCESSES.clear()

# 确保在退出时清理进程
import atexit
atexit.register(cleanup_processes)

# 处理Windows下的SIGTERM信号
if platform.system() == "Windows":
    def handle_windows_signal(sig, frame):
        logger.info(f"接收到信号: {sig}")
        cleanup_processes()
        sys.exit(0)

    # Windows下的信号处理
    try:
        import win32api
        win32api.SetConsoleCtrlHandler(lambda sig: handle_windows_signal(sig, None), True)
    except ImportError:
        logger.warning("无法导入win32api，Windows下可能无法正确处理信号")
else:
    # Unix系统的信号处理
    signal.signal(signal.SIGTERM, lambda sig, frame: handle_windows_signal(sig, frame))

@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def get_devices(request):
    """
    获取已连接的设备列表

    POST方法，返回通过adb devices获取的实际设备数据

    返回数据格式:
    {
        "devices": [
            {
                "serial": "设备序列号",
                "brand": "设备品牌",
                "model": "设备型号",
                "name": "设备名称",
                "status": "设备状态"
            },
            ...
        ]
    }
    """
    try:
        # 记录请求开始
        logger.info("开始获取设备列表...")        # 使用adb命令扫描设备
        result = run_subprocess_utf8(['adb', 'devices'], capture_output=True, check=True)

        # 分析输出
        lines = result.stdout.strip().split('\n')[1:]  # 跳过"List of devices attached"标题行
        devices = []

        # 记录原始输出用于调试
        logger.info(f"ADB原始输出: {result.stdout}")

        for line in lines:
            if not line.strip():
                continue

            # 解析设备信息: 格式通常为 "serial\tstatus"
            parts = line.strip().split('\t')
            if len(parts) >= 2:
                serial, status = parts

                # 只处理已连接的设备和未授权的设备
                if status in ['device', 'unauthorized', 'offline']:
                    device_info = {
                        'serial': serial,
                        'status': status,
                        'brand': '',
                        'model': '',
                        'name': serial  # 默认使用序列号作为名称
                    }

                    # 如果设备已连接授权，获取更多设备信息
                    if status == 'device':
                        try:                            # 获取设备品牌
                            brand_cmd = run_subprocess_utf8(
                                ['adb', '-s', serial, 'shell', 'getprop', 'ro.product.brand'],
                                capture_output=True, timeout=5
                            )
                            device_info['brand'] = brand_cmd.stdout.strip()

                            # 获取设备型号
                            model_cmd = run_subprocess_utf8(
                                ['adb', '-s', serial, 'shell', 'getprop', 'ro.product.model'],
                                capture_output=True, timeout=5
                            )
                            device_info['model'] = model_cmd.stdout.strip()

                            # 设置完整名称
                            if device_info['brand'] and device_info['model']:
                                device_info['name'] = f"{device_info['brand']}-{device_info['model']}"

                        except Exception as e:
                            logger.warning(f"获取设备 {serial} 详情失败: {str(e)}")

                    devices.append(device_info)

            # 记录找到的设备数量
            logger.info(f"成功找到 {len(devices)} 台设备")

        # 返回设备列表
        return Response({'devices': devices})
    except Exception as e:
        # 记录错误
        logger.error(f"获取设备列表失败: {str(e)}", exc_info=True)
        return Response({'error': str(e), 'devices': []}, status=500)

@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def get_scripts(request):
    """
    获取可用的测试脚本列表（数据库+文件系统合并，去重）
    - 优先返回数据库ScriptFile信息
    - 补充testcase目录下所有json文件（如数据库无记录或未覆盖）
    """
    try:
        logger.info(f"开始获取脚本列表... TESTCASE_DIR: {TESTCASE_DIR}")

        # 1. 先查数据库
        script_files = ScriptFile.objects.filter(status='active').order_by('-created_at')
        scripts = []
        db_filenames = set()

        logger.info(f"从数据库查询到的脚本文件数量: {script_files.count()}")

        for script_file in script_files:
            file_path = os.path.join(TESTCASE_DIR, script_file.filename)
            # 检查文件是否存在，避免返回已删除的文件记录
            if os.path.exists(file_path):
                scripts.append({
                    'filename': script_file.filename,
                    'path': script_file.filename,  # 只用文件名
                    'created': script_file.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'step_count': script_file.step_count,
                    'category': script_file.category.name if script_file.category else '未分类',
                    'type': script_file.get_type_display(),
                    'description': script_file.description
                })
                db_filenames.add(script_file.filename)

        logger.info(f"从数据库找到有效脚本文件: {len(scripts)}")

        # 2. 文件系统补充（只补数据库未覆盖的文件）
        os.makedirs(TESTCASE_DIR, exist_ok=True)
        logger.info(f"正在扫描测试用例目录: {TESTCASE_DIR}")

        file_count = 0
        for script_file in glob.glob(os.path.join(TESTCASE_DIR, "*.json")):
            file_count += 1
            filename = os.path.basename(script_file)
            if filename in db_filenames:
                continue  # 已在数据库中

            created_time = datetime.fromtimestamp(os.path.getctime(script_file))
            # 读取脚本内容获取步骤数
            try:
                with open(script_file, 'r', encoding='utf-8') as f:
                    script_data = json.load(f)
                    step_count = len(script_data.get('steps', []))

                scripts.append({
                    'filename': filename,
                    'path': filename,  # 关键：这里只返回文件名，不返回完整路径
                    'created': created_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'step_count': step_count,
                    'category': '未分类',
                    'type': '文件',
                    'description': ''
                })
                logger.info(f"从文件系统添加脚本: {filename}, 步骤数: {step_count}")
            except Exception as e:
                logger.warning(f"读取脚本文件 {filename} 失败: {str(e)}")

        logger.info(f"文件系统中找到的JSON文件总数: {file_count}")
        logger.info(f"最终返回的脚本总数: {len(scripts)}")

        # 3. 按创建时间排序，最新的在前面
        scripts.sort(key=lambda x: x['created'], reverse=True)
        return Response({'scripts': scripts})
    except Exception as e:
        logger.error(f"获取脚本列表失败: {str(e)}", exc_info=True)
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def get_reports(request):
    """获取已生成的测试报告列表"""
    try:
        # 确保目录存在
        os.makedirs(UI_REPORTS_DIR, exist_ok=True)

        # 获取所有HTML报告文件
        reports = []
        for report_file in glob.glob(os.path.join(UI_REPORTS_DIR, "*.html")):
            filename = os.path.basename(report_file)
            # 跳过latest_report.html，这只是一个快捷方式
            if filename == 'latest_report.html':
                continue

            created_time = datetime.fromtimestamp(os.path.getctime(report_file))
            reports.append({
                'filename': filename,
                'path': report_file,
                'created': created_time.strftime('%Y-%m-%d %H:%M:%S'),
                'url': f'/static/reports/{filename}'
            })

        # 按创建时间排序，最新的在前面
        reports.sort(key=lambda x: x['created'], reverse=True)

        # 检查是否有latest_report.html
        latest_report_path = os.path.join(UI_REPORTS_DIR, "latest_report.html")
        has_latest = os.path.exists(latest_report_path)

        return Response({
            'reports': reports,
            'latest_url': '/static/reports/latest_report.html' if has_latest else None
        })
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def get_latest_report(request):
    """获取最新的测试报告"""
    try:
        latest_report_path = os.path.join(UI_REPORTS_DIR, "latest_report.html")
        if os.path.exists(latest_report_path):
            # 提取报告创建时间
            created_time = datetime.fromtimestamp(os.path.getctime(latest_report_path))

            return Response({
                'filename': 'latest_report.html',
                'path': latest_report_path,
                'created': created_time.strftime('%Y-%m-%d %H:%M:%S'),
                'url': '/static/reports/latest_report.html'
            })
        else:
            return Response({'error': '未找到最新报告'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def get_python_envs(request):
    """获取系统中所有可用的Python环境"""
    try:
        envs = []

        # 当前Python环境信息
        current_env = {
            "name": "当前环境",
            "path": sys.executable,
            "version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "active": True,
            "packages": []
        }        # 获取当前环境已安装的包
        try:
            pip_freeze = run_subprocess_utf8([sys.executable, "-m", "pip", "freeze"],
                                      capture_output=True, check=True)
            packages = pip_freeze.stdout.strip().split('\n')
            current_env["packages"] = packages
        except Exception as e:
            logger.warning(f"获取当前环境包列表失败: {e}")

        envs.append(current_env)

        # 检测操作系统
        is_windows = platform.system() == "Windows"

        # 查找系统中的Python环境
        found_paths = []

        # 1. 查找全局Python
        if is_windows:
            # Windows下查找全局Python路径
            potential_paths = [
                r"C:\Python*",
                r"C:\Program Files\Python*",
                r"C:\Users\*\AppData\Local\Programs\Python\Python*"
            ]

            for pattern in potential_paths:
                for path in glob.glob(pattern):
                    python_exe = os.path.join(path, "python.exe")
                    if os.path.exists(python_exe) and python_exe != sys.executable:
                        found_paths.append(python_exe)
        else:            # Mac/Linux下查找全局Python路径
            try:
                which_python3 = run_subprocess_utf8(["which", "python3"],
                                             capture_output=True, check=True)
                python3_path = which_python3.stdout.strip()

                if python3_path and python3_path != sys.executable:
                    found_paths.append(python3_path)
            except Exception as e:
                logger.warning(f"查找全局Python路径失败: {e}")

        # 2. 查找Anaconda/Miniconda环境 - 增强对Conda环境的检测
        conda_env_paths = []

        # 首先尝试运行conda info命令
        try:
            # 查找可能的conda可执行文件
            conda_executables = ['conda', 'conda.exe']
            conda_path = None            # 尝试在PATH中找到conda
            for conda_exe in conda_executables:
                try:
                    if is_windows:
                        conda_proc = run_subprocess_utf8(['where', conda_exe],
                                                   capture_output=True, check=True)
                    else:
                        conda_proc = run_subprocess_utf8(['which', conda_exe],
                                                   capture_output=True, check=True)

                    conda_paths = conda_proc.stdout.strip().split('\n')
                    if conda_paths and conda_paths[0]:
                        conda_path = conda_paths[0]
                        break
                except Exception:
                    continue

            if conda_path:
                # 使用conda env list获取所有环境
                conda_env_proc = run_subprocess_utf8([conda_path, 'env', 'list', '--json'],
                                              capture_output=True, timeout=5)

                if conda_env_proc.returncode == 0:
                    try:
                        conda_envs_data = json.loads(conda_env_proc.stdout)
                        for env in conda_envs_data.get('envs', []):
                            if is_windows:
                                python_exe = os.path.join(env, "python.exe")
                            else:
                                python_exe = os.path.join(env, "bin", "python")

                            if os.path.exists(python_exe) and python_exe != sys.executable:
                                conda_env_paths.append(python_exe)
                    except json.JSONDecodeError:
                        logger.warning("无法解析conda env list输出")
        except Exception as e:
            logger.warning(f"使用conda命令获取环境列表失败: {e}")

        # 如果conda命令失败，回退到原来的目录查找方法
        if not conda_env_paths:
            if is_windows:
                # Windows下查找Anaconda/Miniconda环境
                potential_anaconda_paths = [
                    r"C:\ProgramData\Anaconda*",
                    r"C:\ProgramData\Miniconda*",
                    r"C:\Users\*\Anaconda*",
                    r"C:\Users\*\Miniconda*",
                    r"C:\Users\*\AppData\Local\Continuum\anaconda*",
                    r"C:\Users\*\AppData\Local\Continuum\miniconda*"
                ]

                for pattern in potential_anaconda_paths:
                    for base_path in glob.glob(pattern):
                        # 检查环境目录
                        envs_dir = os.path.join(base_path, "envs")
                        if os.path.exists(envs_dir) and os.path.isdir(envs_dir):
                            for env_dir in os.listdir(envs_dir):
                                python_exe = os.path.join(envs_dir, env_dir, "python.exe")
                                if os.path.exists(python_exe) and python_exe != sys.executable:
                                    conda_env_paths.append(python_exe)

                        # 检查base环境
                        base_python = os.path.join(base_path, "python.exe")
                        if os.path.exists(base_python) and base_python != sys.executable:
                            conda_env_paths.append(base_python)
            else:
                # Mac/Linux下查找Anaconda/Miniconda环境
                home_dir = os.path.expanduser("~")
                potential_anaconda_paths = [
                    os.path.join(home_dir, "anaconda3"),
                    os.path.join(home_dir, "miniconda3"),
                    os.path.join(home_dir, ".conda")
                ]

                for base_path in potential_anaconda_paths:
                    if os.path.exists(base_path) and os.path.isdir(base_path):
                        # 检查环境目录
                        envs_dir = os.path.join(base_path, "envs")
                        if os.path.exists(envs_dir) and os.path.isdir(envs_dir):
                            for env_dir in os.listdir(envs_dir):
                                python_bin = os.path.join(envs_dir, env_dir, "bin", "python")
                                if os.path.exists(python_bin) and python_bin != sys.executable:
                                    conda_env_paths.append(python_bin)

                        # 检查base环境
                        base_python = os.path.join(base_path, "bin", "python")
                        if os.path.exists(base_python) and base_python != sys.executable:
                            conda_env_paths.append(base_python)

        # 合并所有找到的路径
        found_paths.extend(conda_env_paths)

        # 取消重复路径
        found_paths = list(set(found_paths))        # 获取每个Python环境的版本信息
        for python_path in found_paths:
            try:
                # 获取版本信息
                version_cmd = [python_path, "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"]
                version_proc = run_subprocess_utf8(version_cmd, capture_output=True, timeout=3)
                version = version_proc.stdout.strip() if version_proc.returncode == 0 else "未知"

                # 尝试获取环境名称
                name = "Python环境"                # 检查是否为conda环境
                try:
                    conda_info_cmd = [python_path, "-c",
                                     "import os, sys; print(os.environ.get('CONDA_DEFAULT_ENV') or os.path.basename(os.path.dirname(os.path.dirname(sys.executable)))) if 'conda' in sys.version or 'Continuum' in sys.version else print('non-conda')"]
                    conda_info_proc = run_subprocess_utf8(conda_info_cmd, capture_output=True, timeout=3)

                    env_name = conda_info_proc.stdout.strip()
                    if env_name and env_name != 'non-conda':
                        name = f"Conda: {env_name}"
                except Exception:
                    # 回退到从路径提取名称
                    if "anaconda" in python_path.lower() or "miniconda" in python_path.lower() or "conda" in python_path.lower():
                        name_parts = python_path.split(os.sep)
                        # 尝试从路径中提取环境名称
                        if "envs" in name_parts:
                            env_index = name_parts.index("envs")
                            if env_index + 1 < len(name_parts):
                                name = f"Conda: {name_parts[env_index + 1]}"
                        else:
                            # 可能是base环境
                            if "anaconda" in python_path.lower():
                                name = "Conda: Anaconda Base"
                            elif "miniconda" in python_path.lower():
                                name = "Conda: Miniconda Base"
                            else:
                                name = "Conda: Base"                # 获取已安装的包
                packages = []
                try:
                    pip_cmd = [python_path, "-m", "pip", "freeze"]
                    pip_proc = run_subprocess_utf8(pip_cmd, capture_output=True, timeout=5)
                    if pip_proc.returncode == 0:
                        packages = pip_proc.stdout.strip().split('\n')
                except Exception as e:
                    logger.warning(f"获取环境 {python_path} 的包列表失败: {e}")

                # 检查是否有常用包
                has_pytorch = any('torch==' in pkg for pkg in packages)
                has_airtest = any('airtest==' in pkg for pkg in packages)
                has_yolo = any(('yolo' in pkg.lower() and '==' in pkg) for pkg in packages)

                # 添加常用包标记
                features = []
                if has_pytorch:
                    features.append("PyTorch")
                if has_airtest:
                    features.append("Airtest")
                if has_yolo:
                    features.append("YOLO")

                # 添加到环境列表
                envs.append({
                    "name": name,
                    "path": python_path,
                    "version": version,
                    "active": python_path == CURRENT_PYTHON_ENV.get("path", ""),
                    "packages": packages,
                    "features": features
                })
            except Exception as e:
                logger.warning(f"获取环境 {python_path} 信息失败: {e}")

        return JsonResponse({
            'success': True,
            'envs': envs
        })
    except Exception as e:
        error_msg = str(e)
        logger.error(f"检测Python环境失败: {error_msg}")

        return JsonResponse({
            'success': False,
            'message': f'检测Python环境失败: {error_msg}'
        }, status=500)

@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def switch_python_env(request):
    """切换当前使用的Python环境"""
    try:
        data = json.loads(request.body)
        new_env_path = data.get('path')

        if not new_env_path:
            return JsonResponse({
                'success': False,
                'message': '未提供Python环境路径'
            }, status=400)

        # 检查路径是否存在
        if not os.path.exists(new_env_path):
            return JsonResponse({
                'success': False,
                'message': f'Python环境路径不存在: {new_env_path}'
            }, status=400)        # 验证是否为有效的Python解释器
        try:
            check_proc = run_subprocess_utf8([new_env_path, "--version"],
                                      capture_output=True, timeout=3)
            if check_proc.returncode != 0:
                return JsonResponse({
                    'success': False,
                    'message': f'无效的Python解释器: {new_env_path}'
                }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'验证Python解释器失败: {str(e)}'
            }, status=400)

        # 保存新的Python环境路径到全局变量
        CURRENT_PYTHON_ENV["path"] = new_env_path
        CURRENT_PYTHON_ENV["initialized"] = True

        # 保存到数据库，确保持久化存储
        user = request.user if request.user.is_authenticated else None
        SystemConfig.set_value(
            key='python_path',
            value=new_env_path,
            user=user,
            description=f'Python解释器路径设置于 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
        )        # 获取环境名称
        env_name = "未知环境"
        try:
            conda_info_cmd = [new_env_path, "-c",
                             "import os, sys; print(os.environ.get('CONDA_DEFAULT_ENV') or os.path.basename(os.path.dirname(os.path.dirname(sys.executable)))) if 'conda' in sys.version or 'Continuum' in sys.version else print(sys.executable)"]
            conda_info_proc = run_subprocess_utf8(conda_info_cmd, capture_output=True, timeout=3)

            env_name = conda_info_proc.stdout.strip()
        except Exception:
            # 如果获取名称失败，使用路径
            env_name = new_env_path

        # 记录日志，确保设置已保存
        logger.info(f"已切换Python解释器路径并持久化保存: {new_env_path}")

        return JsonResponse({
            'success': True,
            'message': f'已切换到Python环境: {env_name}',
            'path': new_env_path
        })
    except Exception as e:
        error_msg = str(e)
        logger.error(f"切换Python环境失败: {error_msg}")

        return JsonResponse({
            'success': False,
            'message': f'切换Python环境失败: {error_msg}'
        }, status=500)

@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def record_script(request):
    """启动脚本录制"""
    try:
        data = request.data
        record_mode = data.get('record_mode', 'standard')  # standard or enhanced
        device_serial = data.get('device_serial')

        # 获取Python解释器路径
        python_exec = get_persistent_python_path()

        # 获取record_script.py的绝对路径
        record_script_path = os.path.join(SCRIPTS_DIR, "record_script.py")
        logger.info(f"使用脚本路径: {record_script_path}")

        # 验证脚本存在
        if not os.path.exists(record_script_path):
            logger.error(f"录制脚本不存在: {record_script_path}")
            return Response({'error': f'录制脚本不存在: {record_script_path}'}, status=404)

        cmd = [python_exec, record_script_path]

        # 根据模式添加参数
        if record_mode == 'enhanced':
            cmd.append('--record-no-match')
        else:
            cmd.append('--record')

        # 如果指定了设备，添加指定设备参数
        if device_serial:
            cmd.extend(['--main-device', device_serial])

        logger.info(f"启动录制命令: {' '.join(cmd)}")        # 使用subprocess启动录制进程
        process = subprocess.Popen(cmd,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE,
                                  cwd=SCRIPTS_DIR,  # 使用配置中的项目根目录
                                  text=True,
                                  encoding='utf-8',
                                  errors='replace',
                                  env=dict(os.environ, PYTHONIOENCODING='utf-8'))  # 确保Python进程使用UTF-8编码

        # 这里不等待进程完成，立即返回
        return Response({
            'status': 'started',
            'message': '录制进程已启动，请在设备上操作应用。按下Ctrl+C或关闭命令窗口停止录制。',
            'pid': process.pid
        })
    except Exception as e:
        logger.error(f"启动录制脚本失败: {e}")
        return Response({'error': str(e)}, status=500)

# =====================
# 方案3实现 - run_single_replay 函数
# =====================

def check_device_available(device_serial):
    """检查设备是否可用且未被占用"""
    try:
        # 检查 adb 设备状态
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, timeout=10)
        if device_serial in result.stdout and 'device' in result.stdout:
            # 进一步检查设备是否被锁定（可根据实际情况实现）
            logger.info(f"设备 {device_serial} 状态检查通过")
            return True
        else:
            logger.warning(f"设备 {device_serial} 未在adb设备列表中找到")
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.error(f"设备 {device_serial} 状态检查失败: {e}")
    return False

def run_single_replay(device_serial, script_args, log_dir, timeout=3600, max_retries=2):
    """
    为单个设备启动回放脚本子进程，并监控其执行。
    包含完整的错误处理、重试机制和资源清理。

    Args:
        device_serial: 设备序列号
        script_args: 脚本参数列表
        log_dir: 日志目录
        timeout: 超时时间（秒）
        max_retries: 最大重试次数

    Returns:
        dict: 执行结果 {"error": "", "exit_code": 0, "report_url": "", "device": ""}
    """
    logger.info(f"🚀 开始为设备 {device_serial} 启动回放任务")

    # 0. 设备状态预检查
    if not check_device_available(device_serial):
        error_msg = f"设备 {device_serial} 不可用或被占用"
        logger.error(error_msg)
        return {
            "error": error_msg,
            "exit_code": -1,
            "report_url": "",
            "device": device_serial
        }

    # 1. 构造子进程启动命令（使用动态路径避免硬编码）
    # 使用统一的脚本查找函数定位回放脚本
    script_path = find_script_path('replay_script.py')
    if not os.path.exists(script_path):
        error_msg = f"回放脚本不存在: {script_path}"
        logger.error(error_msg)
        return {
            "error": error_msg,
            "exit_code": -1,
            "report_url": "",
            "device": device_serial
        }

    # 🔧 关键修复：确保 script_args 被正确地展开到 cmd 列表中
    # 之前的问题是 script_args 被当作一个单独的元素添加
    cmd = [sys.executable, script_path, '--log-dir', log_dir, '--device', device_serial, '--multi-device']
    cmd.extend(script_args)  # 使用 extend 正确展开参数列表

    device_log_file = os.path.join(log_dir, f"{device_serial}.log")
    result_file = os.path.join(log_dir, f"{device_serial}.result.json")

    # 🔧 重要调试：详细记录命令构造过程
    logger.info(f"🔧 设备 {device_serial} 命令构造详情:")
    logger.info(f"   Python解释器: {sys.executable}")
    logger.info(f"   脚本路径: {script_path}")
    logger.info(f"   日志目录: {log_dir}")
    logger.info(f"   设备序列号: {device_serial}")
    logger.info(f"   脚本参数: {script_args}")
    logger.info(f"   脚本参数类型: {type(script_args)}")
    logger.info(f"   脚本参数长度: {len(script_args)}")

    logger.info(f"🔧 设备 {device_serial} 完整执行命令:")

    # 打印完整命令
    # logger.info(f"🔧 设备 {device_serial} 完整执行命令:")
    # for i, arg in enumerate(cmd):
    #     logger.info(f"   cmd[{i}]: {arg}")
    logger.info(f"🔧 设备 {device_serial} 日志文件: {device_log_file}")
    logger.info(f"🔧 设备 {device_serial} 结果文件: {result_file}")
    logger.info("🔧 ==========================================")

    # 重试机制
    for attempt in range(max_retries + 1):
        log_file_handle = None
        proc = None
        try:
            logger.info(f"设备 {device_serial} 开始第 {attempt + 1} 次尝试")

            # 2. 启动子进程，关键：直接重定向到文件避免二进制内容问题
            creation_flags = 0
            preexec_fn = None
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP
            else:
                preexec_fn = os.setsid            # 🔧 修复：使用更安全的子进程启动方式，先验证参数
            logger.info(f"🔧 设备 {device_serial} 启动前验证:")
            logger.info(f"   工作目录: {os.getcwd()}")
            logger.info(f"   Python可执行: {os.path.exists(sys.executable)}")
            logger.info(f"   脚本文件存在: {os.path.exists(script_path)}")
            logger.info(f"   日志目录存在: {os.path.exists(log_dir)}")

            # 创建更详细的启动日志
            log_file_handle = open(device_log_file, 'w', encoding='utf-8', errors='replace')  # 使用'w'模式重新创建日志文件

            # 在日志文件开头写入启动信息
            log_file_handle.write(f"=== 设备 {device_serial} 回放任务启动 ===\n")
            log_file_handle.write(f"启动时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            log_file_handle.write(f"执行命令: {' '.join(cmd)}\n")
            log_file_handle.write(f"工作目录: {os.getcwd()}\n")
            log_file_handle.write(f"Python路径: {sys.executable}\n")
            log_file_handle.write(f"脚本路径: {script_path}\n")
            log_file_handle.write(f"日志目录: {log_dir}\n")
            log_file_handle.write(f"设备序列号: {device_serial}\n")
            log_file_handle.write(f"脚本参数: {script_args}\n")
            log_file_handle.write("=" * 50 + "\n")
            log_file_handle.flush()  # 确保写入文件

            # 使用更安全的进程启动方式
            proc = subprocess.Popen(
                cmd,
                stdout=log_file_handle,
                stderr=subprocess.STDOUT,
                creationflags=creation_flags,
                preexec_fn=preexec_fn,
                stdin=subprocess.DEVNULL,
                cwd=None,  # 使用当前工作目录
                env=None   # 使用当前环境变量
            )

            logger.info(f"设备 {device_serial} 子进程已启动，PID: {proc.pid}")

            # 3. 等待子进程结束，使用分阶段超时处理
            try:
                proc.wait(timeout=timeout)
                logger.info(f"设备 {device_serial} 子进程已结束，退出码: {proc.returncode}")

                # 🔧 增加：立即读取日志文件的最后几行，了解退出原因
                if log_file_handle:
                    log_file_handle.close()
                    log_file_handle = None

                try:
                    # 读取最近的日志内容
                    with open(device_log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        log_content = f.read()

                    # 获取最后10行
                    log_lines = log_content.strip().split('\n')
                    last_lines = log_lines[-10:] if len(log_lines) > 10 else log_lines
                    logger.info(f"🔍 设备 {device_serial} 日志文件最后10行:")
                    for i, line in enumerate(last_lines, 1):
                        logger.info(f"   [{i:2d}] {line}")
                except Exception as log_e:
                    logger.warning(f"读取日志文件失败: {log_e}")

                # 检查是否有明显的错误信息
                error_indicators = ['error', 'exception', 'traceback', 'failed', '错误', '异常', '失败']
                for line in reversed(log_lines):
                    if any(indicator.lower() in line.lower() for indicator in error_indicators):
                        logger.error(f"🚨 设备 {device_serial} 发现错误信息: {line}")
                        break

            except subprocess.TimeoutExpired:
                logger.warning(f"设备 {device_serial} 执行超时，尝试优雅终止")
                # 优雅终止：先尝试发送终止信号，给进程保存数据的机会
                if sys.platform == "win32":
                    proc.send_signal(signal.CTRL_BREAK_EVENT)
                    try:
                        proc.wait(timeout=10)  # 给10秒优雅退出时间
                    except subprocess.TimeoutExpired:
                        proc.kill()  # 强制终止
                else:
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                    try:
                        proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                return {
                    "error": "执行超时",
                    "exit_code": -1,
                    "report_url": "",
                    "device": device_serial
                }            # 4. 等待结果文件写入完成（避免竞争条件）
            result_wait_timeout = 30
            result_start_time = time.time()
            logger.info(f"设备 {device_serial} 等待结果文件写入: {result_file}")

            while not os.path.exists(result_file) and (time.time() - result_start_time) < result_wait_timeout:
                time.sleep(0.5)

            # 5. 读取并返回 result.json 的内容
            if os.path.exists(result_file):
                logger.info(f"🔍 设备 {device_serial} 找到结果文件: {result_file}")
                try:
                    # 多次尝试读取，确保文件写入完整
                    for read_attempt in range(3):
                        try:
                            with open(result_file, 'r', encoding='utf-8') as f:
                                content = f.read().strip()
                                logger.info(f"🔍 设备 {device_serial} 结果文件内容长度: {len(content)}")
                                logger.info(f"🔍 设备 {device_serial} 结果文件前200字符: {content[:200]}")
                                if content:  # 确保文件不为空
                                    result_data = json.loads(content)
                                    logger.info(f"🔍 设备 {device_serial} 解析后的结果数据: {result_data}")
                                    # 确保返回数据包含设备信息
                                    result_data["device"] = device_serial
                                    logger.info(f"✅ 设备 {device_serial} 执行完成，退出码: {result_data.get('exit_code', 'unknown')}")
                                    return result_data
                                else:
                                    logger.warning(f"⚠️ 设备 {device_serial} 结果文件为空，尝试 {read_attempt + 1}/3")
                        except (json.JSONDecodeError, ValueError) as e:
                            logger.warning(f"❌ 设备 {device_serial} 结果文件解析失败，尝试 {read_attempt + 1}/3: {e}")
                            if read_attempt < 2:
                                time.sleep(1)  # 等待文件写入完成
                            else:
                                raise

                    # 如果所有尝试都失败，检查日志文件获取更多信息
                    error_details = ""
                    if os.path.exists(device_log_file):
                        try:
                            with open(device_log_file, 'r', encoding='utf-8', errors='replace') as f:
                                log_content = f.read()
                                # 提取最后几行作为错误详情
                                log_lines = log_content.strip().split('\n')
                                error_details = '\n'.join(log_lines[-5:]) if log_lines else "日志文件为空"
                        except Exception as e:
                            error_details = f"无法读取日志文件: {e}"

                    return {
                        "error": f"结果文件为空或格式错误。日志详情: {error_details}",
                        "exit_code": proc.returncode,
                        "report_url": "",
                        "device": device_serial
                    }
                except (json.JSONDecodeError, ValueError) as e:
                    if attempt < max_retries:
                        logger.warning(f"设备 {device_serial} 结果文件格式错误，重试 {attempt + 1}/{max_retries}: {e}")
                        time.sleep(2)  # 重试前等待
                        continue
                    return {
                        "error": f"结果文件格式错误: {str(e)}",
                        "exit_code": proc.returncode,
                        "report_url": "",
                        "device": device_serial
                    }
            else:
                logger.error(f"设备 {device_serial} 未找到结果文件: {result_file}")
                # 🔧 增强：更详细的错误诊断
                error_details = ""
                script_execution_status = ""

                if os.path.exists(device_log_file):
                    try:
                        with open(device_log_file, 'r', encoding='utf-8', errors='replace') as f:
                            log_content = f.read()
                            log_lines = log_content.strip().split('\n')

                            # 查找脚本执行相关的关键信息
                            key_lines = []
                            for line in log_lines:
                                if any(keyword in line.lower() for keyword in [
                                    'error', 'exception', 'traceback', 'failed', 'success',
                                    'script', 'device', 'exit', 'complete', '错误', '异常', '失败', '成功'
                                ]):
                                    key_lines.append(line)

                            if key_lines:
                                script_execution_status = f"\n关键执行信息:\n" + '\n'.join(key_lines[-5:])

                            # 提取最后几行作为错误详情
                            error_details = '\n'.join(log_lines[-15:]) if log_lines else "日志文件为空"

                    except Exception as e:
                        error_details = f"无法读取日志文件: {e}"
                else:
                    error_details = "日志文件不存在"

                full_error_msg = f"未找到结果文件，子进程退出码: {proc.returncode}。{script_execution_status}\n\n最后15行日志:\n{error_details}"

                if attempt < max_retries:
                    logger.warning(f"设备 {device_serial} 未找到结果文件，重试 {attempt + 1}/{max_retries}。错误详情: {full_error_msg}")
                    time.sleep(2)
                    continue

                return {
                    "error": full_error_msg,
                    "exit_code": proc.returncode,
                    "report_url": "",
                    "device": device_serial
                }

        except Exception as e:
            if attempt < max_retries:
                logger.warning(f"设备 {device_serial} 执行异常，重试 {attempt + 1}/{max_retries}: {e}")
                time.sleep(2)
                continue
            logger.error(f"设备 {device_serial} 执行失败: {e}")
            return {
                "error": f"执行异常: {str(e)}",
                "exit_code": -1,
                "report_url": "",
                "device": device_serial
            }
        finally:
            # 确保资源清理
            if log_file_handle:
                try:
                    log_file_handle.close()
                except:
                    pass
            if proc and proc.poll() is None:
                try:
                    if sys.platform == "win32":
                        proc.kill()
                    else:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except:
                    pass


# =====================
# 多设备并发回放主API
# =====================

@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def replay_script(request):
    """多设备并发回放指定的测试脚本"""
    try:
        data = json.loads(request.body)
        logger.info(f"收到多设备并发回放请求: {data}")

        # 1. 检查或获取设备参数
        devices = data.get('devices')
        if not devices:
            # 自动获取已连接设备列表
            try:
                result = run_subprocess_utf8(['adb', 'devices'], capture_output=True, check=True)
                lines = result.stdout.strip().split('\n')[1:]
                devices = [line.split()[0] for line in lines if line.strip() and 'device' in line]
            except Exception as e:
                return JsonResponse({'success': False, 'message': f'获取设备列表失败: {e}'}, status=500)
            if not devices:
                return JsonResponse({'success': False, 'message': '未检测到可用设备'}, status=400)

        # 2. 检查脚本参数，兼容scripts数组和script_path参数
        script_configs = data.get('scripts', [])
        if not script_configs and data.get('script_path'):
            # 兼容旧版API，将script_path转换为scripts数组
            script_configs = [{
                'path': data.get('script_path'),
                'loop_count': data.get('loop_count'),
                'max_duration': data.get('max_duration')
            }]

        # 检查是否指定了脚本
        if not script_configs:
            return JsonResponse({
                'success': False,
                'message': '未提供脚本路径'
            }, status=400)

        # 3. 脚本路径规范化处理
        for config in script_configs:
            script_path = config.get('path')
            if not script_path:
                return JsonResponse({
                    'success': False,
                    'message': '脚本配置中缺少path参数'
                }, status=400)

            # 规范化脚本路径 - 类似edit_script函数中的处理
            path_input = script_path.strip()

            # 处理相对路径
            if not os.path.isabs(path_input):
                # 简单文件名直接放入测试用例目录
                if os.sep not in path_input and '/' not in path_input:
                    path_input = os.path.join(TESTCASE_DIR, path_input)
                elif path_input.lower().startswith(('testcase', 'testcase\\', 'testcase/')):
                    # 去掉"testcase"前缀
                    if path_input.lower() == 'testcase':
                        path_input = TESTCASE_DIR
                    else:
                        subpath = path_input[len('testcase'):].lstrip('\\/') if path_input.lower().startswith('testcase') else path_input[len('testcase\\'):] if path_input.lower().startswith('testcase\\') else path_input[len('testcase/'):]
                        path_input = os.path.join(TESTCASE_DIR, subpath)
                else:
                    # 其他相对路径，视为相对于测试用例目录的路径
                    path_input = os.path.join(TESTCASE_DIR, path_input)

            # 绝对路径但是JSON文件，则确保在标准测试用例目录中
            elif path_input.lower().endswith('.json'):
                filename = os.path.basename(path_input)
                # 如果不在标准测试用例目录中，则使用文件名并放入标准目录
                if not path_input.startswith(TESTCASE_DIR):
                    path_input = os.path.join(TESTCASE_DIR, filename)

            # 规范化路径
            path_input = os.path.normpath(path_input)

            # 检查文件是否存在
            if not os.path.exists(path_input):
                return JsonResponse({
                    'success': False,
                    'message': f'脚本文件不存在: {path_input}'
                }, status=404)

            # 更新配置中的路径
            config['path'] = path_input

        # 4. 创建日志目录
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_dir_name = f"multi_device_replay_{timestamp}"
        log_dir = os.path.join(DEVICE_REPORTS_DIR, log_dir_name)
        os.makedirs(log_dir, exist_ok=True)
        # logger.info(f"创建日志目录: {log_dir}")

        # 5. 创建任务并获取任务ID
        task_id = task_manager.create_task(devices, script_configs, log_dir)
        logger.info(f"创建任务: {task_id}")        # 6. 账号预分配（集成现有账号管理器）
        from .account_manager import get_account_manager
        account_manager = get_account_manager()

        device_accounts = {}
        account_allocation_errors = []

        for device_serial in devices:
            try:
                # 调用现有的账号管理器接口
                allocated_account = account_manager.allocate_account(device_serial)
                if allocated_account:
                    device_accounts[device_serial] = {
                        'username': allocated_account[0],
                        'password': allocated_account[1]
                    }
                else:
                    account_allocation_errors.append(f"设备 {device_serial} 账号分配失败")
            except Exception as e:
                account_allocation_errors.append(f"设备 {device_serial} 账号分配异常: {str(e)}")

        # 如果有账号分配失败，取消任务并返回错误
        if account_allocation_errors:
            task_manager.update_task_status(task_id, TaskStatus.FAILED,
                                          error_message="账号分配失败")
            return JsonResponse({
                "success": False,
                "task_id": task_id,
                "error": "账号分配失败",
                "details": account_allocation_errors
            }, status=400)

        # 6. 构造每个设备的任务参数
        device_tasks = {}
        for device_serial in devices:
            account_info = device_accounts[device_serial]
            script_args = []

            # 🔧 调试日志：记录脚本配置
            logger.info(f"🔍 设备 {device_serial} 开始构造任务参数")
            logger.info(f"🔍 账号信息: {account_info['username']}")
            logger.info(f"🔍 脚本配置数量: {len(script_configs)}")

            # 添加脚本参数
            for i, config in enumerate(script_configs):
                logger.info(f"🔍 处理脚本配置 {i+1}: {config}")
                script_args.extend(['--script', config['path']])
                logger.info(f"🔍 添加脚本路径: {config['path']}")

                # 添加循环次数
                loop_count = config.get('loop_count')
                if loop_count:
                    script_args.extend(['--loop-count', str(loop_count)])
                    logger.info(f"🔍 添加循环次数: {loop_count}")

                # 添加最大持续时间
                max_duration = config.get('max_duration')
                if max_duration:
                    script_args.extend(['--max-duration', str(max_duration)])
                    logger.info(f"🔍 添加最大持续时间: {max_duration}")

            # 添加账号信息
            script_args.extend(['--account-user', account_info['username']])
            script_args.extend(['--account-pass', account_info['password']])
            logger.info(f"🔍 添加账号参数: {account_info['username']}")

            device_tasks[device_serial] = script_args
            logger.info(f"🔍 设备 {device_serial} 最终参数: {script_args}")
            logger.info(f"🔍 参数总数: {len(script_args)}")
            logger.info(f"🔍 ===== 设备 {device_serial} 参数构造完成 =====")
            logger.info("")

        # 7. 动态计算最佳并发数
        cpu_count = os.cpu_count() or 4
        try:
            memory_gb = psutil.virtual_memory().total / (1024**3)
            # 基于系统资源计算合理并发数
            cpu_based_limit = cpu_count * 2  # CPU核心数的2倍
            memory_based_limit = int(memory_gb / 0.5)  # 每个任务预估占用500MB内存
            system_based_limit = min(cpu_based_limit, memory_based_limit, 32)  # 系统限制最大32
        except ImportError:
            # 如果无法获取psutil，使用保守估计
            system_based_limit = min(cpu_count * 2, 16)

        max_concurrent = min(system_based_limit, len(devices), data.get('max_concurrent', system_based_limit))
        logger.info(f"计算得出最大并发数: {max_concurrent} (设备数: {len(devices)})")

       # 8. 并发执行回放任务
        results = {}
        completed_count = 0

        logger.info(f"🚀 开始并发执行回放任务，最大并发数: {max_concurrent}")
        log_step_progress(1, 4, f"开始并发执行 {len(devices)} 个设备的回放任务", None, True)
        try:
            with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
                # 🔧 调试：在提交任务前记录每个设备的参数
                logger.info(f"🔧 即将提交 {len(device_tasks)} 个设备任务:")
                for device, args in device_tasks.items():
                    logger.info(f"   设备: {device}")
                    logger.info(f"   参数: {args}")
                    logger.info(f"   参数数量: {len(args)}")

                # 提交所有任务
                futures = {
                    executor.submit(run_single_replay, device, args, log_dir): device
                    for device, args in device_tasks.items()
                }

                logger.info(f"🔧 已提交 {len(futures)} 个任务到线程池")
                log_step_progress(2, 4, f"所有设备任务已提交，等待执行完成", None, True)

                # 等待任务完成并收集结果
                pending_count = len(futures)
                successful_devices = []
                failed_devices = []
                device_results = {}
                device_dirs = []  # 收集设备报告目录用于汇总报告

                # 收集设备结果
                for future in concurrent.futures.as_completed(futures):
                    device = futures[future]
                    try:
                        result = future.result()
                        results[device] = result
                        completed_count += 1

                        # 从结果中获取设备报告目录
                        device_dir = result.get('device_report_dir')
                        if device_dir:
                            # 收集有效的设备报告目录
                            if os.path.exists(device_dir):
                                device_dirs.append(device_dir)
                                logger.info(f"收集到设备 {device} 的报告目录: {device_dir}")
                            else:
                                logger.warning(f"设备 {device} 的报告目录不存在: {device_dir}")

                        # 如果没有获取到设备目录，尝试从report_url中获取
                        elif result.get('report_url'):
                            report_url = result.get('report_url')
                            # 如果report_url包含路径信息
                            if isinstance(report_url, str) and os.path.exists(report_url):
                                device_dirs.append(report_url)
                                logger.info(f"从report_url收集到设备 {device} 的报告目录: {report_url}")

                        # 记录退出码
                        exit_code = result.get('exit_code')
                        success = (exit_code == 0)
                        status_text = "成功" if success else "失败"
                        logger.info(f"✅ 设备 {device} 回放{status_text} ({completed_count}/{len(devices)})")

                        # 添加到结果数据结构
                        device_results[device] = {
                            'exit_code': exit_code,
                            'status': "success" if success else "failed",
                            'report_url': result.get('report_url')
                        }

                        # 记录设备统计信息
                        log_step_progress(len(devices) - pending_count + 1, len(devices) + 2,
                                          f"设备 {device} 执行{status_text}", device, True)

                        # 更新成功/失败设备计数
                        if success:
                            successful_devices.append(device)
                        else:
                            failed_devices.append(device)
                    except Exception as e:
                        logger.error(f"❌ 设备 {device} 执行异常: {e}")
                        device_results[device] = {
                            'exit_code': -1,
                            'status': 'error',
                            'error': str(e)
                        }
                        failed_devices.append(device)
                        completed_count += 1

                    # 减少待处理计数
                    pending_count -= 1

            # 记录日志和统计
            logger.info(f"[多设备] 步骤 3/4: 所有设备任务执行完成")

            # 释放所有设备的账号分配
            for device in devices:
                try:
                    device_name = device if isinstance(device, str) else device.get('serial')
                    if device_name and device_name in device_accounts:
                        account_info = device_accounts.get(device_name)
                        username = account_info.get('username')
                        print(f"释放设备 {device_name} 的账号分配: {username}")
                        account_manager.release_account(device_name)
                        logger.info(f"已释放设备 {device_name} 的账号")
                except Exception as e:
                    logger.warning(f"释放设备账号时出错: {e}")

            # 生成汇总报告 - 在所有设备完成后由主进程统一生成
            if device_dirs and len(device_dirs) > 0:
                try:
                    # 导入报告生成器
                    from apps.reports.report_generator import ReportGenerator
                    from apps.reports.report_manager import ReportManager

                    # 初始化报告管理器
                    report_manager = ReportManager()
                    report_generator = ReportGenerator(report_manager)

                    logger.info(f"📊 所有设备测试完成，开始生成统一汇总报告...")

                    # 将字符串路径转换为Path对象
                    from pathlib import Path
                    device_report_paths = []

                    # 验证设备目录是否存在
                    for dir_path in device_dirs:
                        path = Path(dir_path)
                        if path.exists():
                            device_report_paths.append(path)
                            logger.info(f"✅ 设备目录存在: {path}")
                        else:
                            logger.warning(f"⚠️ 设备目录不存在: {path}")

                    # 如果没有有效的设备目录，尝试查找最新的设备目录
                    if not device_report_paths:
                        logger.warning("⚠️ 没有有效的设备目录，尝试查找最新的设备目录...")
                        base_dir = report_manager.single_device_reports_dir
                        if base_dir.exists():
                            # 查找所有设备目录
                            all_device_dirs = [d for d in base_dir.iterdir() if d.is_dir()]
                            if all_device_dirs:
                                # 按修改时间排序，选择最近的目录
                                device_report_paths = sorted(all_device_dirs, key=lambda x: x.stat().st_mtime, reverse=True)[:len(devices)]
                                logger.info(f"✅ 找到 {len(device_report_paths)} 个最新设备目录")

                    # 准备脚本配置
                    script_info_list = []
                    for config in script_configs:
                        script_info_list.append({
                            "path": config.get("path", ""),
                            "loop_count": config.get("loop_count", 1),
                            "max_duration": config.get("max_duration")
                        })

                    # 1. 首先为每个设备目录生成设备报告
                    for device_dir in device_report_paths:
                        logger.info(f"🔄 为设备 {device_dir.name} 生成设备报告...")
                        report_generator.generate_device_report(device_dir, script_info_list)

                    # 2. 然后生成汇总报告
                    summary_report_path = report_generator.generate_summary_report(device_report_paths, script_info_list)

                    if summary_report_path:
                        logger.info(f"✅ 统一汇总报告生成成功: {summary_report_path}")
                    else:
                        logger.error("❌ 统一汇总报告生成失败")
                except Exception as e:
                    logger.error(f"❌ 生成统一汇总报告失败: {e}")
                    import traceback
                    traceback.print_exc()

            # 生成设备执行摘要
            logger.info("============================================================")

        finally:
            # 9. 资源清理：释放账号
            for device_serial in devices:
                if device_serial in device_accounts:
                    try:
                        account_manager.release_account(device_serial)
                        logger.info(f"已释放设备 {device_serial} 的账号")
                    except Exception as e:
                        logger.warning(f"设备 {device_serial} 账号释放失败: {e}")

        # 10. 确保所有设备都有结果记录
        for device in devices:
            if device not in results:
                results[device] = {
                    "error": "任务未执行或丢失",
                    "exit_code": -1,
                    "report_url": "",
                    "device": device,
                    "log_url": f"/static/reports/{log_dir_name}/{device}.log"
                }

        # 11. 构建响应数据，使用先前创建的 task_id
        response_data = {
            "success": True,
            "task_id": task_id,
            "message": f"多设备并发回放完成，共处理 {len(devices)} 台设备",
            "log_dir": log_dir,
            "results": []
        }
        # 转换结果格式
        for device, result in results.items():
            device_result = {
                "device": device,
                "status": "completed" if result.get("exit_code") == 0 else "failed",
                "exit_code": result.get("exit_code", -1),
                "report_url": result.get("report_url", ""),
                "log_url": f"/static/reports/{log_dir_name}/{device}.log",
                "error": result.get("error", "")
            }
            response_data["results"].append(device_result)

        # 生成设备执行汇总日志
        log_device_summary(list(results.values()))
        log_step_progress(4, 4, f"任务完成，成功: {sum(1 for r in results.values() if r.get('exit_code') == 0)}/{len(devices)}", None, True)

        logger.info(f"多设备并发回放任务完成: {len(devices)} 台设备，成功: {sum(1 for r in results.values() if r.get('exit_code') == 0)}")
        return JsonResponse(response_data)

    except Exception as e:
        error_msg = str(e)
        logger.error(f"多设备并发回放失败: {error_msg}")
        logger.error(f"详细错误信息: {traceback.format_exc()}")

        return JsonResponse({
            'success': False,
            'message': f'多设备并发回放失败: {error_msg}'
        }, status=500)

@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def debug_script(request):
    """
    执行调试命令，支持调试和录制功能

    Args:
        request: 包含command参数的POST请求

    Returns:
        JsonResponse: 操作结果
    """
    try:
        data = json.loads(request.body)
        command_str = data.get('command')

        if not command_str:
            return JsonResponse({'success': False, 'message': '未提供命令'}, status=400)

        logger.info(f"Received command string for debug: {command_str}")

        python_exec = get_persistent_python_path()
        logger.info(f"Using Python interpreter: {python_exec} from project_root: {SCRIPTS_DIR}")

        # 在记录原始命令后，规范化命令中的Windows路径格式
        if platform.system() == "Windows":
            # 检查是否包含可能格式不正确的Windows路径
            if ':' in command_str and ('\\' not in command_str or '/' not in command_str):
                # 导入re模块
                import re

                # 检测是否是一个已知的特殊格式路径 - 例如F:QASoftwareanaconda3envspy39_yolov10python.exe
                if "anaconda3envspy39_yolov10" in command_str.replace("\\", "").replace("/", ""):
                    # 这是Python路径，尝试直接转换为标准格式
                    parts = command_str.split(' ')
                    python_part = parts[0]
                    if ":" in python_part and ".exe" in python_part:
                        # 使用README中指定的Python路径
                        python_path = python_exec

                        # 重新组合完整命令
                        if len(parts) > 1:
                            normalized_command = f"{python_path} {' '.join(parts[1:])}"
                        else:
                            normalized_command = python_path

                        logger.info(f"命令路径已规范化 (Python解释器): {command_str} -> {normalized_command}")
                        command_str = normalized_command
                else:
                    # 处理命令中可能的其他Windows路径问题
                    normalized_command = command_str

                    # 修复驱动器字母后的反斜杠
                    normalized_command = re.sub(r'([A-Za-z]:)([^\\\/])', r'\1\\\2', normalized_command)

                    # 替换命令中的空格为路径分隔符（如果看起来像路径）
                    if ' ' in normalized_command and not normalized_command.startswith('"'):
                        parts = normalized_command.split(' ')
                        for i in range(len(parts) - 1):
                            # 如果当前部分以冒号结尾或包含路径分隔符，且下一部分不以-或/开头
                            if ((parts[i].endswith(':') or '\\' in parts[i]) and
                                i + 1 < len(parts) and
                                not parts[i+1].startswith(('-', '/'))):
                                parts[i] = parts[i] + '\\'

                        normalized_command = ' '.join(parts)

                    # 修复可能的连续分隔符
                    while '\\\\' in normalized_command:
                        normalized_command = normalized_command.replace('\\\\', '\\')
                    while '//' in normalized_command:
                        normalized_command = normalized_command.replace('//', '/')

                    if normalized_command != command_str:
                        logger.info(f"命令路径已规范化: {command_str} -> {normalized_command}")
                        command_str = normalized_command

        # Split the command string into arguments
        # On Windows, shlex.split is better for handling paths with spaces if not already quoted
        try:
            if platform.system() == "Windows":
                import shlex
                # 确保Windows路径中的反斜杠被保留，先替换反斜杠为特殊标记，然后再还原
                command_str_processed = command_str.replace("\\", "___BACKSLASH___")
                args = shlex.split(command_str_processed)
                args = [arg.replace("___BACKSLASH___", "\\") for arg in args]

                # 对于第一个参数，如果是Python可执行文件路径，确保格式正确
                if args and args[0].endswith("python.exe"):
                    # 直接使用get_persistent_python_path()函数获取的Python路径
                    args[0] = python_exec
                    logger.info(f"Python路径已替换为配置路径: {python_exec}")
            else:
                args = command_str.split() # Simpler split for non-Windows
        except Exception as e:
            logger.error(f"Error splitting command string '{command_str}': {e}")
            args = command_str.split() # Fallback to simple split

        logger.info(f"Command args before modification: {args}")

        # Ensure the first argument is the correct Python executable
        # And the second argument (script) is found relative to project_root if not absolute
        if args:
            # Check if the first arg is a python script or 'python' keyword
            if args[0].lower() == 'python' or args[0].endswith('.py'):                # 获取Python解释器路径
                python_executable = python_exec.replace('\\', '\\\\')  # 确保反斜杠被正确处理
                logger.info(f"Using Python executable: {python_executable}")

                if args[0].lower() == 'python': # e.g., "python record_script.py ..."
                    script_name_arg_index = 1
                    args[0] = python_executable # Replace 'python' with full path
                    # 插入 -u 参数以强制无缓冲输出，确保实时日志显示
                    args.insert(1, "-u")
                    script_name_arg_index = 2  # 脚本索引现在是2
                else: # e.g., "record_script.py ..." or "path/to/script.py ..."
                    script_name_arg_index = 0
                    # Prepend python_exec if script.py is the first argument
                    args.insert(0, python_executable)
                    # 插入 -u 参数以强制无缓冲输出，确保实时日志显示
                    args.insert(1, "-u")
                    script_name_arg_index = 2  # 脚本索引现在是2

                # Ensure the script path itself is correct
                if len(args) > script_name_arg_index:
                    script_file_part = args[script_name_arg_index]
                    logger.info(f"脚本文件路径: {script_file_part}")

                    if not os.path.isabs(script_file_part):
                        # 使用辅助函数查找脚本
                        script_path = find_script_path(script_file_part)
                        args[script_name_arg_index] = script_path
                        logger.info(f"找到脚本: {script_path}")
                    # If it was absolute, assume it's correct or will fail naturally
            else:
                # Command does not start with python or a .py file, assume it's a full path to an executable
                # or a system command. For safety, if it's not an absolute path, it might be an issue.
                if not os.path.isabs(args[0]) and not shutil.which(args[0]):
                    logger.warning(f"Command '{args[0]}' is not absolute and not found in PATH. Execution may fail.")

        logger.info(f"Executing command with args: {args}, cwd: {SCRIPTS_DIR}")        # 在执行前记录构建的命令路径
        if len(args) >= 2:
            # 检查args[1]是否是一个Python脚本
            if args[1].endswith('.py'):
                script_path = args[1]
                if not os.path.exists(script_path) or not os.path.isabs(script_path):
                    # 使用辅助函数查找脚本
                    script_basename = os.path.basename(script_path)
                    new_script_path = find_script_path(script_basename)
                    args[1] = new_script_path
                    logger.info(f"脚本路径已更新为: {new_script_path}")
        process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False, # Important: shell=False when args is a list
            text=True, # Use text=True for universal_newlines=True behavior
            encoding='utf-8', errors='replace', # Be explicit about encoding
            cwd=SCRIPTS_DIR,  # 使用配置中的项目根目录
            bufsize=1,  # 行缓冲，提高实时性
            env=dict(os.environ, PYTHONIOENCODING='utf-8')  # 确保Python进程使用UTF-8编码
        )

        process_id = str(process.pid)
        CHILD_PROCESSES[process_id] = process
        # Non-blocking output reading
        def read_output_thread_func(proc, pid):
            try:
                stdout, stderr = proc.communicate()
                if stdout:
                    logger.info(f"[PID:{pid}] STDOUT: {stdout.strip()}")

                if stderr:
                    logger.error(f"[PID:{pid}] STDERR: {stderr.strip()}")
            except Exception as e_thread:
                logger.error(f"[PID:{pid}] Exception in read_output_thread: {e_thread}")
            finally:
                CHILD_PROCESSES.pop(pid, None)
                logger.info(f"[PID:{pid}] Process finished and removed from CHILD_PROCESSES.")

        thread = threading.Thread(target=read_output_thread_func, args=(process, process_id))
        thread.daemon = True
        thread.start()

        return JsonResponse({'success': True, 'message': f'命令已启动，进程ID: {process_id}'})

    except FileNotFoundError as fnf_error:
        logger.error(f"执行命令失败 (FileNotFoundError): {str(fnf_error)}. Command: {command_str if 'command_str' in locals() else 'unknown'}, Args: {args if 'args' in locals() else 'unknown'}")
        return JsonResponse({'success': False, 'message': f'执行命令失败: 文件未找到 - {str(fnf_error)}'}, status=500)
    except Exception as e:
        logger.error(f"执行命令失败: {str(e)}. Command: {command_str if 'command_str' in locals() else 'unknown'}")
        return JsonResponse({'success': False, 'message': f'执行命令失败: {str(e)}'}, status=500)

@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def start_record(request):
    """
    开始录制 - 执行record_script.py --record
    """
    try:
        # 获取Python解释器路径
        python_exec = get_persistent_python_path()

        # 获取record_script.py的绝对路径
        record_script_path = find_script_path("record_script.py")

        # 组装命令
        cmd = [
            python_exec,
            record_script_path,
            "--record"
        ]

        logger.info(f"启动录制命令: {' '.join(cmd)}")        # 启动录制进程
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=SCRIPTS_DIR,  # 使用配置中的项目根目录
            text=True,
            encoding='utf-8',
            errors='replace',
            env=dict(os.environ, PYTHONIOENCODING='utf-8')  # 确保Python进程使用UTF-8编码
        )

        # 存储进程对象，以便后续管理
        process_id = str(process.pid)
        CHILD_PROCESSES[process_id] = process        # 创建线程读取输出，避免缓冲区满
        def read_output(stream, log_func):
            try:
                for line in iter(stream.readline, ''):
                    if line:
                        # 确保正确处理中文字符
                        line_str = line.strip()
                        try:
                            # 如果是字节类型，解码为字符串
                            if isinstance(line_str, bytes):
                                line_str = line_str.decode('utf-8', errors='replace')
                            log_func(f"录制输出: {line_str}")
                        except UnicodeDecodeError:
                            log_func(f"录制输出: {repr(line_str)}")
            except Exception as e:
                logger.error(f"读取录制输出流时出错: {e}")
            finally:
                stream.close()

        # 启动输出读取线程
        stdout_thread = threading.Thread(target=read_output, args=(process.stdout, logger.info))
        stderr_thread = threading.Thread(target=read_output, args=(process.stderr, logger.error))
        stdout_thread.daemon = True
        stderr_thread.daemon = True
        stdout_thread.start()
        stderr_thread.start()

        return JsonResponse({
            'success': True,
            'message': f'录制进程已启动，进程ID: {process_id}',
            'process_id': process_id
        })

    except Exception as e:
        logger.error(f"启动录制功能时出错: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'启动录制失败: {str(e)}'
        }, status=500)

@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def import_script(request):
    """
    导入脚本JSON文件
    """
    if 'file' not in request.FILES:
        return JsonResponse({
            'success': False,
            'message': '没有提供文件'
        }, status=400)

    try:
        uploaded_file = request.FILES['file']

        # 检查文件扩展名
        if not uploaded_file.name.endswith('.json'):
            return JsonResponse({
                'success': False,
                'message': '只支持JSON文件'
            }, status=400)

        # 检查是否是有效的JSON和获取步骤数
        try:
            content = uploaded_file.read()
            uploaded_file.seek(0)  # 重置文件指针
            json_content = json.loads(content.decode('utf-8'))
            step_count = len(json_content.get('steps', []))
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': '无效的JSON文件'
            }, status=400)

        # 保存文件到testcase目录
        target_dir = TESTCASE_DIR  # 使用配置中的testcase目录

        # 确保目录存在
        os.makedirs(target_dir, exist_ok=True)

        # 构建文件保存路径
        file_path = os.path.join(target_dir, uploaded_file.name)

        # 如果文件已存在，添加时间戳避免覆盖
        if os.path.exists(file_path):
            name, ext = os.path.splitext(uploaded_file.name)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            new_name = f"{name}_{timestamp}{ext}"
            file_path = os.path.join(target_dir, new_name)
            filename = new_name
        else:
            filename = uploaded_file.name

        # 写入文件
        with open(file_path, 'wb') as f:
            f.write(content)

        # 获取文件大小
        file_size = os.path.getsize(file_path)

        # 确定脚本类型（基于文件内容判断）
        script_type = 'manual'  # 默认为手动

        # 尝试获取当前用户
        try:
            user = request.user if request.user.is_authenticated else None
        except:
            user = None

        # 尝试从请求数据中获取分类和描述
        category_id = request.POST.get('category')
        description = request.POST.get('description', '')

        # 获取分类
        category = None
        if category_id:
            try:
                category = ScriptCategory.objects.get(id=category_id)
            except:
                pass

        # 保存到数据库
        script_file = ScriptFile.objects.create(
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            step_count=step_count,
            type=script_type,
            category=category,
            description=description,
            uploaded_by=user
        )

        return JsonResponse({
            'success': True,
            'message': f'文件已保存到: {os.path.basename(file_path)}',
            'file_path': file_path,
            'file_name': os.path.basename(file_path),
            'script_id': script_file.id
        })
    except Exception as e:
        error_msg = str(e)
        if not error_msg:
            error_msg = "未知错误"

        print(f"导入脚本错误: {error_msg}")

        return JsonResponse({
            'success': False,
            'message': f'导入脚本失败: {error_msg}'
        }, status=500)

class ScriptCategoryViewSet(viewsets.ModelViewSet):
    """
    脚本分类管理视图集

    提供脚本分类的CRUD操作
    """
    queryset = ScriptCategory.objects.all()
    serializer_class = ScriptCategorySerializer
    permission_classes = [AllowAny]
    http_method_names = ['post']

    def get_queryset(self):
        """
        根据查询参数过滤分类列表
        """
        queryset = ScriptCategory.objects.all()
        name = self.request.query_params.get('name', None)

        if name:
            queryset = queryset.filter(name__icontains=name)

        return queryset

    def perform_create(self, serializer):
        """
        创建分类并记录日志
        """
        serializer.save()
        logger.info(
            f"脚本分类已创建: {serializer.instance.name} - 用户: {self.request.user.username}"
        )


class ScriptViewSet(viewsets.ModelViewSet):
    """
    脚本管理视图集

    提供脚本的CRUD操作和执行功能
    """
    queryset = Script.objects.all()
    serializer_class = ScriptSerializer
    permission_classes = [AllowAny]
    http_method_names = ['post']

    def get_serializer_class(self):
        """
        根据操作类型返回不同的序列化器
        """
        if self.action == 'create':
            return ScriptCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ScriptUpdateSerializer
        return ScriptSerializer

    def get_queryset(self):
        """
        根据查询参数过滤脚本列表
        """
        queryset = Script.objects.all()

        # 名称过滤
        name = self.request.query_params.get('name')
        if name:
            queryset = queryset.filter(name__icontains=name)

        # 类型过滤
        script_type = self.request.query_params.get('type')
        if script_type:
            queryset = queryset.filter(type=script_type)

        # 分类过滤
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__id=category)

        # 状态过滤（是否激活）
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            is_active = is_active.lower() == 'true'
            queryset = queryset.filter(is_active=is_active)

        # 加入日志过滤
        include_in_log = self.request.query_params.get('include_in_log')
        if include_in_log is not None:
            include_in_log = include_in_log.lower() == 'true'
            queryset = queryset.filter(include_in_log=include_in_log)

        return queryset

    def perform_create(self, serializer):
        """
        创建脚本时设置作者为当前用户
        """
        serializer.save(author=self.request.user)
        logger.info(
            f"脚本已创建: {serializer.instance.name} - 用户: {self.request.user.username}"
        )

    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """
        执行脚本

        创建脚本执行记录并更新执行次数
        """
        script = self.get_object()

        # 检查脚本是否启用
        if not script.is_active:
            return Response(
                {"error": _("无法执行未启用的脚本")},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            # 创建执行记录
            execution = ScriptExecution.objects.create(
                script=script,
                status='running',
                start_time=datetime.now(),
                executed_by=request.user
            )

            # 更新脚本执行次数
            script.execution_count += 1
            script.save(update_fields=['execution_count'])

        # 这里应该有实际的脚本执行逻辑，可能通过异步任务处理
        # 为了演示，我们假设脚本执行成功

        serializer = ScriptExecutionSerializer(execution)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def executions(self, request, pk=None):
        """
        获取脚本的执行历史记录
        """
        script = self.get_object()
        executions = script.executions.all()

        # 分页
        page = self.paginate_queryset(executions)
        if page is not None:
            serializer = ScriptExecutionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ScriptExecutionSerializer(executions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """
        启用/禁用脚本
        """
        script = self.get_object()
        script.is_active = not script.is_active
        script.save(update_fields=['is_active'])

        status = "启用" if script.is_active else "禁用"
        logger.info(f"脚本已{status}: {script.name} - 用户: {request.user.username}")

        return Response({
            "id": script.id,
            "name": script.name,
            "is_active": script.is_active
        })

    def create(self, request, *args, **kwargs):
        """
        创建新脚本 - 也用于获取脚本列表API
        当使用POST /api/scripts/ 且没有传递名称时，返回脚本列表
        """
        # 如果请求体为空或缺少必填字段，认为是获取脚本列表的请求
        data = request.data
        name = data.get('name')
        content = data.get('content')

        # 只需检查testcase目录返回脚本列表
        if not name or not content:
            try:
                # 确保目录存在
                os.makedirs(TESTCASE_DIR, exist_ok=True)
                logger.info(f"获取脚本列表，扫描目录: {TESTCASE_DIR}")

                scripts = []
                for f in os.listdir(TESTCASE_DIR):
                    if f.endswith('.json'):
                        script_path = os.path.join(TESTCASE_DIR, f)
                        try:
                            with open(script_path, 'r', encoding='utf-8') as script_file:
                                script_data = json.load(script_file)
                                scripts.append({
                                    'filename': f,
                                    'path': f,  # 关键修复：只返回文件名
                                    'created': datetime.fromtimestamp(os.path.getctime(script_path)).strftime('%Y-%m-%d %H:%M:%S'),
                                    'step_count': len(script_data.get('steps', [])),
                                    'category': '未分类',
                                    'type': '文件',
                                    'description': ''
                                })
                        except Exception as e:
                            logger.warning(f"读取脚本文件 {f} 失败: {str(e)}")

                # 按创建时间排序
                scripts.sort(key=lambda x: x['created'], reverse=True)
                logger.info(f"找到 {len(scripts)} 个脚本文件")
                return Response({'scripts': scripts})
            except Exception as e:
                logger.error(f"获取脚本列表失败: {str(e)}")
                return Response({'error': str(e), 'scripts': []}, status=500)

        # 如果有name和content，按原逻辑创建脚本
        return super().create(request, *args, **kwargs)


class ScriptVersionViewSet(viewsets.ReadOnlyModelViewSet):
    """脚本版本视图集 - 只读"""
    queryset = ScriptVersion.objects.all()
    serializer_class = ScriptVersionSerializer
    permission_classes = [AllowAny]
    http_method_names = ['post']

    def get_queryset(self):
        """
        根据查询参数过滤脚本版本列表
        """
        queryset = ScriptVersion.objects.all()

        # 脚本过滤
        script_id = self.request.query_params.get('script')
        if script_id:
            queryset = queryset.filter(script_id=script_id)

        return queryset


class CloneScriptView(views.APIView):
    """克隆脚本"""
    permission_classes = [permissions.AllowAny]  # 允许所有用户访问

    def post(self, request, pk):
        # 获取源脚本
        source_script = get_object_or_404(Script, pk=pk)

        # 创建新脚本对象
        new_script = Script.objects.create(
            name=f"{source_script.name} - 副本",
            description=source_script.description,
            content=source_script.content,
            category=source_script.category,
            status='draft',  # 新克隆的脚本默认为草稿状态
            version='1.0.0',  # 重置版本号
            author=request.user,
            is_template=source_script.is_template
        )

        # 返回新脚本数据
        serializer = ScriptDetailSerializer(new_script)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ExportScriptView(views.APIView):
    """导出脚本为JSON文件"""
    permission_classes = [permissions.AllowAny]  # 允许所有用户访问

    def get(self, request, pk):
        script = get_object_or_404(Script, pk=pk)

        # 准备导出数据
        export_data = {
            'name': script.name,
            'description': script.description,
            'content': script.content,
            'version': script.version,
            'is_template': script.is_template,
            'exported_at': script.updated_at.isoformat(),
            'exported_by': request.user.username
        }

        # 生成JSON响应
        response = HttpResponse(
            json.dumps(export_data, indent=2, ensure_ascii=False),
            content_type='application/json'
        )
        response['Content-Disposition'] = f'attachment; filename="{script.name.replace(" ", "_")}.json"'
        return response


class ImportScriptView(views.APIView):
    """导入脚本"""
    permission_classes = [permissions.AllowAny]  # 允许所有用户访问

    def post(self, request):
        serializer = ScriptImportSerializer(data=request.data)
        if serializer.is_valid():
            # 读取上传的JSON文件
            uploaded_file = serializer.validated_data['file']
            try:
                script_data = json.load(uploaded_file)



                # 创建新脚本
                script = Script.objects.create(
                    name=script_data.get('name', f'导入脚本_{uuid.uuid4().hex[:8]}'),
                    description=script_data.get('description', ''),
                    content=script_data.get('content', {}),
                    category=serializer.validated_data.get('category'),
                    status='draft',  # 导入的脚本默认为草稿状态
                    version=script_data.get('version', '1.0.0'),
                    author=request.user,
                    is_template=script_data.get('is_template', False)
                )

                # 返回新创建的脚本
                response_serializer = ScriptDetailSerializer(script)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)

            except json.JSONDecodeError:
                return Response(
                    {"error": "无效的JSON文件格式"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RollbackScriptView(views.APIView):
    """回滚脚本到指定版本"""
    permission_classes = [permissions.AllowAny]  # 允许所有用户访问

    def post(self, request, pk, version):
        script = get_object_or_404(Script, pk=pk)

        version_obj = get_object_or_404(ScriptVersion, script=script, version=version)

        # 更新当前脚本为指定版本的内容
        script.content = version_obj.content
        script.save()

        # 返回更新后的脚本
        serializer = ScriptDetailSerializer(script)
        return Response(serializer.data)


class ScriptExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    脚本执行记录视图集

    提供脚本执行记录的查询功能
    """
    queryset = ScriptExecution.objects.all()
    serializer_class = ScriptExecutionSerializer
    permission_classes = [AllowAny]
    http_method_names = ['post']

    def get_queryset(self):
        """
        根据查询参数过滤执行记录
        """
        queryset = ScriptExecution.objects.all()

        # 按脚本过滤
        script_id = self.request.query_params.get('script')
        if script_id:
            queryset = queryset.filter(script_id=script_id)

        # 按状态过滤
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)

        # 按执行人过滤
        executed_by = self.request.query_params.get('executed_by')
        if executed_by:
            queryset = queryset.filter(executed_by_id=executed_by)

        # 按日期范围过滤
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)

        return queryset

# =====================
# 任务管理系统
# =====================

import uuid
from enum import Enum
from typing import Dict, Any, Optional
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"

@dataclass
class TaskInfo:
    task_id: str
    devices: list
    scripts: list
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    log_dir: Optional[str] = None
    results: Dict[str, Any] = None
    executor_future: Any = None

class TaskManager:
    """任务管理器 - 负责任务创建、状态跟踪、取消等功能"""

    def __init__(self):
        self.tasks: Dict[str, TaskInfo] = {}
        self.running_processes: Dict[str, Any] = {}
        self._lock = threading.RLock()

    def create_task(self, devices: list, scripts: list, log_dir: str) -> str:
        """创建新任务并返回任务ID"""
        task_id = str(uuid.uuid4())

        with self._lock:
            task_info = TaskInfo(
                task_id=task_id,
                devices=devices.copy(),
                scripts=scripts.copy(),
                status=TaskStatus.PENDING,
                created_at=datetime.now(),
                log_dir=log_dir,
                results={}
            )
            self.tasks[task_id] = task_info

        return task_id

    def update_task_status(self, task_id: str, status: TaskStatus,
                          error_message: Optional[str] = None,
                          results: Optional[Dict[str, Any]] = None):
        """更新任务状态"""
        with self._lock:
            if task_id not in self.tasks:
                return False

            task = self.tasks[task_id]
            task.status = status

            if status == TaskStatus.RUNNING and not task.started_at:
                task.started_at = datetime.now()
            elif status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.FAILED]:
                task.completed_at = datetime.now()

            if error_message:
                task.error_message = error_message
            if results:
                task.results = results

        return True

    def get_task_info(self, task_id: str) -> Optional[TaskInfo]:
        """获取任务信息"""
        with self._lock:
            return self.tasks.get(task_id)

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        with self._lock:
            if task_id not in self.tasks:
                return False

            task = self.tasks[task_id]
            if task.status not in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                return False

            # 取消正在运行的executor
            if task.executor_future and not task.executor_future.done():
                task.executor_future.cancel()

            # 终止相关子进程
            if task_id in self.running_processes:
                processes = self.running_processes[task_id]
                for proc in processes:
                    try:
                        if proc.poll() is None:  # 进程仍在运行
                            if sys.platform == "win32":
                                proc.terminate()
                                time.sleep(2)
                                if proc.poll() is None:
                                    proc.kill()
                            else:
                                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                                time.sleep(2)
                                if proc.poll() is None:
                                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    except Exception as e:
                        logger.warning(f"终止进程失败: {e}")

                del self.running_processes[task_id]

            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()

        return True

    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """清理过期任务"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

        with self._lock:
            expired_tasks = [
                task_id for task_id, task in self.tasks.items()
                if task.created_at < cutoff_time and
                   task.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.FAILED]
            ]

            for task_id in expired_tasks:
                del self.tasks[task_id]

        return len(expired_tasks)

# 全局任务管理器实例
task_manager = TaskManager()

# =====================
# 任务管理API接口
# =====================

@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def replay_status(request):
    """查询任务执行状态"""
    try:
        data = json.loads(request.body)
        task_id = data.get('task_id')

        if not task_id:
            return JsonResponse({
                'success': False,
                'message': '缺少task_id参数'
            }, status=400)

        task_info = task_manager.get_task_info(task_id)
        if not task_info:
            return JsonResponse({
                'success': False,
                'message': '任务不存在'
            }, status=404)

        # 计算执行时间
        execution_time = None
        if task_info.started_at:
            end_time = task_info.completed_at or datetime.now()
            execution_time = (end_time - task_info.started_at).total_seconds()

        # 计算进度（基于完成的设备数量）
        total_devices = len(task_info.devices)
        completed_devices = len([
            result for result in (task_info.results or {}).values()
            if result.get('exit_code') is not None
        ])
        progress = int((completed_devices / total_devices) * 100) if total_devices > 0 else 0

        response_data = {
            'success': True,
            'task_id': task_id,
            'status': task_info.status.value,
            'devices': task_info.devices,
            'scripts': task_info.scripts,
            'created_at': task_info.created_at.isoformat(),
            'started_at': task_info.started_at.isoformat() if task_info.started_at else None,
            'completed_at': task_info.completed_at.isoformat() if task_info.completed_at else None,
            'execution_time': execution_time,
            'progress': progress,
            'total_devices': total_devices,
            'completed_devices': completed_devices,
            'error_message': task_info.error_message,
            'results': task_info.results or {}
        }

        return JsonResponse(response_data)

    except Exception as e:
        logger.error(f"查询任务状态失败: {e}")
        return JsonResponse({
            'success': False,
            'message': f'查询任务状态失败: {str(e)}'
        }, status=500)

@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def replay_cancel(request):
    """取消正在执行的任务"""
    try:
        data = json.loads(request.body)
        task_id = data.get('task_id')

        if not task_id:
            return JsonResponse({
                'success': False,
                'message': '缺少task_id参数'
            }, status=400)

        success = task_manager.cancel_task(task_id)
        if not success:
            return JsonResponse({
                'success': False,
                'message': '任务不存在或无法取消'
            }, status=404)

        return JsonResponse({
            'success': True,
            'message': '任务已成功取消',
            'task_id': task_id
        })

    except Exception as e:
        logger.error(f"取消任务失败: {e}")
        return JsonResponse({
            'success': False,
            'message': f'取消任务失败: {str(e)}'
        }, status=500)

# =====================
# 存储管理API接口
# =====================

@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def storage_status(request):
    """获取存储状态信息"""
    try:
        from .storage_manager import get_storage_manager
        storage_mgr = get_storage_manager()
        status_info = storage_mgr.get_storage_status()

        return JsonResponse({
            'success': True,
            'data': status_info
        })

    except Exception as e:
        logger.error(f"获取存储状态失败: {e}")
        return JsonResponse({
            'success': False,
            'message': f'获取存储状态失败: {str(e)}'
        }, status=500)


@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def storage_cleanup(request):
    """执行存储清理"""
    try:
        data = json.loads(request.body)
        cleanup_type = data.get('type', 'auto')  # auto, emergency, logs, reports

        from .storage_manager import get_storage_manager
        storage_mgr = get_storage_manager()

        if cleanup_type == 'emergency':
            stats = storage_mgr.emergency_cleanup()
        elif cleanup_type == 'logs':
            days = data.get('days')
            stats = storage_mgr.cleanup_old_logs(days)
        elif cleanup_type == 'reports':
            days = data.get('days')
            stats = storage_mgr.cleanup_old_reports(days)
        else:  # auto
            stats = storage_mgr.auto_cleanup()
            if stats is None:
                return JsonResponse({
                    'success': True,
                    'message': '无需执行清理（距离上次清理时间过短）'
                })

        return JsonResponse({
            'success': True,
            'message': '清理完成',
            'data': {
                'files_deleted': stats.files_deleted,
                'directories_deleted': stats.directories_deleted,
                'space_freed_mb': round(stats.space_freed_mb, 2),
                'errors': stats.errors
            }
        })

    except Exception as e:
        logger.error(f"执行存储清理失败: {e}")
        return JsonResponse({
            'success': False,
            'message': f'执行存储清理失败: {str(e)}'
        }, status=500)

# =====================
# 步骤级日志记录函数
# =====================

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
    logger.info(f"{prefix} {progress_indicator}: {message}")

def log_phase_start(phase_name, device_name=None, is_multi_device=False):
    """记录阶段开始"""
    if is_multi_device and device_name:
        prefix = f"[设备:{device_name}]"
    else:
        prefix = "[单设备]" if not is_multi_device else "[多设备]"

    logger.info(f"{prefix} 🚀 开始阶段: {phase_name}")

def log_phase_complete(phase_name, device_name=None, is_multi_device=False, success=True):
    """记录阶段完成"""
    if is_multi_device and device_name:
        prefix = f"[设备:{device_name}]"
    else:
        prefix = "[单设备]" if not is_multi_device else "[多设备]"

    status = "✅ 完成" if success else "❌ 失败"
    logger.info(f"{prefix} {status}阶段: {phase_name}")

def log_device_summary(device_results):
    """记录多设备执行汇总"""
    if not device_results:
        logger.info("📊 [汇总] 无设备执行结果")
        return

    total_devices = len(device_results)
    successful_devices = sum(1 for result in device_results if result.get('exit_code', -1) == 0)
    failed_devices = total_devices - successful_devices

    logger.info("=" * 60)
    logger.info("📊 [执行汇总]")
    logger.info(f"   总设备数: {total_devices}")
    logger.info(f"   成功设备: {successful_devices}")
    logger.info(f"   失败设备: {failed_devices}")
    logger.info(f"   成功率: {(successful_devices/total_devices*100):.1f}%")

    for i, result in enumerate(device_results):
        device_name = result.get('device', f'设备{i+1}')
        status = "✅" if result.get('exit_code', -1) == 0 else "❌"
        logger.info(f"   {status} {device_name}")
    logger.info("=" * 60)

# =====================
# 设备管理和任务执行
# =====================

