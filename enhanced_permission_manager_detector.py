#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Enhanced Permission Manager - 使用UI结构检测器方式
不使用XML解析，而是使用UI结构检测器的方式来检测和点击权限弹窗
"""

import subprocess
import time
import logging
from typing import Dict, List, Optional, Any, Tuple
import json
import re

logger = logging.getLogger(__name__)

class EnhancedPermissionManager:
    """增强权限管理器 - 使用UI结构检测器方式"""

    def __init__(self):
        self.device_id = None
        self.ui_elements = []

    def detect_and_handle_permission_popup(self, device_id: str) -> bool:
        """检测并处理权限弹窗"""
        self.device_id = device_id

        # 1. 获取UI结构
        if not self._get_ui_structure():
            logger.error("无法获取UI结构")
            return False

        # 2. 检测权限弹窗
        popup_info = self._detect_permission_popup()
        if not popup_info:
            logger.info("未检测到权限弹窗")
            return True  # 没有弹窗也算成功

        # 3. 查找同意按钮
        agree_button = self._find_agree_button()
        if not agree_button:
            logger.error("未找到同意按钮")
            return False

        # 4. 点击同意按钮
        return self._click_button(agree_button)

    def _get_ui_structure(self) -> bool:
        """获取UI结构"""
        try:
            logger.info("正在获取UI结构...")

            # 执行UI dump
            dump_cmd = f"adb -s {self.device_id} shell uiautomator dump"
            result = subprocess.run(dump_cmd, shell=True, capture_output=True, text=True, timeout=10)

            if result.returncode != 0:
                logger.error(f"UI dump失败: {result.stderr}")
                return False

            # 获取UI内容
            get_cmd = f"adb -s {self.device_id} shell cat /sdcard/window_dump.xml"
            result = subprocess.run(get_cmd, shell=True, capture_output=True, text=True, timeout=10)

            if result.returncode != 0:
                logger.error(f"获取UI内容失败: {result.stderr}")
                return False

            # 解析UI元素（简化版本，不使用XML）
            self.ui_elements = self._parse_ui_simple(result.stdout)
            logger.info(f"获取到 {len(self.ui_elements)} 个UI元素")

            return True

        except Exception as e:
            logger.error(f"获取UI结构异常: {e}")
            return False

    def _parse_ui_simple(self, ui_content: str) -> List[Dict[str, Any]]:
        """简化UI解析 - 不使用XML，直接解析文本"""
        elements = []

        try:
            # 查找所有clickable="true"的元素
            clickable_pattern = r'clickable="true"[^>]*text="([^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
            matches = re.findall(clickable_pattern, ui_content)

            for match in matches:
                text, x1, y1, x2, y2 = match
                if text.strip():  # 只保留有文本的元素
                    elements.append({
                        'text': text.strip(),
                        'x1': int(x1),
                        'y1': int(y1),
                        'x2': int(x2),
                        'y2': int(y2),
                        'center_x': (int(x1) + int(x2)) // 2,
                        'center_y': (int(y1) + int(y2)) // 2,
                        'clickable': True
                    })

            # 查找resource-id信息
            id_pattern = r'resource-id="([^"]*)"[^>]*text="([^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
            id_matches = re.findall(id_pattern, ui_content)

            for match in id_matches:
                resource_id, text, x1, y1, x2, y2 = match
                # 更新已有元素的resource-id信息
                for element in elements:
                    if (element['text'] == text.strip() and
                        element['x1'] == int(x1) and element['y1'] == int(y1)):
                        element['resource_id'] = resource_id
                        break

            logger.info(f"解析到可点击元素: {[e['text'] for e in elements]}")
            return elements

        except Exception as e:
            logger.error(f"UI解析异常: {e}")
            return []

    def _detect_permission_popup(self) -> Optional[Dict[str, Any]]:
        """检测权限弹窗"""
        # 权限弹窗关键词
        permission_keywords = [
            "个人信息保护指引", "隐私政策", "用户协议", "权限申请",
            "权限说明", "Privacy Policy", "个人信息", "隐私保护"
        ]

        # 检查是否有权限相关文本
        all_texts = [element['text'] for element in self.ui_elements]
        combined_text = ' '.join(all_texts)

        has_permission_keywords = any(keyword in combined_text for keyword in permission_keywords)

        if has_permission_keywords:
            logger.info(f"检测到权限弹窗，关键词匹配")
            logger.info(f"弹窗文本: {combined_text[:200]}...")

            return {
                'type': 'permission_popup',
                'text': combined_text,
                'elements': self.ui_elements
            }

        return None

    def _find_agree_button(self) -> Optional[Dict[str, Any]]:
        """查找同意按钮"""
        # 同意按钮的可能文本
        agree_patterns = ["同意", "允许", "确定", "OK", "Allow", "Accept", "Agree"]

        for element in self.ui_elements:
            if element.get('clickable') and element['text'] in agree_patterns:
                logger.info(f"找到同意按钮: '{element['text']}' at ({element['center_x']}, {element['center_y']})")
                return element

        # 如果没找到精确匹配，尝试包含匹配
        for element in self.ui_elements:
            if element.get('clickable'):
                for pattern in agree_patterns:
                    if pattern in element['text']:
                        logger.info(f"找到同意按钮(包含匹配): '{element['text']}' at ({element['center_x']}, {element['center_y']})")
                        return element

        logger.warning("未找到同意按钮")
        return None

    def _click_button(self, button: Dict[str, Any]) -> bool:
        """点击按钮"""
        try:
            x = button['center_x']
            y = button['center_y']

            logger.info(f"点击按钮 '{button['text']}' at ({x}, {y})")

            # 执行点击
            tap_cmd = f"adb -s {self.device_id} shell input tap {x} {y}"
            result = subprocess.run(tap_cmd, shell=True, capture_output=True, text=True, timeout=5)

            if result.returncode == 0:
                logger.info("✅ 按钮点击成功")
                time.sleep(1.5)  # 等待响应

                # 验证点击效果 - 重新检测是否还有弹窗
                if self._verify_click_success():
                    logger.info("✅ 点击验证成功，权限弹窗已消失")
                    return True
                else:
                    logger.warning("⚠️ 权限弹窗仍然存在")
                    return False
            else:
                logger.error(f"❌ 按钮点击失败: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"点击按钮异常: {e}")
            return False

    def _verify_click_success(self) -> bool:
        """验证点击是否成功"""
        try:
            # 重新获取UI结构
            if not self._get_ui_structure():
                return False

            # 检查是否还有权限弹窗
            popup_info = self._detect_permission_popup()
            return popup_info is None

        except Exception as e:
            logger.error(f"验证点击效果异常: {e}")
            return False

def test_enhanced_permission_manager():
    """测试增强权限管理器"""
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    device_id = "5c41023b"
    manager = EnhancedPermissionManager()

    print("🧪 测试增强权限管理器...")
    print("=" * 60)

    success = manager.detect_and_handle_permission_popup(device_id)

    if success:
        print("✅ 权限弹窗处理成功")
    else:
        print("❌ 权限弹窗处理失败")

    return success

if __name__ == "__main__":
    test_enhanced_permission_manager()
