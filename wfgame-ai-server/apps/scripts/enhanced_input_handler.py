"""
WFGameAI增强输入处理器 - 识别和处理UI elements 层级元素
功能：集成智能登录操作器的优化算法和焦点检测，严格按照ElementPatterns执行匹配
作者：WFGameAI开发团队
"""

import sys
import os
# 强化：确保wfgame-ai-server根目录在sys.path，保证apps.scripts可导入
current_file = os.path.abspath(__file__)
project_root = os.path.abspath(os.path.join(current_file, "..", "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import os
import time
import xml.etree.ElementTree as ET
from typing import Optional, Tuple, Dict, Any, List
import subprocess
import tempfile
import re
import json
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import Process


class ElementPatterns:
    """UI元素模式定义"""

    # 账号输入框模式
    USERNAME_PATTERNS = {
        'text_hints': ['账号', '用户名', 'username', 'account', '请输入账号', '请输入您的账号', '请输入手机号'],
        'resource_id_keywords': ['username', 'account', 'login', 'phone', 'mobile'],
        'class_types': ['android.widget.EditText'],
        'content_desc_keywords': ['账号', '用户名', 'username']
    }

    # 密码输入框模式
    PASSWORD_PATTERNS = {
        'text_hints': ['密码', 'password', '请输入您的密码', '请输入密码', '验证码'],
        'resource_id_keywords': ['password', 'pass', 'pwd'],
        'class_types': ['android.widget.EditText'],
        'content_desc_keywords': ['密码', 'password'],
        'password_field': True
    }    # 勾选框模式 - 扩展匹配模式以提高识别率
    CHECKBOX_PATTERNS = {
        'text_hints': ['同意', '我已阅读', '已阅读', '接受', '确认', '勾选', '选择', 'agree', 'accept', 'check'],
        'resource_id_keywords': ['agree', 'accept', 'checkbox', 'cb_ag', 'remember', 'check', 'protocol', 'agreement', 'terms', 'privacy', 'policy'],
        'class_types': ["android.widget.CheckBox", "android.widget.ImageView", "android.view.View", "android.widget.TextView"],
        'content_desc_keywords': ['同意', '协议', '记住', '勾选', '选择', '确认', '接受', 'checkbox', 'agree', 'accept'],
        'checkable_priority': True,  # 优先识别可勾选的元素
        'clickable_priority': True   # 优先识别可点击的元素
    }

    # 登录按钮模式
    LOGIN_BUTTON_PATTERNS = {
        'text_hints': ['进入游戏', '立即登录', '登录', '登入', 'login', '开始游戏'],
        'resource_id_keywords': ['login', 'submit', 'enter', 'game', 'start'],
        'class_types': ['android.widget.Button', 'android.widget.TextView'],
        'content_desc_keywords': ['登录', '进入', '开始']
    }

    # 跳过按钮模式
    SKIP_BUTTON_PATTERNS = {
        'text_hints': ['跳过', '跳过引导', 'skip', '关闭', '稍后', '下次再说'],
        'resource_id_keywords': ['skip', 'close', 'dismiss', 'later', 'next_time'],
        'class_types': ['android.widget.Button', 'android.widget.TextView', 'android.widget.ImageView'],
        'content_desc_keywords': ['跳过', '关闭', 'skip', 'close']
    }

    # 登录方式切换按钮模式
    LOGIN_SWITCH_BUTTON_PATTERNS = {
        'text_hints': ['其他登录方式', '其他方式', '切换登录', '账号登录', '密码登录'],
        'resource_id_keywords': ['other_login', 'switch_login', 'login_method', 'more_login', 'password_login'],
        'class_types': ['android.widget.TextView', 'android.widget.Button', 'android.view.View'],
        'content_desc_keywords': ['其他登录方式', '登录方式', '切换登录', '更多选项']
    }    # 系统弹窗统一处理
    SYSTEM_DIALOG_PATTERNS = {
        'text_hints': [
            "接受", '全部允许', '允许', '同意', '确定', '继续', '继续安装',
            '存储', '确认', 'OK', 'Allow', 'Continue', 'Agree',
            '立即更新', '下次再说', '跳过', '知道了', '我知道了',
            '始终允许', 'Always Allow', 'Accept', 'Confirm'
        ],
        'class_types': [
                'android.widget.Button',
                'android.widget.TextView',
                "com.android.permissioncontroller:id/permission_allow_button",
                "android:id/button1",  # 通常是确定/允许按钮
                "com.android.packageinstaller:id/permission_allow_button",
                "android:id/button_once",
                "android:id/button_always",
                "btn_agree", "btn_confirm", "btn_ok", "btn_allow",
                "tv_agree", "tv_confirm", "tv_ok",
                "com.beeplay.card2prepare:id/tv_ok"
                ],
        'priority_keywords': ['允许', '同意', '确定', '继续', 'Allow', 'OK', 'Continue']
    }


    @classmethod
    def create_custom_pattern(cls, target_selector: Dict[str, Any]) -> Dict[str, Any]:
        """创建自定义元素匹配模式"""
        pattern = {}

        # 从target_selector提取匹配条件
        if 'text_hints' in target_selector:
            pattern['text_hints'] = target_selector['text_hints']
        if 'resource_id_keywords' in target_selector:
            pattern['resource_id_keywords'] = target_selector['resource_id_keywords']
        if 'class_types' in target_selector:
            pattern['class_types'] = target_selector['class_types']
        if 'content_desc_keywords' in target_selector:
            pattern['content_desc_keywords'] = target_selector['content_desc_keywords']
        if 'clickable_priority' in target_selector:
            pattern['clickable_priority'] = target_selector['clickable_priority']
        if 'checkable_priority' in target_selector:
            pattern['checkable_priority'] = target_selector['checkable_priority']

        return pattern

    # 通用输入框模式
    GENERIC_INPUT_PATTERNS = {
        'class_types': ['android.widget.EditText'],
        'fallback_keywords': ['input', 'edit', 'text', 'field']
    }


class DeviceScriptReplayer:
    """增强输入处理器：结合智能登录操作器的优化算法，严格按照ElementPatterns执行匹配"""
    def __init__(self, device_serial: Optional[str] = None, is_multi_device_mode: bool = False):
        """
        初始化增强输入处理器

        Args:
            device_serial: 设备序列号，None表示默认设备
            is_multi_device_mode: 是否为多设备模式
        """
        self.device_serial = device_serial
        self._is_multi_device_mode = is_multi_device_mode
        self.adb_prefix = ["adb"]
        if device_serial:
            self.adb_prefix.extend(["-s", device_serial])
        self.patterns = ElementPatterns()

        # 分配账号
        self.device_account = None
        if device_serial:
            self._allocate_device_account()

    def _run_adb_command(self, command: list) -> Tuple[bool, str]:
        """
        执行ADB命令

        Args:
            command: ADB命令列表

        Returns:
            (success, output)
        """
        try:
            full_command = self.adb_prefix + command
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=15
            )

            success = result.returncode == 0
            output = result.stdout if success else result.stderr

            if not success:
                print(f"ADB命令执行失败: {' '.join(full_command)}")
                print(f"错误输出: {output}")

            return success, output

        except subprocess.TimeoutExpired:
            print(f"ADB命令超时: {' '.join(full_command)}")
            return False, "命令执行超时"
        except Exception as e:
            print(f"执行ADB命令时出错: {e}")
            return False, str(e)

    def get_ui_hierarchy(self) -> Optional[str]:
        """
        获取UI层次结构XML

        Returns:
            XML字符串或None
        """
        print("📱 获取UI层次结构...")

        # 先清理设备上的旧文件
        self._run_adb_command(["shell", "rm", "-f", "/sdcard/ui_dump.xml"])

        # 执行UI dump
        success, output = self._run_adb_command(["shell", "uiautomator", "dump", "/sdcard/ui_dump.xml"])
        if not success:
            print(f"❌ UI dump失败: {output}")
            return None

        # 从设备拉取文件
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.xml', delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            success, output = self._run_adb_command(["pull", "/sdcard/ui_dump.xml", temp_path])
            if not success:
                print(f"❌ 拉取UI dump文件失败: {output}")
                return None

            # 读取XML内容
            with open(temp_path, 'r', encoding='utf-8') as f:
                xml_content = f.read()

            print("✅ UI层次结构获取成功")
            return xml_content

        except Exception as e:
            print(f"❌ 读取UI dump文件失败: {e}")
            return None
        finally:
            # 清理临时文件
            try:
                os.unlink(temp_path)
            except:
                pass
            # 清理设备上的文件
            self._run_adb_command(["shell", "rm", "-f", "/sdcard/ui_dump.xml"])

    def _parse_ui_xml(self, xml_content: str) -> List[Dict[str, Any]]:
        """解析UI XML，返回元素列表"""
        elements = []
        try:
            root = ET.fromstring(xml_content)
            for element in root.iter():
                element_info = {
                    'text': element.get('text', ''),
                    'hint': element.get('hint', ''),
                    'resource_id': element.get('resource-id', ''),
                    'class': element.get('class', ''),
                    'content_desc': element.get('content-desc', ''),
                    'bounds': element.get('bounds', ''),
                    'clickable': element.get('clickable', 'false').lower() == 'true',
                    'focusable': element.get('focusable', 'false').lower() == 'true',
                    'focused': element.get('focused', 'false').lower() == 'true',
                    'enabled': element.get('enabled', 'false').lower() == 'true',
                    'password': element.get('password', 'false').lower() == 'true',
                    'checkable': element.get('checkable', 'false').lower() == 'true',
                    'checked': element.get('checked', 'false').lower() == 'true',
                }
                elements.append(element_info)
        except ET.ParseError as e:
            print(f"❌ XML解析失败: {e}")
        return elements

    def find_username_field(self, elements: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """查找用户名输入框（严格按照USERNAME_PATTERNS匹配）"""
        print("🔍 查找用户名输入框（严格按照USERNAME_PATTERNS匹配）...")

        patterns = self.patterns.USERNAME_PATTERNS

        # 优先级1：严格匹配class_types
        for element in elements:
            if element.get('class') in patterns['class_types']:
                text = element.get('text', '').lower()
                hint = element.get('hint', '').lower()
                resource_id = element.get('resource-id', '').lower()
                content_desc = element.get('content-desc', '').lower()

                # 检查text_hints模式
                for kw in patterns['text_hints']:
                    kw_lower = kw.lower()
                    if kw_lower in text or kw_lower in hint:
                        print(f"✅ 找到用户名输入框（text_hints匹配）: {element.get('resource-id', '无ID')} - 匹配关键字: {kw}")
                        return element

                # 检查resource_id_keywords模式
                for kw in patterns['resource_id_keywords']:
                    kw_lower = kw.lower()
                    if kw_lower in resource_id:
                        print(f"✅ 找到用户名输入框（resource_id匹配）: {element.get('resource-id', '无ID')} - 匹配关键字: {kw}")
                        return element

                # 检查content_desc_keywords模式
                for kw in patterns['content_desc_keywords']:
                    kw_lower = kw.lower()
                    if kw_lower in content_desc:
                        print(f"✅ 找到用户名输入框（content_desc匹配）: {element.get('resource-id', '无ID')} - 匹配关键字: {kw}")
                        return element

        print("❌ 未找到用户名输入框")
        return None

    def find_password_field(self, elements: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """查找密码输入框（严格按照PASSWORD_PATTERNS匹配）"""
        print("🔍 查找密码输入框（严格按照PASSWORD_PATTERNS匹配）...")

        patterns = self.patterns.PASSWORD_PATTERNS

        # 优先级1：严格匹配class_types
        for element in elements:
            if element.get('class') in patterns['class_types']:
                text = element.get('text', '').lower()
                hint = element.get('hint', '').lower()
                resource_id = element.get('resource-id', '').lower()
                content_desc = element.get('content-desc', '').lower()
                password_field = element.get('password', False)

                # 优先检查password字段标识
                if password_field:
                    print(f"✅ 找到密码输入框（password字段标识）: {element.get('resource-id', '无ID')}")
                    return element

                # 检查text_hints模式
                for kw in patterns['text_hints']:
                    kw_lower = kw.lower()
                    if kw_lower in text or kw_lower in hint:
                        print(f"✅ 找到密码输入框（text_hints匹配）: {element.get('resource-id', '无ID')} - 匹配关键字: {kw}")
                        return element

                # 检查resource_id_keywords模式
                for kw in patterns['resource_id_keywords']:
                    kw_lower = kw.lower()
                    if kw_lower in resource_id:
                        print(f"✅ 找到密码输入框（resource_id匹配）: {element.get('resource-id', '无ID')} - 匹配关键字: {kw}")
                        return element

                # 检查content_desc_keywords模式
                for kw in patterns['content_desc_keywords']:
                    kw_lower = kw.lower()
                    if kw_lower in content_desc:
                        print(f"✅ 找到密码输入框（content_desc匹配）: {element.get('resource-id', '无ID')} - 匹配关键字: {kw}")
                        return element

        print("❌ 未找到密码输入框")
        return None

    def find_agreement_checkbox(self, elements: List[Dict[str, Any]], target_selector: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """查找协议勾选框（严格按照CHECKBOX_PATTERNS匹配）"""
        print("🔍 查找协议勾选框（严格按照CHECKBOX_PATTERNS匹配）...")

        # 策略1: 使用target_selector指定的类型（优先级最高）
        if target_selector:
            class_types = target_selector.get('class_types', [])
            if class_types:
                print(f"🎯 优先查找指定类型: {class_types}")
                for element in elements:
                    element_class = element.get('class', '')
                    if element_class in class_types:
                        # 检查是否可勾选
                        if element.get('checkable', False) or element_class == 'android.widget.CheckBox':
                            print(f"✅ 找到指定类型checkbox: {element_class} - {element.get('resource-id', '无ID')}")
                            return element

        # 策略2: 使用CHECKBOX_PATTERNS严格匹配
        patterns = self.patterns.CHECKBOX_PATTERNS
        print(f"🔍 使用CHECKBOX_PATTERNS匹配: {patterns}")

        for element in elements:
            element_class = element.get('class', '')
            is_checkable = element.get('checkable', False)

            # 首先检查class_types
            if element_class in patterns['class_types'] or is_checkable:
                resource_id = element.get('resource-id', '').lower()
                content_desc = element.get('content-desc', '').lower()
                text = element.get('text', '').lower()

                # 检查resource_id_keywords模式
                for kw in patterns['resource_id_keywords']:
                    kw_lower = kw.lower()
                    if kw_lower in resource_id:
                        print(f"✅ 找到checkbox（resource_id匹配）: {element.get('resource-id', '无ID')} - 匹配关键字: {kw}")
                        return element

                # 检查content_desc_keywords模式
                for kw in patterns['content_desc_keywords']:
                    kw_lower = kw.lower()
                    if kw_lower in content_desc:
                        print(f"✅ 找到checkbox（content_desc匹配）: {content_desc} - 匹配关键字: {kw}")
                        return element

                # 检查文本内容（协议相关扩展关键字）
                agreement_keywords = ['协议', '同意', '条款', '隐私', 'agree', 'terms', 'privacy', '用户协议', '服务条款']
                for kw in agreement_keywords:
                    kw_lower = kw.lower()
                    if kw_lower in text or kw_lower in content_desc:
                        print(f"✅ 找到checkbox（协议文本匹配）: {text or content_desc} - 匹配关键字: {kw}")
                        return element

        # 策略3: 通用checkbox检测（退化策略）
        print("🔄 未找到特定协议checkbox，查找通用checkbox...")
        checkboxes = []
        for element in elements:
            element_class = element.get('class', '')
            is_checkable = element.get('checkable', False)
            is_enabled = element.get('enabled', True)

            if (element_class == 'android.widget.CheckBox' or is_checkable) and is_enabled:
                checkboxes.append(element)

        if checkboxes:
            print(f"🔍 找到 {len(checkboxes)} 个通用checkbox")
            # 优先选择未勾选的checkbox
            unchecked_boxes = [cb for cb in checkboxes if not cb.get('checked', False)]
            if unchecked_boxes:
                checkbox = unchecked_boxes[0]
                print(f"✅ 找到通用未勾选checkbox: {checkbox.get('resource-id', '无ID')}")
                return checkbox
            else:
                # 如果都已勾选，返回第一个
                checkbox = checkboxes[0]
                print(f"✅ 找到通用checkbox（已勾选）: {checkbox.get('resource-id', '无ID')}")
                return checkbox

        print("⚠️ 未找到任何checkbox元素")
        return None

    def find_login_button(self, elements: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """查找登录按钮（严格按照LOGIN_BUTTON_PATTERNS匹配）"""
        print("🔍 查找登录按钮（严格按照LOGIN_BUTTON_PATTERNS匹配）...")

        patterns = self.patterns.LOGIN_BUTTON_PATTERNS

        for element in elements:
            # 首先检查是否可点击
            if element.get('clickable', False):
                element_class = element.get('class', '')
                text = element.get('text', '').lower()
                resource_id = element.get('resource-id', '').lower()
                content_desc = element.get('content-desc', '').lower()

                # 检查class_types
                if element_class in patterns['class_types']:
                    # 检查text_hints模式
                    for kw in patterns['text_hints']:
                        kw_lower = kw.lower()
                        if kw_lower in text:
                            print(f"✅ 找到登录按钮（text匹配）: '{element.get('text', '无文本')}' - 匹配关键字: {kw}")
                            return element

                    # 检查resource_id_keywords模式
                    for kw in patterns['resource_id_keywords']:
                        kw_lower = kw.lower()
                        if kw_lower in resource_id:
                            print(f"✅ 找到登录按钮（resource_id匹配）: {element.get('resource-id', '无ID')} - 匹配关键字: {kw}")
                            return element

                    # 检查content_desc_keywords模式
                    for kw in patterns['content_desc_keywords']:
                        kw_lower = kw.lower()
                        if kw_lower in content_desc:
                            print(f"✅ 找到登录按钮（content_desc匹配）: {content_desc} - 匹配关键字: {kw}")
                            return element

        print("❌ 未找到登录按钮")
        return None

    def find_best_input_field(self, target_selector: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        使用关键字全匹配查找最佳的输入框 - 增强版
        优先使用USERNAME_PATTERNS，然后使用target_selector中的信息

        Args:
            target_selector: 目标选择器信息

        Returns:
            最佳匹配的输入框元素或None
        """
        print(f"🔍 查找输入框（关键字全匹配）...")

        # 获取UI结构
        xml_content = self.get_ui_hierarchy()
        if not xml_content:
            return None

        elements = self._parse_ui_xml(xml_content)
        print(f"📊 解析到 {len(elements)} 个UI元素")

        # 第一步：使用USERNAME_PATTERNS智能查找
        print("🔍 第一步：使用USERNAME_PATTERNS智能查找...")
        username_field = self.find_username_field(elements)
        if username_field:
            print(f"✅ 通过USERNAME_PATTERNS找到用户名输入框")
            return username_field

        # 第二步：使用target_selector中的具体信息
        print("🔍 第二步：使用target_selector中的placeholder信息...")
        placeholder = target_selector.get('placeholder', '')
        text_hint = target_selector.get('text', '')

        candidates = []
        keywords = []
        if placeholder:
            keywords.append(placeholder.lower())
        if text_hint:
            keywords.append(text_hint.lower())

        for element in elements:
            if element.get('class') == 'android.widget.EditText':
                text = element.get('text', '').lower()
                hint = element.get('hint', '').lower()
                resource_id = element.get('resource-id', '').lower()
                matched = False
                for kw in keywords:
                    if kw and (kw in text or kw in hint or kw in resource_id):
                        matched = True
                        break
                if matched or not keywords:
                    candidates.append(element)

        if candidates:
            print(f"✅ 通过placeholder找到输入框: {candidates[0].get('resource-id', '无ID')}")
            return candidates[0]

        # 第三步：作为最后手段，返回第一个EditText
        print("🔍 第三步：作为最后手段，查找任意EditText...")
        for element in elements:
            if element.get('class') == 'android.widget.EditText':
                print(f"✅ 找到通用输入框: {element.get('resource-id', '无ID')}")
                return element

        print("❌ 未找到任何合适的输入框")
        return None

    def input_text_with_focus_detection(self, text: str, target_selector: Dict[str, Any]) -> bool:
        """
        综合焦点检测和文本输入 - 增强版
        支持clear_previous_text标志

        Args:
            text: 要输入的文本
            target_selector: 目标选择器

        Returns:
            输入是否成功
        """
        print(f"🎯 开始增强版焦点检测和文本输入")
        print(f"📝 原始文本: '{text[:30]}{'...' if len(text) > 30 else ''}'")
        print(f"🎯 选择器信息: {target_selector}")

        try:
            # 重要：首先进行账号参数替换
            processed_text = self._replace_account_parameters(text)
            print(f"📝 处理后文本: '{processed_text[:30]}{'...' if len(processed_text) > 30 else ''}'")            # 第一步：根据target_selector的type智能选择输入框查找方法
            input_type = target_selector.get('type', '').lower()
            best_input_field = None

            if input_type == 'username_field' or input_type == 'username':
                # 用户名输入框：使用专门的用户名输入框查找
                print("🔍 查找用户名输入框...")
                xml_content = self.get_ui_hierarchy()
                if xml_content:
                    elements = self._parse_ui_xml(xml_content)
                    if elements:
                        best_input_field = self.find_username_field(elements)
            elif input_type == 'password_field' or input_type == 'password':
                # 密码输入框：使用专门的密码输入框查找
                print("🔍 查找密码输入框...")
                xml_content = self.get_ui_hierarchy()
                if xml_content:
                    elements = self._parse_ui_xml(xml_content)
                    if elements:
                        best_input_field = self.find_password_field(elements)
            else:
                # 通用输入框：使用原有的通用查找方法
                print("🔍 查找通用输入框...")
                best_input_field = self.find_best_input_field(target_selector)

            if not best_input_field:
                print("❌ 未找到合适的输入框")
                return False

            # 第二步：确保输入框获得焦点
            if not best_input_field.get('focused', False):
                print("🎯 输入框未获得焦点，尝试点击获取焦点...")
                if not self.tap_element(best_input_field):
                    print("❌ 点击输入框获取焦点失败")
                    return False

            # 第三步：智能清空处理 - 根据clear_previous_text标志决定
            clear_previous = target_selector.get('clear_previous_text', False)
            input_field_text = best_input_field.get('text', '').strip()

            if clear_previous and len(input_field_text) > 0:
                print(f"🗑️ 清空现有文本: '{input_field_text}'")
                if not self.clear_input_field():
                    print("⚠️ 清空输入框失败，继续输入")
            elif not clear_previous and len(input_field_text) > 0:
                print(f"📝 保留现有文本: '{input_field_text}'，追加输入")
            else:
                print("📝 输入框为空，直接输入")

            # 第四步：执行智能文本输入（使用处理后的文本）
            if self.input_text_smart(processed_text):
                print("✅ 增强版文本输入成功")
                return True
            else:
                print("❌ 增强版文本输入失败")
                return False

        except Exception as e:
            print(f"❌ 增强版输入处理过程中发生错误: {e}")
            return False

    def perform_checkbox_action(self, target_selector: Dict[str, Any]) -> bool:
        """执行checkbox勾选动作的完整流程（严格按照CHECKBOX_PATTERNS）"""
        try:
            print(f"☑️ 开始执行checkbox勾选动作，选择器: {target_selector}")

            # 获取UI结构
            xml_content = self.get_ui_hierarchy()
            if not xml_content:
                print("❌ 无法获取UI结构")
                return False

            # 解析UI元素
            elements = self._parse_ui_xml(xml_content)
            if not elements:
                print("❌ 无法解析UI元素")
                return False

            print(f"📊 解析到 {len(elements)} 个UI元素")

            # 查找目标checkbox（严格按照CHECKBOX_PATTERNS）
            checkbox_element = self.find_agreement_checkbox(elements, target_selector)
            if not checkbox_element:
                print("❌ 未找到合适的checkbox元素")
                return False

            # 执行勾选操作
            success = self.check_checkbox(checkbox_element)
            if success:
                print("✅ checkbox勾选操作成功")
                return True
            else:
                print("❌ checkbox勾选操作失败")
                return False

        except Exception as e:
            print(f"❌ checkbox勾选动作执行过程中发生错误: {e}")
            return False

    def find_element_by_type(self, elements: List[Dict[str, Any]], target_selector: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        根据target_selector的type参数智能查找元素

        Args:
            elements: UI元素列表
            target_selector: 目标选择器，包含type参数

        Returns:
            找到的元素或None
        """
        element_type = target_selector.get('type', '').lower()

        print(f"🔍 智能查找元素类型: {element_type}")
          # 根据type参数选择对应的查找方法
        if element_type == 'username' or element_type == 'username_field':
            return self.find_username_field(elements)
        elif element_type == 'password' or element_type == 'password_field':
            return self.find_password_field(elements)
        elif element_type == 'checkbox' or element_type == 'agreement_checkbox':
            return self.find_agreement_checkbox(elements, target_selector)
        elif element_type == 'login_button' or element_type == 'button':
            return self.find_login_button(elements)
        elif element_type == 'skip_button':
            return self.find_skip_button(elements)
        elif element_type == 'login_switch_button':
            return self.find_login_switch_button(elements)
        else:
            # 如果没有指定type，使用传统的自定义匹配
            print(f"⚠️ 未知元素类型: {element_type}，使用自定义匹配")
            return self.find_best_input_field(target_selector)

    def find_element_smart(self, target_selector: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        智能元素查找 - 根据target_selector参数自动选择最佳策略

        Args:
            target_selector: 目标选择器配置

        Returns:
            找到的元素或None
        """
        print("🤖 开始智能元素查找...")
          # 获取UI层次结构
        xml_content = self.get_ui_hierarchy()
        if not xml_content:
            print("❌ 无法获取UI层次结构")
            return None

        elements = self._parse_ui_xml(xml_content)
        if not elements:
            print("❌ 未找到任何UI元素")
            return None

        print(f"📊 解析到 {len(elements)} 个UI元素")

        # 使用智能类型匹配
        return self.find_element_by_type(elements, target_selector)

    # 基础操作方法
    def _parse_bounds(self, bounds_str: str) -> Optional[Tuple[int, int]]:
        """解析bounds字符串，返回中心点坐标"""
        try:
            match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds_str)
            if match:
                x1, y1, x2, y2 = map(int, match.groups())
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                return center_x, center_y
        except Exception as e:
            print(f"❌ 解析bounds失败: {e}")
        return None

    def tap_element(self, element: Dict[str, Any]) -> bool:
        """点击元素以获取焦点"""
        bounds = element.get('bounds', '')
        if not bounds:
            print("❌ 元素没有bounds信息，无法点击")
            return False

        coords = self._parse_bounds(bounds)
        if not coords:
            print(f"❌ 无法解析bounds: {bounds}")
            return False

        center_x, center_y = coords
        print(f"👆 点击元素获取焦点: ({center_x}, {center_y})")

        success, output = self._run_adb_command(["shell", "input", "tap", str(center_x), str(center_y)])
        if success:
            print("✅ 元素点击成功")
            time.sleep(0.8)  # 等待焦点切换
            return True
        else:
            print(f"❌ 元素点击失败: {output}")
            return False

    def clear_input_field(self) -> bool:
        """清空当前输入框"""
        print("🗑️ 清空输入框...")

        try:
            # 全选
            success, output = self._run_adb_command(["shell", "input", "keyevent", "KEYCODE_CTRL_A"])
            if success:
                time.sleep(0.3)
                # 删除
                success, output = self._run_adb_command(["shell", "input", "keyevent", "KEYCODE_DEL"])

            if success:
                print("✅ 输入框清空成功")
                time.sleep(0.3)
                return True
            else:
                print(f"❌ 输入框清空失败: {output}")
                return False

        except Exception as e:
            print(f"❌ 清空输入框失败: {e}")
            return False

    def input_text_smart(self, text: str) -> bool:
        """
        智能文本输入

        Args:
            text: 要输入的文本

        Returns:
            输入是否成功
        """
        print(f"⌨️ 智能文本输入: '{text[:30]}{'...' if len(text) > 30 else ''}'")

        try:            # 首先检查是否还包含未替换的账号参数，如果有则说明参数替换失败
            if "${account:" in text:
                print(f"⚠️ 警告: 输入文本包含未替换的账号参数: {text}")
                print(f"⚠️ 可能的原因: 设备未分配账号或参数替换失败")
                # 尝试从账号参数中提取默认值或者报错
                return False

            # 增强的特殊字符转义 - 针对Android shell
            escaped_text = text

            # 转义shell特殊字符，但保留空格正常处理
            special_chars = {
                '$': '\\$',
                '{': '\\{',
                '}': '\\}',
                '(': '\\(',
                ')': '\\)',
                '[': '\\[',
                ']': '\\]',
                '&': '\\&',
                '|': '\\|',
                '<': '\\<',
                '>': '\\>',
                ';': '\\;',
                '`': '\\`',
                '"': '\\"',
                "'": "\\'",
                '\\': '\\\\'
                # 注意：不转义空格，让ADB正常处理
            }

            for char, escaped in special_chars.items():
                escaped_text = escaped_text.replace(char, escaped)            # 使用最安全的文本输入方法：直接传递文本而不进行shell转义
            # 这样可以完全避免shell解析的问题
            try:
                # 方法1：尝试直接输入整个文本
                success, output = self._run_adb_command(["shell", "input", "text", f'"{escaped_text}"'])
                if success:
                    print("✅ 智能文本输入完成（整体输入）")
                    time.sleep(0.5)
                    return True
                else:
                    print(f"⚠️ 整体输入失败，尝试分段输入: {output}")
            except:
                print("⚠️ 整体输入异常，尝试分段输入")

            # 方法2：分段输入作为备选
            max_length = 10  # 进一步减少段长度
            success = True

            for i in range(0, len(escaped_text), max_length):
                segment = escaped_text[i:i + max_length]

                seg_success, output = self._run_adb_command(["shell", "input", "text", f'"{segment}"'])
                if not seg_success:
                    print(f"❌ 文本段输入失败: {segment}, 错误: {output}")
                    success = False
                    break

                # 段间延迟
                if i + max_length < len(escaped_text):
                    time.sleep(0.3)

            if success:
                print("✅ 智能文本输入完成")
                time.sleep(0.5)
                return True
            else:
                print("❌ 智能文本输入失败")
                return False

        except Exception as e:
            print(f"❌ 智能文本输入失败: {e}")
            return False

    def check_checkbox(self, checkbox_element: Dict[str, Any]) -> bool:
        """勾选checkbox - 使用多种策略尝试点击"""
        print("☑️ 执行checkbox勾选...")

        try:
            # 详细记录checkbox信息
            print(f"🔍 Checkbox详细信息:")
            print(f"   - resource-id: {checkbox_element.get('resource-id', '无')}")
            print(f"   - class: {checkbox_element.get('class', '无')}")
            print(f"   - text: '{checkbox_element.get('text', '')}'")
            print(f"   - bounds: {checkbox_element.get('bounds', '')}")
            print(f"   - checked: {checkbox_element.get('checked', False)}")
            print(f"   - checkable: {checkbox_element.get('checkable', False)}")
            print(f"   - clickable: {checkbox_element.get('clickable', False)}")
            print(f"   - enabled: {checkbox_element.get('enabled', False)}")

            # 检查当前勾选状态
            checked = checkbox_element.get('checked', False)
            if checked:
                print("✅ checkbox已经勾选")
                return True

            bounds = checkbox_element.get('bounds', '')
            if not bounds:
                print("❌ checkbox没有bounds信息")
                return False

            # 核心修复：使用更精确的点击策略
            match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
            if not match:
                print(f"❌ 无法解析bounds格式: {bounds}")
                return False

            x1, y1, x2, y2 = map(int, match.groups())
            width = x2 - x1
            height = y2 - y1
            print(f"🎯 checkbox区域: ({x1},{y1}) 到 ({x2},{y2}), 尺寸: {width}x{height}")

            # 新增：针对clickable=False的特殊处理
            clickable = checkbox_element.get('clickable', False)
            if not clickable:
                print("⚠️ checkbox标记为不可点击，尝试替代策略...")

                # 策略1：尝试点击checkbox区域的多个位置
                click_positions = []

                # 添加左侧复选框区域
                click_positions.append((x1 + 20, y1 + height // 2))
                # 添加中心位置
                click_positions.append((x1 + width // 2, y1 + height // 2))
                # 添加右侧位置（如果有文字）
                if width > 100:
                    click_positions.append((x1 + width - 50, y1 + height // 2))

                print(f"🎯 尝试多个点击位置: {click_positions}")

                for i, (click_x, click_y) in enumerate(click_positions):
                    print(f"📍 尝试位置 {i+1}: ({click_x}, {click_y})")
                    success, output = self._run_adb_command([
                        "shell", "input", "tap", str(click_x), str(click_y)
                    ])

                    if success:
                        print(f"✅ 位置 {i+1} 点击成功")
                        time.sleep(1.0) # 等待状态更新

                        # 重新检查状态
                        xml_content = self.get_ui_hierarchy()
                        if xml_content:
                            elements = self._parse_ui_xml(xml_content)
                            target_selector = {"type": "agreement_checkbox"}
                            updated_checkbox = self.find_agreement_checkbox(elements, target_selector)
                            if updated_checkbox and updated_checkbox.get('checked', False):
                                print("✅ checkbox勾选状态已更新")
                                return True

                        # 如果没有状态更新，继续尝试下一个位置
                        print("⚠️ 状态未更新，继续尝试其他位置...")
                    else:
                        print(f"❌ 位置 {i+1} 点击失败: {output}")

                print("❌ 所有位置都尝试失败")
                return False

            else:
                # 原有的点击策略（针对clickable=True的情况）
                if width > 100:  # 如果宽度很大，说明可能包含文字，只点击左侧
                    click_x = x1 + min(30, width // 4)  # 点击左侧1/4处或30像素处
                    click_y = y1 + height // 2
                    print(f"📍 宽checkbox，点击左侧区域: ({click_x}, {click_y})")
                else:  # 如果是小checkbox，点击中心
                    click_x = (x1 + x2) // 2
                    click_y = (y1 + y2) // 2
                    print(f"📍 小checkbox，点击中心: ({click_x}, {click_y})")

                # 执行点击
                success, output = self._run_adb_command([
                    "shell", "input", "tap", str(click_x), str(click_y)
                ])

                if success:
                    print("✅ checkbox点击成功")
                    time.sleep(1.0)  # 等待状态更新
                    return True
                else:
                    print(f"❌ checkbox点击失败: {output}")
                    return False

        except Exception as e:
            print(f"❌ checkbox勾选过程中发生错误: {e}")
            return False

    def find_skip_button(self, elements: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """查找跳过按钮（严格按照SKIP_BUTTON_PATTERNS匹配）"""
        print("🔍 查找跳过按钮（严格按照SKIP_BUTTON_PATTERNS匹配）...")

        patterns = self.patterns.SKIP_BUTTON_PATTERNS

        for element in elements:
            # 检查是否可点击
            if element.get('clickable', False):
                element_class = element.get('class', '')
                text = element.get('text', '').lower()
                resource_id = element.get('resource-id', '').lower()
                content_desc = element.get('content-desc', '').lower()

                # 检查class_types
                if element_class in patterns['class_types']:
                    # 检查text_hints模式
                    for kw in patterns['text_hints']:
                        kw_lower = kw.lower()
                        if kw_lower in text:
                            print(f"✅ 找到跳过按钮（text匹配）: {element.get('resource-id', '无ID')} - 匹配关键字: {kw}")
                            return element

                    # 检查resource_id_keywords模式
                    for kw in patterns['resource_id_keywords']:
                        kw_lower = kw.lower()
                        if kw_lower in resource_id:
                            print(f"✅ 找到跳过按钮（resource_id匹配）: {element.get('resource-id', '无ID')} - 匹配关键字: {kw}")
                            return element

                    # 检查content_desc_keywords模式
                    for kw in patterns['content_desc_keywords']:
                        kw_lower = kw.lower()
                        if kw_lower in content_desc:
                            print(f"✅ 找到跳过按钮（content_desc匹配）: {element.get('resource-id', '无ID')} - 匹配关键字: {kw}")
                            return element

        print("❌ 未找到跳过按钮")
        return None

    def find_login_switch_button(self, elements: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """查找登录方式切换按钮（严格按照LOGIN_SWITCH_BUTTON_PATTERNS匹配）"""
        print("🔍 查找登录方式切换按钮（严格按照LOGIN_SWITCH_BUTTON_PATTERNS匹配）...")

        patterns = self.patterns.LOGIN_SWITCH_BUTTON_PATTERNS

        for element in elements:
            # 检查是否可点击
            if element.get('clickable', False):
                element_class = element.get('class', '')
                text = element.get('text', '').lower()
                resource_id = element.get('resource-id', '').lower()
                content_desc = element.get('content-desc', '').lower()

                # 检查class_types
                if element_class in patterns['class_types']:
                    # 检查text_hints模式
                    for kw in patterns['text_hints']:
                        kw_lower = kw.lower()
                        if kw_lower in text:
                            print(f"✅ 找到登录切换按钮（text匹配）: {element.get('resource-id', '无ID')} - 匹配关键字: {kw}")
                            return element

                    # 检查resource_id_keywords模式
                    for kw in patterns['resource_id_keywords']:
                        kw_lower = kw.lower()
                        if kw_lower in resource_id:
                            print(f"✅ 找到登录切换按钮（resource_id匹配）: {element.get('resource-id', '无ID')} - 匹配关键字: {kw}")
                            return element

                    # 检查content_desc_keywords模式
                    for kw in patterns['content_desc_keywords']:
                        kw_lower = kw.lower()
                        if kw_lower in content_desc:
                            print(f"✅ 找到登录切换按钮（content_desc匹配）: {element.get('resource-id', '无ID')} - 匹配关键字: {kw}")
                            return element

        print("❌ 未找到登录方式切换按钮")
        return None

    # 传统目标点击方法（兼容非参数化target_selector）
    def find_custom_target_element(self, elements: List[Dict[str, Any]], target_selector: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """查找自定义目标元素（传统方式，支持自定义匹配条件）"""
        print(f"🔍 查找自定义目标元素...")
        print(f"🎯 选择器: {target_selector}")

        if not elements:
            print("❌ 元素列表为空")
            return None

        # 提取匹配条件
        target_text = target_selector.get('text', '').lower()
        target_resource_id = target_selector.get('resource_id', '').lower()
        target_class = target_selector.get('class', '')
        target_content_desc = target_selector.get('content_desc', '').lower()
        target_hint = target_selector.get('hint', '').lower()
        require_clickable = target_selector.get('clickable', True)

        best_match = None
        best_score = 0

        for element in elements:
            # 如果要求可点击，检查clickable属性
            if require_clickable and not element.get('clickable', False):
                continue

            score = 0
            element_text = element.get('text', '').lower()
            element_resource_id = element.get('resource-id', '').lower()
            element_class = element.get('class', '')
            element_content_desc = element.get('content-desc', '').lower()
            element_hint = element.get('hint', '').lower()

            # 文本匹配（最高权重）
            if target_text and target_text in element_text:
                score += 100
                print(f"✅ 文本匹配: '{target_text}' in '{element_text}'")

            # Resource ID匹配
            if target_resource_id and target_resource_id in element_resource_id:
                score += 80
                print(f"✅ Resource ID匹配: '{target_resource_id}' in '{element_resource_id}'")

            # 类名匹配
            if target_class and target_class == element_class:
                score += 60
                print(f"✅ 类名匹配: '{target_class}'")

            # Content-desc匹配
            if target_content_desc and target_content_desc in element_content_desc:
                score += 70
                print(f"✅ Content-desc匹配: '{target_content_desc}' in '{element_content_desc}'")

            # Hint匹配
            if target_hint and target_hint in element_hint:
                score += 50
                print(f"✅ Hint匹配: '{target_hint}' in '{element_hint}'")

            # 更新最佳匹配
            if score > best_score:
                best_score = score
                best_match = element
                print(f"🎯 新的最佳匹配，得分: {score}")

        if best_match:
            print(f"✅ 找到最佳目标元素，最终得分: {best_score}")
            print(f"📍 元素信息: text='{best_match.get('text', '')}', resource-id='{best_match.get('resource-id', '')}'")
            return best_match
        else:
            print("❌ 未找到匹配的目标元素")
            return None

    def perform_click_target_action(self, target_selector: Dict[str, Any]) -> bool:
        """执行目标点击动作（传统方式和智能方式兼容）"""
        print(f"🎯 开始执行目标点击动作")
        print(f"🔧 选择器: {target_selector}")

        try:
            # 检查是否使用智能参数化选择器
            if target_selector.get('type'):
                print(f"🤖 使用智能参数化点击: type={target_selector.get('type')}")
                # 使用智能元素查找
                target_element = self.find_element_smart(target_selector)
                if target_element:
                    return self.tap_element(target_element)
                else:
                    print("❌ 智能查找未找到目标元素")
                    return False
            else:
                # 传统方式：使用自定义目标元素查找
                print("🔧 使用传统自定义目标查找")
                xml_content = self.get_ui_hierarchy()
                if not xml_content:
                    print("❌ 无法获取UI层次结构")
                    return False

                elements = self._parse_ui_xml(xml_content)
                if not elements:
                    print("❌ 解析UI元素失败")
                    return False

                target_element = self.find_custom_target_element(elements, target_selector)
                if target_element:
                    return self.tap_element(target_element)
                else:
                    print("❌ 传统查找未找到目标元素")
                    return False

        except Exception as e:
            print(f"❌ 执行目标点击动作时发生错误: {e}")
            return False

    def _allocate_device_account(self):
        """为设备分配账号"""
        try:
            # 导入账号管理器
            try:
                from account_manager import get_account_manager
                account_manager = get_account_manager()
            except ImportError as e:
                print(f"⚠️ 无法导入账号管理器: {e}")
                return

            # 尝试分配账号（只在首次分配时打印日志）
            if self.device_serial:
                # 检查是否已有分配
                existing_account = account_manager.get_account(self.device_serial)
                if existing_account:
                    self.device_account = existing_account
                    return

                # 执行新分配
                device_account = account_manager.allocate_account(self.device_serial)
                if device_account:
                    self.device_account = device_account
                    username, password = device_account
                    print(f"✅ 为设备 {self.device_serial} 分配账号: {username}")
                else:
                    print(f"⚠️ 设备 {self.device_serial} 账号分配失败")
            else:
                print("⚠️ 设备序列号为空，无法分配账号")

        except Exception as e:
            print(f"❌ 账号分配过程中发生错误: {e}")


    def _replace_account_parameters(self, text: str) -> str:
        """替换文本中的账号参数"""
        print(f"🔧 参数替换调试: device_account={self.device_account}")
        print(f"🔧 参数替换调试: device_serial={self.device_serial}")
        print(f"🔧 参数替换调试: 输入文本='{text}'")

        if not text or not self.device_account:
            print(f"⚠️ 参数替换跳过: text={bool(text)}, device_account={bool(self.device_account)}")
            return text

        result_text = text

        # 替换用户名参数
        if "${account:username}" in result_text:
            if self.device_account and len(self.device_account) >= 1:
                result_text = result_text.replace("${account:username}", self.device_account[0])
                print(f"✅ 替换用户名参数: {self.device_account[0]}")
            else:
                print(f"❌ 错误: 设备 {self.device_serial} 没有分配账号，无法替换用户名参数")

        # 替换密码参数
        if "${account:password}" in result_text:
            if self.device_account and len(self.device_account) >= 2:
                result_text = result_text.replace("${account:password}", self.device_account[1])
                print(f"✅ 替换密码参数: {'*' * len(self.device_account[1])}")
            else:
                print(f"❌ 错误: 设备 {self.device_serial} 没有分配账号，无法替换密码参数")

        return result_text

    def perform_auto_login(self, username: str, password: str) -> bool:
        """
        执行完整的自动登录流程

        Args:
            username: 用户名
            password: 密码

        Returns:
            登录是否成功
        """
        print(f"🔐 开始执行自动登录流程")
        print(f"👤 用户名: {username}")
        print(f"🔑 密码: {'*' * len(password)}")

        try:
            # 第一步：查找并填写用户名
            print("🔍 步骤1: 查找用户名输入框...")
            xml_content = self.get_ui_hierarchy()
            if not xml_content:
                print("❌ 无法获取UI结构")
                return False

            elements = self._parse_ui_xml(xml_content)
            if not elements:
                print("❌ 无法解析UI元素")
                return False

            username_field = self.find_username_field(elements)
            if username_field:
                print("✅ 找到用户名输入框")
                # 点击获取焦点
                if self.tap_element(username_field):
                    # 输入用户名
                    if self.input_text_smart(username):
                        print("✅ 用户名输入成功")
                    else:
                        print("❌ 用户名输入失败")
                        return False
                else:
                    print("❌ 用户名输入框点击失败")
                    return False
            else:
                print("❌ 未找到用户名输入框")
                return False

            # 第二步：查找并填写密码
            print("🔍 步骤2: 查找密码输入框...")
            xml_content = self.get_ui_hierarchy()  # 重新获取UI结构
            if xml_content:
                elements = self._parse_ui_xml(xml_content)
                password_field = self.find_password_field(elements)
                if password_field:
                    print("✅ 找到密码输入框")
                    # 点击获取焦点
                    if self.tap_element(password_field):
                        # 输入密码
                        if self.input_text_smart(password):
                            print("✅ 密码输入成功")
                        else:
                            print("❌ 密码输入失败")
                            return False
                    else:
                        print("❌ 密码输入框点击失败")
                        return False
                else:
                    print("❌ 未找到密码输入框")
                    return False
            else:
                print("❌ 无法重新获取UI结构")
                return False

            # 第三步：查找并点击登录按钮
            print("🔍 步骤3: 查找登录按钮...")
            xml_content = self.get_ui_hierarchy()  # 再次获取UI结构
            if xml_content:
                elements = self._parse_ui_xml(xml_content)
                login_button = self.find_login_button(elements)
                if login_button:
                    print("✅ 找到登录按钮")
                    # 点击登录按钮
                    if self.tap_element(login_button):
                        print("✅ 登录按钮点击成功")
                        print("🎉 自动登录流程完成")
                        return True
                    else:
                        print("❌ 登录按钮点击失败")
                        return False
                else:
                    print("❌ 未找到登录按钮")
                    return False
            else:
                print("❌ 无法重新获取UI结构")
                return False

        except Exception as e:
            print(f"❌ 自动登录过程中发生错误: {e}")
            return False
