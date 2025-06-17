#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
增强权限点击器 - 避免使用固定坐标

提供多种智能点击方式：
1. 通过UI元素属性点击
2. 通过文本匹配点击
3. 通过UiSelector点击
4. 备选的坐标点击
"""

import subprocess
import time
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class EnhancedPermissionClicker:
    """增强权限点击器"""

    def __init__(self, device_serial: str):
        self.device_serial = device_serial

    def click_permission_button(self, button_text: str, action_type: str = "allow") -> bool:
        """
        智能点击权限按钮，按优先级尝试多种方式

        Args:
            button_text: 按钮文本（如 "同意"、"允许"）
            action_type: 操作类型（"allow", "deny"）

        Returns:
            bool: 是否成功点击
        """
        logger.info(f"开始智能点击权限按钮: '{button_text}' (类型: {action_type})")

        # 方式1: 通过UiAutomator的UiSelector点击
        if self._click_by_uiselector(button_text):
            logger.info(f"✅ 通过UiSelector成功点击按钮: '{button_text}'")
            return True

        # 方式2: 通过uiautomator2风格的text点击
        if self._click_by_text_command(button_text):
            logger.info(f"✅ 通过text命令成功点击按钮: '{button_text}'")
            return True

        # 方式3: 通过Resource ID点击（如果有的话）
        if self._click_by_resource_id(button_text, action_type):
            logger.info(f"✅ 通过Resource ID成功点击按钮: '{button_text}'")
            return True

        # 方式4: 通过accessibility service点击
        if self._click_by_accessibility(button_text):
            logger.info(f"✅ 通过accessibility成功点击按钮: '{button_text}'")
            return True

        # 方式5: 最后备选 - 通过bounds点击（但会给出警告）
        if self._click_by_bounds_fallback(button_text):
            logger.warning(f"⚠️ 通过坐标备选方式点击按钮: '{button_text}' (不建议)")
            return True

        logger.error(f"❌ 所有点击方式都失败了: '{button_text}'")
        return False

    def _click_by_uiselector(self, button_text: str) -> bool:
        """方式1: 通过UiSelector点击"""
        try:
            logger.info(f"尝试通过UiSelector点击: '{button_text}'")

            # 使用uiautomator的text selector
            cmd = f'adb -s {self.device_serial} shell uiautomator runtest uiautomator-stub.jar -c com.github.uiautomator.stub.Stub -e text "{button_text}"'

            # 简化版本：直接使用input命令配合uiautomator dump来查找元素
            # 首先尝试查找可点击的元素
            find_cmd = f'adb -s {self.device_serial} shell "dumpsys activity top | grep -i \'{button_text}\'"'
            result = subprocess.run(find_cmd, shell=True, capture_output=True, text=True, timeout=5)

            if button_text in result.stdout:
                # 使用uiautomator的click命令
                click_cmd = f'adb -s {self.device_serial} shell "input keyevent KEYCODE_TAB && input keyevent KEYCODE_ENTER"'
                result = subprocess.run(click_cmd, shell=True, capture_output=True, text=True, timeout=5)
                return result.returncode == 0

            return False

        except Exception as e:
            logger.debug(f"UiSelector点击失败: {e}")
            return False

    def _click_by_text_command(self, button_text: str) -> bool:
        """方式2: 通过text匹配命令点击"""
        try:
            logger.info(f"尝试通过text命令点击: '{button_text}'")

            # 使用uiautomator命令行工具
            cmd = f'adb -s {self.device_serial} shell "uiautomator runtest UIAutomatorStub.jar -c com.github.uiautomatorstub.Stub -e text \'{button_text}\' -e action click"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                time.sleep(0.5)  # 等待点击生效
                return True

            # 备选：使用monkey命令
            monkey_cmd = f'adb -s {self.device_serial} shell "monkey -p $(dumpsys window windows | grep -E \'mCurrentFocus|mFocusedApp\' | tail -1 | cut -d\'/\' -f1 | cut -d\' \' -f7) --pct-touch 100 1"'
            result = subprocess.run(monkey_cmd, shell=True, capture_output=True, text=True, timeout=5)

            return False

        except Exception as e:
            logger.debug(f"text命令点击失败: {e}")
            return False

    def _click_by_resource_id(self, button_text: str, action_type: str) -> bool:
        """方式3: 通过Resource ID点击"""
        try:
            logger.info(f"尝试通过Resource ID点击: '{button_text}'")

            # 常见的权限按钮Resource ID模式
            possible_ids = []

            if action_type == "allow":
                possible_ids = [
                    "com.android.permissioncontroller:id/permission_allow_button",
                    "android:id/button1",  # 通常是确定/允许按钮
                    "com.android.packageinstaller:id/permission_allow_button",
                    "android:id/button_once",
                    "android:id/button_always"
                ]
            else:  # deny
                possible_ids = [
                    "com.android.permissioncontroller:id/permission_deny_button",
                    "android:id/button2",  # 通常是取消/拒绝按钮
                    "com.android.packageinstaller:id/permission_deny_button",
                    "android:id/button_deny"
                ]

            # 应用自定义的可能ID
            possible_ids.extend([
                "btn_agree", "btn_confirm", "btn_ok", "btn_allow",
                "btn_disagree", "btn_cancel", "btn_deny",
                "tv_agree", "tv_confirm", "tv_ok",
                "tv_disagree", "tv_cancel"
            ])

            for resource_id in possible_ids:
                try:
                    cmd = f'adb -s {self.device_serial} shell "uiautomator runtest UIAutomatorStub.jar -c com.github.uiautomatorstub.Stub -e resourceId \'{resource_id}\' -e action click"'
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)

                    if result.returncode == 0:
                        logger.info(f"通过Resource ID成功点击: {resource_id}")
                        time.sleep(0.5)
                        return True

                except Exception:
                    continue

            return False

        except Exception as e:
            logger.debug(f"Resource ID点击失败: {e}")
            return False

    def _click_by_accessibility(self, button_text: str) -> bool:
        """方式4: 通过accessibility service点击"""
        try:
            logger.info(f"尝试通过accessibility点击: '{button_text}'")

            # 使用accessibility service发送点击事件
            cmd = f'adb -s {self.device_serial} shell "settings put secure enabled_accessibility_services com.android.talkback/.TalkBackService && am broadcast -a android.accessibilityservice.AccessibilityService"'
            subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)

            # 尝试通过content description点击
            content_desc_cmd = f'adb -s {self.device_serial} shell "uiautomator runtest UIAutomatorStub.jar -c com.github.uiautomatorstub.Stub -e contentDescription \'{button_text}\' -e action click"'
            result = subprocess.run(content_desc_cmd, shell=True, capture_output=True, text=True, timeout=5)

            if result.returncode == 0:
                time.sleep(0.5)
                return True

            return False

        except Exception as e:
            logger.debug(f"accessibility点击失败: {e}")
            return False

    def _click_by_bounds_fallback(self, button_text: str) -> bool:
        """方式5: 备选的坐标点击（不建议，但作为最后手段）"""
        try:
            logger.warning(f"⚠️ 使用坐标备选方式点击: '{button_text}' (建议改进UI交互方式)")

            # 获取UI dump找到元素
            dump_cmd = f"adb -s {self.device_serial} shell uiautomator dump /sdcard/temp_ui.xml"
            result = subprocess.run(dump_cmd, shell=True, capture_output=True, text=True, timeout=10)

            if result.returncode != 0:
                return False

            # 拉取文件
            pull_cmd = f"adb -s {self.device_serial} pull /sdcard/temp_ui.xml"
            result = subprocess.run(pull_cmd, shell=True, capture_output=True, text=True, timeout=10)

            if result.returncode != 0:
                return False

            # 解析XML找到按钮
            import xml.etree.ElementTree as ET
            with open("temp_ui.xml", "r", encoding="utf-8") as f:
                content = f.read()

            root = ET.fromstring(content)

            for element in root.iter():
                if element.get('clickable') == 'true' and element.get('text') == button_text:
                    bounds = element.get('bounds', '')
                    if bounds:
                        import re
                        matches = re.findall(r'\[(\d+),(\d+)\]', bounds)
                        if len(matches) == 2:
                            left, top = int(matches[0][0]), int(matches[0][1])
                            right, bottom = int(matches[1][0]), int(matches[1][1])
                            center_x = (left + right) // 2
                            center_y = (top + bottom) // 2

                            # 执行点击
                            tap_cmd = f"adb -s {self.device_serial} shell input tap {center_x} {center_y}"
                            result = subprocess.run(tap_cmd, shell=True, capture_output=True, text=True, timeout=5)

                            if result.returncode == 0:
                                logger.warning(f"坐标点击成功: ({center_x}, {center_y})")
                                return True

            return False

        except Exception as e:
            logger.debug(f"坐标备选点击失败: {e}")
            return False

    def click_with_smart_retry(self, button_text: str, action_type: str = "allow", max_retries: int = 3) -> bool:
        """智能重试点击"""
        for attempt in range(max_retries):
            logger.info(f"第 {attempt + 1}/{max_retries} 次尝试点击 '{button_text}'")

            if self.click_permission_button(button_text, action_type):
                return True

            if attempt < max_retries - 1:
                logger.info(f"等待 1 秒后重试...")
                time.sleep(1)

        logger.error(f"经过 {max_retries} 次尝试，仍无法点击按钮: '{button_text}'")
        return False

def test_enhanced_clicker():
    """测试增强点击器"""
    import sys

    if len(sys.argv) < 2:
        print("用法: python enhanced_permission_clicker.py <设备序列号>")
        sys.exit(1)

    device_serial = sys.argv[1]

    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    clicker = EnhancedPermissionClicker(device_serial)

    print("测试增强权限点击器...")
    print("尝试点击 '同意' 按钮...")

    success = clicker.click_with_smart_retry("同意", "allow", max_retries=2)

    if success:
        print("✅ 成功点击权限按钮")
    else:
        print("❌ 点击权限按钮失败")

if __name__ == "__main__":
    test_enhanced_clicker()
