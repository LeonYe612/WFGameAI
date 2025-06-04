#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
USB连接检查工具
检查Android设备的USB连接状态和模式
"""

import subprocess
import time
import sys

def check_usb_connection():
    """检查USB连接状态"""
    print("=" * 60)
    print("WFGameAI USB连接检查工具")
    print("=" * 60)

    print("\n🔍 正在检查ADB服务状态...")
    try:
        # 启动ADB服务
        subprocess.run("adb start-server", shell=True, check=True)
        print("✅ ADB服务已启动")
    except Exception as e:
        print(f"❌ ADB服务启动失败: {e}")
        return False

    print("\n🔍 正在检查连接的设备...")
    try:
        result = subprocess.run("adb devices", shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        print("ADB设备列表：")
        print(result.stdout)

        # 解析设备列表
        devices = []
        for line in result.stdout.split('\n')[1:]:
            if line.strip() and '\t' in line:
                device_id, status = line.split('\t')
                devices.append((device_id.strip(), status.strip()))

        if not devices:
            print("❌ 未检测到任何设备")
            print("\n💡 可能的原因：")
            print("1. USB线未连接或连接不良")
            print("2. USB连接模式选择错误（当前为'仅充电'）")
            print("3. USB调试功能未开启")
            print("4. 驱动程序问题")
            print("\n🔧 解决步骤：")
            show_usb_setup_guide()
            return False

        print(f"\n✅ 检测到 {len(devices)} 个设备:")
        for device_id, status in devices:
            status_icon = "✅" if status == "device" else "⚠️" if status == "unauthorized" else "❌"
            print(f"  {status_icon} {device_id}: {status}")

            if status == "unauthorized":
                print(f"    📱 设备 {device_id} 需要授权USB调试")
            elif status == "offline":
                print(f"    🔌 设备 {device_id} 连接异常，可能是USB模式问题")

        return len([d for d in devices if d[1] == "device"]) > 0

    except Exception as e:
        print(f"❌ 检查设备失败: {e}")
        return False

def show_usb_setup_guide():
    """显示USB设置指南"""
    print("\n" + "=" * 60)
    print("📱 Android设备USB连接设置指南")
    print("=" * 60)

    print("""
步骤1: 检查USB连接模式
┌─────────────────────────────────────────┐
│  当手机连接到电脑时，会弹出选择界面：      │
│                                         │
│  选择USB连接方式                        │
│  ○ 仅充电               ← ❌ 不选择此项  │
│  ● 传输文件 (MTP)       ← ✅ 选择此项   │
│  ○ 传输照片 (PTP)       ← ✅ 也可以     │
│  ○ USB网络共享                          │
│  ○ MIDI                                 │
└─────────────────────────────────────────┘

步骤2: 开启USB调试
1. 进入手机"设置"
2. 找到"关于手机"或"关于设备"
3. 连续点击"版本号"7次，开启开发者模式
4. 返回设置主界面
5. 找到"开发者选项"或"开发人员选项"
6. 开启"USB调试"开关

步骤3: 确认授权
1. 重新连接USB线
2. 手机屏幕会弹出"允许USB调试"对话框
3. 勾选"始终允许来自这台计算机"
4. 点击"允许"

步骤4: 验证连接
运行命令: adb devices
正确输出应该类似：
List of devices attached
SM-G973F        device
""")

def check_device_details(device_id):
    """检查设备详细信息"""
    print(f"\n🔍 检查设备 {device_id} 的详细信息...")

    try:
        # 获取设备型号
        result = subprocess.run(f"adb -s {device_id} shell getprop ro.product.model",
                              shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        if result.returncode == 0:
            model = result.stdout.strip()
            print(f"  📱 设备型号: {model}")

        # 获取Android版本
        result = subprocess.run(f"adb -s {device_id} shell getprop ro.build.version.release",
                              shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"  🤖 Android版本: {version}")

        # 检查USB调试状态
        result = subprocess.run(f"adb -s {device_id} shell getprop persist.adb.tcp.port",
                              shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        tcp_port = result.stdout.strip() if result.returncode == 0 else "未设置"
        print(f"  🔌 TCP端口: {tcp_port}")

        # 获取设备IP地址
        result = subprocess.run(f"adb -s {device_id} shell ip route | grep wlan",
                              shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        if result.returncode == 0 and result.stdout.strip():
            print(f"  🌐 网络连接: 已连接WiFi")
            # 尝试获取IP地址
            ip_result = subprocess.run(f"adb -s {device_id} shell ip addr show wlan0 | grep 'inet '",
                                     shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            if ip_result.returncode == 0:
                import re
                ip_match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)', ip_result.stdout)
                if ip_match:
                    ip = ip_match.group(1)
                    print(f"  📡 设备IP: {ip}")
        else:
            print(f"  🌐 网络连接: 未连接WiFi或无法获取")

        return True

    except Exception as e:
        print(f"  ❌ 获取设备信息失败: {e}")
        return False

def test_adb_commands(device_id):
    """测试基本ADB命令"""
    print(f"\n🧪 测试设备 {device_id} 的ADB功能...")

    tests = [
        ("shell echo 'Hello'", "基本shell命令"),
        ("shell ls /sdcard", "文件系统访问"),
        ("shell input keyevent 26", "输入事件（电源键）"),
        ("shell screencap -p", "屏幕截图功能")
    ]

    success_count = 0
    for cmd, desc in tests:
        try:
            result = subprocess.run(f"adb -s {device_id} {cmd}",
                                  shell=True, capture_output=True, text=True, timeout=10, encoding='utf-8', errors='ignore')
            if result.returncode == 0:
                print(f"  ✅ {desc}: 成功")
                success_count += 1
            else:
                print(f"  ❌ {desc}: 失败 - {result.stderr.strip()}")
        except subprocess.TimeoutExpired:
            print(f"  ⏰ {desc}: 超时")
        except Exception as e:
            print(f"  ❌ {desc}: 异常 - {e}")

    print(f"\n📊 测试结果: {success_count}/{len(tests)} 项通过")
    return success_count == len(tests)

def main():
    """主函数"""
    if not check_usb_connection():
        print("\n❌ USB连接检查失败，请根据上述指南进行设置")
        return 1

    # 获取已连接的设备
    try:
        result = subprocess.run("adb devices", shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        devices = []
        for line in result.stdout.split('\n')[1:]:
            if line.strip() and '\t' in line:
                device_id, status = line.split('\t')
                if status.strip() == "device":
                    devices.append(device_id.strip())

        if not devices:
            print("\n⚠️ 没有可用的授权设备")
            return 1

        # 对每个设备进行详细检查
        print("\n" + "=" * 60)
        print("📋 设备详细检查")
        print("=" * 60)

        all_passed = True
        for device_id in devices:
            print(f"\n--- 设备: {device_id} ---")
            if not check_device_details(device_id):
                all_passed = False
            if not test_adb_commands(device_id):
                all_passed = False

        if all_passed:
            print("\n🎉 所有设备检查通过！设备已准备就绪。")
            print("💡 现在可以运行 WFGameAI 进行自动化测试了。")
            return 0
        else:
            print("\n⚠️ 部分设备存在问题，请检查设备设置。")
            return 1

    except Exception as e:
        print(f"\n❌ 设备检查过程中出现错误: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
