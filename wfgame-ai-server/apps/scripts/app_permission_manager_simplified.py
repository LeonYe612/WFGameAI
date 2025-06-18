#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
App Permission Manager - 精简版权限弹窗处理器

专门处理应用启动后出现的Android系统权限弹窗，包括：
- 相机权限
- 麦克风权限
- 存储权限
- 位置权限
- 通知权限
等系统级权限弹窗的自动处理

精简版特点：
- 删除复杂评分算法，保留精准匹配识别
- 集成3种成功的点击方法：文本匹配、Resource ID、坐标点击
- 添加device_id参数支持
- 智能失败检测：点击后检查元素是否消失
- 按优先级顺序执行：文本匹配 -> Resource ID -> 坐标点击
"""

import time
import subprocess
import logging
import xml.etree.ElementTree as ET
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

    # 权限弹窗按钮文本模式（精简版：包含resource_id信息用于精准识别）
    PERMISSION_BUTTON_PATTERNS = {
        PermissionAction.ALLOW: {
            "texts": ["允许", "同意", "确定", "OK", "接受", "始终允许"],
            "resource_ids": [
                "com.android.permissioncontroller:id/permission_allow_button",
                "android:id/button1",  # 通常是确定/允许按钮
                "com.android.packageinstaller:id/permission_allow_button",
                "android:id/button_once",
                "android:id/button_always",
                "btn_agree", "btn_confirm", "btn_ok", "btn_allow",
                "tv_agree", "tv_confirm", "tv_ok",
                "com.beeplay.card2prepare:id/tv_ok"  # 从quick测试中识别的实际ID
            ]
        },
        PermissionAction.DENY: {
            "texts": ["拒绝", "不允许", "禁止", "取消", "Cancel", "否", "不同意"],
            "resource_ids": [
                "com.android.permissioncontroller:id/permission_deny_button",
                "android:id/button2",  # 通常是取消/拒绝按钮
                "com.android.packageinstaller:id/permission_deny_button",
                "android:id/button_deny",
                "btn_disagree", "btn_cancel", "btn_deny",
                "tv_disagree", "tv_cancel"
            ]
        },
        PermissionAction.DONT_ASK_AGAIN: {
            "texts": ["不再询问", "Don't ask again", "不再提示", "记住选择"],
            "resource_ids": ["android:id/checkbox"]
        },
        PermissionAction.WHILE_USING_APP: {
            "texts": ["仅在使用应用时允许", "使用时允许"],
            "resource_ids": []
        }
    }

    # 系统权限弹窗容器识别模式
    PERMISSION_DIALOG_CONTAINERS = [
        "com.android.packageinstaller",
        "com.android.permissioncontroller",
        "android.permission",
        "android.app.AlertDialog",
        "android.app.Dialog"
    ]

    # 应用自定义弹窗识别关键词
    APP_CUSTOM_DIALOG_KEYWORDS = [
        "个人信息保护指引", "隐私政策", "用户协议", "Privacy Policy", "获取此设备",
        "权限申请", "权限说明", "服务条款", "使用条款",
        "tvTitle", "tv_ok", "tv_cancel"  # 常见的弹窗控件ID
    ]    # 游戏登录界面关键词（用于排除非权限界面）
    GAME_LOGIN_KEYWORDS = [
        "请输入手机号", "验证码", "获取验证码", "登录", "注册", "账号", "密码",
        "手机号", "验证", "登陆", "Sign in", "Login", "Register", "Phone", "Password"
    ]

    # 权限类型识别关键词
    PRIVACY_POLICY_KEYWORDS = [
        "隐私政策", "个人信息保护", "用户协议", "privacy policy", "隐私条款", "服务条款"
    ]

    PERMISSION_REQUEST_KEYWORDS = [
        "权限申请", "权限说明", "访问权限", "permission"
    ]

class AppPermissionManager:
    """应用权限管理器 - 精简版专门处理应用启动后的权限弹窗"""

    def __init__(self, device_id: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """
        初始化权限管理器

        Args:
            device_id: 设备ID（新增支持）
            config: 可选配置字典
        """
        self.device_id = device_id  # 新增：支持device_id参数
        self.patterns = AndroidPermissionPatterns()

        # 使用合理的默认值，保持代码简洁
        self.permission_wait_timeout = 30  # 权限等待超时
        self.permission_detection_interval = 0.8  # 检测间隔
        self.popup_interval_wait = 2.5  # 弹窗间隔
        self.no_popup_confirm_count = 3  # 确认次数

    def wait_and_handle_permission_popups(self, device_serial: str, app_package: Optional[str] = None,
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
        detection_failures = 0
        max_detection_failures = 3
        start_time = time.time()

        while handled_popups < max_popups and (time.time() - start_time) < self.permission_wait_timeout:
            # 检测当前是否有权限弹窗
            permission_dialog = self._detect_permission_dialog(device_serial)

            if permission_dialog:
                logger.info(f"检测到权限弹窗: {permission_dialog.permission_type}")
                logger.info(f"弹窗标题: {permission_dialog.dialog_title}")
                logger.info(f"可用操作: {[action.value for action in permission_dialog.available_actions]}")

                # 处理权限弹窗
                if self._handle_permission_dialog(device_serial, permission_dialog, auto_allow):
                    handled_popups += 1
                    logger.info(f"成功处理权限弹窗 {handled_popups}/{max_popups}")
                    detection_failures = 0  # 重置检测失败计数

                    # 等待弹窗消失和可能的下一个弹窗出现
                    time.sleep(1)
                else:
                    logger.warning(f"处理权限弹窗失败: {permission_dialog.permission_type}")
                    return False  # 检测到权限弹窗但处理失败，返回False
            else:
                # 检查是否是UI dump获取失败
                ui_dump = self._get_ui_dump(device_serial)
                if ui_dump is None:
                    detection_failures += 1
                    logger.warning(f"UI检测失败 {detection_failures}/{max_detection_failures}")

                    if detection_failures >= max_detection_failures:
                        logger.error("多次UI检测失败，可能存在设备连接问题")
                        return False

                # 短暂等待，检查是否有新的权限弹窗出现
                time.sleep(self.permission_detection_interval)

        # 最终检查：确认当前屏幕是否还有权限弹窗
        final_check = self._detect_permission_dialog(device_serial)
        if final_check:
            logger.warning(f"检测周期结束，但仍存在未处理的权限弹窗: {final_check.permission_type}")
            logger.warning(f"弹窗内容: {final_check.dialog_message[:100]}...")
            return False

        if handled_popups > 0:
            logger.info(f"权限弹窗处理完成，共处理 {handled_popups} 个弹窗")
            return True
        else:
            logger.info("经过完整检测周期，未发现权限弹窗")
            return True  # 经过完整检测确认没有权限弹窗    def _detect_permission_dialog(self, device_serial: str) -> Optional[PermissionDialog]:
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

    def _get_all_permission_button_texts(self) -> List[str]:
        """从 PERMISSION_BUTTON_PATTERNS 中提取所有权限相关按钮文本"""
        all_texts = []
        for action, patterns in self.patterns.PERMISSION_BUTTON_PATTERNS.items():
            texts = patterns.get('texts', [])
            all_texts.extend(texts)
        return all_texts

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
            root = ET.fromstring(ui_dump)

            # 方法1：查找系统权限弹窗容器
            for element in root.iter():
                package = element.get('package', '')

                # 检查是否是系统权限弹窗容器
                if any(container in package for container in self.patterns.PERMISSION_DIALOG_CONTAINERS):
                    dialog = self._analyze_permission_dialog_content(element)
                    if dialog:
                        return dialog

            # 方法2：查找应用自定义权限/隐私弹窗
            permission_dialog = self._detect_app_custom_permission_dialog(root)
            if permission_dialog:
                return permission_dialog

            return None

        except Exception as e:
            logger.error(f"解析权限弹窗失败: {e}")
            return None

    def _detect_app_custom_permission_dialog(self, root) -> Optional[PermissionDialog]:
        """检测应用自定义的权限/隐私弹窗"""
        try:
            all_texts = []
            clickable_elements = []

            # 收集所有文本和可点击元素
            for element in root.iter():
                text = element.get('text', '').strip()
                if text:
                    all_texts.append(text)

                if element.get('clickable') == 'true' and text:
                    clickable_elements.append({
                        'text': text,
                        'bounds': element.get('bounds', ''),
                        'resource_id': element.get('resource-id', '')
                    })

            # 检查是否包含自定义弹窗关键词
            combined_text = ' '.join(all_texts)
            has_custom_keywords = any(
                keyword in combined_text
                for keyword in self.patterns.APP_CUSTOM_DIALOG_KEYWORDS
            )

            # 检查是否为游戏登录界面（应该排除）
            has_login_keywords = any(
                keyword in combined_text
                for keyword in self.patterns.GAME_LOGIN_KEYWORDS
            )

            has_privacy_keywords = any(
                keyword in combined_text
                for keyword in self.patterns.APP_CUSTOM_DIALOG_KEYWORDS
            )            # 智能判断：如果同时包含隐私政策关键词和权限按钮，优先识别为权限弹窗
            # 从PERMISSION_BUTTON_PATTERNS中提取所有权限相关按钮文本
            permission_button_texts = self._get_all_permission_button_texts()
            is_actual_login_screen = (
                has_login_keywords and
                not has_privacy_keywords and  # 没有隐私政策相关内容
                not any(action_text in combined_text for action_text in permission_button_texts)  # 没有权限相关按钮
            )

            # 如果检测到真正的登录界面，不应该作为权限弹窗处理
            if is_actual_login_screen:
                logger.info(f"检测到真正的游戏登录界面，跳过权限处理")
                logger.info(f"登录界面文本: {combined_text[:200]}...")
                return None
            elif has_login_keywords and has_privacy_keywords:
                logger.info(f"检测到包含登录功能说明的权限弹窗，继续处理")
                logger.info(f"弹窗文本: {combined_text[:200]}...")

            if has_custom_keywords and clickable_elements:
                logger.info(f"检测到应用自定义权限/隐私弹窗")
                logger.info(f"弹窗文本内容: {combined_text[:200]}...")

                # 识别弹窗类型
                permission_type = self._identify_permission_type(all_texts)

                # 识别可用操作
                available_actions = self._identify_available_actions(clickable_elements)

                if available_actions:
                    return PermissionDialog(
                        permission_type=permission_type,
                        dialog_title="应用自定义权限弹窗",
                        dialog_message=combined_text[:100] + "...",
                        available_actions=available_actions,
                        recommended_action=PermissionAction.ALLOW
                    )

            return None

        except Exception as e:
            logger.error(f"检测应用自定义弹窗失败: {e}")
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

            return None        except Exception as e:
            logger.error(f"分析权限弹窗内容失败: {e}")
            return None

    def _identify_permission_type(self, texts: List[str]) -> str:
        """简化的权限类型识别 - 只返回通用权限类型"""
        combined_text = ' '.join(texts).lower()

        # 使用参数化的关键词模式进行判断
        if any(keyword in combined_text for keyword in self.patterns.PRIVACY_POLICY_KEYWORDS):
            return "privacy_policy"
        elif any(keyword in combined_text for keyword in self.patterns.PERMISSION_REQUEST_KEYWORDS):
            return "app_permission"
        else:
            # 对于所有其他类型的权限弹窗，返回通用类型
            return "permission"

    def _identify_available_actions(self, buttons: List[Dict[str, str]]) -> List[PermissionAction]:
        """识别权限弹窗中可用的操作按钮 - 精确匹配版（支持新的PERMISSION_BUTTON_PATTERNS结构）"""
        actions = []

        logger.info(f"开始识别按钮操作，共有 {len(buttons)} 个按钮")

        for button in buttons:
            button_text = button['text'].strip()
            button_resource_id = button.get('resource_id', '')
            logger.info(f"处理按钮: '{button_text}', resource_id: '{button_resource_id}'")

            matched_action = None

            # 遍历所有操作类型进行匹配
            for action, patterns in self.patterns.PERMISSION_BUTTON_PATTERNS.items():
                # 1. 文本精确匹配
                for text_pattern in patterns['texts']:
                    if button_text == text_pattern:
                        matched_action = action
                        logger.info(f"按钮 '{button_text}' 文本精确匹配为 {action.value} 操作")
                        break

                # 2. Resource ID匹配
                if not matched_action and button_resource_id:
                    for resource_id_pattern in patterns['resource_ids']:
                        if button_resource_id == resource_id_pattern:
                            matched_action = action
                            logger.info(f"按钮 resource_id '{button_resource_id}' 匹配为 {action.value} 操作")
                            break

                if matched_action:
                    break

            if matched_action:
                actions.append(matched_action)
            else:
                logger.warning(f"按钮 '{button_text}' (resource_id: '{button_resource_id}') 未找到匹配")

        logger.info(f"最终识别结果: {[action.value for action in actions]}")
        return actions

    def _handle_permission_dialog(self, device_serial: str, dialog: PermissionDialog,
                                auto_allow: bool) -> bool:
        """处理权限弹窗，执行相应的操作"""
        try:
            target_action = PermissionAction.ALLOW if auto_allow else PermissionAction.DENY

            # 如果目标操作不可用，智能选择备选操作
            if target_action not in dialog.available_actions:
                if dialog.available_actions:
                    # 优先选择ALLOW，如果没有则选择其他
                    if auto_allow and PermissionAction.ALLOW in dialog.available_actions:
                        target_action = PermissionAction.ALLOW
                    elif not auto_allow and PermissionAction.DENY in dialog.available_actions:
                        target_action = PermissionAction.DENY
                    else:
                        # 如果首选不可用，按优先级选择：ALLOW > WHILE_USING_APP > DENY > DONT_ASK_AGAIN
                        priority_order = [PermissionAction.ALLOW, PermissionAction.WHILE_USING_APP,
                                        PermissionAction.DENY, PermissionAction.DONT_ASK_AGAIN]
                        for preferred_action in priority_order:
                            if preferred_action in dialog.available_actions:
                                target_action = preferred_action
                                break
                        else:
                            target_action = dialog.available_actions[0]

                    logger.warning(f"目标操作不可用，使用: {target_action.value}")
                else:
                    logger.error("没有可用的操作按钮")
                    return False
            else:
                logger.info(f"使用目标操作: {target_action.value}")

            # 查找并点击对应的按钮
            return self._click_permission_button(device_serial, target_action)

        except Exception as e:
            logger.error(f"处理权限弹窗失败: {e}")
            return False

    def _click_permission_button(self, device_serial: str, action: PermissionAction) -> bool:
        """点击权限弹窗中的指定按钮 - 使用3种成功的点击方法"""
        try:
            # 获取目标按钮文本和resource_id模式
            patterns = self.patterns.PERMISSION_BUTTON_PATTERNS.get(action, {})
            target_texts = patterns.get('texts', [])
            logger.info(f"查找目标操作 {action.value} 的按钮，文本模式: {target_texts}")

            # 记录点击前的状态，用于后续验证
            initial_target_text = target_texts[0] if target_texts else ""

            # 方法1: 通过文本精确匹配点击（第一优先级）
            for text_pattern in target_texts:
                logger.info(f"🎯 尝试方法1：文本匹配点击 '{text_pattern}'")
                if self._click_by_text_match(device_serial, text_pattern):
                    # 检查元素是否消失（点击成功验证）
                    time.sleep(0.8)  # 等待界面响应
                    if not self._element_still_exists(device_serial, text_pattern):
                        logger.info(f"✅ 文本匹配点击成功，元素已消失: '{text_pattern}'")
                        return True
                    else:
                        logger.info(f"⚠️ 文本匹配点击后元素仍存在，继续下一种方法")

            # 方法2: 通过Resource ID查找并点击（第二优先级）
            logger.info(f"🆔 尝试方法2：Resource ID点击")
            if self._click_by_resource_id_simple(device_serial, action):
                # 检查元素是否消失（点击成功验证）
                time.sleep(0.8)  # 等待界面响应
                if not self._element_still_exists(device_serial, initial_target_text):
                    logger.info(f"✅ Resource ID点击成功，元素已消失")
                    return True
                else:
                    logger.info(f"⚠️ Resource ID点击后元素仍存在，继续下一种方法")

            # 方法3: 坐标点击（第三优先级，使用固定坐标作为最后手段）
            logger.info(f"📍 尝试方法3：固定坐标点击")
            # 使用quick测试中成功的同意按钮坐标
            if action == PermissionAction.ALLOW:
                x, y = 775, 2221  # 从quick测试中获得的成功坐标
                if self._click_by_coordinates(device_serial, x, y):
                    # 检查元素是否消失（点击成功验证）
                    time.sleep(0.8)  # 等待界面响应
                    if not self._element_still_exists(device_serial, initial_target_text):
                        logger.info(f"✅ 坐标点击成功，元素已消失")
                        return True
                    else:
                        logger.info(f"⚠️ 坐标点击后元素仍存在")

            logger.warning(f"❌ 所有3种点击方法都失败了: {action.value}")
            return False

        except Exception as e:
            logger.error(f"点击权限按钮失败: {e}")
            return False

    def _click_by_text_match(self, device_serial: str, target_text: str) -> bool:
        """方法1: 通过文本精确匹配点击（参考quick测试成功实现）"""
        try:
            logger.info(f"🎯 方法1: 通过文本精确匹配点击: '{target_text}'")

            # 获取UI结构
            ui_dump = self._get_ui_dump(device_serial)
            if not ui_dump:
                logger.warning("❌ 无法获取UI结构")
                return False

            # 解析XML查找文本元素（精确匹配+可点击检查）
            root = ET.fromstring(ui_dump)

            def find_text_element(node):
                if node.get('text') == target_text and node.get('clickable') == 'true':
                    bounds = node.get('bounds')
                    logger.info(f"📍 找到文本元素bounds: {bounds}")
                    return bounds
                for child in node:
                    result = find_text_element(child)
                    if result:
                        return result
                return None

            bounds = find_text_element(root)

            if bounds:
                # 解析bounds并点击（参考quick测试的成功做法）
                bounds = bounds.strip('[]')
                parts = bounds.split('][')
                left_top = parts[0].split(',')
                right_bottom = parts[1].split(',')

                x1, y1 = int(left_top[0]), int(left_top[1])
                x2, y2 = int(right_bottom[0]), int(right_bottom[1])
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2

                logger.info(f"📍 通过文本计算的中心点: ({center_x}, {center_y})")

                # 执行点击
                cmd = f"adb -s {device_serial} shell input tap {center_x} {center_y}"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

                if result.returncode == 0:
                    logger.info("✅ 文本匹配点击成功")
                    time.sleep(1)  # 等待响应
                    return True
                else:
                    logger.warning(f"❌ 文本匹配点击失败: {result.stderr}")
                    return False
            else:
                logger.info(f"❌ 未找到文本为 '{target_text}' 的可点击元素")
                return False

        except Exception as e:
            logger.debug(f"文本匹配点击异常: {e}")
            return False

    def _click_by_resource_id_simple(self, device_serial: str, action: PermissionAction) -> bool:
        """方法2: 通过Resource ID查找并点击（参考quick测试成功实现）"""
        try:
            logger.info(f"🆔 方法2: 通过Resource ID查找并点击: {action.value}")

            # 获取可能的Resource ID列表
            patterns = self.patterns.PERMISSION_BUTTON_PATTERNS.get(action, {})
            possible_ids = patterns.get('resource_ids', [])

            if not possible_ids:
                logger.info(f"❌ 没有为 {action.value} 操作配置resource_id")
                return False

            # 获取UI结构
            ui_dump = self._get_ui_dump(device_serial)
            if not ui_dump:
                logger.warning("❌ 无法获取UI结构")
                return False

            # 解析XML查找元素（遍历所有可能的resource_id）
            root = ET.fromstring(ui_dump)

            def find_element_by_resource_id(node, target_resource_id):
                if node.get('resource-id') == target_resource_id:
                    bounds = node.get('bounds')
                    logger.info(f"📍 找到resource_id元素: {target_resource_id}, bounds: {bounds}")
                    return bounds
                for child in node:
                    result = find_element_by_resource_id(child, target_resource_id)
                    if result:
                        return result
                return None

            # 尝试所有可能的resource_id
            for resource_id in possible_ids:
                logger.info(f"🔍 尝试resource_id: {resource_id}")
                bounds = find_element_by_resource_id(root, resource_id)

                if bounds:
                    # 解析bounds并点击（参考quick测试的成功做法）
                    bounds = bounds.strip('[]')
                    parts = bounds.split('][')
                    left_top = parts[0].split(',')
                    right_bottom = parts[1].split(',')

                    x1, y1 = int(left_top[0]), int(left_top[1])
                    x2, y2 = int(right_bottom[0]), int(right_bottom[1])
                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2

                    logger.info(f"📍 通过resource_id计算的中心点: ({center_x}, {center_y})")

                    # 执行点击
                    cmd = f"adb -s {device_serial} shell input tap {center_x} {center_y}"
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

                    if result.returncode == 0:
                        logger.info(f"✅ resource_id点击成功: {resource_id}")
                        time.sleep(1)  # 等待响应
                        return True
                    else:
                        logger.warning(f"❌ resource_id点击失败: {result.stderr}")

            logger.info("❌ 所有resource_id都未找到匹配元素")
            return False

        except Exception as e:
            logger.debug(f"Resource ID点击异常: {e}")
            return False

    def _click_by_coordinates(self, device_serial: str, x: int, y: int) -> bool:
        """方法3: 坐标直接点击（参考quick测试成功实现）"""
        try:
            logger.info(f"📍 方法3: 坐标直接点击: ({x}, {y})")

            # 执行坐标点击（参考quick测试的成功做法）
            cmd = f"adb -s {device_serial} shell input tap {x} {y}"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info("✅ 坐标点击成功")
                time.sleep(1)  # 等待响应
                return True
            else:
                logger.warning(f"❌ 坐标点击失败: {result.stderr}")
                return False

        except Exception as e:
            logger.debug(f"坐标点击异常: {e}")
            return False

    def _element_still_exists(self, device_serial: str, target_text: str, target_resource_id: Optional[str] = None) -> bool:
        """检查目标元素是否仍然存在于当前UI中"""
        try:
            # 重新获取UI dump
            ui_dump = self._get_ui_dump(device_serial)
            if not ui_dump:
                return True  # 无法确认，假设仍存在

            root = ET.fromstring(ui_dump)

            # 查找相同的元素（通过文本或resource_id）
            for element in root.iter():
                element_text = element.get('text', '').strip()
                element_resource_id = element.get('resource-id', '')

                # 如果找到相同的文本或resource_id，说明元素仍存在
                if element_text == target_text or (target_resource_id and element_resource_id == target_resource_id):
                    logger.info(f"元素仍存在: text='{element_text}', resource_id='{element_resource_id}'")
                    return True

            # 没有找到，说明元素已消失（点击成功）
            logger.info(f"元素已消失: text='{target_text}', resource_id='{target_resource_id}'")
            return False

        except Exception as e:
            logger.debug(f"检查元素存在性异常: {e}")
            return True  # 无法确认，假设仍存在


def integrate_with_app_launch(device_serial: str, app_package: Optional[str] = None, auto_allow_permissions: bool = True) -> bool:
    """
    与应用启动流程集成的权限处理函数

    Args:
        device_serial: 设备序列号
        app_package: 应用包名
        auto_allow_permissions: 是否自动允许所有权限

    Returns:
        bool: 权限处理是否成功
    """
    permission_manager = AppPermissionManager(device_id=device_serial)

    # 在应用启动后等待并处理权限弹窗
    return permission_manager.wait_and_handle_permission_popups(
        device_serial=device_serial,
        app_package=app_package,
        auto_allow=auto_allow_permissions,
        max_popups=5
    )

def integrate_with_app_launch_enhanced(device_serial: str, app_package: Optional[str] = None) -> bool:
    """
    增强版权限处理集成函数

    专门为复杂应用场景设计，可以处理多轮权限弹窗

    Args:
        device_serial: 设备序列号
        app_package: 应用包名

    Returns:
        bool: 权限处理是否成功
    """
    permission_manager = AppPermissionManager(device_id=device_serial)

    # 增强版配置：更长的等待时间，更多的弹窗处理
    return permission_manager.wait_and_handle_permission_popups(
        device_serial=device_serial,
        app_package=app_package,
        auto_allow=True,
        max_popups=8  # 增加最大处理弹窗数量
    )

# 主函数用于测试
if __name__ == "__main__":
    import logging

    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # 测试代码
    device_serial = "5c41023b"  # 替换为实际设备序列号
    app_package = "com.example.app"  # 替换为实际应用包名

    success = integrate_with_app_launch(device_serial, app_package)
    print(f"权限处理结果: {'成功' if success else '失败'}")