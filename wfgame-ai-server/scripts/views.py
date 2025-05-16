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

from django.shortcuts import get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from rest_framework import viewsets, status, views, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

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

# 添加配置文件读取功能
def load_config():
    """
    加载配置文件，如果配置文件不存在，则使用默认值
    
    Returns:
        config: 配置对象
    """
    config = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
    
    # 获取服务器目录
    server_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 配置文件路径
    config_path = os.path.join(server_dir, "config.ini")
    
    if os.path.exists(config_path):
        try:
            config.read(config_path, encoding='utf-8')
            logger.info(f"已加载配置文件: {config_path}")
            
            # 如果配置文件中没有设置项目根目录，则根据当前文件位置计算
            if 'paths' not in config or 'project_root' not in config['paths']:
                project_root = os.path.dirname(server_dir)
                if 'paths' not in config:
                    config['paths'] = {}
                config['paths']['project_root'] = project_root
                logger.info(f"配置文件中未设置project_root，已自动计算: {project_root}")
            
            # 如果配置文件中关键路径缺失，则自动计算
            if 'paths' in config:
                paths = config['paths']
                project_root = paths.get('project_root', os.path.dirname(server_dir))
                
                # 确保服务器目录存在
                if 'server_dir' not in paths:
                    paths['server_dir'] = server_dir
                    logger.info(f"配置文件中未设置server_dir，已自动计算: {server_dir}")
                
                # 确保测试用例目录存在
                if 'testcase_dir' not in paths:
                    paths['testcase_dir'] = os.path.join(server_dir, "testcase")
                    logger.info(f"配置文件中未设置testcase_dir，已自动计算: {paths['testcase_dir']}")
                
                # 确保脚本目录存在
                if 'scripts_dir' not in paths:
                    paths['scripts_dir'] = os.path.join(server_dir, "scripts")
                    logger.info(f"配置文件中未设置scripts_dir，已自动计算: {paths['scripts_dir']}")
                
                # 确保报告目录存在
                if 'reports_dir' not in paths:
                    paths['reports_dir'] = os.path.join(project_root, "outputs", "WFGameAI-reports")
                    logger.info(f"配置文件中未设置reports_dir，已自动计算: {paths['reports_dir']}")
                
                if 'ui_reports_dir' not in paths:
                    paths['ui_reports_dir'] = os.path.join(paths['reports_dir'], "ui_reports")
                    logger.info(f"配置文件中未设置ui_reports_dir，已自动计算: {paths['ui_reports_dir']}")
        except Exception as e:
            logger.error(f"读取配置文件失败: {e}")
            # 使用默认配置
            config = create_default_config(server_dir)
    else:
        logger.warning(f"配置文件不存在: {config_path}，将使用默认配置")
        # 使用默认配置
        config = create_default_config(server_dir)
        
    return config

def create_default_config(server_dir):
    """
    创建默认配置
    
    Args:
        server_dir: 服务器目录
        
    Returns:
        config: 默认配置对象
    """
    config = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
    
    project_root = os.path.dirname(server_dir)
    
    config['paths'] = {
        'python_path': sys.executable,
        'project_root': project_root,
        'server_dir': server_dir,
        'scripts_dir': os.path.join(server_dir, "scripts"),
        'testcase_dir': os.path.join(server_dir, "testcase"),
        'reports_dir': os.path.join(project_root, "outputs", "WFGameAI-reports"),
        'ui_reports_dir': os.path.join(project_root, "outputs", "WFGameAI-reports", "ui_reports")
    }
    
    config['database'] = {
        'host': '127.0.0.1',
        'username': 'root',
        'password': 'qa123456',
        'dbname': 'gogotest_data'
    }
    
    config['settings'] = {
        'default_loop_count': '1',
        'default_max_duration': '30'
    }
    
    return config

# 加载配置
CONFIG = load_config()

# 设置主要路径
try:
    PATHS = CONFIG['paths']
    PYTHON_PATH = PATHS.get('python_path')
    PROJECT_ROOT = PATHS.get('project_root')
    SERVER_DIR = PATHS.get('server_dir')
    SCRIPTS_DIR = PATHS.get('scripts_dir')
    TESTCASE_DIR = PATHS.get('testcase_dir')
    REPORTS_DIR = PATHS.get('reports_dir')
    UI_REPORTS_DIR = PATHS.get('ui_reports_dir')
    
    # 创建必要的目录
    os.makedirs(TESTCASE_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    os.makedirs(UI_REPORTS_DIR, exist_ok=True)
    
    logger.info(f"已加载路径配置: PYTHON_PATH={PYTHON_PATH}, TESTCASE_DIR={TESTCASE_DIR}")
except Exception as e:
    logger.error(f"设置路径配置失败: {e}")
    # 回退到旧的路径定义方式
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    TESTCASE_DIR = os.path.join(BASE_DIR, "testcase")
    REPORTS_DIR = os.path.join(os.path.dirname(BASE_DIR), "outputs", "WFGameAI-reports")
    UI_REPORTS_DIR = os.path.join(REPORTS_DIR, "ui_reports")
    PYTHON_PATH = sys.executable
    
    # 创建必要的目录
    os.makedirs(TESTCASE_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    os.makedirs(UI_REPORTS_DIR, exist_ok=True)
    
    logger.warning(f"使用回退路径配置: TESTCASE_DIR={TESTCASE_DIR}")

# 从数据库加载Python解释器路径
def get_persistent_python_path():
    """从数据库加载Python解释器路径, 优先使用当前运行环境的解释器如果DB配置不佳."""
    # 优先使用配置文件中的Python路径
    if PYTHON_PATH and os.path.exists(PYTHON_PATH) and os.path.isfile(PYTHON_PATH):
        logger.info(f"使用配置文件中的Python路径: {PYTHON_PATH}")
        return PYTHON_PATH
        
        
    # 如果README中的路径不存在，则尝试从数据库加载
    db_python_path = None
    try:
        db_python_path = SystemConfig.get_value('python_path')
    except Exception as e:
        logger.error(f"从数据库加载Python路径时出错: {e}")

    current_sys_executable = sys.executable
    # 用户期望的特定环境路径 (根据项目上下文)
    preferred_env_path_segment = os.path.join("anaconda3", "envs", "py39_yolov10") 

    if db_python_path:
        logger.info(f"从数据库加载的Python路径: {db_python_path}")
        # 检查DB路径是否有效
        if os.path.exists(db_python_path) and os.path.isfile(db_python_path):
            # 如果DB路径是特定环境，很好
            if preferred_env_path_segment.lower() in db_python_path.lower():
                logger.info(f"数据库Python路径 '{db_python_path}' 指向特定环境，将使用此路径.")
                return db_python_path
            # 如果 sys.executable 是特定环境而DB路径不是, 优先 sys.executable
            elif preferred_env_path_segment.lower() in current_sys_executable.lower():
                logger.warning(f"数据库Python路径 '{db_python_path}' 不是特定环境路径, "
                               f"但当前运行的Python '{current_sys_executable}' 是特定环境. "
                               f"将优先使用当前运行的Python.")
                return current_sys_executable
            # 否则，DB路径有效但不是特定环境，仍使用它但记录警告
            else:
                logger.warning(f"数据库Python路径 '{db_python_path}' 有效但不是期望的特定环境. "
                               f"当前运行的Python是 '{current_sys_executable}'. 将使用数据库路径.")
                return db_python_path
        else:
            logger.warning(f"数据库中的Python路径 '{db_python_path}' 无效或不存在.")

    # 如果DB路径无效或未设置，检查当前sys.executable是否是特定环境
    if preferred_env_path_segment.lower() in current_sys_executable.lower():
        logger.info(f"数据库Python路径无效/未设置或非特定环境. "
                      f"当前运行的Python '{current_sys_executable}' 是特定环境，将使用此路径.")
        return current_sys_executable
    
    # 作为最终回退，如果sys.executable也不是特定环境，但DB值存在（即使不是特定环境的）
    if db_python_path and os.path.exists(db_python_path) and os.path.isfile(db_python_path):
        logger.warning(f"最终回退: 使用数据库中的Python路径 '{db_python_path}'因为它有效, "
                       f"尽管它或当前 sys.executable ('{current_sys_executable}') 都不是首选环境.")
        return db_python_path

    logger.error(f"无法确定有效的Python解释器路径. 数据库路径: '{db_python_path}', "
                   f"系统可执行文件: '{current_sys_executable}'. 将回退到系统默认 '{sys.executable}'.")
    return sys.executable # Fallback to current interpreter if DB path is invalid

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
    """获取已连接的设备列表"""
    try:
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')[1:]  # 跳过标题行
        devices = []
        
        for line in lines:
            if line.strip():
                parts = line.strip().split('\t')
                if len(parts) == 2:
                    serial, status = parts
                    if status == 'device':  # 只添加已连接的设备
                        # 获取设备信息
                        brand = subprocess.run(['adb', '-s', serial, 'shell', 'getprop', 'ro.product.brand'], 
                                              capture_output=True, text=True).stdout.strip()
                        model = subprocess.run(['adb', '-s', serial, 'shell', 'getprop', 'ro.product.model'], 
                                              capture_output=True, text=True).stdout.strip()
                        devices.append({
                            'serial': serial,
                            'brand': brand,
                            'model': model,
                            'name': f"{brand}-{model}"
                        })
        
        return Response({'devices': devices})
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def get_scripts(request):
    """获取可用的测试脚本列表"""
    try:
        # 从数据库中获取脚本文件列表
        script_files = ScriptFile.objects.filter(status='active').order_by('-created_at')
        
        scripts = []
        for script_file in script_files:
            # 确保path只使用文件名，而不是完整路径
            scripts.append({
                'filename': script_file.filename,
                'path': script_file.filename,  # 修改这里，只使用文件名
                'created': script_file.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'step_count': script_file.step_count,
                'category': script_file.category.name if script_file.category else '未分类',
                'type': script_file.get_type_display(),
                'description': script_file.description
            })
        
        # 如果数据库中没有记录，则尝试从文件系统获取
        if not scripts:
            # 确保目录存在
            os.makedirs(TESTCASE_DIR, exist_ok=True)
            
            # 获取所有JSON脚本文件
            for script_file in glob.glob(os.path.join(TESTCASE_DIR, "*.json")):
                filename = os.path.basename(script_file)
                created_time = datetime.fromtimestamp(os.path.getctime(script_file))
                
                # 读取脚本内容获取步骤数
                try:
                    with open(script_file, 'r', encoding='utf-8') as f:
                        script_data = json.load(f)
                        step_count = len(script_data.get('steps', []))
                except:
                    step_count = 0
                    
                scripts.append({
                    'filename': filename,
                    'path': filename,  # 修改这里，只使用文件名
                    'created': created_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'step_count': step_count,
                    'category': '未分类',
                    'type': '未知',
                    'description': ''
                })
            
            # 按创建时间排序，最新的在前面
            scripts.sort(key=lambda x: x['created'], reverse=True)
        
        return Response({'scripts': scripts})
    except Exception as e:
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
        }
        
        # 获取当前环境已安装的包
        try:
            pip_freeze = subprocess.run([sys.executable, "-m", "pip", "freeze"], 
                                      capture_output=True, text=True, check=True)
            packages = pip_freeze.stdout.strip().split('\n')
            current_env["packages"] = packages
        except Exception as e:
            print(f"获取当前环境包列表失败: {e}")
        
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
        else:
            # Mac/Linux下查找全局Python路径
            try:
                which_python3 = subprocess.run(["which", "python3"], 
                                             capture_output=True, text=True, check=True)
                python3_path = which_python3.stdout.strip()
                
                if python3_path and python3_path != sys.executable:
                    found_paths.append(python3_path)
            except Exception as e:
                print(f"查找全局Python路径失败: {e}")
        
        # 2. 查找Anaconda/Miniconda环境 - 增强对Conda环境的检测
        conda_env_paths = []
        
        # 首先尝试运行conda info命令
        try:
            # 查找可能的conda可执行文件
            conda_executables = ['conda', 'conda.exe']
            conda_path = None
            
            # 尝试在PATH中找到conda
            for conda_exe in conda_executables:
                try:
                    if is_windows:
                        conda_proc = subprocess.run(['where', conda_exe], 
                                                   capture_output=True, text=True, check=True)
                    else:
                        conda_proc = subprocess.run(['which', conda_exe], 
                                                   capture_output=True, text=True, check=True)
                    
                    conda_paths = conda_proc.stdout.strip().split('\n')
                    if conda_paths and conda_paths[0]:
                        conda_path = conda_paths[0]
                        break
                except subprocess.CalledProcessError:
                    continue
            
            if conda_path:
                # 使用conda env list获取所有环境
                conda_env_proc = subprocess.run([conda_path, 'env', 'list', '--json'], 
                                              capture_output=True, text=True, timeout=5)
                
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
                        print("无法解析conda env list输出")
        except Exception as e:
            print(f"使用conda命令获取环境列表失败: {e}")
        
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
        found_paths = list(set(found_paths))
        
        # 获取每个Python环境的版本信息
        for python_path in found_paths:
            try:
                # 获取版本信息
                version_cmd = [python_path, "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"]
                version_proc = subprocess.run(version_cmd, capture_output=True, text=True, timeout=3)
                version = version_proc.stdout.strip() if version_proc.returncode == 0 else "未知"
                
                # 尝试获取环境名称
                name = "Python环境"
                
                # 检查是否为conda环境
                try:
                    conda_info_cmd = [python_path, "-c", 
                                     "import os, sys; print(os.environ.get('CONDA_DEFAULT_ENV') or os.path.basename(os.path.dirname(os.path.dirname(sys.executable)))) if 'conda' in sys.version or 'Continuum' in sys.version else print('non-conda')"]
                    conda_info_proc = subprocess.run(conda_info_cmd, capture_output=True, text=True, timeout=3)
                    
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
                                name = "Conda: Base"
                
                # 获取已安装的包
                packages = []
                try:
                    pip_cmd = [python_path, "-m", "pip", "freeze"]
                    pip_proc = subprocess.run(pip_cmd, capture_output=True, text=True, timeout=5)
                    if pip_proc.returncode == 0:
                        packages = pip_proc.stdout.strip().split('\n')
                except Exception as e:
                    print(f"获取环境 {python_path} 的包列表失败: {e}")
                
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
                print(f"获取环境 {python_path} 信息失败: {e}")
        
        return JsonResponse({
            'success': True,
            'envs': envs
        })
    except Exception as e:
        error_msg = str(e)
        print(f"检测Python环境失败: {error_msg}")
        
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
            }, status=400)
        
        # 验证是否为有效的Python解释器
        try:
            check_proc = subprocess.run([new_env_path, "--version"], 
                                      capture_output=True, text=True, timeout=3)
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
        )
        
        # 获取环境名称
        env_name = "未知环境"
        try:
            conda_info_cmd = [new_env_path, "-c", 
                             "import os, sys; print(os.environ.get('CONDA_DEFAULT_ENV') or os.path.basename(os.path.dirname(os.path.dirname(sys.executable)))) if 'conda' in sys.version or 'Continuum' in sys.version else print(sys.executable)"]
            conda_info_proc = subprocess.run(conda_info_cmd, capture_output=True, text=True, timeout=3)
            
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
        
        cmd = [python_exec, record_script_path]
        
        # 根据模式添加参数
        if record_mode == 'enhanced':
            cmd.append('--record-no-match')
        else:
            cmd.append('--record')
            
        # 如果指定了设备，添加指定设备参数
        if device_serial:
            cmd.extend(['--main-device', device_serial])
        
        logger.info(f"启动录制命令: {' '.join(cmd)}")
        
        # 使用subprocess启动录制进程
        process = subprocess.Popen(cmd, 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE,
                                  cwd=PROJECT_ROOT,  # 使用配置中的项目根目录
                                  text=True)
        
        # 这里不等待进程完成，立即返回
        return Response({
            'status': 'started',
            'message': '录制进程已启动，请在设备上操作应用。按下Ctrl+C或关闭命令窗口停止录制。',
            'pid': process.pid
        })
    except Exception as e:
        logger.error(f"启动录制脚本失败: {e}")
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def replay_script(request):
    """回放指定的测试脚本"""
    try:
        data = json.loads(request.body)
        
        # 检查脚本参数，兼容scripts数组和script_path参数
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
        
        # 对脚本路径进行规范化处理
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
        
        # 获取Python解释器路径
        python_exec = get_persistent_python_path()
        logger.info(f"使用Python环境: {python_exec}")
        
        # 获取replay_script.py的绝对路径
        replay_script_path = os.path.join(SCRIPTS_DIR, "replay_script.py")
        
        # 组装命令
        cmd = [
            python_exec,
            replay_script_path
        ]
        
        # 添加显示屏幕参数
        if data.get('show_screens'):
            cmd.append("--show-screens")
        
        # 添加脚本参数
        for config in script_configs:
            script_path = config.get('path')
            cmd.extend(["--script", script_path])
            
            # 添加循环次数
            loop_count = config.get('loop_count')
            if loop_count:
                cmd.extend(["--loop-count", str(loop_count)])
            
            # 添加最大持续时间
            max_duration = config.get('max_duration')
            if max_duration:
                cmd.extend(["--max-duration", str(max_duration)])
        
        # 日志输出
        logger.info(f"执行回放命令: {' '.join(cmd)}")
        
        # 启动回放进程
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=PROJECT_ROOT,  # 使用配置中的项目根目录
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        # 存储进程对象，以便后续管理
        CHILD_PROCESSES[process.pid] = process
        
        # 创建线程读取输出，避免缓冲区满
        def read_output(stream, log_func):
            for line in iter(stream.readline, ''):
                if line:
                    log_func(f"回放输出: {line.strip()}")
            stream.close()
        
        # 启动输出读取线程
        stdout_thread = threading.Thread(target=read_output, args=(process.stdout, logger.info))
        stderr_thread = threading.Thread(target=read_output, args=(process.stderr, logger.error))
        stdout_thread.daemon = True
        stderr_thread.daemon = True
        stdout_thread.start()
        stderr_thread.start()
        
        # 等待进程完成，设置超时避免无限等待
        try:
            process.wait(timeout=1)  # 短暂等待，不阻塞响应
        except subprocess.TimeoutExpired:
            # 进程仍在运行，这是正常的
            pass
        
        # 获取最新生成的报告URL
        report_url = ""
        try:
            # 查找最新的报告目录
            report_dirs = []
            for device_dir in os.listdir(UI_REPORTS_DIR):
                device_path = os.path.join(UI_REPORTS_DIR, device_dir)
                if os.path.isdir(device_path):
                    for report_dir in os.listdir(device_path):
                        report_path = os.path.join(device_path, report_dir)
                        if os.path.isdir(report_path):
                            report_dirs.append((report_path, os.path.getmtime(report_path)))
            
            # 按修改时间排序，获取最新的报告
            if report_dirs:
                report_dirs.sort(key=lambda x: x[1], reverse=True)
                latest_report_dir = report_dirs[0][0]
                
                # 构建报告URL
                relative_path = os.path.relpath(latest_report_dir, os.path.dirname(PROJECT_ROOT))
                report_url = f"/static/{relative_path.replace(os.path.sep, '/')}/index.html"
        except Exception as e:
            logger.error(f"获取报告URL失败: {e}")
        
        # 返回播放成功响应
        return JsonResponse({
            'success': True,
            'message': '成功启动脚本回放',
            'process_id': process.pid,
            'command': ' '.join(cmd),  # 添加命令行
            'report_url': report_url
        })
    except Exception as e:
        error_msg = str(e)
        logger.error(f"回放脚本时出错: {error_msg}")
        
        return JsonResponse({
            'success': False,
            'message': f'回放脚本失败: {error_msg}'
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
        logger.info(f"Using Python interpreter: {python_exec} from project_root: {PROJECT_ROOT}")

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
            if args[0].lower() == 'python' or args[0].endswith('.py'):
                # 获取Python解释器路径
                python_executable = python_exec.replace('\\', '\\\\')  # 确保反斜杠被正确处理
                logger.info(f"Using Python executable: {python_executable}")
                
                if args[0].lower() == 'python': # e.g., "python record_script.py ..."
                    script_name_arg_index = 1
                    args[0] = python_executable # Replace 'python' with full path
                else: # e.g., "record_script.py ..." or "path/to/script.py ..."
                    script_name_arg_index = 0
                    # Prepend python_exec if script.py is the first argument
                    args.insert(0, python_executable)
                
                # Ensure the script path itself is correct
                if len(args) > script_name_arg_index:
                    script_file_part = args[script_name_arg_index]
                    if not os.path.isabs(script_file_part):
                        # 先检查scripts目录
                        abs_script_path = os.path.join(SCRIPTS_DIR, script_file_part)
                        if os.path.exists(abs_script_path):
                            args[script_name_arg_index] = abs_script_path
                            logger.info(f"Resolved script path to scripts directory: {abs_script_path}")
                        else:
                            # 如果不在scripts目录，尝试项目根目录
                            abs_script_path = os.path.join(PROJECT_ROOT, script_file_part)
                            if os.path.exists(abs_script_path):
                                args[script_name_arg_index] = abs_script_path
                                logger.info(f"Resolved relative script path to project root: {abs_script_path}")
                            else:
                                logger.warning(f"Script '{script_file_part}' not found in scripts directory or project root. Using original relative path.")
                    # If it was absolute, assume it's correct or will fail naturally
            else:
                # Command does not start with python or a .py file, assume it's a full path to an executable
                # or a system command. For safety, if it's not an absolute path, it might be an issue.
                if not os.path.isabs(args[0]) and not shutil.which(args[0]):
                    logger.warning(f"Command '{args[0]}' is not absolute and not found in PATH. Execution may fail.")

        logger.info(f"Executing command with args: {args}, cwd: {PROJECT_ROOT}")
        
        process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False, # Important: shell=False when args is a list
            text=True, # Use text=True for universal_newlines=True behavior
            encoding='utf-8', errors='replace', # Be explicit about encoding
            cwd=PROJECT_ROOT  # 使用配置中的项目根目录
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
        record_script_path = os.path.join(SCRIPTS_DIR, "record_script.py")
        
        # 组装命令
        cmd = [
            python_exec,
            record_script_path,
            "--record"
        ]
        
        logger.info(f"启动录制命令: {' '.join(cmd)}")
        
        # 启动录制进程
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=PROJECT_ROOT,  # 使用配置中的项目根目录
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        # 存储进程对象，以便后续管理
        process_id = str(process.pid)
        CHILD_PROCESSES[process_id] = process
        
        # 创建线程读取输出，避免缓冲区满
        def read_output(stream, log_func):
            for line in iter(stream.readline, ''):
                if line:
                    log_func(f"录制输出: {line.strip()}")
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
    permission_classes = [permissions.IsAuthenticated]
    
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
    permission_classes = [permissions.IsAuthenticated]
    
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
        
        status_str = "启用" if script.is_active else "禁用"
        logger.info(f"脚本已{status_str}: {script.name} - 用户: {request.user.username}")
        
        return Response({
            "id": script.id,
            "name": script.name,
            "is_active": script.is_active
        })


class ScriptVersionViewSet(viewsets.ReadOnlyModelViewSet):
    """脚本版本视图集 - 只读"""
    queryset = ScriptVersion.objects.all()
    serializer_class = ScriptVersionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['script']


class CloneScriptView(views.APIView):
    """克隆脚本"""
    permission_classes = [permissions.IsAuthenticated]
    
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
    permission_classes = [permissions.IsAuthenticated]
    
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
    permission_classes = [permissions.IsAuthenticated]
    
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
    permission_classes = [permissions.IsAuthenticated]
    
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
    permission_classes = [permissions.IsAuthenticated]
    
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

@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def edit_script(request, script_path=None):
    """
    获取和更新脚本内容 - 统一使用POST请求
    操作类型由请求体中的operation字段决定：
    - 'read': 读取脚本内容
    - 'write': 更新脚本内容
    """
    try:
        # 从POST请求体中获取参数
        data = json.loads(request.body)
        logger.info(f"Edit script request - data: {data}")
        operation = data.get('operation', 'read')  # 默认为读取操作
        filename = data.get('filename')  # 从请求体中获取文件名
        
        if not filename:
            return JsonResponse({'success': False, 'message': '未提供文件名'}, status=400)
            
        logger.info(f"Edit script request - filename: {filename}")
        
        # 构建完整路径 - 确保路径安全
        # 只使用文件名，忽略任何路径信息，并限制在测试用例目录内
        safe_filename = os.path.basename(filename)  # 提取文件名，移除任何路径
        final_absolute_path = os.path.join(TESTCASE_DIR, safe_filename)
        
        logger.info(f"Final absolute path: {final_absolute_path}")
        
        # 根据操作类型处理请求
        if operation == 'read':
            # 读取文件
            try:
                # 尝试以UTF-8读取
                try:
                    with open(final_absolute_path, 'r', encoding='utf-8') as file:
                        content = file.read()
                except UnicodeDecodeError:
                    # 如果UTF-8解码失败，尝试以二进制方式读取
                    with open(final_absolute_path, 'rb') as file:
                        content_bytes = file.read()
                        # 尝试检测编码
                        encodings = ['utf-8', 'latin1', 'gbk', 'gb2312', 'big5']
                        content = None
                        for encoding in encodings:
                            try:
                                content = content_bytes.decode(encoding)
                                logger.info(f"成功使用{encoding}解码")
                                break
                            except UnicodeDecodeError:
                                continue
                        
                        # 如果所有编码都失败，将其作为latin1（能处理任何字节）
                        if content is None:
                            content = content_bytes.decode('latin1')
                            logger.warning(f"使用latin1作为回退编码")
                
                script_json_data = {}
                try:
                    script_json_data = json.loads(content)
                    formatted_content = json.dumps(script_json_data, indent=2, ensure_ascii=False)
                except json.JSONDecodeError:
                    formatted_content = content
                    logger.warning(f"Content of '{final_absolute_path}' is not valid JSON. Serving raw.")
                
                created_time = datetime.fromtimestamp(os.path.getctime(final_absolute_path))
                modified_time = datetime.fromtimestamp(os.path.getmtime(final_absolute_path))
                step_count = len(script_json_data.get('steps', [])) if isinstance(script_json_data, dict) else 0
                
                return JsonResponse({
                    'success': True, 'filename': safe_filename, 'path': final_absolute_path,
                    'content': formatted_content, 'created': created_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'modified': modified_time.strftime('%Y-%m-%d %H:%M:%S'), 'step_count': step_count
                })
            except FileNotFoundError:
                logger.error(f"File not found: {final_absolute_path}")
                return JsonResponse({'success': False, 'message': f'脚本文件不存在: {safe_filename}'}, status=404)
            except Exception as e_read:
                logger.error(f"Error reading script file '{final_absolute_path}': {str(e_read)}")
                return JsonResponse({'success': False, 'message': f'读取脚本文件失败: {str(e_read)}'}, status=500)
        
        elif operation == 'write':
            # 更新文件内容
            new_content_str = data.get('content')
            if new_content_str is None:
                return JsonResponse({'success': False, 'message': '未提供新的脚本内容'}, status=400)
            
            # 验证JSON格式
            try:
                json.loads(new_content_str)
            except json.JSONDecodeError as e_json:
                logger.error(f"Invalid JSON content: {str(e_json)}")
                return JsonResponse({'success': False, 'message': f'无效的JSON格式: {str(e_json)}'}, status=400)
            
            # 确保目录存在
            os.makedirs(os.path.dirname(final_absolute_path), exist_ok=True)
            
            # 写入文件
            with open(final_absolute_path, 'w', encoding='utf-8') as file:
                file.write(new_content_str)
            logger.info(f"Script updated successfully: {final_absolute_path}")
            
            return JsonResponse({
                'success': True, 'message': '脚本已成功更新',
                'modified': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        else:
            # 不支持的操作类型
            return JsonResponse({'success': False, 'message': f'不支持的操作类型: {operation}'}, status=400)
    
    except Exception as e:
        logger.error(f"Error processing script edit request: {str(e)}")
        return JsonResponse({'success': False, 'message': f'处理脚本编辑请求失败: {str(e)}'}, status=500)
