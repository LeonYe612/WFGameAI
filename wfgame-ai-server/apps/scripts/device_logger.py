# -*- coding: utf-8 -*-
"""
多设备并发日志管理器
解决多设备并发回放时的乱码问题：
1. 给每个设备进程单独写文件日志
2. 日志中严格只输出纯文本，将截图、二进制流先做Base64或存文件
3. 显式指定encoding='utf-8'，避免编码问题
4. 提供线程/进程安全的日志处理机制
"""

import os
import sys
import json
import time
import base64
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Union, Any


class DeviceLogger:
    """
    设备级别的日志处理器
    为每个设备进程提供独立的日志文件，避免多进程输出混乱
    """

    def __init__(self, device_serial: str, log_dir: Optional[str] = None):
        """
        初始化设备日志器

        Args:
            device_serial: 设备序列号
            log_dir: 日志目录，如果为None则创建默认目录
        """
        self.device_serial = device_serial
        self.process_id = os.getpid()
        self.thread_id = threading.get_ident()

        # 创建设备专用日志目录
        if log_dir is None:
            timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            safe_serial = "".join(c for c in device_serial if c.isalnum() or c in ('-', '_', '.'))
            log_dir = f"device_logs/{safe_serial}_{timestamp}"

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 设备专用日志文件
        self.console_log_file = self.log_dir / "console.log"
        self.error_log_file = self.log_dir / "error.log"
        self.binary_data_dir = self.log_dir / "binary_data"
        self.binary_data_dir.mkdir(exist_ok=True)

        # 线程锁，确保多线程环境下的日志写入安全
        self._lock = threading.Lock()

        # 初始化日志文件
        self._init_log_files()

    def _init_log_files(self):
        """初始化日志文件，写入头部信息"""
        init_info = {
            "device_serial": self.device_serial,
            "process_id": self.process_id,
            "thread_id": self.thread_id,
            "start_time": datetime.now().isoformat(),
            "log_dir": str(self.log_dir)
        }

        # 写入初始化信息到console.log
        self._write_to_file(
            self.console_log_file,
            f"=== 设备 {self.device_serial} 日志初始化 ===\n{json.dumps(init_info, ensure_ascii=False, indent=2)}\n"
        )

    def _write_to_file(self, file_path: Path, content: str):
        """
        安全写入文件，确保UTF-8编码

        Args:
            file_path: 文件路径
            content: 要写入的内容
        """
        try:
            with open(file_path, 'a', encoding='utf-8', errors='replace') as f:
                f.write(content)
                f.flush()  # 确保立即写入磁盘
        except Exception as e:
            # 如果日志文件写入失败，fallback到stderr
            try:
                safe_content = repr(content)  # 确保内容可以安全输出
                sys.stderr.write(f"[LOG_ERROR] 写入 {file_path} 失败: {e}, 内容: {safe_content[:100]}\n")
                sys.stderr.flush()
            except:
                pass  # 最后的防线，避免任何异常导致程序崩溃

    def _safe_format_data(self, data: Any) -> str:
        """
        安全格式化数据，过滤二进制内容

        Args:
            data: 要格式化的数据

        Returns:
            安全的字符串表示
        """
        if isinstance(data, bytes):
            # 二进制数据保存到文件，返回文件路径
            return self._save_binary_data(data)
        elif isinstance(data, (dict, list, tuple)):
            try:
                # 递归处理复合数据类型
                return json.dumps(data, ensure_ascii=False, default=str, indent=2)
            except Exception:
                return repr(data)
        elif hasattr(data, '__dict__'):
            # 对象类型，提取属性
            try:
                obj_dict = {k: v for k, v in data.__dict__.items() if not k.startswith('_')}
                return f"{data.__class__.__name__}: {json.dumps(obj_dict, ensure_ascii=False, default=str)}"
            except Exception:
                return repr(data)
        else:
            # 基本数据类型
            try:
                str_data = str(data)
                # 检查是否包含不可打印字符
                if any(ord(c) < 32 and c not in '\t\n\r' for c in str_data):
                    return self._save_binary_data(str_data.encode('utf-8', errors='replace'))
                return str_data
            except Exception:
                return repr(data)

    def _save_binary_data(self, data: Union[bytes, str]) -> str:
        """
        保存二进制数据到文件

        Args:
            data: 二进制数据或包含不可打印字符的字符串

        Returns:
            保存的文件路径引用
        """
        try:
            if isinstance(data, str):
                data = data.encode('utf-8', errors='replace')

            # 生成唯一文件名
            timestamp = int(time.time() * 1000)
            file_name = f"binary_{timestamp}_{len(data)}.dat"
            file_path = self.binary_data_dir / file_name

            # 保存二进制数据
            with open(file_path, 'wb') as f:
                f.write(data)

            return f"[BINARY_DATA: {file_name}, size: {len(data)} bytes]"
        except Exception as e:
            return f"[BINARY_DATA_ERROR: {e}]"

    def log(self, level: str, message: str, *args, **kwargs):
        """
        记录日志消息

        Args:
            level: 日志级别 (INFO, WARNING, ERROR, DEBUG)
            message: 日志消息
            *args: 格式化参数
            **kwargs: 额外的数据
        """
        with self._lock:
            try:
                # 格式化消息
                if args:
                    safe_args = [self._safe_format_data(arg) for arg in args]
                    formatted_message = message % tuple(safe_args)
                else:
                    formatted_message = message

                # 处理额外数据
                extra_data = ""
                if kwargs:
                    safe_kwargs = {k: self._safe_format_data(v) for k, v in kwargs.items()}
                    extra_data = f" | 额外数据: {json.dumps(safe_kwargs, ensure_ascii=False)}"

                # 生成时间戳和进程信息
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

                # 构建日志条目
                log_entry = f"[{timestamp}][{level}][PID:{self.process_id}][TID:{self.thread_id}][{self.device_serial}] {formatted_message}{extra_data}\n"

                # 写入对应的日志文件
                if level == "ERROR":
                    self._write_to_file(self.error_log_file, log_entry)

                # 所有日志都写入console.log
                self._write_to_file(self.console_log_file, log_entry)

            except Exception as e:
                # 日志记录失败时的fallback
                error_entry = f"[{datetime.now().isoformat()}][LOG_ERROR][PID:{self.process_id}] 日志记录失败: {e}\n"
                try:
                    self._write_to_file(self.error_log_file, error_entry)
                except:
                    sys.stderr.write(error_entry)
                    sys.stderr.flush()

    def info(self, message: str, *args, **kwargs):
        """记录INFO级别日志"""
        self.log("INFO", message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        """记录WARNING级别日志"""
        self.log("WARNING", message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs):
        """记录ERROR级别日志"""
        self.log("ERROR", message, *args, **kwargs)

    def debug(self, message: str, *args, **kwargs):
        """记录DEBUG级别日志"""
        self.log("DEBUG", message, *args, **kwargs)

    def log_screenshot(self, screenshot_data: bytes, description: str = "截图") -> str:
        """
        安全记录截图数据

        Args:
            screenshot_data: 截图的二进制数据
            description: 截图描述

        Returns:
            截图文件路径
        """
        try:
            timestamp = int(time.time() * 1000)
            screenshot_file = self.binary_data_dir / f"screenshot_{timestamp}.jpg"

            with open(screenshot_file, 'wb') as f:
                f.write(screenshot_data)

            self.info(f"{description}: 已保存到 {screenshot_file.name}, 大小: {len(screenshot_data)} bytes")
            return str(screenshot_file)
        except Exception as e:
            self.error(f"保存截图失败: {e}")
            return ""

    def close(self):
        """关闭日志器，写入结束信息"""
        end_info = {
            "device_serial": self.device_serial,
            "process_id": self.process_id,
            "end_time": datetime.now().isoformat(),
            "log_files": {
                "console_log": str(self.console_log_file),
                "error_log": str(self.error_log_file),
                "binary_data_dir": str(self.binary_data_dir)
            }
        }

        self._write_to_file(
            self.console_log_file,
            f"\n=== 设备 {self.device_serial} 日志结束 ===\n{json.dumps(end_info, ensure_ascii=False, indent=2)}\n"
        )


class DeviceLoggerManager:
    """
    设备日志器管理器
    管理多个设备的日志器实例
    """

    def __init__(self):
        self._loggers = {}
        self._lock = threading.Lock()

    def get_logger(self, device_serial: str, log_dir: Optional[str] = None) -> DeviceLogger:
        """
        获取或创建设备日志器

        Args:
            device_serial: 设备序列号
            log_dir: 日志目录

        Returns:
            设备日志器实例
        """
        with self._lock:
            if device_serial not in self._loggers:
                self._loggers[device_serial] = DeviceLogger(device_serial, log_dir)
            return self._loggers[device_serial]

    def close_logger(self, device_serial: str):
        """关闭指定设备的日志器"""
        with self._lock:
            if device_serial in self._loggers:
                self._loggers[device_serial].close()
                del self._loggers[device_serial]

    def close_all(self):
        """关闭所有设备日志器"""
        with self._lock:
            for logger in self._loggers.values():
                logger.close()
            self._loggers.clear()


# 全局设备日志器管理器
_device_logger_manager = DeviceLoggerManager()


def get_device_logger(device_serial: str, log_dir: Optional[str] = None) -> DeviceLogger:
    """
    获取设备日志器的全局函数

    Args:
        device_serial: 设备序列号
        log_dir: 日志目录

    Returns:
        设备日志器实例
    """
    return _device_logger_manager.get_logger(device_serial, log_dir)


def device_print_realtime(device_serial: str, message: str, level: str = "INFO", log_dir: Optional[str] = None):
    """
    设备级别的实时日志输出函数
    替代原来的print_realtime，为每个设备提供独立的日志文件

    Args:
        device_serial: 设备序列号
        message: 日志消息
        level: 日志级别
        log_dir: 日志目录
    """
    logger = get_device_logger(device_serial, log_dir)
    logger.log(level, message)


def close_device_logger(device_serial: str):
    """关闭指定设备的日志器"""
    _device_logger_manager.close_logger(device_serial)


def close_all_device_loggers():
    """关闭所有设备日志器"""
    _device_logger_manager.close_all()


# 工具函数：安全的subprocess调用，确保UTF-8编码
def safe_subprocess_run(cmd, **kwargs):
    """
    安全的subprocess调用，确保UTF-8编码

    Args:
        cmd: 要执行的命令
        **kwargs: subprocess.run的其他参数

    Returns:
        subprocess.CompletedProcess实例
    """
    import subprocess

    # 强制设置UTF-8编码
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
        # 记录错误到stderr，避免影响主流程
        error_msg = f"subprocess执行失败: {cmd}, 错误: {e}\n"
        sys.stderr.write(error_msg)
        sys.stderr.flush()
        raise


def safe_subprocess_popen(cmd, **kwargs):
    """
    安全的subprocess.Popen调用，确保UTF-8编码

    Args:
        cmd: 要执行的命令
        **kwargs: subprocess.Popen的其他参数

    Returns:
        subprocess.Popen实例
    """
    import subprocess

    # 强制设置UTF-8编码
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
        # 记录错误到stderr，避免影响主流程
        error_msg = f"subprocess.Popen失败: {cmd}, 错误: {e}\n"
        sys.stderr.write(error_msg)
        sys.stderr.flush()
        raise
