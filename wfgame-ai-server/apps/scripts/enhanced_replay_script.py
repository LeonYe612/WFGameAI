# -*- coding: utf-8 -*-
"""
增强的多设备并发回放脚本
支持方案3需求：多设备并发、文件日志、二进制内容处理
"""

import os
import sys
import time
import json
import subprocess
import signal
from datetime import datetime
from adbutils import adb


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
    """
    # 验证 result_data 格式
    if not isinstance(result_data, dict):
        result_data = {"error": "无效的结果数据格式", "exit_code": -1, "report_url": ""}

    # 确保必要字段存在
    required_fields = ["exit_code", "report_url"]
    for field in required_fields:
        if field not in result_data:
            result_data[field] = "" if field == "report_url" else -1

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


def parse_enhanced_arguments(args_list):
    """解析增强的脚本参数，支持多设备并发参数"""
    scripts = []
    current_script = None
    current_loop_count = 1
    current_max_duration = None

    # 多设备并发回放参数
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
                scripts.append({
                    'path': current_script,
                    'loop_count': current_loop_count,
                    'max_duration': current_max_duration
                })

            # 开始新脚本
            if i + 1 < len(args_list):
                current_script = args_list[i + 1]
                i += 1
            else:
                print("错误: --script 参数后缺少脚本路径")
                break

        elif arg == '--loop-count':
            if i + 1 < len(args_list):
                try:
                    current_loop_count = int(args_list[i + 1])
                    i += 1
                except ValueError:
                    print(f"错误: 无效的循环次数: {args_list[i + 1]}")
            else:
                print("错误: --loop-count 参数后缺少数值")

        elif arg == '--max-duration':
            if i + 1 < len(args_list):
                try:
                    current_max_duration = int(args_list[i + 1])
                    i += 1
                except ValueError:
                    print(f"错误: 无效的最大持续时间: {args_list[i + 1]}")
            else:
                print("错误: --max-duration 参数后缺少数值")

        # 多设备并发回放参数
        elif arg == '--log-dir':
            if i + 1 < len(args_list):
                log_dir = args_list[i + 1]
                i += 1
            else:
                print("错误: --log-dir 参数后缺少目录路径")

        elif arg == '--device':
            if i + 1 < len(args_list):
                device_serial = args_list[i + 1]
                i += 1
            else:
                print("错误: --device 参数后缺少设备序列号")

        elif arg == '--account-user':
            if i + 1 < len(args_list):
                account_user = args_list[i + 1]
                i += 1
            else:
                print("错误: --account-user 参数后缺少用户名")

        elif arg == '--account-pass':
            if i + 1 < len(args_list):
                account_pass = args_list[i + 1]
                i += 1
            else:
                print("错误: --account-pass 参数后缺少密码")

        i += 1

    # 保存最后一个脚本
    if current_script:
        scripts.append({
            'path': current_script,
            'loop_count': current_loop_count,
            'max_duration': current_max_duration
        })

    # 返回解析结果，包括新的多设备参数
    return scripts, {
        'log_dir': log_dir,
        'device_serial': device_serial,
        'account_user': account_user,
        'account_pass': account_pass
    }


def main():
    """主函数 - 支持多设备并发回放和文件日志"""
    import sys

    # 解析脚本参数和多设备参数
    if '--script' not in sys.argv:
        print("❌ 错误: 必须指定 --script 参数")
        print("用法示例:")
        print("  python enhanced_replay_script.py --script testcase/scene1.json")
        print("  python enhanced_replay_script.py --log-dir /path/to/logs --device serial123 --script testcase/scene1.json")
        return

    scripts, multi_device_params = parse_enhanced_arguments(sys.argv[1:])

    if not scripts:
        print("❌ 未找到有效的脚本参数")
        return

    # 提取多设备参数
    log_dir = multi_device_params.get('log_dir')
    device_serial = multi_device_params.get('device_serial')
    account_user = multi_device_params.get('account_user')
    account_pass = multi_device_params.get('account_pass')
    show_screens = '--show-screens' in sys.argv

    # 如果指定了log_dir和device_serial，则启用文件日志模式
    file_logger = None
    if log_dir and device_serial:
        try:
            file_logger = FileLogger(log_dir, device_serial)
            file_logger.log(f"🎬 启动设备 {device_serial} 的脚本回放")

            # 重定向stdout和stderr到文件日志
            original_stdout = sys.stdout
            original_stderr = sys.stderr
            sys.stdout = SafeOutputWrapper(file_logger, "stdout")
            sys.stderr = SafeOutputWrapper(file_logger, "stderr")

            print(f"✅ 文件日志已启用: {log_dir}/{device_serial}.log")
        except Exception as e:
            print(f"⚠️ 文件日志启用失败: {e}")

    exit_code = 0
    report_url = ""

    try:
        print("🎬 启动增强版脚本回放")
        print(f"📝 将执行 {len(scripts)} 个脚本")

        if account_user:
            print(f"👤 使用账号: {account_user}")
        if device_serial:
            print(f"📱 目标设备: {device_serial}")

        # 验证脚本文件存在
        missing_scripts = []
        for script in scripts:
            if not os.path.exists(script['path']):
                missing_scripts.append(script['path'])

        if missing_scripts:
            print("❌ 以下脚本文件不存在:")
            for path in missing_scripts:
                print(f"  - {path}")
            exit_code = -1
        else:
            # 获取连接的设备
            try:
                devices = adb.device_list()

                if not devices:
                    print("❌ 未找到连接的设备")
                    exit_code = -1
                else:
                    print(f"📱 找到 {len(devices)} 个设备")

                    # 如果指定了特定设备，检查是否存在
                    if device_serial:
                        device_found = any(d.serial == device_serial for d in devices)
                        if not device_found:
                            print(f"❌ 指定的设备 {device_serial} 未找到")
                            exit_code = -1
                        else:
                            print(f"✅ 使用指定设备: {device_serial}")

                    # 这里可以调用原始的replay_script.py来执行实际的脚本
                    # 现在先模拟执行成功
                    if exit_code == 0:
                        print("✅ 脚本回放执行完成（模拟）")
                        # 实际实现中，这里应该调用原始的replay_script.py
                        # 或者复制其核心逻辑

            except Exception as e:
                print(f"❌ 设备操作失败: {e}")
                exit_code = -1

    except Exception as e:
        print(f"❌ 脚本回放过程出错: {e}")
        exit_code = -1
    finally:
        # 资源清理和结果写入
        if file_logger and log_dir and device_serial:
            try:
                # 恢复原始输出流
                if 'original_stdout' in locals():
                    sys.stdout = original_stdout
                if 'original_stderr' in locals():
                    sys.stderr = original_stderr

                # 写入结果文件
                result_data = {
                    "exit_code": exit_code,
                    "report_url": report_url,
                    "device": device_serial,
                    "timestamp": time.time()
                }
                write_result(log_dir, device_serial, result_data)
                file_logger.log(f"✅ 结果已写入: {result_data}")
            except Exception as e:
                print(f"⚠️ 结果写入失败: {e}")

        print("🏁 脚本回放任务结束")


if __name__ == "__main__":
    main()
