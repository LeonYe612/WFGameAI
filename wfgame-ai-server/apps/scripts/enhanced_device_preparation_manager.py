#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WFGameAI 设备预处理管理器 - 增强版
集成USB连接检查、设备预处理和详细测试报告功能
"""

import os
import sys
import time
import json
import subprocess
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import textwrap

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DeviceTestResult:
    """设备测试结果数据类"""
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.model = "未知"
        self.android_version = "未知"
        self.connection_status = "未知"
        self.authorization_status = "未知"
        self.usb_mode = "未知"
        self.wifi_status = "未知"
        self.ip_address = "未获取"
        self.tcp_port = "未设置"
        self.basic_commands = {}
        self.rsa_configured = False
        self.wireless_enabled = False
        self.overall_status = "失败"

class EnhancedDevicePreparationManager:
    """增强版设备预处理管理器"""

    def __init__(self, config_path: str = None):
        self.config_path = config_path or "config.ini"
        self.adb_keys_path = Path.home() / ".android"
        self.device_info_cache = {}
        self.wireless_connections = {}
        self.test_results: List[DeviceTestResult] = []

    def run_comprehensive_check(self) -> bool:
        """运行综合设备检查和预处理"""
        print("=" * 80)
        print("WFGameAI 设备预处理管理器 - 增强版")
        print("=" * 80)

        try:
            # 1. USB连接检查
            print("\n🔍 第一步：USB连接状态检查")
            if not self._check_usb_connections():
                print("\n❌ USB连接检查失败，请根据指南进行设置")
                self._show_usb_setup_guide()
                return False

            # 2. 设备预处理
            print("\n🔧 第二步：设备预处理和配置")
            success = self._prepare_all_devices()

            # 3. 详细测试
            print("\n🧪 第三步：设备功能测试")
            self._run_detailed_tests()

            # 4. 生成报告
            print("\n📊 第四步：生成测试报告")
            self._generate_test_report()

            return success

        except Exception as e:
            logger.error(f"综合检查过程中出现错误: {e}")
            return False

    def _check_usb_connections(self) -> bool:
        """检查USB连接状态"""
        print("\n🔍 正在检查ADB服务状态...")
        try:
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
                return False

            print(f"\n✅ 检测到 {len(devices)} 个设备:")
            authorized_count = 0
            for device_id, status in devices:
                status_icon = "✅" if status == "device" else "⚠️" if status == "unauthorized" else "❌"
                print(f"  {status_icon} {device_id}: {status}")

                if status == "unauthorized":
                    print(f"    📱 设备 {device_id} 需要授权USB调试")
                elif status == "offline":
                    print(f"    🔌 设备 {device_id} 连接异常，可能是USB模式问题")
                elif status == "device":
                    authorized_count += 1

            return authorized_count > 0

        except Exception as e:
            print(f"❌ 检查设备失败: {e}")
            return False

    def _show_usb_setup_guide(self):
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
""")

    def _prepare_all_devices(self) -> bool:
        """预处理所有连接的设备"""
        logger.info("开始设备预处理流程...")

        try:
            # 1. 确保ADB服务运行
            self._ensure_adb_server()

            # 2. 获取所有设备
            devices = self._get_connected_devices()
            if not devices:
                logger.warning("未检测到连接的设备")
                return False

            logger.info(f"检测到 {len(devices)} 个设备: {devices}")

            # 3. 为每个设备执行预处理
            success_count = 0
            for device_id in devices:
                result = DeviceTestResult(device_id)
                self.test_results.append(result)

                if self._prepare_single_device(device_id, result):
                    success_count += 1
                    result.overall_status = "成功"

            logger.info(f"预处理完成，成功处理 {success_count}/{len(devices)} 个设备")
            return success_count > 0

        except Exception as e:
            logger.error(f"设备预处理失败: {e}")
            return False

    def _prepare_single_device(self, device_id: str, result: DeviceTestResult) -> bool:
        """预处理单个设备"""
        logger.info(f"预处理设备: {device_id}")

        try:
            # 获取设备基本信息
            self._get_device_basic_info(device_id, result)

            # 配置RSA密钥授权
            if self._configure_rsa_authorization(device_id):
                result.rsa_configured = True
                result.authorization_status = "已授权"

            # 配置无线连接
            if self._setup_wireless_connection(device_id):
                result.wireless_enabled = True

            # 解决权限问题
            self._fix_device_permissions(device_id)

            # 解决锁屏问题
            self._handle_screen_lock(device_id)

            return True

        except Exception as e:
            logger.error(f"设备 {device_id} 预处理失败: {e}")
            return False

    def _get_device_basic_info(self, device_id: str, result: DeviceTestResult):
        """获取设备基本信息"""
        try:
            # 获取设备型号
            model_result = subprocess.run(
                f"adb -s {device_id} shell getprop ro.product.model",
                shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore'
            )
            if model_result.returncode == 0:
                result.model = model_result.stdout.strip()

            # 获取Android版本
            version_result = subprocess.run(
                f"adb -s {device_id} shell getprop ro.build.version.release",
                shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore'
            )
            if version_result.returncode == 0:
                result.android_version = version_result.stdout.strip()

            # 检查TCP端口
            tcp_result = subprocess.run(
                f"adb -s {device_id} shell getprop persist.adb.tcp.port",
                shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore'
            )
            if tcp_result.returncode == 0:
                result.tcp_port = tcp_result.stdout.strip() or "未设置"

            # 获取WiFi状态和IP
            wifi_result = subprocess.run(
                f"adb -s {device_id} shell ip route | grep wlan",
                shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore'
            )
            if wifi_result.returncode == 0 and wifi_result.stdout.strip():
                result.wifi_status = "已连接"

                # 获取IP地址
                ip_result = subprocess.run(
                    f"adb -s {device_id} shell ip addr show wlan0 | grep 'inet '",
                    shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore'
                )
                if ip_result.returncode == 0:
                    import re
                    ip_match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)', ip_result.stdout)
                    if ip_match:
                        result.ip_address = ip_match.group(1)
            else:
                result.wifi_status = "未连接"

        except Exception as e:
            logger.error(f"获取设备 {device_id} 基本信息失败: {e}")

    def _run_detailed_tests(self):
        """运行详细功能测试"""
        for result in self.test_results:
            print(f"\n🧪 测试设备 {result.device_id} 的ADB功能...")

            tests = [
                ("shell echo 'Hello'", "基本shell命令"),
                ("shell ls /sdcard", "文件系统访问"),
                ("shell input keyevent 26", "输入事件（电源键）"),
                ("shell screencap -p", "屏幕截图功能")
            ]

            for cmd, desc in tests:
                try:
                    test_result = subprocess.run(
                        f"adb -s {result.device_id} {cmd}",
                        shell=True, capture_output=True, text=True,
                        timeout=10, encoding='utf-8', errors='ignore'
                    )
                    success = test_result.returncode == 0
                    result.basic_commands[desc] = "✅ 成功" if success else "❌ 失败"
                    print(f"  {'✅' if success else '❌'} {desc}: {'成功' if success else '失败'}")

                except subprocess.TimeoutExpired:
                    result.basic_commands[desc] = "⏰ 超时"
                    print(f"  ⏰ {desc}: 超时")
                except Exception as e:
                    result.basic_commands[desc] = f"❌ 异常: {str(e)[:20]}..."
                    print(f"  ❌ {desc}: 异常 - {e}")

    def _generate_test_report(self):
        """生成设备测试报告表格"""
        print("\n" + "=" * 120)
        print("📊 设备测试结果汇总报告")
        print("=" * 120)

        if not self.test_results:
            print("⚠️ 没有测试结果数据")
            return

        # 表格标题
        headers = [
            "设备ID", "型号", "Android版本", "连接状态", "授权状态",
            "WiFi状态", "IP地址", "Shell命令", "文件访问", "输入事件", "截图功能", "总体状态"
        ]

        # 计算列宽
        col_widths = [12, 15, 10, 8, 8, 8, 15, 8, 8, 8, 8, 8]

        # 打印表格头
        self._print_table_row(headers, col_widths, is_header=True)
        self._print_table_separator(col_widths)

        # 打印数据行
        for result in self.test_results:
            row_data = [
                result.device_id[:10] + "..." if len(result.device_id) > 10 else result.device_id,
                result.model[:13] + "..." if len(result.model) > 13 else result.model,
                result.android_version,
                "✅ 正常" if ":" in result.device_id else "🔌 USB",
                "✅ 是" if result.rsa_configured else "❌ 否",
                "📶 是" if result.wifi_status == "已连接" else "❌ 否",
                result.ip_address[:13] + "..." if len(result.ip_address) > 13 else result.ip_address,
                result.basic_commands.get("基本shell命令", "❌")[:6],
                result.basic_commands.get("文件系统访问", "❌")[:6],
                result.basic_commands.get("输入事件（电源键）", "❌")[:6],
                result.basic_commands.get("屏幕截图功能", "❌")[:6],
                "✅ 通过" if result.overall_status == "成功" else "❌ 失败"
            ]
            self._print_table_row(row_data, col_widths)

        self._print_table_separator(col_widths)

        # 统计信息
        total_devices = len(self.test_results)
        successful_devices = len([r for r in self.test_results if r.overall_status == "成功"])
        authorized_devices = len([r for r in self.test_results if r.rsa_configured])
        wifi_devices = len([r for r in self.test_results if r.wifi_status == "已连接"])

        print(f"\n📈 统计汇总:")
        print(f"  总设备数: {total_devices}")
        print(f"  成功设备: {successful_devices} ({successful_devices/total_devices*100:.1f}%)")
        print(f"  已授权设备: {authorized_devices} ({authorized_devices/total_devices*100:.1f}%)")
        print(f"  WiFi连接设备: {wifi_devices} ({wifi_devices/total_devices*100:.1f}%)")

        if successful_devices == total_devices:
            print("\n🎉 所有设备检查通过！设备已准备就绪。")
            print("💡 现在可以运行 WFGameAI 进行自动化测试了。")
        else:
            print(f"\n⚠️ {total_devices - successful_devices} 个设备存在问题，请检查设备设置。")

    def _print_table_row(self, data: List[str], widths: List[int], is_header: bool = False):
        """打印表格行"""
        row = "│"
        for i, (item, width) in enumerate(zip(data, widths)):
            # 确保内容不超过列宽
            content = str(item)[:width-1]
            if is_header:
                row += f" {content:^{width-2}} │"
            else:
                row += f" {content:<{width-2}} │"
        print(row)

    def _print_table_separator(self, widths: List[int]):
        """打印表格分隔线"""
        line = "├"
        for width in widths:
            line += "─" * (width-1) + "┼"
        line = line[:-1] + "┤"
        print(line)

    # 保留原有的核心功能方法
    def _ensure_adb_server(self):
        """确保ADB服务运行"""
        try:
            subprocess.run("adb start-server", shell=True, check=True, capture_output=True)
            logger.info("ADB服务已启动")
        except Exception as e:
            logger.error(f"启动ADB服务失败: {e}")
            raise

    def _get_connected_devices(self) -> List[str]:
        """获取已连接的设备列表"""
        try:
            result = subprocess.run("adb devices", shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            devices = []
            for line in result.stdout.split('\n')[1:]:
                if line.strip() and '\t' in line:
                    device_id, status = line.split('\t')
                    if status.strip() == "device":
                        devices.append(device_id.strip())
            return devices
        except Exception as e:
            logger.error(f"获取设备列表失败: {e}")
            return []

    def _configure_rsa_authorization(self, device_id: str) -> bool:
        """配置RSA密钥授权"""
        try:
            # 检查是否已授权
            result = subprocess.run(f"adb -s {device_id} shell echo 'test'",
                                  shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"设备 {device_id} 已授权")
                return True
            else:
                logger.warning(f"设备 {device_id} 需要手动授权")
                return False
        except Exception as e:
            logger.error(f"检查设备 {device_id} 授权状态失败: {e}")
            return False

    def _setup_wireless_connection(self, device_id: str) -> bool:
        """设置无线连接"""
        try:
            # 获取设备IP
            ip_result = subprocess.run(
                f"adb -s {device_id} shell ip addr show wlan0 | grep 'inet '",
                shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore'
            )

            if ip_result.returncode != 0:
                return False

            import re
            ip_match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)', ip_result.stdout)
            if not ip_match:
                return False

            device_ip = ip_match.group(1)

            # 启用TCP/IP连接
            subprocess.run(f"adb -s {device_id} tcpip 5555", shell=True, capture_output=True)
            time.sleep(2)

            # 尝试连接
            connect_result = subprocess.run(f"adb connect {device_ip}:5555",
                                          shell=True, capture_output=True, text=True)

            if "connected" in connect_result.stdout:
                self.wireless_connections[device_id] = f"{device_ip}:5555"
                logger.info(f"设备 {device_id} 无线连接成功: {device_ip}:5555")
                return True

            return False

        except Exception as e:
            logger.error(f"设置设备 {device_id} 无线连接失败: {e}")
            return False

    def _fix_device_permissions(self, device_id: str):
        """修复设备权限问题"""
        try:
            # 授予必要权限
            permissions = [
                "android.permission.WRITE_EXTERNAL_STORAGE",
                "android.permission.READ_EXTERNAL_STORAGE"
            ]

            for permission in permissions:
                subprocess.run(
                    f"adb -s {device_id} shell pm grant android {permission}",
                    shell=True, capture_output=True
                )

        except Exception as e:
            logger.warning(f"修复设备 {device_id} 权限时出错: {e}")

    def _handle_screen_lock(self, device_id: str):
        """处理锁屏问题"""
        try:
            # 唤醒屏幕
            subprocess.run(f"adb -s {device_id} shell input keyevent 26",
                         shell=True, capture_output=True)
            time.sleep(1)

            # 滑动解锁（假设是简单滑动解锁）
            subprocess.run(f"adb -s {device_id} shell input swipe 500 1000 500 500",
                         shell=True, capture_output=True)

        except Exception as e:
            logger.warning(f"处理设备 {device_id} 锁屏时出错: {e}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='WFGameAI 设备预处理管理器 - 增强版')
    parser.add_argument('--config', type=str, help='配置文件路径')
    parser.add_argument('--report', action='store_true', help='只生成设备报告')

    args = parser.parse_args()

    manager = EnhancedDevicePreparationManager(args.config)

    if args.report:
        # 只运行检查和报告
        manager._check_usb_connections()
        manager._prepare_all_devices()
        manager._run_detailed_tests()
        manager._generate_test_report()
    else:
        # 运行完整的综合检查
        success = manager.run_comprehensive_check()
        return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
