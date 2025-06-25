# -*- coding: utf-8 -*-
"""
多设备并发脚本回放器
专门用于多进程并发执行脚本回放，避免循环导入问题
"""

import os
import sys
import time
from datetime import datetime
from multiprocessing import Process, Manager
import multiprocessing


def device_worker(device_serial, scripts, shared_results):
    """
    设备工作进程 - 每台设备独立执行所有脚本

    Args:
        device_serial: 设备序列号
        scripts: 脚本配置列表
        shared_results: 共享结果字典
    """
    try:
        # 在子进程中重新导入必要模块，避免循环导入
        from adbutils import adb

        # 安全导入 DeviceScriptReplayer
        try:
            # 确保当前目录在 Python 路径中
            current_dir = os.path.dirname(os.path.abspath(__file__))
            if current_dir not in sys.path:
                sys.path.insert(0, current_dir)

            from enhanced_input_handler import DeviceScriptReplayer
        except ImportError as e:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[进程 {os.getpid()}][{timestamp}] 无法导入 DeviceScriptReplayer: {e}")
            shared_results[device_serial] = {
                'success': False,
                'error': f'导入失败: {e}'
            }
            return

        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[进程 {os.getpid()}][{timestamp}] 设备 {device_serial} 开始处理")

        # 获取设备连接
        device = None
        for dev in adb.device_list():
            if dev.serial == device_serial:
                device = dev
                break

        if not device:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[进程 {os.getpid()}][{timestamp}] 设备 {device_serial} 连接失败")
            shared_results[device_serial] = {
                'success': False,
                'error': '设备连接失败'
            }
            return        # 创建 DeviceScriptReplayer 实例 - 标记为多设备模式
        replayer = DeviceScriptReplayer(device_serial, is_multi_device_mode=True)

        # 执行每个脚本
        has_execution = False
        total_success = 0
        total_failed = 0

        for script_config in scripts:
            script_path = script_config["path"]
            script_loop_count = script_config.get("loop_count", 1)

            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[进程 {os.getpid()}][{timestamp}] 设备 {device_serial} 开始执行脚本: {os.path.basename(script_path)}")

            # 循环执行脚本
            for loop in range(script_loop_count):
                if script_loop_count > 1:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    print(f"[进程 {os.getpid()}][{timestamp}] 设备 {device_serial} 第 {loop+1}/{script_loop_count} 次循环")

                try:
                    result = replayer.replay_single_script(script_path)
                    if result:
                        has_execution = True
                        total_success += 1
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        print(f"[进程 {os.getpid()}][{timestamp}] 设备 {device_serial} 脚本执行成功")
                    else:
                        total_failed += 1
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        print(f"[进程 {os.getpid()}][{timestamp}] 设备 {device_serial} 脚本执行失败")

                    time.sleep(1.0)  # 循环间短暂等待

                except Exception as e:
                    total_failed += 1
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    print(f"[进程 {os.getpid()}][{timestamp}] 设备 {device_serial} 脚本执行异常: {e}")

        # 记录最终结果
        if has_execution:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[进程 {os.getpid()}][{timestamp}] 设备 {device_serial} 回放完成 - 成功:{total_success}, 失败:{total_failed}")
            shared_results[device_serial] = {
                'success': True,
                'total_success': total_success,
                'total_failed': total_failed
            }
        else:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[进程 {os.getpid()}][{timestamp}] 设备 {device_serial} 未执行任何操作")
            shared_results[device_serial] = {
                'success': False,
                'total_success': 0,
                'total_failed': total_failed
            }

    except Exception as e:
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[进程 {os.getpid()}][{timestamp}] 设备 {device_serial} 工作进程异常: {e}")
        import traceback
        traceback.print_exc()
        shared_results[device_serial] = {
            'success': False,
            'error': str(e),
            'total_success': 0,
            'total_failed': 1
        }


def replay_scripts_on_devices(device_serials, scripts, max_workers=4):
    """
    多设备并发回放：所有设备依次执行同一批脚本

    Args:
        device_serials: 设备序列号列表
        scripts: 脚本路径列表
        max_workers: 最大并发进程数

    Returns:
        dict: 每台设备的执行结果
    """
    # Windows 下需要设置启动方法
    if hasattr(multiprocessing, 'set_start_method'):
        try:
            multiprocessing.set_start_method('spawn', force=True)
        except RuntimeError:
            # 启动方法已经设置过了
            pass

    print(f"🚀 启动多设备并发回放，设备数量: {len(device_serials)}")

    # 使用Manager创建共享结果字典
    with Manager() as manager:
        shared_results = manager.dict()
        processes = []

        # 为每台设备创建独立进程
        for i, device_serial in enumerate(device_serials):
            p = Process(
                target=device_worker,
                args=(device_serial, scripts, shared_results)
            )
            p.daemon = True
            processes.append(p)
            p.start()

            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] 已启动设备 {device_serial} 的回放进程，PID: {p.pid}")

            # 错峰启动，避免瞬时ADB冲突
            time.sleep(0.3)

        # 等待所有进程完成
        print(f"⏳ 等待 {len(processes)} 个进程完成...")
        for i, p in enumerate(processes):
            p.join()
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] 进程 {i+1}/{len(processes)} 已完成")

        # 收集并返回结果
        results = dict(shared_results)

        # 统计结果
        success_count = sum(1 for r in results.values() if r.get('success', False))
        total_success_ops = sum(r.get('total_success', 0) for r in results.values())
        total_failed_ops = sum(r.get('total_failed', 0) for r in results.values())

        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] ✅ 多设备并发回放完成")
        print(f"📊 成功设备: {success_count}/{len(device_serials)}")
        print(f"📊 成功操作: {total_success_ops}, 失败操作: {total_failed_ops}")

        return results


if __name__ == "__main__":
    import argparse

    # 处理命令行参数
    parser = argparse.ArgumentParser(description='多设备并发脚本回放')
    parser.add_argument('script_path', nargs='?', default=None, help='脚本文件路径')
    parser.add_argument('--max-workers', type=int, default=4, help='最大并发进程数')
    parser.add_argument('--loop-count', type=int, default=1, help='脚本循环次数')

    args = parser.parse_args()

    # 测试用例
    from adbutils import adb

    # 获取连接的设备
    devices = adb.device_list()
    if not devices:
        print("❌ 未找到连接的设备")
        exit(1)

    device_serials = [device.serial for device in devices]    # 确定要执行的脚本
    if args.script_path:
        script_path = args.script_path
        # 如果没有testcase前缀，自动添加
        if not script_path.startswith('testcase/') and not script_path.startswith('testcase\\'):
            if not script_path.startswith('testcase'):
                script_path = f"testcase/{script_path}"
    else:
        # 提示用户必须指定脚本
        print("❌ 错误: 必须指定脚本文件路径")
        print("用法示例:")
        print("  python multi_device_replayer.py testcase/1_app_start_wetest_and_permission.json")
        print("  python multi_device_replayer.py 1_app_start_wetest_and_permission.json --max-workers 2")
        print("  python multi_device_replayer.py testcase/scene1.json --loop-count 3")
        exit(1)

    # 测试脚本配置
    scripts = [
        {
            "path": script_path,
            "loop_count": args.loop_count
        }
    ]

    print(f"🧪 测试多设备并发回放")
    print(f"📱 设备: {device_serials}")
    print(f"📄 脚本: {[s['path'] for s in scripts]}")
    print(f"🔄 循环次数: {args.loop_count}")
    print(f"⚙️ 最大并发数: {args.max_workers}")

    results = replay_scripts_on_devices(device_serials, scripts, args.max_workers)

    print(f"\n📋 最终结果:")
    for device_serial, result in results.items():
        if result.get('success'):
            print(f"  ✅ {device_serial}: 成功 ({result.get('total_success', 0)} 操作)")
        else:
            error = result.get('error', '未知错误')
            print(f"  ❌ {device_serial}: 失败 - {error}")


class MultiDeviceReplayer:
    """
    多设备并发脚本回放器
    提供面向对象的接口来管理多设备并发回放
    """

    def __init__(self, max_workers=4):
        """
        初始化多设备回放器

        Args:
            max_workers: 最大并发进程数
        """
        self.max_workers = max_workers

    def execute_concurrent_scripts(self, device_configs):
        """
        执行多设备并发脚本回放

        Args:
            device_configs: 设备配置列表，每个配置包含:
                - serial: 设备序列号
                - scripts: 脚本配置列表

        Returns:
            dict: 每台设备的执行结果
        """
        if not device_configs:
            return {}

        # 提取设备序列号和脚本
        device_serials = [config['serial'] for config in device_configs]
        scripts = device_configs[0].get('scripts', [])  # 假设所有设备执行相同脚本

        print(f"🚀 启动 {len(device_serials)} 台设备的并发回放")
        print(f"📱 设备列表: {', '.join(device_serials)}")
        print(f"📄 脚本数量: {len(scripts)}")

        return replay_scripts_on_devices(device_serials, scripts, self.max_workers)

    def execute_single_device(self, device_serial, scripts):
        """
        执行单设备脚本回放（用于测试）

        Args:
            device_serial: 设备序列号
            scripts: 脚本配置列表

        Returns:
            dict: 执行结果
        """
        device_configs = [{
            'serial': device_serial,
            'scripts': scripts
        }]

        results = self.execute_concurrent_scripts(device_configs)
        return results.get(device_serial, {'success': False, 'error': '未知错误'})
