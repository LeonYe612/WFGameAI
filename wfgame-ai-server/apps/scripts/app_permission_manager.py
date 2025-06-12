#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
App Permission Manager - 应用启动后权限弹窗处理器

专门处理应用启动后出现的Android系统权限弹窗，包括：
- 相机权限
- 麦克风权限
- 存储权限
- 位置权限
- 通知权限
等系统级权限弹窗的自动处理
"""

import time
import subprocess
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class PermissionAction(Enum):
    """权限弹窗可能的操作"""
    ALLOW = "allow"
    DENY = "deny"
    DONT_ASK_AGAIN = "dont_ask_again"
    WHILE_USING_APP = "while_using_app"

@dataclass
class PermissionDialog:
    """权限弹窗信息"""
    permission_type: str  # camera, microphone, storage, location, etc.
    dialog_title: str
    dialog_message: str
    available_actions: List[PermissionAction]
    recommended_action: PermissionAction = PermissionAction.ALLOW

class AndroidPermissionPatterns:
    """Android系统权限弹窗识别模式"""

    # 权限弹窗按钮文本模式
    PERMISSION_BUTTON_PATTERNS = {
        PermissionAction.ALLOW: [
            "允许", "Allow", "ALLOW", "同意", "确定", "OK", "接受"
        ],
        PermissionAction.DENY: [
            "拒绝", "Deny", "DENY", "不允许", "取消", "Cancel", "否"
        ],
        PermissionAction.DONT_ASK_AGAIN: [
            "不再询问", "Don't ask again", "不再提示", "记住选择"
        ],
        PermissionAction.WHILE_USING_APP: [
            "仅在使用应用时允许", "While using app", "使用时允许"
        ]
    }

    # 权限类型识别模式
    PERMISSION_TYPE_PATTERNS = {
        "camera": ["相机", "摄像头", "Camera", "camera", "拍照", "录像"],
        "microphone": ["麦克风", "音频", "Microphone", "microphone", "录音", "Audio"],
        "storage": ["存储", "文件", "Storage", "storage", "访问文件", "读写"],
        "location": ["位置", "定位", "Location", "location", "GPS", "地理位置"],
        "notification": ["通知", "Notification", "notification", "推送"],
        "contacts": ["通讯录", "联系人", "Contacts", "contacts"],
        "phone": ["电话", "Phone", "phone", "通话状态"],
        "sms": ["短信", "SMS", "sms", "消息"]
    }

    # 系统权限弹窗容器识别模式
    PERMISSION_DIALOG_CONTAINERS = [
        "com.android.packageinstaller",
        "com.android.permissioncontroller",
        "android.permission",
        "android.app.AlertDialog",
        "android.app.Dialog"
    ]

class AppPermissionManager:
    """应用权限管理器 - 专门处理应用启动后的权限弹窗"""

    def __init__(self):
        self.patterns = AndroidPermissionPatterns()
        self.permission_wait_timeout = 10  # 等待权限弹窗出现的超时时间(秒)
        self.permission_detection_interval = 0.5  # 权限弹窗检测间隔(秒)

    def wait_and_handle_permission_popups(self, device_serial: str, app_package: str = None,
                                        auto_allow: bool = True, max_popups: int = 5) -> bool:
        """
        等待并处理应用启动后的权限弹窗

        Args:
            device_serial: 设备序列号
            app_package: 应用包名（可选，用于更精确的检测）
            auto_allow: 是否自动允许权限（默认True）
            max_popups: 最多处理的权限弹窗数量

        Returns:
            bool: 是否成功处理所有权限弹窗
        """
        logger.info(f"开始等待并处理应用权限弹窗 - 设备: {device_serial}, 应用: {app_package}")

        handled_popups = 0
        start_time = time.time()

        while handled_popups < max_popups and (time.time() - start_time) < self.permission_wait_timeout:
            # 检测当前是否有权限弹窗
            permission_dialog = self._detect_permission_dialog(device_serial)

            if permission_dialog:
                logger.info(f"检测到权限弹窗: {permission_dialog.permission_type}")

                # 处理权限弹窗
                if self._handle_permission_dialog(device_serial, permission_dialog, auto_allow):
                    handled_popups += 1
                    logger.info(f"成功处理权限弹窗 {handled_popups}/{max_popups}")

                    # 等待弹窗消失和可能的下一个弹窗出现
                    time.sleep(1)
                else:
                    logger.warning(f"处理权限弹窗失败: {permission_dialog.permission_type}")
                    break
            else:
                # 短暂等待，检查是否有新的权限弹窗出现
                time.sleep(self.permission_detection_interval)

        if handled_popups > 0:
            logger.info(f"权限弹窗处理完成，共处理 {handled_popups} 个弹窗")
            return True
        else:
            logger.info("未检测到权限弹窗或权限弹窗已处理完毕")
            return True  # 没有权限弹窗也算成功

    def _detect_permission_dialog(self, device_serial: str) -> Optional[PermissionDialog]:
        """检测当前屏幕是否有权限弹窗"""
        try:
            # 获取当前UI层次结构
            ui_dump = self._get_ui_dump(device_serial)
            if not ui_dump:
                return None

            # 解析UI并查找权限弹窗
            return self._parse_permission_dialog(ui_dump)

        except Exception as e:
            logger.error(f"检测权限弹窗时出错: {e}")
            return None

    def _get_ui_dump(self, device_serial: str) -> Optional[str]:
        """获取设备UI层次结构"""
        try:
            # 导出UI层次结构到设备
            dump_cmd = f"adb -s {device_serial} shell uiautomator dump /sdcard/ui_dump.xml"
            result = subprocess.run(dump_cmd, shell=True, capture_output=True, text=True, timeout=10)

            if result.returncode != 0:
                return None

            # 拉取UI dump文件
            pull_cmd = f"adb -s {device_serial} pull /sdcard/ui_dump.xml"
            result = subprocess.run(pull_cmd, shell=True, capture_output=True, text=True, timeout=10)

            if result.returncode != 0:
                return None

            # 读取文件内容
            with open("ui_dump.xml", "r", encoding="utf-8") as f:
                content = f.read()

            return content

        except Exception as e:
            logger.error(f"获取UI dump失败: {e}")
            return None

    def _parse_permission_dialog(self, ui_dump: str) -> Optional[PermissionDialog]:
        """解析UI dump，查找权限弹窗"""
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(ui_dump)

            # 查找权限弹窗容器
            for element in root.iter():
                package = element.get('package', '')

                # 检查是否是权限弹窗容器
                if any(container in package for container in self.patterns.PERMISSION_DIALOG_CONTAINERS):
                    # 进一步分析弹窗内容
                    return self._analyze_permission_dialog_content(element)

            return None

        except Exception as e:
            logger.error(f"解析权限弹窗失败: {e}")
            return None

    def _analyze_permission_dialog_content(self, dialog_element) -> Optional[PermissionDialog]:
        """分析权限弹窗内容，识别权限类型和可用操作"""
        try:
            dialog_texts = []
            available_buttons = []

            # 收集弹窗中的所有文本和按钮
            for element in dialog_element.iter():
                text = element.get('text', '').strip()
                if text:
                    dialog_texts.append(text)

                # 查找按钮
                if element.get('clickable') == 'true' and text:
                    available_buttons.append({
                        'text': text,
                        'bounds': element.get('bounds', ''),
                        'resource_id': element.get('resource-id', '')
                    })

            # 识别权限类型
            permission_type = self._identify_permission_type(dialog_texts)

            # 识别可用操作
            available_actions = self._identify_available_actions(available_buttons)

            if permission_type and available_actions:
                return PermissionDialog(
                    permission_type=permission_type,
                    dialog_title=' '.join(dialog_texts[:2]),  # 前两个文本作为标题
                    dialog_message=' '.join(dialog_texts),
                    available_actions=available_actions,
                    recommended_action=PermissionAction.ALLOW
                )

            return None

        except Exception as e:
            logger.error(f"分析权限弹窗内容失败: {e}")
            return None

    def _identify_permission_type(self, texts: List[str]) -> Optional[str]:
        """根据弹窗文本识别权限类型"""
        combined_text = ' '.join(texts).lower()

        for perm_type, keywords in self.patterns.PERMISSION_TYPE_PATTERNS.items():
            if any(keyword.lower() in combined_text for keyword in keywords):
                return perm_type

        return "unknown"

    def _identify_available_actions(self, buttons: List[Dict[str, str]]) -> List[PermissionAction]:
        """识别权限弹窗中可用的操作按钮"""
        actions = []

        for button in buttons:
            button_text = button['text'].lower()

            for action, patterns in self.patterns.PERMISSION_BUTTON_PATTERNS.items():
                if any(pattern.lower() in button_text for pattern in patterns):
                    actions.append(action)
                    break

        return actions

    def _handle_permission_dialog(self, device_serial: str, dialog: PermissionDialog,
                                auto_allow: bool) -> bool:
        """处理权限弹窗，执行相应的操作"""
        try:
            target_action = PermissionAction.ALLOW if auto_allow else PermissionAction.DENY

            # 如果目标操作不可用，使用第一个可用操作
            if target_action not in dialog.available_actions:
                if dialog.available_actions:
                    target_action = dialog.available_actions[0]
                    logger.warning(f"目标操作不可用，使用: {target_action}")
                else:
                    logger.error("没有可用的操作按钮")
                    return False

            # 查找并点击对应的按钮
            return self._click_permission_button(device_serial, target_action)

        except Exception as e:
            logger.error(f"处理权限弹窗失败: {e}")
            return False

    def _click_permission_button(self, device_serial: str, action: PermissionAction) -> bool:
        """点击权限弹窗中的指定按钮"""
        try:
            # 重新获取UI层次，查找对应按钮
            ui_dump = self._get_ui_dump(device_serial)
            if not ui_dump:
                return False

            import xml.etree.ElementTree as ET
            root = ET.fromstring(ui_dump)

            # 查找匹配的按钮
            target_patterns = self.patterns.PERMISSION_BUTTON_PATTERNS.get(action, [])

            for element in root.iter():
                if element.get('clickable') == 'true':
                    text = element.get('text', '').strip()
                    if any(pattern.lower() in text.lower() for pattern in target_patterns):
                        # 找到目标按钮，点击它
                        bounds = element.get('bounds', '')
                        if bounds and self._click_bounds(device_serial, bounds):
                            logger.info(f"成功点击权限按钮: {text}")
                            return True

            logger.warning(f"未找到匹配的权限按钮: {action}")
            return False

        except Exception as e:
            logger.error(f"点击权限按钮失败: {e}")
            return False

    def _click_bounds(self, device_serial: str, bounds_str: str) -> bool:
        """根据bounds字符串点击屏幕位置"""
        try:
            # 解析bounds字符串: [left,top][right,bottom]
            import re
            matches = re.findall(r'\[(\d+),(\d+)\]', bounds_str)
            if len(matches) != 2:
                return False

            left, top = int(matches[0][0]), int(matches[0][1])
            right, bottom = int(matches[1][0]), int(matches[1][1])

            # 计算中心点
            center_x = (left + right) // 2
            center_y = (top + bottom) // 2

            # 执行点击
            tap_cmd = f"adb -s {device_serial} shell input tap {center_x} {center_y}"
            result = subprocess.run(tap_cmd, shell=True, capture_output=True, text=True, timeout=5)

            return result.returncode == 0

        except Exception as e:
            logger.error(f"点击bounds失败: {e}")
            return False

def integrate_with_app_launch(device_serial: str, app_package: str, auto_allow_permissions: bool = True) -> bool:
    """
    与应用启动流程集成的权限处理函数

    Args:
        device_serial: 设备序列号
        app_package: 应用包名
        auto_allow_permissions: 是否自动允许所有权限

    Returns:
        bool: 权限处理是否成功
    """
    permission_manager = AppPermissionManager()

    # 在应用启动后等待并处理权限弹窗
    return permission_manager.wait_and_handle_permission_popups(
        device_serial=device_serial,
        app_package=app_package,
        auto_allow=auto_allow_permissions,
        max_popups=5
    )

if __name__ == "__main__":
    # 测试使用
    import sys

    if len(sys.argv) < 2:
        print("Usage: python app_permission_manager.py <device_serial> [app_package]")
        sys.exit(1)

    device_serial = sys.argv[1]
    app_package = sys.argv[2] if len(sys.argv) > 2 else None

    success = integrate_with_app_launch(device_serial, app_package)
    print(f"权限处理结果: {'成功' if success else '失败'}")
