#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================
Description:
此脚本用于同时启动WFGame AI自动化测试平台的前端和后端服务。
Author: WFGame AI团队
CreateDate: 2025-05-13
Version: 1.0
===============================
"""

"""
python 环境：
conda activate py39_yolov10

使用
python start_wfgame_ai.py --config config.ini → 线上环境绑定 8000
python start_wfgame_ai.py --config config_dev.ini → 开发环境绑定 9000
"""
import os
import sys
import time
import subprocess
import threading
import signal
import webbrowser
import platform
import argparse

# 全局变量，存储进程句柄，用于程序退出时终止进程
processes = []

def print_colored(text, color):
    """
    打印彩色文本

    Args:
        text (str): 要打印的文本
        color (str): 颜色代码，例如: 'green', 'red', 'yellow', 'blue'

    Returns:
        None
    """
    colors = {
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'purple': '\033[95m',
        'cyan': '\033[96m',
        'white': '\033[97m',
        'reset': '\033[0m'
    }

    # Windows命令行需要特殊处理才能显示彩色文本
    if platform.system() == 'Windows':
        os.system('color')

    print(f"{colors.get(color, '')}{text}{colors['reset']}")

def prepare_devices():
    """
    启动前预处理设备，解决ADB连接和权限问题
    """
    print_colored("🔧 正在预处理设备连接和权限...", 'yellow')

    try:
        # 检查是否存在设备预处理脚本
        project_root = get_project_root()
        device_prep_script = os.path.join(project_root, "wfgame-ai-server", "apps", "scripts", "device_preparation_manager.py")

        if os.path.exists(device_prep_script):
            print_colored("📱 正在检查和配置连接的设备...", 'blue')

            # 执行设备预处理
            result = subprocess.run([
                sys.executable, device_prep_script
            ], capture_output=True, text=True, timeout=60)

            if result.returncode == 0:
                print_colored("✅ 设备预处理完成", 'green')

                # 显示处理结果摘要
                if "成功处理" in result.stdout:
                    print_colored(f"   {result.stdout.split('成功处理')[1].split('个设备')[0].strip()}个设备已准备就绪", 'green')

                return True
            else:
                print_colored("⚠️  设备预处理出现问题，但不影响服务启动", 'yellow')
                if result.stderr:
                    print_colored(f"   错误信息: {result.stderr.strip()}", 'yellow')
                return False
        else:
            print_colored("⚠️  未找到设备预处理脚本，跳过设备预处理", 'yellow')
            return False

    except subprocess.TimeoutExpired:
        print_colored("⚠️  设备预处理超时，继续启动服务", 'yellow')
        return False
    except Exception as e:
        print_colored(f"⚠️  设备预处理异常: {str(e)}", 'yellow')
        return False

def show_banner():
    """
    显示启动横幅
    """
    banner = """
    ██╗    ██╗███████╗ ██████╗  █████╗ ███╗   ███╗███████╗     █████╗ ██╗
    ██║    ██║██╔════╝██╔════╝ ██╔══██╗████╗ ████║██╔════╝    ██╔══██╗██║
    ██║ █╗ ██║█████╗  ██║  ███╗███████║██╔████╔██║█████╗      ███████║██║
    ██║███╗██║██╔══╝  ██║   ██║██╔══██║██║╚██╔╝██║██╔══╝      ██╔══██║██║
    ╚███╔███╔╝██║     ╚██████╔╝██║  ██║██║ ╚═╝ ██║███████╗    ██║  ██║██║
     ╚══╝╚══╝ ╚═╝      ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝    ╚═╝  ╚═╝╚═╝

    自动化测试平台服务启动工具 v1.0
    """
    print_colored(banner, 'cyan')
    print_colored("\n正在启动服务...\n", 'green')

def get_project_root():
    """
    获取项目根目录

    Returns:
        str: 项目根目录的绝对路径
    """
    # 获取当前脚本的绝对路径
    current_path = os.path.abspath(__file__)

    # 获取当前脚本所在的目录，即项目根目录
    project_root = os.path.dirname(current_path)

    return project_root

def run_command(command, cwd=None, name=None, env_vars=None):
    """
    运行命令并捕获输出

    Args:
        command (list): 命令和参数列表
        cwd (str, optional): 工作目录
        name (str, optional): 进程名称，用于日志
        env_vars (dict, optional): 额外的环境变量，会在当前环境基础上叠加

    Returns:
        subprocess.Popen: 进程对象
    """
    if not cwd:
        cwd = get_project_root()

    log_prefix = f"[{name}] " if name else ""

    print_colored(f"{log_prefix}执行命令: {' '.join(command)}", 'blue')
    print_colored(f"{log_prefix}工作目录: {cwd}", 'blue')    # 创建进程，设置不同的输出管道
    # 组装环境变量
    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True,
        encoding='utf-8',
        errors='replace'  # 遇到编码错误时替换为?而不是抛出异常
    )

    # 将进程添加到全局列表
    processes.append(process)

    # 创建输出处理线程
    def handle_output(stream, is_error=False):
        prefix_color = 'red' if is_error else 'green'
        try:
            for line in stream:
                # 额外的编码安全处理
                try:
                    safe_line = line.encode('utf-8', errors='replace').decode('utf-8')
                    print_colored(f"{log_prefix}{safe_line.rstrip()}", prefix_color)
                except UnicodeError:
                    # 如果还有编码问题，直接跳过这行
                    print_colored(f"{log_prefix}[编码错误，跳过一行日志]", 'yellow')
        except Exception as e:
            print_colored(f"{log_prefix}输出处理异常: {e}", 'red')

    # 启动输出处理线程
    stdout_thread = threading.Thread(target=handle_output, args=(process.stdout, False))
    stderr_thread = threading.Thread(target=handle_output, args=(process.stderr, True))

    stdout_thread.daemon = True
    stderr_thread.daemon = True

    stdout_thread.start()
    stderr_thread.start()

    return process

def start_backend(config_path: str = None, port: int = 8000):
    """
    启动Django后端服务

    Returns:
        subprocess.Popen: 后端进程对象
    """
    print_colored("\n====== 启动后端服务 ======", 'yellow')

    backend_dir = os.path.join(get_project_root(), 'wfgame-ai-server')

    # 检查后端目录是否存在
    if not os.path.exists(backend_dir):
        print_colored(f"错误: 后端目录不存在: {backend_dir}", 'red')
        return None    # 统一使用localhost:8000，但仍绑定到0.0.0.0以允许外部访问
    bind = f"0.0.0.0:{port}"
    command = [sys.executable, 'manage.py', 'runserver', bind]

    # 配置文件环境变量
    env_vars = {}
    if config_path:
        env_vars['WFGAMEAI_CONFIG'] = config_path
        print_colored(f"使用配置文件: {config_path}", 'cyan')
    print_colored(f"后端绑定端口: {bind}", 'cyan')

    process = run_command(command, cwd=backend_dir, name="后端", env_vars=env_vars)

    print_colored("后端服务启动中，请稍后...", 'yellow')
    print_colored(f"注意: 服务绑定到{bind}，推荐使用localhost:{port}访问", 'cyan')
    return process

def start_usb_monitor(config_path: str = None):
    """
    启动USB设备监控脚本

    Returns:
        subprocess.Popen: 监控进程对象
    """
    print_colored("\n====== 启动USB设备监控 ======", 'yellow')

    monitor_script = os.path.join(get_project_root(), "wfgame-ai-server", "scripts", "monitor_usb.py")

    if not os.path.exists(monitor_script):
        print_colored(f"错误: USB监控脚本不存在: {monitor_script}", 'red')
        return None

    # 配置文件环境变量
    env_vars = {}
    if config_path:
        env_vars['WFGAMEAI_CONFIG'] = config_path
        print_colored(f"使用配置文件: {config_path}", 'cyan')

    command = [sys.executable, monitor_script]
    process = run_command(command, cwd=get_project_root(), name="USB监控", env_vars=env_vars)

    print_colored("USB设备监控启动中，请稍后...", 'yellow')
    return process

def start_frontend():
    """
    启动Vue前端服务

    Returns:
        subprocess.Popen: 前端进程对象
    """
    # 暂时跳过前端启动
    print_colored("\n====== 暂时跳过前端服务启动 ======", 'yellow')
    print_colored("当前仅启动后端服务，前端服务暂不启动", 'cyan')

    return None

def wait_for_services(frontend_process, backend_process, port: int = 8000):
    """
    等待服务启动，并在浏览器中打开前端页面

    Args:
        frontend_process (subprocess.Popen): 前端进程
        backend_process (subprocess.Popen): 后端进程
        port (int): 后端端口
    """
    # 等待前端服务启动（检测"Compiled successfully"消息）
    frontend_ready = True  # 由于跳过前端，默认为True
    backend_ready = False

    print_colored("\n等待服务启动...", 'yellow')

    # 计数器，用于超时检测
    timeout_count = 0
    max_timeout = 60  # 最长等待60秒

    try:
        while (not backend_ready) and timeout_count < max_timeout:
            # 检查进程是否仍在运行
            if backend_process and backend_process.poll() is not None:
                print_colored("后端进程意外退出", 'red')
                return

            time.sleep(1)
            timeout_count += 1

            # 每10秒显示一次等待消息
            if timeout_count % 10 == 0:
                print_colored(f"仍在等待后端服务启动... ({timeout_count}秒)", 'yellow')

            # 20秒后自动认为服务已启动
            if timeout_count >= 20:
                backend_ready = True

        if timeout_count >= max_timeout:
            print_colored("等待服务启动超时", 'red')
        else:
            print_colored("\n服务已成功启动！", 'green')
            print_colored("\n访问地址:", 'green')
            print_colored(f"- 后端: http://172.20.19.101:{port}", 'cyan')
            # print_colored("- API文档: http://localhost:8000/api/docs/", 'cyan')

            # 自动打开浏览器访问后端
            # webbrowser.open('http://localhost:8000/api/docs/')

    except KeyboardInterrupt:
        pass

def cleanup():
    """
    清理所有启动的进程
    """
    print_colored("\n正在关闭服务...", 'yellow')

    for process in processes:
        if process and process.poll() is None:  # 检查进程是否仍在运行
            try:
                if platform.system() == 'Windows':
                    # Windows上使用taskkill强制终止进程及其子进程
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(process.pid)],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                else:
                    # 在Unix系统上，使用terminate方法
                    process.terminate()
            except Exception as e:
                print_colored(f"关闭进程时出错: {e}", 'red')

    print_colored("所有服务已关闭", 'green')

def signal_handler(sig, frame):
    """
    信号处理函数，用于捕获Ctrl+C

    Args:
        sig: 信号
        frame: 栈帧
    """
    print_colored("\n接收到终止信号，正在关闭服务...", 'yellow')
    cleanup()
    sys.exit(0)

def main():
    """
    主函数
    """
    # 注册信号处理器，用于捕获Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # 显示启动横幅
        show_banner()

        # 命令行参数
        parser = argparse.ArgumentParser(description='WFGame AI 启动器')
        parser.add_argument('--config', type=str, default=None,
                            help='配置文件名或路径，支持 config.ini / config_dev.ini 或自定义路径')
        parser.add_argument('--env', type=str, default=None, choices=['prod', 'online'],
                            help='运行环境：prod(生产:9000) / online(线上:8000)')
        args = parser.parse_args()

        project_root = get_project_root()
        # 解析配置文件路径
        selected_config = None
        if args.config:
            # 如果传入的是文件名，则拼接到项目根目录
            if os.path.isabs(args.config):
                selected_config = args.config
            else:
                selected_config = os.path.join(project_root, args.config)
        else:
            # 未指定时，默认使用项目根目录下的 config.ini
            selected_config = os.path.join(project_root, 'config.ini')

        # 解析端口：严格按配置文件名固定映射（写死映射，不考虑其他情况）
        base = os.path.basename(selected_config).lower()
        # 线上环境
        if base == 'config.ini':
            port = 8000
        # 开发环境
        elif base == 'config_dev.ini':
            port = 9000
        else:
            # 默认 8000（仅在用户给了其他文件名时兜底）
            port = 8000

        # 启动后端服务
        backend_process = start_backend(config_path=selected_config, port=port)
        if not backend_process:
            print_colored("后端服务启动失败", 'red')
            return

        # 跳过前端服务启动
        frontend_process = None

        # 预处理设备
        prepare_devices()

        # 启动USB设备监控服务
        usb_monitor_process = start_usb_monitor(config_path=selected_config)
        if not usb_monitor_process:
            print_colored("USB设备监控服务启动失败", 'red')
            return

        # 等待服务启动
        wait_for_services(frontend_process, backend_process, port=port)

        # 保持脚本运行，直到用户按下Ctrl+C
        print_colored("\n服务正在运行中，按Ctrl+C停止...", 'green')

        # 等待进程结束
        backend_process.wait()

    except KeyboardInterrupt:
        print_colored("\n接收到用户中断，关闭服务...", 'yellow')
    finally:
        cleanup()

if __name__ == "__main__":
    main()