#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用UI检测器 - Universal UI Detector
支持多种Android版本和设备的UI结构检测
具备高兼容性和容错能力
"""

import subprocess
import json
import time
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import argparse
import tempfile
from pathlib import Path

# 设置编码
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 可选依赖检查
try:
    from adbutils import adb
    ADB_UTILS_AVAILABLE = True
except ImportError:
    ADB_UTILS_AVAILABLE = False

try:
    from airtest.core.api import connect_device
    AIRTEST_AVAILABLE = True
except ImportError:
    AIRTEST_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class UniversalUIDetector:
    """通用UI检测器 - 支持多种Android版本和设备"""

    def __init__(self,
                 device_id: Optional[str] = None,
                 save_files: bool = False,
                 output_dir: str = "ui_detection_output",
                 timeout: int = 60,
                 max_retries: int = 3):
        """
        初始化通用UI检测器

        Args:
            device_id: 指定设备ID，None表示自动检测
            save_files: 是否保存文件到本地
            output_dir: 输出目录
            timeout: 操作超时时间（秒）
            max_retries: 最大重试次数
        """
        self.device_id = device_id
        self.save_files = save_files
        self.output_dir = output_dir
        self.timeout = timeout
        self.max_retries = max_retries

        # 支持的设备路径策略
        self.device_paths = {
            'temp_dirs': ['/data/local/tmp', '/data', '/sdcard', '/storage/emulated/0'],
            'fallback_dirs': ['/cache', '/tmp'],
            'screenshot_formats': ['.png', '.jpg'],
            'xml_paths': [
                '/data/local/tmp/window_dump.xml',
                '/data/window_dump.xml',
                '/sdcard/window_dump.xml',
                '/storage/emulated/0/window_dump.xml'
            ]
        }

        # Android版本特定配置
        self.android_configs = {
            '9': {
                'requires_special_handling': True,
                'accessibility_reset': True,
                'ui_restart': True,
                'extra_wait_time': 5
            },
            '10': {
                'requires_special_handling': False,
                'scoped_storage': True
            },
            '11': {
                'requires_special_handling': False,
                'scoped_storage': True,
                'enhanced_permissions': True
            },
            '12': {
                'requires_special_handling': False,
                'scoped_storage': True,
                'enhanced_permissions': True
            },
            '13': {
                'requires_special_handling': False,
                'scoped_storage': True,
                'enhanced_permissions': True,
                'notification_permissions': True
            },
            '14': {
                'requires_special_handling': False,
                'scoped_storage': True,
                'enhanced_permissions': True,
                'notification_permissions': True,
                'partial_media_access': True
            }
        }

        # 设备厂商特定配置
        self.vendor_configs = {
            'xiaomi': {
                'miui_paths': ['/sdcard/window_dump.xml', '/storage/emulated/0/window_dump.xml'],
                'requires_accessibility_fix': True,
                'default_screenshot_path': '/sdcard/screenshot.png'
            },
            'huawei': {
                'emui_paths': ['/data/local/tmp/window_dump.xml'],
                'requires_developer_options': True
            },
            'oppo': {
                'coloros_paths': ['/data/local/tmp/window_dump.xml'],
                'requires_usb_debugging_plus': True
            },
            'vivo': {
                'funtouch_paths': ['/data/local/tmp/window_dump.xml'],
                'requires_developer_mode': True
            },
            'samsung': {
                'oneui_paths': ['/data/local/tmp/window_dump.xml'],
                'knox_compatibility': True
            },
            'oneplus': {
                'oxygenos_paths': ['/data/local/tmp/window_dump.xml'],
                'gaming_mode_detection': True
            }
        }

        self._init_logging()
        self._init_output_dir()

    def _init_logging(self):
        """初始化日志系统"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file_path = os.path.join(self.output_dir, f"ui_detector_log_{timestamp}.txt")

        # 确保目录存在
        os.makedirs(os.path.dirname(self.log_file_path), exist_ok=True)

        self.log_file = open(self.log_file_path, "w", encoding="utf-8")
        self.log("🚀 通用UI检测器启动")
        self.log(f"📝 日志文件: {self.log_file_path}")

    def _init_output_dir(self):
        """初始化输出目录"""
        if self.save_files:
            os.makedirs(self.output_dir, exist_ok=True)
            self.log(f"📁 输出目录: {os.path.abspath(self.output_dir)}")

    def log(self, message: str, level: str = "INFO", show_in_terminal: bool = True):
        """统一日志方法"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {level}: {message}"

        # 写入日志文件
        if hasattr(self, 'log_file') and self.log_file:
            self.log_file.write(log_message + "\n")
            self.log_file.flush()

        # 终端显示（简化格式）
        if show_in_terminal:
            print(message)

    def get_connected_devices(self) -> List[Dict[str, Any]]:
        """获取所有连接的设备及其详细信息"""
        devices = []

        try:
            if ADB_UTILS_AVAILABLE:
                # 使用adbutils获取设备信息
                device_list = adb.device_list()
                for device in device_list:
                    if device.get_state() == "device":
                        device_info = self._get_device_info(device.serial)
                        device_info['serial'] = device.serial
                        device_info['connection_type'] = 'adbutils'
                        devices.append(device_info)
            else:
                # 使用基础ADB命令
                result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
                lines = result.stdout.strip().split('\n')[1:]
                for line in lines:
                    if line.strip() and '\t' in line:
                        parts = line.split('\t')
                        if len(parts) >= 2 and parts[1].strip() == 'device':
                            serial = parts[0].strip()
                            device_info = self._get_device_info(serial)
                            device_info['serial'] = serial
                            device_info['connection_type'] = 'adb'
                            devices.append(device_info)

        except Exception as e:
            self.log(f"❌ 获取设备列表失败: {e}", "ERROR")

        return devices

    def _get_device_info(self, device_id: str) -> Dict[str, Any]:
        """获取设备详细信息"""
        info = {
            'android_version': 'unknown',
            'brand': 'unknown',
            'model': 'unknown',
            'manufacturer': 'unknown',
            'api_level': 'unknown',
            'architecture': 'unknown',
            'resolution': 'unknown',
            'density': 'unknown'
        }

        try:
            # 获取Android版本
            version_cmd = f"adb -s {device_id} shell getprop ro.build.version.release"
            version_result = subprocess.run(version_cmd, shell=True, capture_output=True, text=True, timeout=10)
            if version_result.returncode == 0:
                info['android_version'] = version_result.stdout.strip()

            # 获取品牌信息
            brand_cmd = f"adb -s {device_id} shell getprop ro.product.brand"
            brand_result = subprocess.run(brand_cmd, shell=True, capture_output=True, text=True, timeout=10)
            if brand_result.returncode == 0:
                info['brand'] = brand_result.stdout.strip().lower()

            # 获取型号
            model_cmd = f"adb -s {device_id} shell getprop ro.product.model"
            model_result = subprocess.run(model_cmd, shell=True, capture_output=True, text=True, timeout=10)
            if model_result.returncode == 0:
                info['model'] = model_result.stdout.strip()

            # 获取制造商
            manufacturer_cmd = f"adb -s {device_id} shell getprop ro.product.manufacturer"
            manufacturer_result = subprocess.run(manufacturer_cmd, shell=True, capture_output=True, text=True, timeout=10)
            if manufacturer_result.returncode == 0:
                info['manufacturer'] = manufacturer_result.stdout.strip().lower()

            # 获取API级别
            api_cmd = f"adb -s {device_id} shell getprop ro.build.version.sdk"
            api_result = subprocess.run(api_cmd, shell=True, capture_output=True, text=True, timeout=10)
            if api_result.returncode == 0:
                info['api_level'] = api_result.stdout.strip()

            # 获取屏幕信息
            resolution_cmd = f"adb -s {device_id} shell wm size"
            resolution_result = subprocess.run(resolution_cmd, shell=True, capture_output=True, text=True, timeout=10)
            if resolution_result.returncode == 0 and "Physical size:" in resolution_result.stdout:
                info['resolution'] = resolution_result.stdout.split("Physical size:")[1].strip()

            density_cmd = f"adb -s {device_id} shell wm density"
            density_result = subprocess.run(density_cmd, shell=True, capture_output=True, text=True, timeout=10)
            if density_result.returncode == 0 and "Physical density:" in density_result.stdout:
                info['density'] = density_result.stdout.split("Physical density:")[1].strip()

        except Exception as e:
            self.log(f"⚠️ 获取设备 {device_id} 信息时出错: {e}", "WARNING")

        return info

    def _get_device_strategy(self, device_info: Dict[str, Any]) -> Dict[str, Any]:
        """根据设备信息确定最佳策略"""
        android_version = device_info.get('android_version', 'unknown')
        brand = device_info.get('brand', 'unknown')
        manufacturer = device_info.get('manufacturer', 'unknown')

        strategy = {
            'android_config': {},
            'vendor_config': {},
            'temp_paths': self.device_paths['temp_dirs'][:],
            'xml_paths': self.device_paths['xml_paths'][:],
            'requires_special_handling': False,
            'max_retries': self.max_retries,
            'timeout': self.timeout
        }

        # Android版本特定策略
        android_major = android_version.split('.')[0] if android_version != 'unknown' else 'unknown'
        if android_major in self.android_configs:
            strategy['android_config'] = self.android_configs[android_major]
            strategy['requires_special_handling'] = strategy['android_config'].get('requires_special_handling', False)

        # 厂商特定策略
        vendor_key = None
        if 'xiaomi' in brand or 'xiaomi' in manufacturer or 'redmi' in brand:
            vendor_key = 'xiaomi'
        elif 'huawei' in brand or 'huawei' in manufacturer or 'honor' in brand:
            vendor_key = 'huawei'
        elif 'oppo' in brand or 'oppo' in manufacturer or 'realme' in brand:
            vendor_key = 'oppo'
        elif 'vivo' in brand or 'vivo' in manufacturer or 'iqoo' in brand:
            vendor_key = 'vivo'
        elif 'samsung' in brand or 'samsung' in manufacturer:
            vendor_key = 'samsung'
        elif 'oneplus' in brand or 'oneplus' in manufacturer:
            vendor_key = 'oneplus'

        if vendor_key and vendor_key in self.vendor_configs:
            strategy['vendor_config'] = self.vendor_configs[vendor_key]
            # 合并厂商特定路径
            if f'{vendor_key}_paths' in strategy['vendor_config']:
                strategy['xml_paths'] = strategy['vendor_config'][f'{vendor_key}_paths'] + strategy['xml_paths']

        return strategy

    def take_screenshot(self, device_id: str, device_info: Dict[str, Any]) -> Optional[str]:
        """通用截图方法"""
        self.log(f"📸 开始截图设备 {device_id}...")

        strategy = self._get_device_strategy(device_info)
        timestamp = int(time.time())

        # 方法1: 使用adbutils（推荐）
        if ADB_UTILS_AVAILABLE:
            screenshot_path = self._screenshot_adbutils(device_id, timestamp)
            if screenshot_path:
                return screenshot_path

        # 方法2: 使用标准ADB
        screenshot_path = self._screenshot_adb(device_id, timestamp, strategy)
        if screenshot_path:
            return screenshot_path

        # 方法3: 使用Airtest备用
        if AIRTEST_AVAILABLE:
            screenshot_path = self._screenshot_airtest(device_id, timestamp)
            if screenshot_path:
                return screenshot_path

        self.log(f"❌ 所有截图方法都失败", "ERROR")
        return None

    def _screenshot_adbutils(self, device_id: str, timestamp: int) -> Optional[str]:
        """使用adbutils截图"""
        try:
            self.log(f"🔍 尝试adbutils截图...")
            device = adb.device(device_id)

            # 测试多个路径
            for temp_dir in self.device_paths['temp_dirs']:
                device_path = f'{temp_dir}/screenshot_{timestamp}.png'

                try:
                    # 截图到设备
                    device.shell(f'screencap -p {device_path}')
                    time.sleep(1)

                    # 验证文件
                    check_result = device.shell(f'ls -l {device_path}')
                    if check_result and "No such file" not in check_result:
                        if self.save_files:
                            local_path = os.path.join(self.output_dir, f"screenshot_{device_id}_{timestamp}.png")
                            device.sync.pull(device_path, local_path)
                            device.shell(f'rm {device_path}')
                            self.log(f"✅ adbutils截图已保存: {local_path}")
                            return local_path
                        else:
                            device.shell(f'rm {device_path}')
                            self.log(f"✅ adbutils截图成功 (未保存)")
                            return "screenshot_captured"
                except Exception as e:
                    self.log(f"⚠️ 路径 {device_path} 失败: {e}", "WARNING")
                    continue

        except Exception as e:
            self.log(f"⚠️ adbutils截图失败: {e}", "WARNING")

        return None

    def _screenshot_adb(self, device_id: str, timestamp: int, strategy: Dict[str, Any]) -> Optional[str]:
        """使用标准ADB截图"""
        try:
            self.log(f"🔍 尝试标准ADB截图...")

            for temp_dir in strategy['temp_paths']:
                device_path = f'{temp_dir}/screenshot_{timestamp}.png'

                # 测试路径可写性
                test_cmd = f"adb -s {device_id} shell touch {device_path}"
                test_result = subprocess.run(test_cmd, shell=True, capture_output=True, text=True, timeout=10)

                if test_result.returncode == 0:
                    # 清理测试文件
                    subprocess.run(f"adb -s {device_id} shell rm {device_path}", shell=True, capture_output=True, text=True)

                    # 执行截图
                    screencap_cmd = f"adb -s {device_id} shell screencap -p {device_path}"
                    result = subprocess.run(screencap_cmd, shell=True, capture_output=True, text=True, timeout=30)

                    if result.returncode == 0:
                        # 验证文件
                        check_cmd = f"adb -s {device_id} shell ls {device_path}"
                        check_result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True, timeout=10)

                        if check_result.returncode == 0:
                            if self.save_files:
                                local_path = os.path.join(self.output_dir, f"screenshot_{device_id}_{timestamp}.png")
                                pull_cmd = f"adb -s {device_id} pull {device_path} {local_path}"
                                pull_result = subprocess.run(pull_cmd, shell=True, capture_output=True, text=True, timeout=30)

                                subprocess.run(f"adb -s {device_id} shell rm {device_path}", shell=True, check=False)

                                if pull_result.returncode == 0:
                                    self.log(f"✅ ADB截图已保存: {local_path}")
                                    return local_path
                            else:
                                subprocess.run(f"adb -s {device_id} shell rm {device_path}", shell=True, check=False)
                                self.log(f"✅ ADB截图成功 (未保存)")
                                return "screenshot_captured"

        except Exception as e:
            self.log(f"⚠️ 标准ADB截图失败: {e}", "WARNING")

        return None

    def _screenshot_airtest(self, device_id: str, timestamp: int) -> Optional[str]:
        """使用Airtest截图"""
        try:
            self.log(f"🔍 尝试Airtest截图...")
            airtest_device = connect_device(f"Android:///{device_id}")
            screenshot_data = airtest_device.snapshot()

            if screenshot_data:
                if self.save_files:
                    local_path = os.path.join(self.output_dir, f"screenshot_{device_id}_{timestamp}.png")
                    screenshot_data.save(local_path)
                    self.log(f"✅ Airtest截图已保存: {local_path}")
                    return local_path
                else:
                    self.log(f"✅ Airtest截图成功 (未保存)")
                    return "screenshot_captured"

        except Exception as e:
            self.log(f"⚠️ Airtest截图失败: {e}", "WARNING")

        return None

    def dump_ui_hierarchy(self, device_id: str, device_info: Dict[str, Any]) -> Optional[str]:
        """通用UI层次结构获取方法"""
        self.log(f"🔍 开始获取UI层次结构...")

        strategy = self._get_device_strategy(device_info)

        # 如果需要特殊处理（主要是Android 9）
        if strategy['requires_special_handling']:
            return self._dump_ui_special_handling(device_id, device_info, strategy)
        else:
            return self._dump_ui_standard(device_id, device_info, strategy)

    def _dump_ui_standard(self, device_id: str, device_info: Dict[str, Any], strategy: Dict[str, Any]) -> Optional[str]:
        """标准UI dump方法"""
        self.log(f"🔧 使用标准UIAutomator方法...")

        # 清理UIAutomator进程
        subprocess.run(f"adb -s {device_id} shell pkill uiautomator", shell=True, capture_output=True, text=True)
        time.sleep(1)

        # 确保屏幕唤醒
        subprocess.run(f"adb -s {device_id} shell input keyevent KEYCODE_WAKEUP", shell=True, capture_output=True, text=True)
        time.sleep(1)

        # 尝试默认dump
        xml_path = self._try_default_dump(device_id, strategy)
        if xml_path:
            return self._pull_xml_file(device_id, xml_path)        # 尝试指定路径dump
        xml_path = self._try_specified_path_dump(device_id, strategy)
        if xml_path:
            return self._pull_xml_file(device_id, xml_path)

        self.log(f"❌ 标准方法失败", "ERROR")
        return None

    def _dump_ui_special_handling(self, device_id: str, device_info: Dict[str, Any], strategy: Dict[str, Any]) -> Optional[str]:
        """特殊处理方法（主要针对Android 9）"""
        self.log(f"🔧 使用特殊处理方法（Android {device_info.get('android_version', 'unknown')}）...")

        # 1. 重置Accessibility服务（Android 9关键修复）
        if strategy['android_config'].get('accessibility_reset', False):
            self.log("🔄 重置Accessibility服务...")
            try:
                # 清空accessibility服务
                subprocess.run(f"adb -s {device_id} shell settings put secure enabled_accessibility_services ''",
                              shell=True, capture_output=True, text=True, timeout=10)
                time.sleep(1)

                # 重新启用系统默认accessibility
                subprocess.run(f"adb -s {device_id} shell settings put secure accessibility_enabled 1",
                              shell=True, capture_output=True, text=True, timeout=10)
                time.sleep(2)
                self.log("✅ Accessibility服务重置完成")
            except Exception as e:
                self.log(f"⚠️ Accessibility重置失败: {e}", "WARNING")

        # 2. 重启UIAutomator服务（Android 9关键修复）
        if strategy['android_config'].get('ui_restart', False):
            self.log("🔄 重启UIAutomator服务...")
            try:
                # 强制停止所有UIAutomator进程
                subprocess.run(f"adb -s {device_id} shell pkill -f uiautomator",
                              shell=True, capture_output=True, text=True)
                subprocess.run(f"adb -s {device_id} shell pkill -f 'com.android.uiautomator'",
                              shell=True, capture_output=True, text=True)
                time.sleep(2)

                # 清理UIAutomator缓存
                subprocess.run(f"adb -s {device_id} shell rm -rf /data/local/tmp/uiautomator*",
                              shell=True, capture_output=True, text=True)
                time.sleep(1)
                self.log("✅ UIAutomator服务重启完成")
            except Exception as e:
                self.log(f"⚠️ UIAutomator重启失败: {e}", "WARNING")

        # 3. OnePlus特殊处理
        is_oneplus = 'oneplus' in strategy.get('vendor_config', {})
        if is_oneplus and strategy['vendor_config'].get('gaming_mode_detection', False):
            self.log("🎮 检测并关闭OnePlus游戏模式...")
            try:
                # 关闭游戏模式，避免影响UIAutomator
                subprocess.run(f"adb -s {device_id} shell settings put global game_driver_all_apps 0",
                              shell=True, capture_output=True, text=True, timeout=10)
                subprocess.run(f"adb -s {device_id} shell am force-stop com.oneplus.gamespace",
                              shell=True, capture_output=True, text=True, timeout=10)
                time.sleep(1)
                self.log("✅ OnePlus游戏模式处理完成")
            except Exception as e:
                self.log(f"⚠️ OnePlus游戏模式处理失败: {e}", "WARNING")

        # 4. 确保屏幕唤醒和解锁
        self.log("📱 确保屏幕状态正常...")
        try:
            subprocess.run(f"adb -s {device_id} shell input keyevent KEYCODE_WAKEUP",
                          shell=True, capture_output=True, text=True)
            time.sleep(1)
            subprocess.run(f"adb -s {device_id} shell input keyevent KEYCODE_MENU",
                          shell=True, capture_output=True, text=True)
            time.sleep(1)
        except Exception as e:
            self.log(f"⚠️ 屏幕状态处理失败: {e}", "WARNING")

        # 5. 多次尝试dump
        for attempt in range(1, strategy['max_retries'] + 1):
            self.log(f"🔄 第 {attempt} 次尝试...")

            # 尝试特殊dump方法
            xml_path = self._try_special_dump(device_id, strategy, attempt)
            if xml_path:
                return self._pull_xml_file(device_id, xml_path)

            if attempt < strategy['max_retries']:
                wait_time = strategy['android_config'].get('extra_wait_time', 3)
                self.log(f"⏳ 等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)

        self.log(f"❌ 特殊处理方法失败", "ERROR")
        return None

    def _try_default_dump(self, device_id: str, strategy: Dict[str, Any]) -> Optional[str]:
        """尝试默认dump"""
        self.log(f"🔍 尝试默认dump...")

        dump_cmd = f"adb -s {device_id} shell uiautomator dump"
        result = subprocess.run(dump_cmd, shell=True, capture_output=True, text=True, timeout=strategy['timeout'])

        if result.returncode == 0 and "ERROR:" not in result.stderr:
            # 检查预定义路径
            for xml_path in strategy['xml_paths']:
                check_cmd = f"adb -s {device_id} shell ls {xml_path}"
                check_result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True, timeout=10)
                if check_result.returncode == 0:
                    self.log(f"✅ 找到默认dump文件: {xml_path}")
                    return xml_path

        return None

    def _try_specified_path_dump(self, device_id: str, strategy: Dict[str, Any]) -> Optional[str]:
        """尝试指定路径dump"""
        self.log(f"🔍 尝试指定路径dump...")

        timestamp = int(time.time())

        for temp_dir in strategy['temp_paths']:
            xml_path = f"{temp_dir}/ui_dump_{timestamp}.xml"
            self.log(f"🎯 尝试路径: {xml_path}")

            # 清理旧文件
            subprocess.run(f"adb -s {device_id} shell rm {xml_path}", shell=True, capture_output=True, text=True)

            # 重启UIAutomator
            subprocess.run(f"adb -s {device_id} shell pkill uiautomator", shell=True, capture_output=True, text=True)
            time.sleep(2)

            # 执行dump
            dump_cmd = f"adb -s {device_id} shell uiautomator dump {xml_path}"
            result = subprocess.run(dump_cmd, shell=True, capture_output=True, text=True, timeout=strategy['timeout'])

            self.log(f"🔧 dump返回码: {result.returncode}")
            if result.stderr:
                self.log(f"🔧 dump错误: {result.stderr}")
            if result.stdout:
                self.log(f"🔧 dump输出: {result.stdout}")

            if result.returncode == 0:
                # 验证文件
                if self._verify_xml_file(device_id, xml_path, result.stdout):
                    return xml_path

                # 检查厂商特定位置
                vendor_path = self._check_vendor_specific_paths(device_id, strategy)
                if vendor_path:
                    return vendor_path

        return None

    def _try_special_dump(self, device_id: str, strategy: Dict[str, Any], attempt: int) -> Optional[str]:
        """特殊dump方法"""
        timestamp = int(time.time()) + attempt

        for temp_dir in strategy['temp_paths']:
            xml_path = f"{temp_dir}/ui_dump_special_{timestamp}.xml"

            # 清理
            subprocess.run(f"adb -s {device_id} shell rm {xml_path}", shell=True, capture_output=True, text=True)

            # 执行dump
            dump_cmd = f"adb -s {device_id} shell uiautomator dump {xml_path}"
            result = subprocess.run(dump_cmd, shell=True, capture_output=True, text=True, timeout=strategy['timeout'])

            if result.returncode == 0:
                if self._verify_xml_file(device_id, xml_path, result.stdout):
                    return xml_path

        return None

    def _verify_xml_file(self, device_id: str, xml_path: str, dump_output: str) -> bool:
        """验证XML文件是否有效"""
        try:
            check_cmd = f"adb -s {device_id} shell ls -l {xml_path}"
            check_result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True, timeout=10)

            if check_result.returncode == 0:
                file_info = check_result.stdout.strip()
                if file_info and len(file_info.split()) >= 5:
                    try:
                        file_size = int(file_info.split()[4])
                        if file_size > 100:  # 有效XML文件应该至少100字节
                            self.log(f"✅ 验证成功: {xml_path} (大小: {file_size}字节)")
                            return True
                        else:
                            self.log(f"⚠️ 文件太小: {file_size}字节")
                    except (ValueError, IndexError):
                        pass

                # 如果无法解析大小但文件存在，也认为有效
                self.log(f"✅ 文件存在: {xml_path}")
                return True

            # 即使验证失败，如果dump输出显示成功，也尝试使用
            elif "dumped to:" in dump_output.lower():
                self.log(f"💡 根据dump输出判断文件可能存在: {xml_path}")
                return True

        except Exception as e:
            self.log(f"⚠️ 验证文件时出错: {e}", "WARNING")

        return False

    def _check_vendor_specific_paths(self, device_id: str, strategy: Dict[str, Any]) -> Optional[str]:
        """检查厂商特定路径"""
        vendor_config = strategy.get('vendor_config', {})

        for key, paths in vendor_config.items():
            if key.endswith('_paths'):
                for vendor_path in paths:
                    check_cmd = f"adb -s {device_id} shell ls -l {vendor_path}"
                    check_result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True, timeout=10)

                    if check_result.returncode == 0:
                        file_info = check_result.stdout.strip()
                        if file_info and len(file_info.split()) >= 5:
                            file_size = file_info.split()[4]
                            if file_size != "0":
                                self.log(f"✅ 在厂商特定位置找到文件: {vendor_path} (大小: {file_size})")
                                return vendor_path

        return None

    def _pull_xml_file(self, device_id: str, xml_path: str) -> Optional[str]:
        """拉取XML文件到本地"""
        try:
            if self.save_files:
                local_path = os.path.join(self.output_dir, f"ui_hierarchy_{device_id}_{int(time.time())}.xml")
            else:
                local_path = os.path.join(tempfile.gettempdir(), f"temp_ui_{int(time.time())}.xml")

            pull_cmd = f"adb -s {device_id} pull {xml_path} {local_path}"
            pull_result = subprocess.run(pull_cmd, shell=True, capture_output=True, text=True, timeout=30)

            if pull_result.returncode == 0:
                if self.save_files:
                    self.log(f"✅ UI层次结构已保存: {local_path}")
                else:
                    self.log(f"✅ UI层次结构已获取 (临时文件)")

                # 清理设备上的文件
                subprocess.run(f"adb -s {device_id} shell rm {xml_path}", shell=True, check=False)
                return local_path
            else:
                self.log(f"❌ 拉取文件失败: {pull_result.stderr}", "ERROR")

        except Exception as e:
            self.log(f"❌ 拉取文件时出错: {e}", "ERROR")

        return None

    def parse_ui_hierarchy(self, xml_path: str) -> Dict[str, Any]:
        """解析UI层次结构"""
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            ui_structure = {
                "timestamp": datetime.now().isoformat(),
                "xml_file": xml_path,
                "total_nodes": 0,
                "clickable_nodes": 0,
                "scrollable_nodes": 0,
                "text_nodes": 0,
                "input_nodes": 0,
                "elements": [],
                "hierarchy": self._parse_node(root)
            }

            self._count_nodes(root, ui_structure)
            return ui_structure

        except Exception as e:
            self.log(f"❌ 解析UI层次结构失败: {e}", "ERROR")
            return {}

    def _parse_node(self, node: ET.Element, level: int = 0) -> Dict[str, Any]:
        """递归解析XML节点"""
        node_info = {
            "tag": node.tag,
            "level": level,
            "attributes": dict(node.attrib),
            "children": []
        }

        for child in node:
            child_info = self._parse_node(child, level + 1)
            node_info["children"].append(child_info)

        return node_info

    def _count_nodes(self, node: ET.Element, stats: Dict[str, Any]):
        """统计节点信息"""
        stats["total_nodes"] += 1

        clickable = node.get("clickable", "false").lower() == "true"
        scrollable = node.get("scrollable", "false").lower() == "true"
        text = node.get("text", "").strip()
        class_name = node.get("class", "")

        if clickable:
            stats["clickable_nodes"] += 1
        if scrollable:
            stats["scrollable_nodes"] += 1
        if text:
            stats["text_nodes"] += 1
        if "EditText" in class_name or "edit" in class_name.lower():
            stats["input_nodes"] += 1

        # 提取重要元素
        if clickable or scrollable or text or "Button" in class_name:
            element_info = {
                "class": class_name.split(".")[-1] if class_name else "",
                "text": text,
                "content_desc": node.get("content-desc", ""),
                "resource_id": node.get("resource-id", "").split("/")[-1] if node.get("resource-id") else "",
                "bounds": node.get("bounds", ""),
                "clickable": clickable,
                "scrollable": scrollable,
                "enabled": node.get("enabled", "false").lower() == "true",
                "focused": node.get("focused", "false").lower() == "true",
                "package": node.get("package", "")
            }
            stats["elements"].append(element_info)

        # 递归处理子节点
        for child in node:
            self._count_nodes(child, stats)

    def analyze_device(self, device_info: Dict[str, Any]) -> Dict[str, Any]:
        """分析单个设备"""
        device_id = device_info['serial']

        self.log(f"🔬 开始分析设备 {device_id}")
        self.log(f"📱 设备信息: {device_info['brand']} {device_info['model']} (Android {device_info['android_version']})")

        result = {
            "device_info": device_info,
            "analysis_time": datetime.now().isoformat(),
            "screenshot_path": None,
            "ui_hierarchy_path": None,
            "ui_structure": {},
            "success": False,
            "errors": []
        }

        try:
            # 1. 截图
            screenshot_path = self.take_screenshot(device_id, device_info)
            if screenshot_path:
                result["screenshot_path"] = screenshot_path

            # 2. 获取UI层次结构
            ui_hierarchy_path = self.dump_ui_hierarchy(device_id, device_info)
            if ui_hierarchy_path:
                result["ui_hierarchy_path"] = ui_hierarchy_path

                # 3. 解析UI结构
                ui_structure = self.parse_ui_hierarchy(ui_hierarchy_path)
                if ui_structure:
                    result["ui_structure"] = ui_structure
                    result["success"] = True

                # 4. 清理临时文件
                if not self.save_files and ui_hierarchy_path and os.path.exists(ui_hierarchy_path):
                    try:
                        os.remove(ui_hierarchy_path)
                    except Exception:
                        pass

            if not result["success"]:
                result["errors"].append("无法获取UI层次结构")

        except Exception as e:
            error_msg = f"分析设备时出错: {e}"
            self.log(f"❌ {error_msg}", "ERROR")
            result["errors"].append(error_msg)

        return result

    def run(self, target_device: Optional[str] = None) -> List[Dict[str, Any]]:
        """运行检测器"""
        self.log("🚀 启动通用UI检测器")
        self.log("=" * 60)

        # 获取设备列表
        devices = self.get_connected_devices()
        if not devices:
            self.log("❌ 未发现连接的设备", "ERROR")
            return []

        self.log(f"🔍 发现 {len(devices)} 个设备:")
        for i, device in enumerate(devices):
            self.log(f"   {i+1}. {device['serial']} - {device['brand']} {device['model']} (Android {device['android_version']})")

        # 确定目标设备
        target_devices = []
        if target_device:
            target_devices = [d for d in devices if d['serial'] == target_device]
            if not target_devices:
                self.log(f"❌ 指定的设备 {target_device} 未找到", "ERROR")
                return []
        else:
            target_devices = devices

        # 分析设备
        results = []
        for device_info in target_devices:
            try:
                result = self.analyze_device(device_info)
                results.append(result)
                self._print_analysis_result(result)

                if len(target_devices) > 1:
                    self.log("=" * 60)

            except Exception as e:
                self.log(f"❌ 分析设备 {device_info['serial']} 时出错: {e}", "ERROR")

        self.log("✅ 检测完成!")
        self._cleanup()

        return results

    def _print_analysis_result(self, result: Dict[str, Any]):
        """打印分析结果"""
        device_info = result["device_info"]
        device_id = device_info["serial"]

        print(f"\n📊 设备 {device_id} 分析结果")
        print("=" * 60)

        # 设备信息
        print("📱 设备信息:")
        print(f"   设备ID: {device_id}")
        print(f"   品牌: {device_info.get('brand', 'unknown')}")
        print(f"   型号: {device_info.get('model', 'unknown')}")
        print(f"   制造商: {device_info.get('manufacturer', 'unknown')}")
        print(f"   Android版本: {device_info.get('android_version', 'unknown')}")
        print(f"   API级别: {device_info.get('api_level', 'unknown')}")
        print(f"   屏幕分辨率: {device_info.get('resolution', 'unknown')}")
        print(f"   屏幕密度: {device_info.get('density', 'unknown')}")

        # 检测结果
        print(f"\n🎯 检测结果:")
        print(f"   截图: {'✅ 成功' if result['screenshot_path'] else '❌ 失败'}")
        print(f"   UI层次结构: {'✅ 成功' if result['ui_hierarchy_path'] else '❌ 失败'}")
        print(f"   整体状态: {'✅ 成功' if result['success'] else '❌ 失败'}")

        # UI统计信息
        ui_structure = result.get("ui_structure", {})
        if ui_structure:
            print(f"\n🔍 UI结构统计:")
            print(f"   总元素数: {ui_structure.get('total_nodes', 0)}")
            print(f"   可交互元素: {ui_structure.get('clickable_nodes', 0)}")
            print(f"   可滚动元素: {ui_structure.get('scrollable_nodes', 0)}")
            print(f"   文本元素: {ui_structure.get('text_nodes', 0)}")
            print(f"   输入元素: {ui_structure.get('input_nodes', 0)}")

            # 显示主要元素
            elements = ui_structure.get("elements", [])
            if elements:
                print(f"\n📋 主要UI元素 (前10个):")
                for i, element in enumerate(elements[:10]):
                    print(f"   {i+1}. {element.get('class', 'Unknown')}")
                    if element.get('text'):
                        print(f"      文本: '{element['text'][:50]}{'...' if len(element['text']) > 50 else ''}'")
                    if element.get('resource_id'):
                        print(f"      ID: {element['resource_id']}")
                    attrs = []
                    if element.get('clickable'):
                        attrs.append('可点击')
                    if element.get('scrollable'):
                        attrs.append('可滚动')
                    if attrs:
                        print(f"      属性: {', '.join(attrs)}")

        # 错误信息
        if result.get("errors"):
            print(f"\n⚠️ 错误信息:")
            for error in result["errors"]:
                print(f"   - {error}")

    def _cleanup(self):
        """清理资源"""
        if hasattr(self, 'log_file') and self.log_file:
            self.log_file.close()

    def __del__(self):
        """析构函数"""
        self._cleanup()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="通用UI检测器 - 支持多种Android版本和设备")
    parser.add_argument("--device", "-d", help="指定设备ID")
    parser.add_argument("--save", "-s", action="store_true", help="保存文件到本地")
    parser.add_argument("--output", "-o", default="ui_detection_output", help="输出目录")
    parser.add_argument("--timeout", "-t", type=int, default=60, help="操作超时时间（秒）")
    parser.add_argument("--retries", "-r", type=int, default=3, help="最大重试次数")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")

    args = parser.parse_args()

    # 创建检测器
    detector = UniversalUIDetector(
        device_id=args.device,
        save_files=args.save,
        output_dir=args.output,
        timeout=args.timeout,
        max_retries=args.retries
    )

    # 运行检测
    results = detector.run(args.device)

    # 保存结果摘要
    # if args.save and results:
    #     summary_path = os.path.join(args.output, f"detection_summary_{int(time.time())}.json")
    #     try:
    #         with open(summary_path, 'w', encoding='utf-8') as f:
    #             json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    #         print(f"\n💾 检测摘要已保存: {summary_path}")
    #     except Exception as e:
    #         print(f"⚠️ 保存摘要失败: {e}")


if __name__ == "__main__":
    main()
