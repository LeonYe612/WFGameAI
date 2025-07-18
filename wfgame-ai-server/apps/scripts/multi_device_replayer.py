# -*- coding: utf-8 -*-
"""
多设备并发脚本回放器
专门用于多进程并发执行脚本回放，避免循环导入问题
🔧 已修复：集成统一报告管理系统，解决设备报告目录创建问题
"""

import os
import sys
import time
from datetime import datetime
from multiprocessing import Process, Manager
import multiprocessing

# 🔧 新增：禁用第三方库DEBUG日志
try:
    from disable_debug_logs import setup_clean_logging
    setup_clean_logging()
except ImportError:
    # 如果导入失败，使用简单的配置
    import logging
    logging.getLogger('airtest').setLevel(logging.WARNING)
    logging.getLogger('airtest.core.android.adb').setLevel(logging.WARNING)


def device_worker(device_serial, scripts, shared_results):
    """
    设备工作进程 - 每台设备独立执行所有脚本
    🔧 已修复：集成统一报告管理系统，创建设备报告目录

    Args:
        device_serial: 设备序列号
        scripts: 脚本配置列表
        shared_results: 共享结果字典
    """
    try:
        # 在子进程中重新导入必要模块，避免循环导入
        from adbutils import adb

        # 🔧 新增：导入统一报告管理系统
        try:
            # 确保当前目录在 Python 路径中
            current_dir = os.path.dirname(os.path.abspath(__file__))
            if current_dir not in sys.path:
                sys.path.insert(0, current_dir)

            # 导入报告管理系统
            project_root = os.path.dirname(os.path.dirname(current_dir))
            reports_path = os.path.join(project_root, 'apps', 'reports')
            if reports_path not in sys.path:
                sys.path.insert(0, reports_path)

            from report_manager import ReportManager
            from action_processor import ActionProcessor

            # 初始化报告管理器
            report_manager = ReportManager()

        except ImportError as e:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[进程 {os.getpid()}][{timestamp}] 报告系统导入失败: {e}")
            # 继续执行，但不生成报告
            report_manager = None

        # 安全导入ActionProcessor
        try:
            from action_processor import ActionProcessor
        except ImportError as e:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[进程 {os.getpid()}][{timestamp}] 无法导入 ActionProcessor: {e}")
            shared_results[device_serial] = {
                'success': False,
                'error': f'导入失败: {e}',
                'device_report_dir': None
            }
            return

        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[进程 {os.getpid()}][{timestamp}] 设备 {device_serial} 开始处理")

        # 🔧 新增：为设备创建报告目录
        device_report_dir = None
        if report_manager:
            try:
                # 清理设备名称作为目录名
                clean_device_name = "".join(c for c in device_serial if c.isalnum() or c in ('-', '_', '.'))
                if not clean_device_name:
                    clean_device_name = f"device_{abs(hash(device_serial)) % 10000}"

                device_report_dir = report_manager.create_device_report_dir(clean_device_name)
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"[进程 {os.getpid()}][{timestamp}] 设备 {device_serial} 报告目录创建: {device_report_dir}")

            except Exception as e:
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"[进程 {os.getpid()}][{timestamp}] 设备 {device_serial} 报告目录创建失败: {e}")

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
                'error': '设备连接失败',
                'device_report_dir': device_report_dir
            }
            return

        # 分配账号（使用Windows兼容的跨进程安全账号管理器）
        try:
            try:
                # 优先尝试跨平台版本
                from cross_process_account_manager import get_cross_process_account_manager
                account_manager = get_cross_process_account_manager()
            except ImportError:
                # 在Windows上使用Windows专用版本
                from windows_cross_process_account_manager import get_windows_cross_process_account_manager
                account_manager = get_windows_cross_process_account_manager()

            device_account = account_manager.allocate_account(device_serial)

            timestamp = datetime.now().strftime("%H:%M:%S")
            if device_account:
                print(f"[进程 {os.getpid()}][{timestamp}] 设备 {device_serial} 分配账号: {device_account.get('username', 'N/A')}")
            else:
                print(f"[进程 {os.getpid()}][{timestamp}] 设备 {device_serial} 账号分配失败")

        except Exception as alloc_e:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[进程 {os.getpid()}][{timestamp}] 设备 {device_serial} 账号分配异常: {alloc_e}")
            device_account = None

        # 尝试导入AI检测功能
        detect_buttons_func = None
        try:
            # 尝试导入AI检测函数
            from replay_script import detect_buttons, load_yolo_model_for_detection

            # 初始化YOLO模型
            if load_yolo_model_for_detection():
                detect_buttons_func = detect_buttons
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"[进程 {os.getpid()}][{timestamp}] 设备 {device_serial} AI检测功能已加载")
            else:
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"[进程 {os.getpid()}][{timestamp}] 设备 {device_serial} YOLO模型加载失败")

        except ImportError as e:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[进程 {os.getpid()}][{timestamp}] 设备 {device_serial} AI检测功能导入失败: {e}")
        except Exception as e:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[进程 {os.getpid()}][{timestamp}] 设备 {device_serial} AI检测功能初始化异常: {e}")
            # 🔧 修复：创建ActionProcessor实例时设置log_txt_path
        log_txt_path = None

        if device_report_dir:
            # 🔧 修复：直接在设备目录下创建log.txt，不创建log子目录
            log_txt_path = os.path.join(str(device_report_dir), "log.txt")
            print(f"[进程 {os.getpid()}][{timestamp}] 设备 {device_serial} 日志文件路径: {log_txt_path}")

        action_processor = ActionProcessor(
            device=device,
            device_name=device_serial,
            log_txt_path=log_txt_path,
            detect_buttons_func=detect_buttons_func
        )

        # 如果有分配到账号，设置到ActionProcessor
        if device_account:
            action_processor.set_device_account(device_account)        # 执行脚本列表
        total_success = 0
        total_failed = 0
        executed_scripts = []
        script_execution_success = True  # 新增：脚本执行状态标记

        for script_config in scripts:
            script_path = script_config.get('path')
            loop_count = script_config.get('loop_count', 1)
            max_duration = script_config.get('max_duration')

            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[进程 {os.getpid()}][{timestamp}] 设备 {device_serial} 开始执行脚本: {os.path.basename(script_path)}")

            try:
                # 🔧 修改：传递设备报告目录到ActionProcessor
                if device_report_dir and hasattr(action_processor, 'set_device_report_dir'):
                    action_processor.set_device_report_dir(device_report_dir)                # 执行脚本 - 使用正确的方法名
                result = action_processor.process_script(script_path)

                # 处理返回结果
                if hasattr(result, 'success'):
                    if result.success:
                        success_count = 1
                        failed_count = 0
                    else:
                        success_count = 0
                        failed_count = 1
                else:
                    # 兼容其他返回格式
                    success_count = 1 if result else 0
                    failed_count = 0 if result else 1

                total_success += success_count
                total_failed += failed_count
                executed_scripts.append({
                    'script': os.path.basename(script_path),
                    'success': success_count,
                    'failed': failed_count
                })

                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"[进程 {os.getpid()}][{timestamp}] 设备 {device_serial} 脚本执行完成 - 成功:{success_count}, 失败:{failed_count}")

            except Exception as e:
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"[进程 {os.getpid()}][{timestamp}] 设备 {device_serial} 脚本执行异常: {e}")
                total_failed += 1
                # 脚本执行异常时，标记为执行失败
                if "读取脚本失败" in str(e) or "脚本文件不存在" in str(e):
                    script_execution_success = False

        # 释放分配的账号
        if device_account:
            try:
                account_manager.release_account(device_serial)
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"[进程 {os.getpid()}][{timestamp}] 设备 {device_serial} 账号已释放（跨进程）")
            except Exception as e:
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"[进程 {os.getpid()}][{timestamp}] 设备 {device_serial} 账号释放失败: {e}")

        # 🔧 新增：生成设备HTML报告
        if report_manager and device_report_dir:
            try:
                from report_generator import ReportGenerator
                report_generator = ReportGenerator(report_manager)

                # 准备脚本配置用于报告生成
                script_configs = []
                for script_config in scripts:
                    script_configs.append({
                        'path': script_config.get('path'),
                        'loop_count': script_config.get('loop_count', 1),
                        'max_duration': script_config.get('max_duration')
                    })

                # 生成设备HTML报告
                html_report = report_generator.generate_device_html_report(
                    device_name=clean_device_name,
                    device_dir=device_report_dir
                )

                if html_report:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    print(f"[进程 {os.getpid()}][{timestamp}] 设备 {device_serial} HTML报告生成成功")

            except Exception as e:
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"[进程 {os.getpid()}][{timestamp}] 设备 {device_serial} HTML报告生成失败: {e}")        # 返回执行结果
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[进程 {os.getpid()}][{timestamp}] 设备 {device_serial} 回放完成 - 成功:{total_success}, 失败:{total_failed}")

        # 修改成功判断逻辑：分离脚本执行状态与步骤执行结果
        # 只要脚本能够成功读取和处理，就认为脚本执行成功
        # 步骤执行的成败不影响脚本执行的成功状态
        device_success = script_execution_success  # 基于脚本执行状态，而非步骤成功率

        shared_results[device_serial] = {
            'success': device_success,  # 修改：使用脚本执行状态而非步骤成功率
            'total_success': total_success,
            'total_failed': total_failed,
            'executed_scripts': executed_scripts,
            'device_report_dir': str(device_report_dir) if device_report_dir else None,  # 🔧 新增：返回设备报告目录路径
            'script_execution_success': script_execution_success,  # 新增：明确的脚本执行状态
            'step_success_rate': total_success / (total_success + total_failed) if (total_success + total_failed) > 0 else 0  # 新增：步骤成功率
        }

    except Exception as e:
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[进程 {os.getpid()}][{timestamp}] 设备 {device_serial} 处理异常: {e}")
        import traceback
        traceback.print_exc()
        shared_results[device_serial] = {
            'success': False,
            'error': str(e),
            'device_report_dir': None
        }


def replay_scripts_on_devices(device_serials, scripts, max_workers=4, strategy="hybrid"):
    """
    多设备并发回放：所有设备依次执行同一批脚本
    🔧 新增：支持智能混合执行策略
    🔧 已修复：返回设备报告目录列表用于汇总报告生成

    Args:
        device_serials: 设备序列号列表
        scripts: 脚本路径列表
        max_workers: 最大并发进程数（传统模式使用）
        strategy: 执行策略 ("hybrid", "unlimited", "intelligent", "traditional")

    Returns:
        tuple: (results_dict, device_report_dirs_list)
    """
    # 智能混合执行策略
    if strategy in ["hybrid", "unlimited", "intelligent"]:
        try:
            from optimized_hybrid_executor import replay_scripts_on_devices_hybrid

            print(f"🚀 使用智能混合执行策略: {strategy}")
            return replay_scripts_on_devices_hybrid(device_serials, scripts, strategy)

        except ImportError as e:
            print(f"❌ 智能混合执行器导入失败，回退到传统模式: {e}")
            strategy = "traditional"

    # 传统执行模式
    if strategy == "traditional":
        print(f"🔧 使用传统并发模式，max_workers={max_workers}")

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

        # 🔧 新增：收集设备报告目录路径
        device_report_dirs = []
        for device_serial, result in results.items():
            device_report_dir = result.get('device_report_dir')
            if device_report_dir:
                from pathlib import Path
                device_report_dirs.append(Path(device_report_dir))

        # 统计结果
        success_count = sum(1 for r in results.values() if r.get('success', False))
        total_success_ops = sum(r.get('total_success', 0) for r in results.values())
        total_failed_ops = sum(r.get('total_failed', 0) for r in results.values())

        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] ✅ 多设备并发回放完成")
        print(f"📊 成功设备: {success_count}/{len(device_serials)}")
        print(f"📊 成功操作: {total_success_ops}, 失败操作: {total_failed_ops}")
        print(f"📂 生成设备报告: {len(device_report_dirs)} 个")  # 🔧 新增：报告目录数量

        return results, device_report_dirs  # 🔧 修改：返回结果和设备报告目录列表


if __name__ == "__main__":
    import argparse

    # 处理命令行参数
    parser = argparse.ArgumentParser(description='多设备并发脚本回放')
    parser.add_argument('script_path', nargs='?', default=None, help='脚本文件路径')
    parser.add_argument('--max-workers', type=int, default=4, help='最大并发进程数（传统模式）')
    parser.add_argument('--loop-count', type=int, default=1, help='脚本循环次数')
    parser.add_argument('--strategy', choices=['hybrid', 'unlimited', 'intelligent', 'traditional'],
                       default='hybrid', help='执行策略选择')

    args = parser.parse_args()

    # 测试用例
    from adbutils import adb

    # 获取连接的设备
    devices = adb.device_list()
    if not devices:
        print("❌ 未找到连接的设备")
        exit(1)

    device_serials = [device.serial for device in devices]

    # 确定要执行的脚本
    if args.script_path:
        script_path = args.script_path
        # 如果没有testcase前缀，自动添加
        if not script_path.startswith('testcase/') and not script_path.startswith('testcase\\'):
            script_path = os.path.join('testcase', script_path)
    else:
        # 默认脚本
        script_path = "testcase/4_main_page_guide_steps_updated.json"

    # 检查脚本文件是否存在
    if not os.path.exists(script_path):
        print(f"❌ 脚本文件不存在: {script_path}")
        exit(1)

    # 构建脚本配置
    scripts = [{
        'path': script_path,
        'loop_count': args.loop_count,
        'max_duration': None
    }]

    print(f"📱 找到 {len(device_serials)} 个设备: {device_serials}")
    print(f"📜 将执行脚本: {script_path}")
    print(f"🔄 循环次数: {args.loop_count}")
    print(f"⚙️ 执行策略: {args.strategy}")

    # 执行多设备并发回放
    results, device_report_dirs = replay_scripts_on_devices(
        device_serials, scripts, args.max_workers, args.strategy
    )

    # 显示结果
    print("\n📊 执行结果:")
    for device_serial, result in results.items():
        status = "✅ 成功" if result.get('success') else "❌ 失败"
        print(f"  {device_serial}: {status}")
        if not result.get('success') and 'error' in result:
            print(f"    错误: {result['error']}")

    print(f"\n📂 生成的设备报告目录: {len(device_report_dirs)} 个")
    for report_dir in device_report_dirs:
        print(f"  {report_dir}")
