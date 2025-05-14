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

import os
import sys
import time
import subprocess
import threading
import signal
import webbrowser
import platform

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

def run_command(command, cwd=None, name=None):
    """
    运行命令并捕获输出

    Args:
        command (list): 命令和参数列表
        cwd (str, optional): 工作目录
        name (str, optional): 进程名称，用于日志

    Returns:
        subprocess.Popen: 进程对象
    """
    if not cwd:
        cwd = get_project_root()
    
    log_prefix = f"[{name}] " if name else ""
    
    print_colored(f"{log_prefix}执行命令: {' '.join(command)}", 'blue')
    print_colored(f"{log_prefix}工作目录: {cwd}", 'blue')
    
    # 创建进程，设置不同的输出管道
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    # 将进程添加到全局列表
    processes.append(process)
    
    # 创建输出处理线程
    def handle_output(stream, is_error=False):
        prefix_color = 'red' if is_error else 'green'
        for line in stream:
            print_colored(f"{log_prefix}{line.rstrip()}", prefix_color)
    
    # 启动输出处理线程
    stdout_thread = threading.Thread(target=handle_output, args=(process.stdout, False))
    stderr_thread = threading.Thread(target=handle_output, args=(process.stderr, True))
    
    stdout_thread.daemon = True
    stderr_thread.daemon = True
    
    stdout_thread.start()
    stderr_thread.start()
    
    return process

def start_backend():
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
        return None
    
    command = [sys.executable, 'manage.py', 'runserver', '0.0.0.0:8000']
    process = run_command(command, cwd=backend_dir, name="后端")
    
    print_colored("后端服务启动中，请稍后...", 'yellow')
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

def wait_for_services(frontend_process, backend_process):
    """
    等待服务启动，并在浏览器中打开前端页面

    Args:
        frontend_process (subprocess.Popen): 前端进程
        backend_process (subprocess.Popen): 后端进程
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
            print_colored("- 后端: http://localhost:8000", 'cyan')
            print_colored("- API文档: http://localhost:8000/api/docs/", 'cyan')
            
            # 自动打开浏览器访问后端
            webbrowser.open('http://localhost:8000/api/docs/')
    
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
                    # 在Unix系统上，发送SIGTERM信号
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
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
        
        # 启动后端服务
        backend_process = start_backend()
        if not backend_process:
            print_colored("后端服务启动失败", 'red')
            return
        
        # 跳过前端服务启动
        frontend_process = None
        
        # 等待服务启动
        wait_for_services(frontend_process, backend_process)
        
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