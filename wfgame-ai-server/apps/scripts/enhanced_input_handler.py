"""
WFGameAI增强输入处理器
功能：集成智能登录操作器的优化算法和焦点检测
作者：WFGameAI开发团队
"""

import os
import time
import xml.etree.ElementTree as ET
from typing import Optional, Tuple, Dict, Any, List
import subprocess
import tempfile
import re
from datetime import datetime


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
    }

    # 勾选框模式 - 直接识别checkbox控件，不依赖文本提示
    CHECKBOX_PATTERNS = {
        'resource_id_keywords': ['agree', 'accept', 'checkbox', 'cb_ag', 'remember'],
        'class_types': ['android.widget.CheckBox'],
        'content_desc_keywords': ['同意', '协议', '记住'],
        'checkable_priority': True  # 优先识别可勾选的元素
    }

    # 登录按钮模式
    LOGIN_BUTTON_PATTERNS = {
        'text_hints': ['进入游戏', '立即登录', '登录', '登入', 'login', '开始游戏'],
        'resource_id_keywords': ['login', 'submit', 'enter', 'game', 'start'],
        'class_types': ['android.widget.Button', 'android.widget.TextView'],
        'content_desc_keywords': ['登录', '进入', '开始']
    }

    # 通用输入框模式
    GENERIC_INPUT_PATTERNS = {
        'class_types': ['android.widget.EditText'],
        'fallback_keywords': ['input', 'edit', 'text', 'field']
    }


class EnhancedInputHandler:
    """增强输入处理器：结合智能登录操作器的优化算法"""

    def __init__(self, device_serial: Optional[str] = None):
        """
        初始化增强输入处理器

        Args:
            device_serial: 设备序列号，None表示默认设备
        """
        self.device_serial = device_serial
        self.adb_prefix = ["adb"]
        if device_serial:
            self.adb_prefix.extend(["-s", device_serial])
        self.patterns = ElementPatterns()

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

    def _calculate_match_score(self, element: Dict[str, Any], patterns: Dict[str, Any]) -> float:
        """
        计算元素与模式的匹配分数

        Args:
            element: 元素信息
            patterns: 匹配模式

        Returns:
            匹配分数 (0-1之间)
        """
        score = 0.0
        max_score = 0.0

        # 特殊处理：勾选框优先级识别 (权重: 40)
        if patterns.get('checkable_priority', False):
            max_score += 40
            if element.get('checkable', False) or element.get('class') == 'android.widget.CheckBox':
                score += 40
        else:
            # 检查文本提示匹配 (权重: 30)
            text_hints = patterns.get('text_hints', [])
            if text_hints:
                max_score += 30
                element_text = (element.get('text', '') + ' ' + element.get('hint', '')).lower()
                for hint in text_hints:
                    if hint.lower() in element_text:
                        score += 30
                        break

        # 检查resource-id关键词匹配 (权重: 25)
        resource_keywords = patterns.get('resource_id_keywords', [])
        if resource_keywords:
            max_score += 25
            resource_id = element.get('resource_id', '').lower()
            for keyword in resource_keywords:
                if keyword in resource_id:
                    score += 25
                    break

        # 检查class类型匹配 (权重: 20)
        class_types = patterns.get('class_types', [])
        if class_types:
            max_score += 20
            element_class = element.get('class', '')
            if element_class in class_types:
                score += 20

        # 检查content-desc匹配 (权重: 15)
        content_keywords = patterns.get('content_desc_keywords', [])
        if content_keywords:
            max_score += 15
            content_desc = element.get('content_desc', '').lower()
            for keyword in content_keywords:
                if keyword.lower() in content_desc:
                    score += 15
                    break

        # 检查密码字段特征 (权重: 10)
        if patterns.get('password_field'):
            max_score += 10
            if element.get('password', False):
                score += 10

        # 基础可用性检查 (权重: 10)
        max_score += 10
        if element.get('enabled', False):
            score += 5
        if element.get('clickable', False) or element.get('checkable', False):
            score += 5

        return score / max_score if max_score > 0 else 0.0

    def find_best_input_field(self, target_selector: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        使用智能算法查找最佳的输入框

        Args:
            target_selector: 目标选择器信息

        Returns:
            最佳匹配的输入框元素或None
        """
        print(f"🔍 智能查找输入框...")

        # 获取UI结构
        xml_content = self.get_ui_hierarchy()
        if not xml_content:
            return None

        elements = self._parse_ui_xml(xml_content)
        print(f"📊 解析到 {len(elements)} 个UI元素")

        # 提取目标信息
        placeholder = target_selector.get('placeholder', '')
        text_hint = target_selector.get('text', '')

        candidates = []

        # 如果有placeholder信息，使用专门的模式匹配
        if placeholder:
            print(f"🎯 使用placeholder '{placeholder}' 进行智能匹配")

            # 根据placeholder内容判断可能的输入类型
            if any(keyword in placeholder.lower() for keyword in ['密码', 'password', '验证码']):
                patterns = self.patterns.PASSWORD_PATTERNS
                print("📝 识别为密码类型输入框")
            elif any(keyword in placeholder.lower() for keyword in ['账号', '用户名', 'username', 'account', '手机号']):
                patterns = self.patterns.USERNAME_PATTERNS
                print("📝 识别为用户名类型输入框")
            else:
                patterns = self.patterns.GENERIC_INPUT_PATTERNS
                print("📝 识别为通用输入框")

            # 临时添加placeholder到匹配模式中
            temp_patterns = patterns.copy()
            if 'text_hints' not in temp_patterns:
                temp_patterns['text_hints'] = []
            temp_patterns['text_hints'].append(placeholder)

            # 查找匹配的输入框
            for element in elements:
                if element.get('class') == 'android.widget.EditText':
                    score = self._calculate_match_score(element, temp_patterns)
                    if score > 0.2:  # 降低阈值以提高匹配成功率
                        candidates.append((element, score))
                        print(f"  🎯 候选元素: {element.get('resource_id', '无ID')} (得分: {score:.2f})")

        # 如果没有找到匹配的，尝试通用匹配
        if not candidates:
            print("🔄 使用通用策略查找输入框...")
            for element in elements:
                if (element.get('class') == 'android.widget.EditText' and
                    element.get('enabled', False) and
                    element.get('focusable', False)):

                    # 简单的通用评分
                    score = 0.5
                    if element.get('bounds'):
                        score += 0.2
                    if element.get('clickable', False):
                        score += 0.1

                    candidates.append((element, score))
                    print(f"  📝 通用候选元素: {element.get('resource_id', '无ID')} (得分: {score:.2f})")

        # 选择最佳候选
        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            best_match = candidates[0]
            print(f"✅ 找到最佳输入框: {best_match[0].get('resource_id', '无ID')} (得分: {best_match[1]:.2f})")
            return best_match[0]

        print("❌ 未找到合适的输入框")
        return None

    def find_username_field(self, elements: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """查找用户名输入框"""
        print("🔍 正在查找用户名输入框...")

        candidates = []
        for element in elements:
            if element.get('class') == 'android.widget.EditText':
                score = self._calculate_match_score(element, self.patterns.USERNAME_PATTERNS)
                if score > 0.3:  # 最低匹配阈值
                    candidates.append((element, score))

        if candidates:
            # 按分数排序，选择最高分的
            candidates.sort(key=lambda x: x[1], reverse=True)
            best_match = candidates[0]
            print(f"✅ 找到用户名输入框: {best_match[0].get('resource_id', '无ID')} (得分: {best_match[1]:.2f})")
            return best_match[0]

        print("❌ 未找到用户名输入框")
        return None

    def find_password_field(self, elements: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """查找密码输入框"""
        print("🔍 正在查找密码输入框...")

        candidates = []
        for element in elements:
            if element.get('class') == 'android.widget.EditText':
                score = self._calculate_match_score(element, self.patterns.PASSWORD_PATTERNS)
                if score > 0.3:  # 最低匹配阈值
                    candidates.append((element, score))

        if candidates:
            # 按分数排序，选择最高分的
            candidates.sort(key=lambda x: x[1], reverse=True)
            best_match = candidates[0]
            print(f"✅ 找到密码输入框: {best_match[0].get('resource_id', '无ID')} (得分: {best_match[1]:.2f})")
            return best_match[0]

        print("❌ 未找到密码输入框")
        return None

    def find_agreement_checkbox(self, elements: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """查找协议勾选框 - 优化版：直接通过checkable属性和class类型识别"""
        print("🔍 正在查找协议勾选框...")

        candidates = []
        for element in elements:
            # 优先匹配真正的CheckBox控件
            if element.get('class') == 'android.widget.CheckBox':
                score = self._calculate_match_score(element, self.patterns.CHECKBOX_PATTERNS)
                candidates.append((element, score))
                print(f"🎯 发现CheckBox控件: {element.get('resource_id', '无ID')} (得分: {score:.2f})")
            # 其次匹配可勾选的元素
            elif element.get('checkable', False):
                score = self._calculate_match_score(element, self.patterns.CHECKBOX_PATTERNS)
                if score > 0.2:  # 降低阈值
                    candidates.append((element, score))
                    print(f"🎯 发现可勾选元素: {element.get('resource_id', '无ID')} (得分: {score:.2f})")

        if candidates:
            # 按分数排序，选择最高分的
            candidates.sort(key=lambda x: x[1], reverse=True)
            best_match = candidates[0]
            print(f"✅ 找到协议勾选框: {best_match[0].get('resource_id', '无ID')} (得分: {best_match[1]:.2f})")
            print(f"   类型: {best_match[0].get('class')}")
            print(f"   可勾选: {best_match[0].get('checkable')}")
            print(f"   边界: {best_match[0].get('bounds')}")
            return best_match[0]

        print("⚠️ 未找到协议勾选框（可能不是必须的）")
        return None

    def find_login_button(self, elements: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """查找登录按钮"""
        print("🔍 正在查找登录按钮...")

        candidates = []
        for element in elements:
            if element.get('clickable', False):
                score = self._calculate_match_score(element, self.patterns.LOGIN_BUTTON_PATTERNS)
                if score > 0.3:  # 最低匹配阈值
                    candidates.append((element, score))

        if candidates:
            # 按分数排序，选择最高分的
            candidates.sort(key=lambda x: x[1], reverse=True)
            best_match = candidates[0]
            print(f"✅ 找到登录按钮: {best_match[0].get('text', '无文本')} (得分: {best_match[1]:.2f})")
            return best_match[0]

        print("❌ 未找到登录按钮")
        return None

    def check_checkbox(self, checkbox_element: Dict[str, Any]) -> bool:
        """勾选checkbox"""
        print("☑️ 执行checkbox勾选...")

        try:
            bounds = checkbox_element.get('bounds', '')
            if not bounds:
                print("❌ checkbox没有bounds信息")
                return False

            coords = self._parse_bounds(bounds)
            if not coords:
                print(f"❌ 无法解析checkbox的bounds: {bounds}")
                return False

            center_x, center_y = coords

            # 检查当前勾选状态
            checked = checkbox_element.get('checked', False)
            if checked:
                print("✅ checkbox已经勾选")
                return True

            print(f"👆 点击checkbox进行勾选: ({center_x}, {center_y})")
            success, output = self._run_adb_command([
                "shell", "input", "tap", str(center_x), str(center_y)
            ])

            if success:
                print("✅ checkbox勾选成功")
                time.sleep(0.5)
                return True
            else:
                print(f"❌ checkbox勾选失败: {output}")
                return False

        except Exception as e:
            print(f"❌ checkbox勾选过程中发生错误: {e}")
            return False

    def click_login_button(self, button_element: Dict[str, Any]) -> bool:
        """点击登录按钮"""
        print("🔘 执行登录按钮点击...")

        try:
            bounds = button_element.get('bounds', '')
            if not bounds:
                print("❌ 登录按钮没有bounds信息")
                return False

            coords = self._parse_bounds(bounds)
            if not coords:
                print(f"❌ 无法解析登录按钮的bounds: {bounds}")
                return False

            center_x, center_y = coords
            print(f"👆 点击登录按钮: ({center_x}, {center_y})")

            success, output = self._run_adb_command([
                "shell", "input", "tap", str(center_x), str(center_y)
            ])

            if success:
                print("✅ 登录按钮点击成功")
                time.sleep(1.0)  # 等待登录处理
                return True
            else:
                print(f"❌ 登录按钮点击失败: {output}")
                return False

        except Exception as e:
            print(f"❌ 登录按钮点击过程中发生错误: {e}")
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

        try:
            # 转义特殊字符
            escaped_text = text.replace(' ', '%s').replace('&', '\\&').replace('<', '\\<').replace('>', '\\>')

            # 分段输入，避免过长文本问题
            max_length = 20
            success = True

            for i in range(0, len(escaped_text), max_length):
                segment = escaped_text[i:i + max_length]

                seg_success, output = self._run_adb_command(["shell", "input", "text", segment])
                if not seg_success:
                    print(f"❌ 输入文本段失败: '{segment}', 错误: {output}")
                    success = False
                    break

                # 段间延迟
                if i + max_length < len(escaped_text):
                    time.sleep(0.2)

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

    def input_text_with_focus_detection(self, text: str, target_selector: Dict[str, Any]) -> bool:
        """
        综合焦点检测和文本输入 - 增强版

        Args:
            text: 要输入的文本
            target_selector: 目标选择器

        Returns:
            输入是否成功
        """
        print(f"🎯 开始增强版焦点检测和文本输入")
        print(f"📝 目标文本: '{text[:30]}{'...' if len(text) > 30 else ''}'")
        print(f"🎯 选择器信息: {target_selector}")

        try:
            # 第一步：使用智能算法查找最佳输入框
            best_input_field = self.find_best_input_field(target_selector)

            if not best_input_field:
                print("❌ 未找到合适的输入框")
                return False

            # 第二步：确保输入框获得焦点
            if not best_input_field.get('focused', False):
                print("🎯 输入框未聚焦，点击获取焦点")
                if not self.tap_element(best_input_field):
                    print("❌ 点击输入框失败")
                    return False

            # 第三步：清空现有内容
            if not self.clear_input_field():
                print("⚠️ 清空输入框失败，但继续尝试输入")

            # 第四步：执行智能文本输入
            if self.input_text_smart(text):
                print("✅ 增强版焦点检测和文本输入完成")
                return True
            else:
                print("❌ 文本输入失败")
                return False

        except Exception as e:
            print(f"❌ 增强版输入处理过程中发生错误: {e}")
            return False

    def perform_auto_login(self, username: str, password: str) -> bool:
        """
        执行完整的自动登录流程

        Args:
            username: 用户名
            password: 密码

        Returns:
            登录是否成功
        """
        print("🚀 开始执行完整自动登录流程")
        print(f"👤 用户名: {username}")
        print(f"🔐 密码: {'*' * len(password)}")

        try:
            # 第一步：获取UI结构
            xml_content = self.get_ui_hierarchy()
            if not xml_content:
                print("❌ 无法获取UI结构，登录失败")
                return False

            elements = self._parse_ui_xml(xml_content)
            print(f"📊 解析到 {len(elements)} 个UI元素")

            # 第二步：查找用户名输入框
            username_field = self.find_username_field(elements)
            if not username_field:
                print("❌ 未找到用户名输入框，登录失败")
                return False

            # 第三步：查找密码输入框
            password_field = self.find_password_field(elements)
            if not password_field:
                print("❌ 未找到密码输入框，登录失败")
                return False

            # 第四步：查找登录按钮
            login_button = self.find_login_button(elements)
            if not login_button:
                print("❌ 未找到登录按钮，登录失败")
                return False

            # 第五步：查找协议勾选框（可选）
            checkbox = self.find_agreement_checkbox(elements)

            # 第六步：输入用户名
            print("📝 输入用户名...")
            if not self.tap_element(username_field):
                print("❌ 点击用户名输入框失败")
                return False

            self.clear_input_field()  # 清空现有内容
            if not self.input_text_smart(username):
                print("❌ 输入用户名失败")
                return False

            # 第七步：输入密码
            print("🔐 输入密码...")
            if not self.tap_element(password_field):
                print("❌ 点击密码输入框失败")
                return False

            self.clear_input_field()  # 清空现有内容
            if not self.input_text_smart(password):
                print("❌ 输入密码失败")
                return False

            # 第八步：勾选协议（如果存在）
            if checkbox:
                print("☑️ 勾选用户协议...")
                if not self.check_checkbox(checkbox):
                    print("⚠️ 勾选协议失败，但继续登录流程")

            # 第九步：点击登录按钮
            print("🔘 点击登录按钮...")
            if not self.click_login_button(login_button):
                print("❌ 点击登录按钮失败")
                return False

            print("✅ 完整自动登录流程执行成功")
            return True

        except Exception as e:
            print(f"❌ 自动登录流程中发生错误: {e}")
            return False

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


def test_enhanced_input_handler():
    """测试增强输入处理器功能"""
    print("=== 增强输入处理器测试 ===")

    handler = EnhancedInputHandler()

    # 测试UI结构获取
    xml_content = handler.get_ui_hierarchy()
    if xml_content:
        print("✅ UI结构获取成功")
        elements = handler._parse_ui_xml(xml_content)
        print(f"📊 解析到 {len(elements)} 个UI元素")
    else:
        print("❌ UI结构获取失败")

    # 测试智能输入框查找
    test_selector = {
        'placeholder': '请输入用户名'
    }
    input_field = handler.find_best_input_field(test_selector)
    if input_field:
        print(f"✅ 找到输入框: {input_field}")
    else:
        print("❌ 未找到输入框")


if __name__ == "__main__":
    test_enhanced_input_handler()
