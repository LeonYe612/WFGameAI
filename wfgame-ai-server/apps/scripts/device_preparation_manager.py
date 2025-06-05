#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WFGameAI 设备预处理管理器
解决设备连接、权限、锁屏等问题，特别是断电重连后的ADB授权问题
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

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DevicePreparationManager:
    """设备预处理管理器"""

    def __init__(self, config_path: str = None):
        self.config_path = config_path or "config.ini"
        self.adb_keys_path = Path.home() / ".android"
        self.device_info_cache = {}
        self.wireless_connections = {}

    def prepare_all_devices(self) -> bool:
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
                if self._prepare_single_device(device_id):
                    success_count += 1

            logger.info(f"设备预处理完成: {success_count}/{len(devices)} 个设备成功")
            return success_count > 0

        except Exception as e:
            logger.error(f"设备预处理失败: {str(e)}")
            return False

    def _prepare_single_device(self, device_id: str) -> bool:
        """预处理单个设备"""
        logger.info(f"开始预处理设备: {device_id}")

        try:
            # 1. 检查设备状态
            device_status = self._check_device_status(device_id)
            logger.info(f"设备 {device_id} 状态: {device_status}")

            # 2. 处理未授权状态
            if device_status == "unauthorized":
                logger.info(f"设备 {device_id} 未授权，尝试处理...")
                if not self._handle_unauthorized_device(device_id):
                    logger.error(f"设备 {device_id} 授权处理失败")
                    return False

            # 3. 设置RSA密钥持久化授权
            self._setup_rsa_persistent_auth(device_id)

            # 4. 配置无线ADB备选连接
            self._setup_wireless_adb_fallback(device_id)

            # 5. 处理设备权限问题
            self._grant_device_permissions(device_id)

            # 6. 解决屏幕锁定问题
            self._handle_screen_lock_issues(device_id)

            # 7. 处理系统UI干扰
            self._handle_system_ui_interference(device_id)

            # 8. 保存设备信息
            self._save_device_info(device_id)

            logger.info(f"设备 {device_id} 预处理完成")
            return True

        except Exception as e:
            logger.error(f"设备 {device_id} 预处理失败: {str(e)}")
            return False

    def _ensure_adb_server(self):
        """确保ADB服务器正常运行"""
        try:
            subprocess.run("adb kill-server", shell=True, check=False)
            time.sleep(1)
            subprocess.run("adb start-server", shell=True, check=True)
            logger.info("ADB服务器已启动")
        except Exception as e:
            logger.error(f"启动ADB服务器失败: {str(e)}")
            raise

    def _get_connected_devices(self) -> List[str]:
        """获取所有连接的设备"""
        try:
            result = subprocess.run("adb devices", shell=True, capture_output=True, text=True, check=True)
            devices = []

            for line in result.stdout.split('\n')[1:]:  # 跳过标题行
                if line.strip() and '\t' in line:
                    device_id = line.split('\t')[0].strip()
                    if device_id:
                        devices.append(device_id)

            return devices
        except Exception as e:
            logger.error(f"获取设备列表失败: {str(e)}")
            return []

    def _check_device_status(self, device_id: str) -> str:
        """检查设备授权状态"""
        try:
            result = subprocess.run("adb devices", shell=True, capture_output=True, text=True, check=True)

            for line in result.stdout.split('\n'):
                if device_id in line:
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        return parts[1].strip()

            return "offline"
        except Exception as e:
            logger.error(f"检查设备状态失败: {str(e)}")
            return "unknown"

    def _handle_unauthorized_device(self, device_id: str) -> bool:
        """处理未授权的设备"""
        logger.info(f"处理未授权设备: {device_id}")

        # 方法1: 自动点击允许按钮
        if self._auto_accept_usb_debugging(device_id):
            time.sleep(3)  # 等待授权生效
            if self._check_device_status(device_id) == "device":
                return True

        # 方法2: 提示用户手动授权
        logger.warning(f"设备 {device_id} 需要手动授权USB调试")
        print(f"\n请在设备 {device_id} 上手动点击'允许USB调试'")
        print("等待授权完成...")

        # 等待用户授权，最多等待30秒
        for i in range(30):
            time.sleep(1)
            if self._check_device_status(device_id) == "device":
                logger.info(f"设备 {device_id} 授权成功")
                return True
            if i % 5 == 0:
                print(f"等待中... ({30-i}秒)")

        logger.error(f"设备 {device_id} 授权超时")
        return False

    def _auto_accept_usb_debugging(self, device_id: str) -> bool:
        """自动接受USB调试授权请求"""
        try:
            # 截取屏幕
            subprocess.run(f"adb -s {device_id} shell screencap -p /sdcard/screen.png",
                         shell=True, check=True)
            subprocess.run(f"adb -s {device_id} pull /sdcard/screen.png screen_{device_id}.png",
                         shell=True, check=True)

            # 使用UI自动化检测并点击"允许"按钮
            # 这里可以集成OCR或图像识别来检测对话框
            # 简化实现：点击常见的允许按钮位置

            # 获取屏幕尺寸
            result = subprocess.run(f"adb -s {device_id} shell wm size",
                                  shell=True, capture_output=True, text=True)
            if "Physical size:" in result.stdout:
                size_match = re.search(r'(\d+)x(\d+)', result.stdout)
                if size_match:
                    width, height = int(size_match.group(1)), int(size_match.group(2))

                    # 点击右下角"允许"按钮的常见位置
                    allow_x, allow_y = int(width * 0.75), int(height * 0.85)
                    subprocess.run(f"adb -s {device_id} shell input tap {allow_x} {allow_y}",
                                 shell=True, check=True)

                    logger.info(f"已自动点击设备 {device_id} 的允许按钮")
                    return True

        except Exception as e:
            logger.warning(f"自动接受USB调试失败: {str(e)}")

        return False

    def _setup_rsa_persistent_auth(self, device_id: str) -> bool:
        """设置RSA密钥持久化授权"""
        logger.info(f"为设备 {device_id} 设置RSA持久化授权...")

        try:
            # 1. 确保本地ADB密钥存在
            if not self._ensure_adb_keys():
                return False

            # 2. 检查设备是否已root
            is_rooted = self._check_device_rooted(device_id)

            if is_rooted:
                logger.info(f"设备 {device_id} 已root，配置永久ADB授权...")

                # 3. 推送RSA公钥到设备
                adb_pub_key = self.adb_keys_path / "adbkey.pub"
                if adb_pub_key.exists():
                    # 推送公钥文件
                    subprocess.run(f"adb -s {device_id} push {adb_pub_key} /data/misc/adb/adb_keys",
                                 shell=True, check=True)

                    # 设置正确的权限
                    subprocess.run(f"adb -s {device_id} shell su -c 'chmod 644 /data/misc/adb/adb_keys'",
                                 shell=True, check=False)
                    subprocess.run(f"adb -s {device_id} shell su -c 'chown system:system /data/misc/adb/adb_keys'",
                                 shell=True, check=False)

                    logger.info(f"设备 {device_id} RSA永久授权配置完成")
                    return True
            else:
                logger.info(f"设备 {device_id} 未root，RSA密钥将在用户授权后自动保存")
                # 非root设备，RSA密钥会在用户点击"允许"后自动保存
                return True

        except Exception as e:
            logger.error(f"设置RSA持久化授权失败: {str(e)}")

        return False

    def _ensure_adb_keys(self) -> bool:
        """确保ADB RSA密钥存在"""
        try:
            adb_key = self.adb_keys_path / "adbkey"
            adb_pub_key = self.adb_keys_path / "adbkey.pub"

            if not adb_key.exists() or not adb_pub_key.exists():
                logger.info("生成ADB RSA密钥...")
                self.adb_keys_path.mkdir(exist_ok=True)

                # 重启ADB服务以生成密钥
                subprocess.run("adb kill-server", shell=True, check=False)
                subprocess.run("adb start-server", shell=True, check=True)

                # 等待密钥生成
                time.sleep(2)

                if not adb_key.exists():
                    logger.error("ADB密钥生成失败")
                    return False

            logger.info("ADB RSA密钥已准备就绪")
            return True

        except Exception as e:
            logger.error(f"确保ADB密钥失败: {str(e)}")
            return False

    def _check_device_rooted(self, device_id: str) -> bool:
        """检查设备是否已root"""
        try:
            result = subprocess.run(f"adb -s {device_id} shell su -c 'echo rooted'",
                                  shell=True, capture_output=True, text=True, timeout=5)
            return "rooted" in result.stdout
        except:
            return False

    def _setup_wireless_adb_fallback(self, device_id: str) -> bool:
        """设置无线ADB备选连接"""
        logger.info(f"为设备 {device_id} 配置无线ADB备选连接...")

        try:
            # 获取设备IP地址
            device_ip = self._get_device_ip(device_id)
            if not device_ip:
                logger.warning(f"无法获取设备 {device_id} 的IP地址")
                return False

            # 启用TCP连接
            subprocess.run(f"adb -s {device_id} tcpip 5555", shell=True, check=True)
            time.sleep(2)

            # 测试无线连接
            connect_result = subprocess.run(f"adb connect {device_ip}:5555",
                                          shell=True, capture_output=True, text=True)

            if "connected" in connect_result.stdout.lower():
                # 保存无线连接信息
                self.wireless_connections[device_id] = {
                    "ip": device_ip,
                    "port": 5555,
                    "status": "configured"
                }
                logger.info(f"设备 {device_id} 无线ADB配置成功: {device_ip}:5555")
                return True

        except Exception as e:
            logger.error(f"配置无线ADB失败: {str(e)}")

        return False

    def _get_device_ip(self, device_id: str) -> Optional[str]:
        """获取设备IP地址"""
        try:
            # 方法1: 通过wlan0接口获取
            result = subprocess.run(
                f"adb -s {device_id} shell ip addr show wlan0 | grep 'inet\\s'",
                shell=True, capture_output=True, text=True
            )

            ip_match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)', result.stdout)
            if ip_match:
                return ip_match.group(1)

            # 方法2: 通过ifconfig获取（备选）
            result = subprocess.run(
                f"adb -s {device_id} shell ifconfig wlan0",
                shell=True, capture_output=True, text=True
            )

            ip_match = re.search(r'inet addr:(\d+\.\d+\.\d+\.\d+)', result.stdout)
            if ip_match:
                return ip_match.group(1)

        except Exception as e:
            logger.warning(f"获取设备IP失败: {str(e)}")

        return None

    def _grant_device_permissions(self, device_id: str) -> bool:
        """授予设备必要权限"""
        logger.info(f"为设备 {device_id} 授予必要权限...")

        # 常用权限列表
        permissions = [
            "android.permission.CAMERA",
            "android.permission.RECORD_AUDIO",
            "android.permission.READ_EXTERNAL_STORAGE",
            "android.permission.WRITE_EXTERNAL_STORAGE",
            "android.permission.ACCESS_FINE_LOCATION",
            "android.permission.ACCESS_COARSE_LOCATION",
            "android.permission.READ_PHONE_STATE"
        ]

        try:
            # 获取已安装的包名（这里需要根据实际测试的应用包名调整）
            # 暂时使用通用设置

            # 启用开发者选项相关设置
            commands = [
                f"adb -s {device_id} shell settings put global adb_enabled 1",
                f"adb -s {device_id} shell settings put global development_settings_enabled 1",
                f"adb -s {device_id} shell settings put system screen_off_timeout 2147483647",  # 禁用休眠
                f"adb -s {device_id} shell settings put global zen_mode 1",  # 启用勿扰模式
                f"adb -s {device_id} shell settings put system screen_brightness 255"  # 最高亮度
            ]

            for cmd in commands:
                subprocess.run(cmd, shell=True, check=False)

            logger.info(f"设备 {device_id} 基本权限配置完成")
            return True

        except Exception as e:
            logger.error(f"权限配置失败: {str(e)}")
            return False

    def _handle_screen_lock_issues(self, device_id: str) -> bool:
        """处理设备屏幕锁定问题"""
        logger.info(f"处理设备 {device_id} 屏幕锁定问题...")

        try:
            # 1. 唤醒设备
            subprocess.run(f"adb -s {device_id} shell input keyevent KEYCODE_WAKEUP",
                         shell=True, check=False)
            time.sleep(1)

            # 2. 解锁屏幕（滑动解锁）
            subprocess.run(f"adb -s {device_id} shell input keyevent 82",
                         shell=True, check=False)
            time.sleep(1)

            # 3. 检查屏幕状态
            result = subprocess.run(f"adb -s {device_id} shell dumpsys power | grep 'Display Power'",
                                  shell=True, capture_output=True, text=True)

            if "state=ON" in result.stdout:
                logger.info(f"设备 {device_id} 屏幕已唤醒")

            # 4. 禁用锁屏（需要root权限）
            if self._check_device_rooted(device_id):
                subprocess.run(f"adb -s {device_id} shell su -c 'settings put secure lockscreen.disabled 1'",
                             shell=True, check=False)

            # 5. 设置屏幕常亮
            subprocess.run(f"adb -s {device_id} shell svc power stayon true",
                         shell=True, check=False)

            return True

        except Exception as e:
            logger.error(f"处理屏幕锁定问题失败: {str(e)}")
            return False

    def _handle_system_ui_interference(self, device_id: str) -> bool:
        """处理系统UI干扰"""
        logger.info(f"处理设备 {device_id} 系统UI干扰...")

        try:
            # 1. 关闭所有系统对话框
            subprocess.run(f"adb -s {device_id} shell am broadcast -a android.intent.action.CLOSE_SYSTEM_DIALOGS",
                         shell=True, check=False)

            # 2. 禁用ANR对话框
            subprocess.run(f"adb -s {device_id} shell settings put global anr_show_background 0",
                         shell=True, check=False)

            # 3. 折叠状态栏
            subprocess.run(f"adb -s {device_id} shell cmd statusbar collapse",
                         shell=True, check=False)

            # 4. 清除通知
            subprocess.run(f"adb -s {device_id} shell service call notification 1",
                         shell=True, check=False)

            # 5. 禁用系统更新检查
            subprocess.run(f"adb -s {device_id} shell settings put global ota_disable 1",
                         shell=True, check=False)

            # 6. 禁用设置向导
            subprocess.run(f"adb -s {device_id} shell settings put secure user_setup_complete 1",
                         shell=True, check=False)
            subprocess.run(f"adb -s {device_id} shell settings put global device_provisioned 1",
                         shell=True, check=False)

            logger.info(f"设备 {device_id} 系统UI干扰处理完成")
            return True

        except Exception as e:
            logger.error(f"处理系统UI干扰失败: {str(e)}")
            return False

    def _save_device_info(self, device_id: str):
        """保存设备信息"""
        try:
            # 获取设备基本信息
            device_info = {
                "device_id": device_id,
                "timestamp": time.time(),
                "preparation_status": "completed"
            }

            # 获取设备型号
            result = subprocess.run(f"adb -s {device_id} shell getprop ro.product.model",
                                  shell=True, capture_output=True, text=True)
            device_info["model"] = result.stdout.strip()

            # 获取Android版本
            result = subprocess.run(f"adb -s {device_id} shell getprop ro.build.version.release",
                                  shell=True, capture_output=True, text=True)
            device_info["android_version"] = result.stdout.strip()

            # 获取屏幕分辨率
            result = subprocess.run(f"adb -s {device_id} shell wm size",
                                  shell=True, capture_output=True, text=True)
            if "Physical size:" in result.stdout:
                size_match = re.search(r'(\d+)x(\d+)', result.stdout)
                if size_match:
                    device_info["screen_resolution"] = f"{size_match.group(1)}x{size_match.group(2)}"

            # 添加无线连接信息
            if device_id in self.wireless_connections:
                device_info["wireless_connection"] = self.wireless_connections[device_id]

            # 保存到缓存
            self.device_info_cache[device_id] = device_info

            # 保存到文件
            cache_file = Path("device_preparation_cache.json")
            all_cache = {}
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    all_cache = json.load(f)

            all_cache[device_id] = device_info

            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(all_cache, f, indent=2, ensure_ascii=False)

            logger.info(f"设备 {device_id} 信息已保存")

        except Exception as e:
            logger.error(f"保存设备信息失败: {str(e)}")

    def reconnect_device(self, device_id: str) -> bool:
        """重新连接设备（用于断电后重连）"""
        logger.info(f"尝试重新连接设备: {device_id}")

        try:
            # 1. 首先尝试USB连接
            current_devices = self._get_connected_devices()
            if device_id in current_devices:
                status = self._check_device_status(device_id)
                if status == "device":
                    logger.info(f"设备 {device_id} USB连接正常")
                    return True
                elif status == "unauthorized":
                    logger.info(f"设备 {device_id} 需要重新授权")
                    return self._handle_unauthorized_device(device_id)

            # 2. 尝试无线连接
            if device_id in self.wireless_connections:
                wireless_info = self.wireless_connections[device_id]
                ip = wireless_info.get("ip")
                port = wireless_info.get("port", 5555)

                if ip:
                    logger.info(f"尝试无线连接设备: {ip}:{port}")
                    result = subprocess.run(f"adb connect {ip}:{port}",
                                          shell=True, capture_output=True, text=True)

                    if "connected" in result.stdout.lower():
                        logger.info(f"设备 {device_id} 无线连接成功")
                        return True

            logger.warning(f"设备 {device_id} 重连失败")
            return False

        except Exception as e:
            logger.error(f"重连设备失败: {str(e)}")
            return False

    def get_device_preparation_report(self) -> Dict:
        """获取设备预处理报告"""
        return {
            "prepared_devices": len(self.device_info_cache),
            "wireless_connections": len(self.wireless_connections),
            "device_details": self.device_info_cache,
            "wireless_details": self.wireless_connections
        }

# 主函数和命令行接口
def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="WFGameAI设备预处理管理器")
    parser.add_argument("--config", help="配置文件路径", default="config.ini")
    parser.add_argument("--reconnect", help="重新连接指定设备ID")
    parser.add_argument("--report", action="store_true", help="显示预处理报告")

    args = parser.parse_args()

    manager = DevicePreparationManager(args.config)

    if args.reconnect:
        success = manager.reconnect_device(args.reconnect)
        print(f"设备重连{'成功' if success else '失败'}")
        return 0 if success else 1

    if args.report:
        report = manager.get_device_preparation_report()
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0

    # 默认执行完整预处理
    success = manager.prepare_all_devices()

    if success:
        print("\n设备预处理完成！")
        report = manager.get_device_preparation_report()
        print(f"成功处理 {report['prepared_devices']} 个设备")
        if report['wireless_connections'] > 0:
            print(f"配置了 {report['wireless_connections']} 个无线连接备选方案")
    else:
        print("设备预处理失败！")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
