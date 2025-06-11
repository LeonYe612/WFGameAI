"""
WFGameAI输入处理器
功能：焦点检测和文本输入处理
作者：WFGameAI开发团队
"""

import os
import time
import xml.etree.ElementTree as ET
from typing import Optional, Tuple, Dict, Any
import subprocess
import tempfile


class InputHandler:
    """输入处理器：焦点检测和文本输入"""

    def __init__(self, device_serial: Optional[str] = None):
        """
        初始化输入处理器

        Args:
            device_serial: 设备序列号，None表示默认设备
        """
        self.device_serial = device_serial
        self.adb_prefix = ["adb"]
        if device_serial:
            self.adb_prefix.extend(["-s", device_serial])

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
                timeout=10
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

    def detect_input_focus_by_placeholder(self, target_placeholder: str) -> Optional[Dict[str, Any]]:
        """
        通过placeholder属性检测输入焦点

        Args:
            target_placeholder: 目标placeholder文本

        Returns:
            焦点元素信息或None
        """
        print(f"🔍 检测placeholder为'{target_placeholder}'的输入框焦点...")

        xml_content = self.get_ui_hierarchy()
        if not xml_content:
            return None

        try:
            root = ET.fromstring(xml_content)

            # 搜索包含目标placeholder的输入元素
            for element in root.iter():
                placeholder = element.get('placeholder', '')
                hint = element.get('hint', '')  # Android中hint相当于placeholder
                text = element.get('text', '')
                class_name = element.get('class', '')
                focused = element.get('focused', 'false').lower() == 'true'

                # 检查是否为输入框类型
                is_input = any(input_type in class_name.lower() for input_type in
                              ['edittext', 'textfield', 'input'])

                # 检查placeholder匹配
                placeholder_match = (target_placeholder.lower() in placeholder.lower() or
                                   target_placeholder.lower() in hint.lower())

                if is_input and placeholder_match:
                    bounds = element.get('bounds', '')

                    element_info = {
                        'placeholder': placeholder or hint,
                        'text': text,
                        'class': class_name,
                        'focused': focused,
                        'bounds': bounds,
                        'clickable': element.get('clickable', 'false').lower() == 'true'
                    }

                    focus_status = "已聚焦" if focused else "未聚焦"
                    print(f"✅ 找到匹配的输入框: placeholder='{element_info['placeholder']}', 状态={focus_status}")

                    return element_info

            print(f"❌ 未找到placeholder为'{target_placeholder}'的输入框")
            return None

        except ET.ParseError as e:
            print(f"❌ XML解析失败: {e}")
            return None
        except Exception as e:
            print(f"❌ 检测输入焦点失败: {e}")
            return None

    def detect_input_focus_by_keyboard(self) -> bool:
        """
        通过键盘状态检测是否有输入焦点

        Returns:
            True表示键盘可见（有输入焦点），False表示无焦点
        """
        print("🔍 通过键盘状态检测输入焦点...")

        success, output = self._run_adb_command(["shell", "dumpsys", "input_method"])
        if not success:
            print(f"❌ 获取输入法状态失败: {output}")
            return False

        # 检查键盘可见性指标
        keyboard_indicators = [
            "mInputShown=true",
            "mIsInputViewShown=true",
            "mWindowVisible=true",
            "keyboardShown=true"
        ]

        for indicator in keyboard_indicators:
            if indicator in output:
                print(f"✅ 检测到键盘可见: {indicator}")
                return True

        print("❌ 未检测到键盘，可能无输入焦点")
        return False

    def input_text_segmented(self, text: str, segment_delay: float = 0.1) -> bool:
        """
        分段输入文本

        Args:
            text: 要输入的文本
            segment_delay: 每段之间的延迟（秒）

        Returns:
            输入是否成功
        """
        print(f"⌨️ 分段输入文本: '{text}'")

        try:
            # 将文本分割为更小的段，避免一次性输入过长
            max_segment_length = 10

            for i in range(0, len(text), max_segment_length):
                segment = text[i:i + max_segment_length]

                # 使用ADB输入文本段
                success, output = self._run_adb_command(["shell", "input", "text", segment])

                if not success:
                    print(f"❌ 输入文本段失败: '{segment}', 错误: {output}")
                    return False

                print(f"✅ 输入文本段: '{segment}'")

                # 段间延迟
                if segment_delay > 0 and i + max_segment_length < len(text):
                    time.sleep(segment_delay)

            print(f"✅ 文本输入完成: '{text}'")
            return True

        except Exception as e:
            print(f"❌ 输入文本失败: {e}")
            return False

    def clear_input_field(self) -> bool:
        """
        清空当前输入框

        Returns:
            清空是否成功
        """
        print("🗑️ 清空输入框...")

        try:
            # 先选择所有文本（Ctrl+A）
            success, output = self._run_adb_command(["shell", "input", "keyevent", "KEYCODE_CTRL_A"])

            if success:
                time.sleep(0.2)
                # 删除选中的文本
                success, output = self._run_adb_command(["shell", "input", "keyevent", "KEYCODE_DEL"])

            if success:
                print("✅ 输入框清空成功")
                return True
            else:
                print(f"❌ 输入框清空失败: {output}")
                return False

        except Exception as e:
            print(f"❌ 清空输入框失败: {e}")
            return False

    def click_input_field(self, bounds: str) -> bool:
        """
        点击输入框以获取焦点

        Args:
            bounds: 元素边界字符串，格式如"[x1,y1][x2,y2]"

        Returns:
            点击是否成功
        """
        print(f"👆 点击输入框获取焦点: {bounds}")

        try:
            # 解析边界坐标
            import re
            match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
            if not match:
                print(f"❌ 无法解析边界坐标: {bounds}")
                return False

            x1, y1, x2, y2 = map(int, match.groups())

            # 计算中心点
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2

            # 点击中心点
            success, output = self._run_adb_command(["shell", "input", "tap", str(center_x), str(center_y)])

            if success:
                print(f"✅ 输入框点击成功: ({center_x}, {center_y})")
                time.sleep(0.5)  # 等待焦点切换
                return True
            else:
                print(f"❌ 输入框点击失败: {output}")
                return False

        except Exception as e:
            print(f"❌ 点击输入框失败: {e}")
            return False

    def input_text_with_focus_detection(self, text: str, target_selector: Dict[str, Any]) -> bool:
        """
        综合焦点检测和文本输入

        Args:
            text: 要输入的文本
            target_selector: 目标选择器（包含placeholder等信息）

        Returns:
            输入是否成功
        """
        print(f"🎯 开始焦点检测和文本输入: '{text[:20]}{'...' if len(text) > 20 else ''}'")

        try:
            # 尝试通过placeholder检测焦点
            placeholder = target_selector.get('placeholder', '')
            input_field_info = None

            if placeholder:
                print(f"🔍 第一步: 尝试通过placeholder '{placeholder}' 检测焦点")
                input_field_info = self.detect_input_focus_by_placeholder(placeholder)

                if input_field_info:
                    # 如果找到输入框但未聚焦，尝试点击获取焦点
                    if not input_field_info.get('focused', False):
                        bounds = input_field_info.get('bounds', '')
                        if bounds and input_field_info.get('clickable', False):
                            print("🎯 输入框未聚焦，尝试点击获取焦点")
                            click_success = self.click_input_field(bounds)
                            if not click_success:
                                print("❌ 点击输入框失败，尝试键盘状态检测")
                                input_field_info = None
                        else:
                            print("❌ 输入框不可点击或无边界信息，尝试键盘状态检测")
                            input_field_info = None

            # 如果placeholder检测失败，使用键盘状态检测作为备用方案
            if not input_field_info:
                print("🔍 第二步: 使用键盘状态检测作为备用方案")
                has_keyboard_focus = self.detect_input_focus_by_keyboard()

                if not has_keyboard_focus:
                    print("❌ 未检测到键盘输入焦点，无法输入文本")
                    return False

                print("✅ 键盘状态检测成功，继续文本输入")

            # 清空现有输入（可选）
            clear_success = self.clear_input_field()
            if not clear_success:
                print("⚠️ 清空输入框失败，但继续尝试输入")

            # 执行文本输入
            input_success = self.input_text_segmented(text)

            if input_success:
                print("✅ 焦点检测和文本输入完成")
                return True
            else:
                print("❌ 文本输入失败")
                return False

        except Exception as e:
            print(f"❌ 焦点检测和文本输入过程中发生错误: {e}")
            return False


def test_input_handler():
    """测试输入处理器功能"""
    print("=== 输入处理器测试 ===")

    handler = InputHandler()

    # 测试键盘状态检测
    has_focus = handler.detect_input_focus_by_keyboard()
    print(f"键盘状态检测结果: {'有焦点' if has_focus else '无焦点'}")

    # 测试placeholder检测
    placeholder_result = handler.detect_input_focus_by_placeholder("用户名")
    if placeholder_result:
        print(f"Placeholder检测结果: {placeholder_result}")
    else:
        print("未找到匹配的placeholder")


if __name__ == "__main__":
    test_input_handler()
