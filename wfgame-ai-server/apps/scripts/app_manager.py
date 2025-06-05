#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用生命周期管理器命令行工具
提供便捷的应用启动/停止/监控功能
"""

import sys
import os
import json
import argparse
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_lifecycle_manager import AppLifecycleManager, AppTemplate


def print_status_table(status_data):
    """打印状态表格"""
    if not status_data:
        print("没有运行中的应用")
        return

    print("\n应用运行状态:")
    print("-" * 100)
    print(f"{'设备':<20} {'应用包名':<30} {'状态':<12} {'启动时间':<20} {'重启次数':<8}")
    print("-" * 100)

    for instance_key, info in status_data.items():
        device = info['device_serial']
        package = info['package_name']
        state = info['state']
        start_time = info['start_time']
        restart_count = info['restart_count']

        start_time_str = ""
        if start_time:
            import time
            start_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time))

        print(f"{device:<20} {package:<30} {state:<12} {start_time_str:<20} {restart_count:<8}")

        if info['error_message']:
            print(f"{'':>20} 错误信息: {info['error_message']}")

    print("-" * 100)


def list_templates(manager):
    """列出所有模板"""
    templates = manager.get_app_templates()

    if not templates:
        print("没有找到应用模板")
        return

    print("\n可用的应用模板:")
    print("-" * 80)
    print(f"{'模板名称':<20} {'应用包名':<30} {'描述':<20}")
    print("-" * 80)

    for name, template in templates.items():
        description = template.custom_params.get('description', '') if template.custom_params else ''
        print(f"{name:<20} {template.package_name:<30} {description:<20}")

    print("-" * 80)


def list_devices():
    """列出连接的设备"""
    import subprocess

    try:
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
        if result.returncode != 0:
            print("无法获取设备列表，请确保ADB已安装并正常运行")
            return []

        lines = result.stdout.strip().split('\n')[1:]  # 跳过标题行
        devices = []

        for line in lines:
            if line.strip() and '\t' in line:
                device_id, status = line.split('\t')
                if status.strip() == 'device':
                    devices.append(device_id.strip())

        if devices:
            print("\n连接的设备:")
            for i, device in enumerate(devices, 1):
                print(f"  {i}. {device}")
        else:
            print("没有找到连接的设备")

        return devices

    except Exception as e:
        print(f"获取设备列表失败: {e}")
        return []


def interactive_mode(manager):
    """交互模式"""
    print("\n=== 应用生命周期管理器 - 交互模式 ===")

    while True:
        print("\n请选择操作:")
        print("1. 启动应用")
        print("2. 停止应用")
        print("3. 重启应用")
        print("4. 查看状态")
        print("5. 列出模板")
        print("6. 列出设备")
        print("7. 创建新模板")
        print("0. 退出")

        choice = input("\n请输入选择 (0-7): ").strip()

        try:
            if choice == "0":
                break
            elif choice == "1":
                _interactive_start_app(manager)
            elif choice == "2":
                _interactive_stop_app(manager)
            elif choice == "3":
                _interactive_restart_app(manager)
            elif choice == "4":
                status = manager.get_app_status()
                print_status_table(status)
            elif choice == "5":
                list_templates(manager)
            elif choice == "6":
                list_devices()
            elif choice == "7":
                _interactive_create_template(manager)
            else:
                print("无效选择，请重新输入")

        except KeyboardInterrupt:
            print("\n\n操作已取消")
        except Exception as e:
            print(f"\n操作出错: {e}")


def _interactive_start_app(manager):
    """交互式启动应用"""
    list_templates(manager)
    template_name = input("\n请输入模板名称: ").strip()

    if not template_name or template_name not in manager.get_app_templates():
        print("无效的模板名称")
        return

    devices = list_devices()
    if not devices:
        return

    if len(devices) == 1:
        device_serial = devices[0]
    else:
        try:
            choice = int(input("\n请选择设备 (输入序号): ").strip())
            if 1 <= choice <= len(devices):
                device_serial = devices[choice - 1]
            else:
                print("无效的设备选择")
                return
        except ValueError:
            print("请输入有效的数字")
            return

    print(f"\n正在启动应用 {template_name} 到设备 {device_serial}...")
    success = manager.start_app(template_name, device_serial)
    print(f"启动{'成功' if success else '失败'}")


def _interactive_stop_app(manager):
    """交互式停止应用"""
    status = manager.get_app_status()
    if not status:
        print("没有运行中的应用")
        return

    print_status_table(status)

    print("\n可停止的应用:")
    running_apps = [(key, info) for key, info in status.items()
                   if info['state'] in ['running', 'starting']]

    if not running_apps:
        print("没有可停止的应用")
        return

    for i, (key, info) in enumerate(running_apps, 1):
        print(f"  {i}. {info['device_serial']} - {info['package_name']}")

    try:
        choice = int(input("\n请选择要停止的应用 (输入序号): ").strip())
        if 1 <= choice <= len(running_apps):
            key, info = running_apps[choice - 1]

            # 找到对应的模板
            template_name = None
            for name, template in manager.get_app_templates().items():
                if template.package_name == info['package_name']:
                    template_name = name
                    break

            if template_name:
                print(f"\n正在停止应用 {template_name}...")
                success = manager.stop_app(template_name, info['device_serial'])
                print(f"停止{'成功' if success else '失败'}")
            else:
                print("找不到对应的模板")
        else:
            print("无效的选择")
    except ValueError:
        print("请输入有效的数字")


def _interactive_restart_app(manager):
    """交互式重启应用"""
    status = manager.get_app_status()
    if not status:
        print("没有应用实例")
        return

    print_status_table(status)

    print("\n可重启的应用:")
    for i, (key, info) in enumerate(status.items(), 1):
        print(f"  {i}. {info['device_serial']} - {info['package_name']} ({info['state']})")

    try:
        choice = int(input("\n请选择要重启的应用 (输入序号): ").strip())
        apps = list(status.items())
        if 1 <= choice <= len(apps):
            key, info = apps[choice - 1]

            # 找到对应的模板
            template_name = None
            for name, template in manager.get_app_templates().items():
                if template.package_name == info['package_name']:
                    template_name = name
                    break

            if template_name:
                print(f"\n正在重启应用 {template_name}...")
                success = manager.restart_app(template_name, info['device_serial'])
                print(f"重启{'成功' if success else '失败'}")
            else:
                print("找不到对应的模板")
        else:
            print("无效的选择")
    except ValueError:
        print("请输入有效的数字")


def _interactive_create_template(manager):
    """交互式创建模板"""
    print("\n=== 创建新应用模板 ===")

    name = input("模板名称: ").strip()
    if not name:
        print("模板名称不能为空")
        return

    package_name = input("应用包名: ").strip()
    if not package_name:
        print("应用包名不能为空")
        return

    activity_name = input("Activity名称 (可选): ").strip() or None

    try:
        startup_wait_time = int(input("启动等待时间 (秒, 默认5): ").strip() or "5")
        max_restart_attempts = int(input("最大重启次数 (默认3): ").strip() or "3")
        health_check_interval = int(input("健康检查间隔 (秒, 默认30): ").strip() or "30")
    except ValueError:
        print("请输入有效的数字")
        return

    description = input("描述 (可选): ").strip()

    template_data = {
        "name": name,
        "package_name": package_name,
        "activity_name": activity_name,
        "startup_wait_time": startup_wait_time,
        "max_restart_attempts": max_restart_attempts,
        "health_check_interval": health_check_interval,
        "custom_params": {
            "description": description
        } if description else {}
    }

    if manager.create_app_template(template_data):
        print(f"\n模板 '{name}' 创建成功！")
    else:
        print("\n模板创建失败")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="应用生命周期管理器")
    parser.add_argument("--action", choices=["start", "stop", "restart", "status", "list-templates", "list-devices", "interactive"],
                       help="操作类型")
    parser.add_argument("--template", help="应用模板名称")
    parser.add_argument("--device", help="设备序列号")
    parser.add_argument("--config", help="配置文件路径")

    args = parser.parse_args()

    # 如果没有指定参数，进入交互模式
    if len(sys.argv) == 1:
        args.action = "interactive"

    manager = AppLifecycleManager(args.config)

    try:
        if args.action == "interactive":
            interactive_mode(manager)

        elif args.action == "list-templates":
            list_templates(manager)

        elif args.action == "list-devices":
            list_devices()

        elif args.action == "status":
            status = manager.get_app_status(args.template, args.device)
            print_status_table(status)

        elif args.action in ["start", "stop", "restart"]:
            if not args.template:
                print(f"操作 {args.action} 需要指定 --template")
                return 1

            if not args.device:
                devices = list_devices()
                if len(devices) == 1:
                    args.device = devices[0]
                    print(f"自动选择设备: {args.device}")
                else:
                    print(f"操作 {args.action} 需要指定 --device")
                    return 1

            if args.action == "start":
                success = manager.start_app(args.template, args.device)
                print(f"启动应用: {'成功' if success else '失败'}")

            elif args.action == "stop":
                success = manager.stop_app(args.template, args.device)
                print(f"停止应用: {'成功' if success else '失败'}")

            elif args.action == "restart":
                success = manager.restart_app(args.template, args.device)
                print(f"重启应用: {'成功' if success else '失败'}")

            return 0 if success else 1

        else:
            parser.print_help()
            return 1

    except KeyboardInterrupt:
        print("\n操作已取消")
        return 1
    except Exception as e:
        print(f"执行出错: {e}")
        return 1

    finally:
        manager.cleanup()

    return 0


if __name__ == "__main__":
    sys.exit(main())
