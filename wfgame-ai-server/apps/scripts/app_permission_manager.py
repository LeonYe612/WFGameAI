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

修改记录：
- 精简复杂评分算法，保留精准匹配识别
- 集成3种成功的点击方法：文本匹配、Resource ID、坐标点击
- 添加device_id参数支持
- 增强PERMISSION_BUTTON_PATTERNS，包含resource_id信息
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
    """Android系统权限弹窗识别模式"""    # 权限弹窗按钮文本模式（增强版：包含resource_id信息用于精准识别）
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
    ]    # 新增：应用自定义弹窗识别关键词
    APP_CUSTOM_DIALOG_KEYWORDS = [
        "个人信息保护指引", "隐私政策", "用户协议", "Privacy Policy", "获取此设备",
        "权限申请", "权限说明", "服务条款", "使用条款",
        "tvTitle", "tv_ok", "tv_cancel"  # 常见的弹窗控件ID
    ]    # 新增：游戏登录界面关键词（用于排除非权限界面）
    GAME_LOGIN_KEYWORDS = [
        "请输入手机号", "验证码", "获取验证码", "登录", "注册", "账号", "密码",
        "手机号", "验证", "登陆", "Sign in", "Login", "Register", "Phone", "Password"
    ]

    # 新增：权限类型识别关键词
    PRIVACY_POLICY_KEYWORDS = [
        "隐私政策", "个人信息保护", "用户协议", "privacy policy", "隐私条款", "服务条款"
    ]

    PERMISSION_REQUEST_KEYWORDS = [
        "权限申请", "权限说明", "访问权限", "permission"
    ]

class AppPermissionManager:
    """应用权限管理器 - 专门处理应用启动后的权限弹窗"""
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
        logger.info(f"超时设置: {self.permission_wait_timeout}秒, 最大弹窗数: {max_popups}")

        handled_popups = 0
        detection_failures = 0
        max_detection_failures = 3
        start_time = time.time()
        check_count = 0        # 添加连续无弹窗计数，避免无意义的长时间等待
        consecutive_no_popup_count = 0
        max_consecutive_no_popup = 3  # 连续3次没有弹窗就退出

        while handled_popups < max_popups and (time.time() - start_time) < self.permission_wait_timeout:
            check_count += 1
            elapsed_time = time.time() - start_time
            logger.info(f"权限检测轮次 {check_count}, 已耗时: {elapsed_time:.1f}秒")

            # 检测当前是否有权限弹窗
            try:
                permission_dialog = self._detect_permission_dialog(device_serial)
            except Exception as e:
                logger.warning(f"权限检测异常: {e}")
                detection_failures += 1
                if detection_failures >= max_detection_failures:
                    logger.error("权限检测异常次数过多，退出检测")
                    break
                time.sleep(1)
                continue

            if permission_dialog:
                logger.info(f"检测到权限弹窗: {permission_dialog.permission_type}")
                logger.info(f"弹窗标题: {permission_dialog.dialog_title}")
                logger.info(f"可用操作: {[action.value for action in permission_dialog.available_actions]}")

                # 重置连续无弹窗计数
                consecutive_no_popup_count = 0

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
                consecutive_no_popup_count += 1
                logger.debug(f"未检测到权限弹窗 (轮次 {check_count}, 连续无弹窗: {consecutive_no_popup_count})")

                # 如果连续多次没有检测到弹窗，可以提前退出
                if consecutive_no_popup_count >= max_consecutive_no_popup:
                    logger.info(f"连续 {max_consecutive_no_popup} 次未检测到权限弹窗，提前结束检测")
                    break

                # 检查是否是UI dump获取失败
                ui_dump = self._get_ui_dump(device_serial)
                if ui_dump is None:
                    detection_failures += 1
                    logger.warning(f"UI检测失败 {detection_failures}/{max_detection_failures}")

                    if detection_failures >= max_detection_failures:
                        logger.error("多次UI检测失败，可能存在设备连接问题")
                        return False

                # 短暂等待，检查是否有新的权限弹窗出现
                time.sleep(self.permission_detection_interval)# 最终检查：确认当前屏幕是否还有权限弹窗
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
            return True  # 经过完整检测确认没有权限弹窗

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
            import xml.etree.ElementTree as ET
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
                    })            # 检查是否包含自定义弹窗关键词
            combined_text = ' '.join(all_texts)
            has_custom_keywords = any(
                keyword in combined_text
                for keyword in self.patterns.APP_CUSTOM_DIALOG_KEYWORDS
            )            # 新增：检查是否为游戏登录界面（应该排除）
            # 更智能的登录界面检测：需要同时满足多个条件
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
                logger.info(f"弹窗文本内容: {combined_text[:200]}...")                # 识别弹窗类型
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
            permission_type = self._identify_permission_type(dialog_texts)            # 识别可用操作
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

    def _click_by_element_attributes(self, device_serial: str, target_patterns: List[str]) -> bool:
        """方式4: 通过元素属性组合点击（智能备选方案）"""
        try:
            logger.info("尝试通过元素属性组合点击...")

            # 重新获取UI层次，但这次不计算坐标，而是使用元素的其他属性
            ui_dump = self._get_ui_dump(device_serial)
            if not ui_dump:
                return False

            import xml.etree.ElementTree as ET
            root = ET.fromstring(ui_dump)

            for element in root.iter():
                if element.get('clickable') == 'true':
                    text = element.get('text', '').strip()

                    if text in target_patterns:
                        # 尝试通过元素的多种属性进行点击
                        element_class = element.get('class', '')
                        resource_id = element.get('resource-id', '')
                        content_desc = element.get('content-desc', '')

                        logger.info(f"找到目标元素 - 文本:'{text}', 类:'{element_class}', ID:'{resource_id}'")

                        # 尝试通过class + text组合点击
                        if element_class and self._click_by_class_text_combo(device_serial, element_class, text):
                            return True

                        # 尝试通过index点击（如果是相同class的多个元素）
                        if self._click_by_element_index(device_serial, element, root):
                            return True

            return False

        except Exception as e:
            logger.debug(f"元素属性组合点击失败: {e}")
            return False

    def _click_by_class_text_combo(self, device_serial: str, element_class: str, text: str) -> bool:
        """通过class和text组合点击"""
        try:
            # 使用UiSelector的组合条件
            cmd = f'adb -s {device_serial} shell "uiautomator runtest UIAutomatorStub.jar -c com.github.uiautomatorstub.Stub -e className \'{element_class}\' -e text \'{text}\' -e action click"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)

            if result.returncode == 0:
                time.sleep(0.5)
                return True

            return False

        except Exception as e:
            logger.debug(f"class+text组合点击失败: {e}")
            return False

    def _click_by_element_index(self, device_serial: str, target_element, root) -> bool:
        """通过元素索引点击"""
        try:
            # 计算元素在同类元素中的索引
            element_class = target_element.get('class', '')
            target_text = target_element.get('text', '')

            if not element_class:
                return False

            # 找到所有相同class的clickable元素
            same_class_elements = []
            for element in root.iter():
                if (element.get('class') == element_class and
                    element.get('clickable') == 'true'):
                    same_class_elements.append(element)

            # 找到目标元素的索引
            target_index = -1
            for i, element in enumerate(same_class_elements):
                if element.get('text') == target_text:
                    target_index = i
                    break

            if target_index >= 0:
                # 使用索引点击
                cmd = f'adb -s {device_serial} shell "uiautomator runtest UIAutomatorStub.jar -c com.github.uiautomatorstub.Stub -e className \'{element_class}\' -e instance {target_index} -e action click"'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)

                if result.returncode == 0:
                    logger.info(f"通过索引{target_index}成功点击元素")
                    time.sleep(0.5)
                    return True

            return False

        except Exception as e:
            logger.debug(f"元素索引点击失败: {e}")
            return False

    def _click_by_coordinates_fallback(self, device_serial: str, target_patterns: List[str]) -> bool:
        """方式5: 坐标备选点击 - 从UI中找到元素并直接点击坐标"""
        try:
            logger.info("尝试坐标备选点击方式...")

            # 重新获取UI层次
            ui_dump = self._get_ui_dump(device_serial)
            if not ui_dump:
                logger.warning("无法获取UI dump进行坐标点击")
                return False

            import xml.etree.ElementTree as ET
            root = ET.fromstring(ui_dump)

            # 寻找目标按钮元素
            for element in root.iter():
                if element.get('clickable') == 'true':
                    text = element.get('text', '').strip()

                    if text in target_patterns:
                        bounds = element.get('bounds', '')
                        if bounds:
                            logger.info(f"找到目标按钮元素: '{text}', bounds: {bounds}")

                            # 解析bounds并计算中心点
                            try:
                                import re
                                matches = re.findall(r'\[(\d+),(\d+)\]', bounds)
                                if len(matches) == 2:
                                    x1, y1 = int(matches[0][0]), int(matches[0][1])
                                    x2, y2 = int(matches[1][0]), int(matches[1][1])

                                    center_x = (x1 + x2) // 2
                                    center_y = (y1 + y2) // 2

                                    logger.info(f"计算点击坐标: ({center_x}, {center_y})")

                                    # 执行直接坐标点击
                                    tap_cmd = f"adb -s {device_serial} shell input tap {center_x} {center_y}"
                                    result = subprocess.run(tap_cmd, shell=True, capture_output=True, text=True, timeout=5)

                                    if result.returncode == 0:
                                        logger.info(f"✅ 坐标点击成功: ({center_x}, {center_y})")
                                        time.sleep(1.0)  # 等待响应
                                        return True
                                    else:
                                        logger.warning(f"坐标点击命令失败: {result.stderr}")

                            except Exception as parse_error:
                                logger.warning(f"解析bounds失败: {parse_error}")
                                continue

            logger.warning("坐标备选点击未找到可点击的目标按钮")
            return False

        except Exception as e:
            logger.debug(f"坐标备选点击失败: {e}")
            return False

    def _parse_bounds_enhanced(self, bounds_str: str) -> Optional[Tuple[int, int]]:
        """解析bounds字符串，返回中心点坐标（参考enhanced_input_handler的成功做法）"""
        try:
            import re
            matches = re.findall(r'\[(\d+),(\d+)\]', bounds_str)
            if len(matches) == 2:
                x1, y1 = int(matches[0][0]), int(matches[0][1])
                x2, y2 = int(matches[1][0]), int(matches[1][1])
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                return (center_x, center_y)
            return None
        except Exception as e:
            logger.debug(f"解析bounds失败: {e}")
            return None

    def _execute_adb_tap(self, device_serial: str, x: int, y: int) -> bool:
        """执行adb tap命令（使用enhanced_input_handler的成功格式）"""
        try:
            # 使用简单的adb shell input tap命令，参考enhanced_input_handler的成功做法
            cmd = f"adb -s {device_serial} shell input tap {x} {y}"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)

            if result.returncode == 0:
                time.sleep(0.8)  # 等待响应
                return True
            else:
                logger.warning(f"adb tap命令执行失败: {result.stderr}")
                return False
        except Exception as e:
            logger.debug(f"执行adb tap失败: {e}")
            return False
    def _click_by_simplified_method(self, device_serial: str, target_patterns: List[str]) -> bool:
        """方式6: 简化点击方法 - 完全参考click_target成功做法"""
        try:
            logger.info("🔄 尝试简化点击方法（完全参考click_target成功做法）...")

            # 使用EnhancedInputHandler的方法来处理按钮点击
            from enhanced_input_handler import EnhancedInputHandler
            enhanced_handler = EnhancedInputHandler(device_serial)

            # 获取UI结构
            xml_content = enhanced_handler.get_ui_hierarchy()
            if not xml_content:
                logger.warning("无法获取UI结构")
                return False

            # 解析UI元素
            elements = enhanced_handler._parse_ui_xml(xml_content)
            if not elements:
                logger.warning("无法解析UI元素")
                return False

            logger.info(f"📊 解析到 {len(elements)} 个UI元素")
            # 查找最佳匹配的按钮元素
            best_match = None
            best_score = 0

            for element in elements:
                if element.get('clickable') == 'true':
                    text = element.get('text', '').strip()
                    element_class = element.get('class', '')
                    bounds = element.get('bounds', '')
                    if text:
                        # 🔧 关键修复2.0：更严格的按钮识别逻辑和更合理的评分系统
                        score = 0

                        # 1. 精确匹配（最高优先级）- 进一步提高精确匹配的权重
                        exact_match = False
                        for pattern in target_patterns:
                            if text.strip() == pattern.strip():
                                score += 2000  # 极高的精确匹配分数
                                exact_match = True
                                logger.info(f"🎯 精确匹配按钮: '{text}' = '{pattern}'")
                                break

                        # 2. 只有在精确匹配失败时，才考虑部分匹配，并且严格限制文本长度
                        if not exact_match:
                            # 2.1 严格限制长度 - 权限按钮文本通常很短
                            if len(text) <= 8:  # 更严格的长度限制
                                for pattern in target_patterns:
                                    # 2.2 包含匹配 - 只有在文本较短时才考虑
                                    if pattern.lower() in text.lower():
                                        # 短文本得分更高
                                        base_score = 50
                                        length_ratio = (10 - len(text)) / 10  # 越短得分越高
                                        adjusted_score = base_score + (base_score * length_ratio)
                                        score += int(adjusted_score)
                                        logger.info(f"🔍 短文本包含匹配: '{text}' 包含 '{pattern}', 加分: {int(adjusted_score)}")
                                        break
                            elif len(text) > 30:
                                # 长文本很可能是描述，而非按钮，直接大幅降分
                                score -= 500
                                logger.info(f"⚠️ 文本过长，降分: '{text[:30]}...'")

                        # 3. 元素类型评分 - 优先选择真正的UI控件
                        if 'Button' in element_class:
                            button_score = 300  # 提高Button类型的权重
                            score += button_score
                            logger.info(f"🔘 Button类型加分: {button_score}")
                        elif 'TextView' in element_class:
                            if len(text) <= 5:
                                # 短文本TextView更可能是按钮
                                tv_score = 150
                                score += tv_score
                                logger.info(f"📝 短TextView加分: {tv_score}, 文本: '{text}'")
                            elif len(text) <= 10:
                                # 中等长度TextView也可能是按钮，但分数低一些
                                tv_score = 80
                                score += tv_score
                                logger.info(f"📝 中等TextView加分: {tv_score}, 文本: '{text}'")

                        # 4. 位置和尺寸过滤 - 改进的尺寸评分算法
                        if bounds:
                            try:
                                import re
                                matches = re.findall(r'\[(\d+),(\d+)\]', bounds)
                                if len(matches) == 2:
                                    x1, y1 = int(matches[0][0]), int(matches[0][1])
                                    x2, y2 = int(matches[1][0]), int(matches[1][1])
                                    width = x2 - x1
                                    height = y2 - y1
                                    area = width * height

                                    # 记录尺寸信息用于调试
                                    logger.info(f"📏 元素尺寸: {width}x{height}，面积: {area}像素")

                                    # 4.1 过大元素惩罚 - 很可能是详细信息区域，而非按钮
                                    if width > 800 or height > 200 or area > 100000:
                                        penalty = min(1000, int(area / 200))  # 面积越大，惩罚越重
                                        score = max(0, score - penalty)
                                        logger.info(f"📏 大尺寸元素严重降分: -{penalty}, 降分后: {score}")

                                    # 4.2 合理尺寸加分 - 典型按钮尺寸范围
                                    elif 80 <= width <= 400 and 30 <= height <= 120:
                                        size_score = 100
                                        score += size_score
                                        logger.info(f"📏 理想按钮尺寸加分: +{size_score}")                                    # 4.3 过小元素惩罚 - 可能是图标或装饰元素
                                    elif width < 50 or height < 25:
                                        score = max(0, score - 120)
                                        logger.info(f"📏 尺寸过小降分: -120, 降分后: {score}")

                                    # 5. 位置评分 - 屏幕底部的元素更可能是操作按钮
                                    screen_height = 2400  # 假设的屏幕高度，实际应动态获取
                                    y_center = (y1 + y2) // 2
                                    if y_center > screen_height / 2:
                                        bottom_score = int((y_center - (screen_height/2)) / 10)
                                        score += bottom_score
                                        logger.info(f"📱 屏幕位置加分: +{bottom_score} (底部位置更可能是按钮)")
                            except Exception as e:
                                logger.debug(f"解析bounds失败: {e}")

                        if score > 0:
                            logger.info(f"🏆 候选按钮: '{text}' (类型: {element_class}, 总分: {score})")

                        if score > best_score:
                            best_score = score
                            best_match = element            # 找到最佳匹配的按钮
            if best_match and best_score > 0:
                text = best_match.get('text', '')
                element_class = best_match.get('class', '')
                bounds = best_match.get('bounds', '')
                logger.info(f"✅ 最终选择按钮: '{text}' (类型: {element_class}, 最高分: {best_score})")
                logger.info(f"📍 按钮位置: {bounds}")

                # 关键：使用 EnhancedInputHandler 的精确点击方法
                success = enhanced_handler.click_custom_target(best_match)
                if success:
                    logger.info("✅ 简化点击方法成功")
                    return True
                else:
                    logger.warning("❌ 简化点击方法失败")
                    return False
            else:
                logger.warning("❌ 未找到匹配的按钮")
                # 输出所有可点击元素用于调试
                logger.info("🔍 所有可点击元素：")
                for element in elements:
                    if element.get('clickable') == 'true':
                        elem_text = element.get('text', '').strip()
                        elem_class = element.get('class', '')
                        elem_bounds = element.get('bounds', '')
                        if elem_text:
                            logger.info(f"  - 文本: '{elem_text}' | 类型: {elem_class} | 位置: {elem_bounds}")
                return False

        except Exception as e:
            logger.debug(f"简化点击方法失败: {e}")
            return False

def integrate_with_app_launch(device_serial: str, app_package: Optional[str] = None, auto_allow_permissions: bool = True) -> bool:
    """
    与应用启动流程集成的权限处理函数

    Args:
        device_serial: 设备序列号
        app_package: 应用包名
        auto_allow_permissions: 是否自动允许所有权限    Returns:
        bool: 权限处理是否成功
    """
    logger.info(f"开始权限处理 - 设备: {device_serial}, 应用: {app_package}")

    try:
        permission_manager = AppPermissionManager()

        # 减少超时时间，避免长时间卡住
        permission_manager.permission_wait_timeout = 8  # 从30秒减少到8秒
        permission_manager.permission_detection_interval = 1.0  # 增加检测间隔，减少检测频率

        logger.info("正在检测权限弹窗...")

        # 在应用启动后等待并处理权限弹窗
        result = permission_manager.wait_and_handle_permission_popups(
            device_serial=device_serial,
            app_package=app_package,
            auto_allow=auto_allow_permissions,
            max_popups=2  # 进一步减少最大检测次数
        )

        logger.info(f"权限处理完成，结果: {result}")
        return result

    except Exception as e:
        logger.warning(f"权限处理异常: {e}")
        logger.info("假设无权限弹窗，继续执行")
        return True  # 出现异常时假设成功，避免阻塞整个流程

def integrate_with_app_launch_enhanced(device_serial: str, app_package: Optional[str] = None) -> bool:
    """
    增强版权限处理集成函数

    Args:
        device_serial: 设备序列号
        app_package: 应用包名

    Returns:
        bool: 权限处理是否成功
    """
    logger.info(f"增强版权限处理开始 - 设备: {device_serial}, 应用: {app_package}")

    permission_manager = AppPermissionManager()

    # 处理权限弹窗
    success = permission_manager.wait_and_handle_permission_popups(
        device_serial=device_serial,
        app_package=app_package,
        auto_allow=True,
        max_popups=5
    )

    if success:
        logger.info("增强版权限处理完成")
    else:
        logger.warning("增强版权限处理未完全成功")

    return success

if __name__ == "__main__":
    # 测试使用
    import sys

    # 配置日志级别
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    if len(sys.argv) < 2:
        print("Usage: python app_permission_manager.py <device_serial> [app_package]")
        sys.exit(1)

    device_serial = sys.argv[1]
    app_package = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"开始权限处理测试 - 设备: {device_serial}, 应用: {app_package}")
    success = integrate_with_app_launch(device_serial, app_package)
    print(f"权限处理结果: {'成功' if success else '失败'}")
