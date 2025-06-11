#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能登录操作实现器
基于UI结构分析结果，自动识别并操作登录界面的各个元素
支持账号输入、密码输入、checkbox勾选、登录按钮点击等操作
"""

import subprocess
import json
import time
import os
from typing import List, Dict, Any, Optional, Tuple
import re
from datetime import datetime

class LoginElementPatterns:
    """登录元素模式定义"""

    # 账号输入框模式
    USERNAME_PATTERNS = {
        'text_hints': ['账号', '用户名', 'username', 'account', '请输入账号','请输入您的账号', '请输入手机号'],
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
        'password_field': True  # 密码字段特征
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

class SmartLoginOperator:
    """智能登录操作器"""

    def __init__(self, device_id: Optional[str] = None):
        self.device_id = device_id
        self.patterns = LoginElementPatterns()

    def get_ui_structure(self, device_id: str) -> Optional[Dict[str, Any]]:
        """获取当前UI结构"""
        try:
            # 使用uiautomator dump获取UI结构
            xml_path = f"/sdcard/ui_dump_{int(time.time())}.xml"

            # 在设备上执行UI dump
            dump_cmd = f"adb -s {device_id} shell uiautomator dump {xml_path}"
            result = subprocess.run(dump_cmd, shell=True, capture_output=True, text=True)

            if result.returncode != 0:
                print(f"❌ UI dump失败: {result.stderr}")
                return None

            # 将XML文件拉取到本地
            local_xml_path = f"current_ui_{device_id}.xml"
            pull_cmd = f"adb -s {device_id} pull {xml_path} {local_xml_path}"
            pull_result = subprocess.run(pull_cmd, shell=True, capture_output=True, text=True)

            if pull_result.returncode != 0:
                print(f"❌ 拉取XML文件失败: {pull_result.stderr}")
                return None

            # 解析XML并提取元素信息
            elements = self._parse_ui_xml(local_xml_path)

            # 清理临时文件
            subprocess.run(f"adb -s {device_id} shell rm {xml_path}", shell=True, check=False)
            if os.path.exists(local_xml_path):
                os.remove(local_xml_path)

            return {
                "device_id": device_id,
                "timestamp": datetime.now().isoformat(),
                "elements": elements
            }

        except Exception as e:
            print(f"❌ 获取UI结构失败: {e}")
            return None

    def _parse_ui_xml(self, xml_path: str) -> List[Dict[str, Any]]:
        """解析UI XML文件"""
        import xml.etree.ElementTree as ET

        elements = []
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            def parse_node(node):
                if node.tag == 'node':
                    element = {
                        "class": node.get("class", ""),
                        "text": node.get("text", ""),
                        "content_desc": node.get("content-desc", ""),
                        "resource_id": node.get("resource-id", ""),
                        "bounds": node.get("bounds", ""),
                        "clickable": node.get("clickable", "false").lower() == "true",
                        "scrollable": node.get("scrollable", "false").lower() == "true",
                        "enabled": node.get("enabled", "false").lower() == "true",
                        "focused": node.get("focused", "false").lower() == "true",
                        "password": node.get("password", "false").lower() == "true",
                        "checkable": node.get("checkable", "false").lower() == "true",
                        "checked": node.get("checked", "false").lower() == "true",
                        "package": node.get("package", "")
                    }
                    elements.append(element)

                # 递归处理子节点
                for child in node:
                    parse_node(child)

            parse_node(root)

        except Exception as e:
            print(f"⚠️ 解析XML失败: {e}")

        return elements

    def _calculate_match_score(self, element: Dict[str, Any], patterns: Dict[str, Any]) -> float:
        """计算元素与模式的匹配分数"""
        score = 0.0
        max_score = 0.0

        # 特殊处理：勾选框优先级识别 (权重: 40)
        if patterns.get('checkable_priority', False):
            max_score += 40
            if element.get("checkable", False) or element.get("class") == "android.widget.CheckBox":
                score += 40
        else:
            # 检查文本提示匹配 (权重: 30)
            max_score += 30
            text = element.get("text", "").lower()
            for hint in patterns.get('text_hints', []):
                if hint.lower() in text:
                    score += 30
                    break

        # 检查resource-id匹配 (权重: 25)
        max_score += 25
        resource_id = element.get("resource_id", "").lower()
        for keyword in patterns.get('resource_id_keywords', []):
            if keyword.lower() in resource_id:
                score += 25
                break

        # 检查class类型匹配 (权重: 20)
        max_score += 20
        element_class = element.get("class", "")
        if element_class in patterns.get('class_types', []):
            score += 20

        # 检查content-desc匹配 (权重: 15)
        max_score += 15
        content_desc = element.get("content_desc", "").lower()
        for keyword in patterns.get('content_desc_keywords', []):
            if keyword.lower() in content_desc:
                score += 15
                break

        # 特殊检查：密码字段 (权重: 10)
        if patterns.get('password_field', False):
            max_score += 10
            if element.get("password", False):
                score += 10

        # 基础可用性检查 (权重: 10)
        max_score += 10
        if element.get("enabled", False):
            score += 5
        if element.get("clickable", False) or element.get("checkable", False):
            score += 5

        return score / max_score if max_score > 0 else 0.0

    def find_username_field(self, elements: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """查找用户名输入框"""
        print("🔍 正在查找用户名输入框...")

        candidates = []
        for element in elements:
            if element.get("class") == "android.widget.EditText":
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
            if element.get("class") == "android.widget.EditText":
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
            if element.get("class") == "android.widget.CheckBox":
                score = self._calculate_match_score(element, self.patterns.CHECKBOX_PATTERNS)
                candidates.append((element, score))
                print(f"🎯 发现CheckBox控件: {element.get('resource_id', '无ID')} (得分: {score:.2f})")
            # 其次匹配可勾选的元素
            elif element.get("checkable", False):
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
            if element.get("clickable", False):
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

    def _parse_bounds(self, bounds_str: str) -> Tuple[int, int]:
        """解析bounds字符串，返回中心点坐标"""
        # bounds格式: "[x1,y1][x2,y2]"
        try:
            import re
            match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds_str)
            if match:
                x1, y1, x2, y2 = map(int, match.groups())
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                return center_x, center_y
        except Exception as e:
            print(f"⚠️ 解析bounds失败: {e}")

        return 540, 1200  # 默认中心位置

    def tap_element(self, device_id: str, element: Dict[str, Any]) -> bool:
        """点击元素"""
        try:
            bounds = element.get("bounds", "")
            if not bounds:
                print("❌ 元素没有bounds信息")
                return False

            x, y = self._parse_bounds(bounds)
            print(f"📱 点击位置: ({x}, {y})")

            tap_cmd = f"adb -s {device_id} shell input tap {x} {y}"
            result = subprocess.run(tap_cmd, shell=True, capture_output=True, text=True)

            if result.returncode == 0:
                print("✅ 点击成功")
                time.sleep(1)  # 等待响应
                return True
            else:
                print(f"❌ 点击失败: {result.stderr}")
                return False

        except Exception as e:
            print(f"❌ 点击操作失败: {e}")
            return False

    def input_text(self, device_id: str, element: Dict[str, Any], text: str) -> bool:
        """输入文本到元素"""
        try:
            # 先点击元素获得焦点
            if not self.tap_element(device_id, element):
                return False

            # 清空现有文本
            clear_cmd = f"adb -s {device_id} shell input keyevent KEYCODE_CTRL_A"
            subprocess.run(clear_cmd, shell=True, check=False)
            time.sleep(0.5)

            delete_cmd = f"adb -s {device_id} shell input keyevent KEYCODE_DEL"
            subprocess.run(delete_cmd, shell=True, check=False)
            time.sleep(0.5)

            # 输入新文本
            # 转义特殊字符
            escaped_text = text.replace(' ', '%s').replace('&', '\\&').replace('<', '\\<').replace('>', '\\>')
            input_cmd = f"adb -s {device_id} shell input text '{escaped_text}'"
            result = subprocess.run(input_cmd, shell=True, capture_output=True, text=True)

            if result.returncode == 0:
                print(f"✅ 输入文本成功: {text}")
                time.sleep(1)  # 等待输入完成
                return True
            else:
                print(f"❌ 输入文本失败: {result.stderr}")
                return False

        except Exception as e:
            print(f"❌ 输入操作失败: {e}")
            return False

    def check_checkbox(self, device_id: str, element: Dict[str, Any]) -> bool:
        """勾选复选框 - 直接点击checkbox框"""
        try:
            # 检查是否已经勾选
            if element.get("checked", False):
                print("✅ 复选框已经勾选")
                return True

            # 直接点击复选框的中心位置进行勾选
            print(f"🎯 正在点击复选框: {element.get('class')} (可勾选: {element.get('checkable')})")
            if self.tap_element(device_id, element):
                print("✅ 复选框勾选成功")
                return True
            else:
                print("❌ 复选框勾选失败")
                return False

        except Exception as e:
            print(f"❌ 勾选操作失败: {e}")
            return False

    def perform_login(self, device_id: str, username: str, password: str) -> bool:
        """执行完整的登录操作"""
        print(f"🚀 开始执行设备 {device_id} 的登录操作")
        print("=" * 60)

        # 1. 获取当前UI结构
        ui_data = self.get_ui_structure(device_id)
        if not ui_data:
            print("❌ 无法获取UI结构")
            return False

        elements = ui_data.get("elements", [])
        print(f"📊 获取到 {len(elements)} 个UI元素")

        # 2. 查找各个登录元素
        username_field = self.find_username_field(elements)
        password_field = self.find_password_field(elements)
        agreement_checkbox = self.find_agreement_checkbox(elements)
        login_button = self.find_login_button(elements)

        # 检查必要元素是否都找到
        if not username_field:
            print("❌ 未找到用户名输入框，无法继续登录")
            return False

        if not password_field:
            print("❌ 未找到密码输入框，无法继续登录")
            return False

        if not login_button:
            print("❌ 未找到登录按钮，无法继续登录")
            return False

        # 3. 开始执行登录步骤
        print("\n🎯 开始执行登录步骤:")

        # 步骤1: 输入用户名
        print("步骤1: 输入用户名")
        if not self.input_text(device_id, username_field, username):
            print("❌ 用户名输入失败")
            return False

        # 步骤2: 输入密码
        print("步骤2: 输入密码")
        if not self.input_text(device_id, password_field, password):
            print("❌ 密码输入失败")
            return False

        # 步骤3: 勾选协议（如果存在）
        if agreement_checkbox:
            print("步骤3: 勾选用户协议")
            if not self.check_checkbox(device_id, agreement_checkbox):
                print("⚠️ 协议勾选失败，但继续执行")
        else:
            print("步骤3: 跳过（未发现协议勾选框）")

        # 步骤4: 点击登录按钮
        print("步骤4: 点击登录按钮")
        if not self.tap_element(device_id, login_button):
            print("❌ 登录按钮点击失败")
            return False

        print("\n🎉 登录操作执行完成！")
        print("⏳ 请等待登录结果...")

        # 等待登录处理
        time.sleep(5)

        return True

    def demo_login_with_analysis(self, device_id: str) -> bool:
        """使用分析结果进行演示登录"""
        print(f"🎮 开始演示登录操作 - 设备: {device_id}")

        # 使用演示账号密码
        demo_username = "testuser123"
        demo_password = "password123"

        return self.perform_login(device_id, demo_username, demo_password)

def main():
    """主函数"""
    print("🔐 智能登录操作实现器")
    print("=" * 60)

    # 获取连接的设备
    try:
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')[1:]
        devices = []

        for line in lines:
            if line.strip() and '\t' in line:
                parts = line.split('\t')
                if len(parts) >= 2 and parts[1].strip() == 'device':
                    devices.append(parts[0].strip())

        if not devices:
            print("❌ 未发现连接的设备！")
            return

        print(f"🔍 发现 {len(devices)} 个连接的设备:")
        for i, device in enumerate(devices):
            print(f"   {i+1}. {device}")

        # 选择设备
        if len(devices) == 1:
            target_device = devices[0]
            print(f"\n🎯 自动选择设备: {target_device}")
        else:
            while True:
                try:
                    choice = input(f"\n请选择设备 (1-{len(devices)}): ").strip()
                    index = int(choice) - 1
                    if 0 <= index < len(devices):
                        target_device = devices[index]
                        print(f"🎯 选择设备: {target_device}")
                        break
                    else:
                        print("❌ 无效选择，请重新输入")
                except ValueError:
                    print("❌ 请输入数字")

        # 创建登录操作器
        login_operator = SmartLoginOperator(target_device)

        # 选择操作模式
        print("\n📋 选择操作模式:")
        print("1. 演示模式（使用测试账号密码）")
        print("2. 自定义模式（输入自己的账号密码）")
        print("3. 仅分析UI结构（不执行登录）")

        while True:
            try:
                mode = input("请选择模式 (1-3): ").strip()
                if mode in ['1', '2', '3']:
                    break
                else:
                    print("❌ 无效选择，请重新输入")
            except KeyboardInterrupt:
                print("\n👋 操作已取消")
                return

        if mode == '1':
            # 演示模式
            success = login_operator.demo_login_with_analysis(target_device)

        elif mode == '2':
            # 自定义模式
            try:
                username = input("请输入用户名: ").strip()
                password = input("请输入密码: ").strip()

                if not username or not password:
                    print("❌ 用户名和密码不能为空")
                    return

                success = login_operator.perform_login(target_device, username, password)

            except KeyboardInterrupt:
                print("\n👋 操作已取消")
                return

        elif mode == '3':
            # 仅分析模式
            ui_data = login_operator.get_ui_structure(target_device)
            if ui_data:
                elements = ui_data.get("elements", [])
                print(f"\n📊 UI结构分析结果:")
                print(f"   设备: {target_device}")
                print(f"   时间: {ui_data.get('timestamp')}")
                print(f"   元素总数: {len(elements)}")

                # 分析各种登录元素
                username_field = login_operator.find_username_field(elements)
                password_field = login_operator.find_password_field(elements)
                agreement_checkbox = login_operator.find_agreement_checkbox(elements)
                login_button = login_operator.find_login_button(elements)

                print(f"\n🎯 登录元素识别结果:")
                print(f"   用户名输入框: {'✅ 已找到' if username_field else '❌ 未找到'}")
                print(f"   密码输入框: {'✅ 已找到' if password_field else '❌ 未找到'}")
                print(f"   协议勾选框: {'✅ 已找到' if agreement_checkbox else '⚠️ 未找到'}")
                print(f"   登录按钮: {'✅ 已找到' if login_button else '❌ 未找到'}")

                # 保存分析结果
                output_file = f"login_analysis_{target_device}_{int(time.time())}.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(ui_data, f, ensure_ascii=False, indent=2)
                print(f"\n💾 详细分析结果已保存到: {output_file}")

            return

        if mode in ['1', '2']:
            if success:
                print("\n🎉 登录操作完成！请检查设备上的登录结果。")
            else:
                print("\n❌ 登录操作失败，请检查设备状态和UI界面。")

    except KeyboardInterrupt:
        print("\n👋 操作已取消")
    except Exception as e:
        print(f"❌ 程序执行出错: {e}")

if __name__ == "__main__":
    main()
