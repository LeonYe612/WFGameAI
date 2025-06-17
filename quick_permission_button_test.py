#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
权限按钮综合点击测试
测试三种点击方式：坐标点击、resource_id点击、文本点击
集成权限管理器功能，提供完整的权限处理解决方案
"""

import subprocess
import time
import os
import sys
import json
import xml.etree.ElementTree as ET

# 添加项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = current_dir
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'wfgame-ai-server', 'apps', 'scripts'))

class PermissionButtonTester:
    """权限按钮测试器 - 集成权限管理器功能"""

    def __init__(self, device_id: str = "5c41023b"):
        self.device_id = device_id
        self.permission_manager = None
        self.setup_permission_manager()

    def setup_permission_manager(self):
        """初始化权限管理器"""
        try:
            # 尝试导入权限管理器
            from app_permission_manager import AppPermissionManager
            self.permission_manager = AppPermissionManager(device_id=self.device_id)
            self.log("✅ 权限管理器已初始化")
        except ImportError:
            self.log("⚠️ 权限管理器模块未找到，使用基础测试功能")
            self.permission_manager = None
        except Exception as e:
            self.log(f"⚠️ 权限管理器初始化失败: {e}")
            self.permission_manager = None

    def log(self, message: str):
        """日志输出"""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")

    def take_screenshot(self, name: str):
        """快速截图"""
        try:
            timestamp = int(time.time())
            remote_path = f"/sdcard/test_{name}_{timestamp}.png"
            local_path = f"ui_structure_analysis/test_{name}_{timestamp}.png"

            # 确保目录存在
            os.makedirs("ui_structure_analysis", exist_ok=True)

            # 截图并拉取
            subprocess.run(f"adb -s {self.device_id} shell screencap -p {remote_path}", shell=True, check=False)
            subprocess.run(f"adb -s {self.device_id} pull {remote_path} {local_path}", shell=True, check=False)
            subprocess.run(f"adb -s {self.device_id} shell rm {remote_path}", shell=True, check=False)

            self.log(f"📸 截图保存: {local_path}")
            return local_path
        except Exception as e:
            self.log(f"❌ 截图失败: {e}")
            return None

    def dump_current_ui(self):
        """获取当前UI结构"""
        try:
            timestamp = int(time.time())
            remote_path = f"/sdcard/ui_current_{timestamp}.xml"
            local_path = f"ui_structure_analysis/ui_current_{timestamp}.xml"

            # 确保目录存在
            os.makedirs("ui_structure_analysis", exist_ok=True)

            # dump UI并拉取
            result = subprocess.run(f"adb -s {self.device_id} shell uiautomator dump {remote_path}",
                                  shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                subprocess.run(f"adb -s {self.device_id} pull {remote_path} {local_path}",
                             shell=True, check=False)
                subprocess.run(f"adb -s {self.device_id} shell rm {remote_path}",
                             shell=True, check=False)
                self.log(f"📄 UI结构保存: {local_path}")
                return local_path
            else:
                self.log(f"❌ UI dump失败: {result.stderr}")
                return None
        except Exception as e:
            self.log(f"❌ 获取UI结构失败: {e}")
            return None

    def test_click_by_bounds(self):
        """测试通过坐标点击"""
        self.log("\n🎯 测试方法1: 通过坐标点击")

        # 同意按钮的坐标范围: [554,2190][996,2252]
        # 计算中心点: (554+996)/2, (2190+2252)/2 = (775, 2221)
        x, y = 775, 2221

        self.log(f"📍 计算中心点坐标: ({x}, {y})")
        self.take_screenshot("before_bounds_click")

        try:
            cmd = f"adb -s {self.device_id} shell input tap {x} {y}"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

            if result.returncode == 0:
                self.log("✅ 坐标点击命令执行成功")
                time.sleep(2)  # 等待界面响应
                self.take_screenshot("after_bounds_click")
                self.dump_current_ui()
                return True
            else:
                self.log(f"❌ 坐标点击失败: {result.stderr}")
                return False

        except Exception as e:
            self.log(f"❌ 坐标点击异常: {e}")
            return False

    def test_click_by_resource_id(self):
        """测试通过resource_id点击（间接方式）"""
        self.log("\n🆔 测试方法2: 通过resource_id查找并点击")

        # resource_id: com.beeplay.card2prepare:id/tv_ok
        resource_id = "com.beeplay.card2prepare:id/tv_ok"

        self.log(f"🔍 查找resource_id: {resource_id}")
        self.take_screenshot("before_resource_click")

        try:
            # 先获取UI结构
            ui_file = self.dump_current_ui()
            if not ui_file:
                self.log("❌ 无法获取UI结构")
                return False

            # 解析XML查找元素
            tree = ET.parse(ui_file)
            root = tree.getroot()

            def find_element(node):
                if node.get('resource-id') == resource_id:
                    bounds = node.get('bounds')
                    self.log(f"📍 找到元素bounds: {bounds}")
                    return bounds
                for child in node:
                    result = find_element(child)
                    if result:
                        return result
                return None

            bounds = find_element(root)

            if bounds:
                # 解析bounds并点击
                bounds = bounds.strip('[]')
                parts = bounds.split('][')
                left_top = parts[0].split(',')
                right_bottom = parts[1].split(',')

                x1, y1 = int(left_top[0]), int(left_top[1])
                x2, y2 = int(right_bottom[0]), int(right_bottom[1])
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2

                self.log(f"📍 通过resource_id计算的中心点: ({center_x}, {center_y})")

                cmd = f"adb -s {self.device_id} shell input tap {center_x} {center_y}"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

                if result.returncode == 0:
                    self.log("✅ resource_id点击成功")
                    time.sleep(2)
                    self.take_screenshot("after_resource_click")
                    return True
                else:
                    self.log(f"❌ resource_id点击失败: {result.stderr}")
                    return False
            else:
                self.log(f"❌ 未找到resource_id为 {resource_id} 的元素")
                return False

        except Exception as e:
            self.log(f"❌ resource_id点击异常: {e}")
            return False

    def test_click_by_text(self):
        """测试通过文本点击（间接方式）"""
        self.log("\n📝 测试方法3: 通过文本查找并点击")

        target_text = "同意"
        self.log(f"🔍 查找文本: '{target_text}'")
        self.take_screenshot("before_text_click")

        try:
            # 先获取UI结构
            ui_file = self.dump_current_ui()
            if not ui_file:
                self.log("❌ 无法获取UI结构")
                return False

            # 解析XML查找文本元素
            tree = ET.parse(ui_file)
            root = tree.getroot()

            def find_text_element(node):
                if node.get('text') == target_text and node.get('clickable') == 'true':
                    bounds = node.get('bounds')
                    self.log(f"📍 找到文本元素bounds: {bounds}")
                    return bounds
                for child in node:
                    result = find_text_element(child)
                    if result:
                        return result
                return None

            bounds = find_text_element(root)

            if bounds:
                # 解析bounds并点击
                bounds = bounds.strip('[]')
                parts = bounds.split('][')
                left_top = parts[0].split(',')
                right_bottom = parts[1].split(',')

                x1, y1 = int(left_top[0]), int(left_top[1])
                x2, y2 = int(right_bottom[0]), int(right_bottom[1])
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2

                self.log(f"📍 通过文本计算的中心点: ({center_x}, {center_y})")

                cmd = f"adb -s {self.device_id} shell input tap {center_x} {center_y}"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

                if result.returncode == 0:
                    self.log("✅ 文本点击成功")
                    time.sleep(2)
                    self.take_screenshot("after_text_click")
                    return True
                else:
                    self.log(f"❌ 文本点击失败: {result.stderr}")
                    return False
            else:
                self.log(f"❌ 未找到文本为 '{target_text}' 的可点击元素")
                return False

        except Exception as e:
            self.log(f"❌ 文本点击异常: {e}")
            return False

    def test_permission_manager_click(self):
        """测试使用权限管理器点击"""
        self.log("\n🎯 测试方法4: 使用权限管理器点击")

        if not self.permission_manager:
            self.log("❌ 权限管理器未初始化，跳过测试")
            return False

        self.take_screenshot("before_pm_click")

        try:
            # 检测权限对话框
            has_permission = self.permission_manager.check_permission_dialog()
            self.log(f"权限对话框检测: {'✅ 发现' if has_permission else '❌ 未发现'}")

            if has_permission:
                # 处理权限
                result = self.permission_manager.handle_permission_dialog()
                self.log(f"权限处理结果: {'✅ 成功' if result else '❌ 失败'}")

                if result:
                    time.sleep(2)
                    self.take_screenshot("after_pm_click")
                    return True

            return False

        except Exception as e:
            self.log(f"❌ 权限管理器点击异常: {e}")
            return False

    def test_enhanced_button_scoring(self):
        """测试增强的按钮评分算法"""
        self.log("\n📊 测试增强的按钮评分算法")

        try:
            # 获取UI并分析按钮
            ui_file = self.dump_current_ui()
            if not ui_file:
                return False

            # 分析按钮元素
            xml_content = open(ui_file, 'r', encoding='utf-8').read()

            # 模拟评分过程
            self.log("🔍 正在分析当前界面的按钮元素...")

            root = ET.fromstring(xml_content)

            button_candidates = []

            def analyze_element(node):
                text = node.get('text', '').strip()
                clickable = node.get('clickable', 'false') == 'true'
                class_name = node.get('class', '').split('.')[-1]
                bounds = node.get('bounds', '')

                if text and clickable:
                    # 计算评分
                    score = 0

                    # 精确匹配
                    if text in ["同意", "确定", "允许", "OK"]:
                        score += 2000

                    # 文本长度检查
                    if len(text) <= 8:
                        score += 1000
                    elif len(text) > 30:
                        score -= 500

                    # 类型评分
                    if 'Button' in class_name:
                        score += 300
                    elif 'TextView' in class_name and len(text) <= 5:
                        score += 150

                    # 大小评分
                    if bounds:
                        try:
                            bounds_clean = bounds.strip('[]')
                            parts = bounds_clean.split('][')
                            if len(parts) == 2:
                                left_top = parts[0].split(',')
                                right_bottom = parts[1].split(',')
                                x1, y1 = int(left_top[0]), int(left_top[1])
                                x2, y2 = int(right_bottom[0]), int(right_bottom[1])
                                area = (x2 - x1) * (y2 - y1)
                                if area > 100000:
                                    penalty = min(1000, int(area / 200))
                                    score = max(0, score - penalty)
                        except:
                            pass

                    button_candidates.append({
                        'text': text,
                        'class': class_name,
                        'score': score,
                        'bounds': bounds
                    })

                for child in node:
                    analyze_element(child)

            analyze_element(root)

            # 排序并显示结果
            button_candidates.sort(key=lambda x: x['score'], reverse=True)

            self.log(f"📈 找到 {len(button_candidates)} 个按钮候选:")
            for i, btn in enumerate(button_candidates[:5]):  # 显示前5个
                self.log(f"   {i+1}. '{btn['text']}' - 分数: {btn['score']} - 类型: {btn['class']}")

            return len(button_candidates) > 0

        except Exception as e:
            self.log(f"❌ 评分算法测试异常: {e}")
            return False

    def run_all_tests(self):
        """运行所有测试"""
        self.log("🚀 开始权限按钮综合测试")
        self.log("=" * 50)

        # 测试前状态
        self.log("📋 获取测试前状态")
        self.take_screenshot("initial_state")
        self.dump_current_ui()

        results = {}

        # 测试1: 坐标点击
        results['bounds'] = self.test_click_by_bounds()
        time.sleep(3)

        # 测试2: resource_id点击
        results['resource_id'] = self.test_click_by_resource_id()
        time.sleep(3)

        # 测试3: 文本点击
        results['text'] = self.test_click_by_text()
        time.sleep(3)

        # 测试4: 权限管理器点击 (如果可用)
        results['permission_manager'] = self.test_permission_manager_click()
        time.sleep(3)

        # 测试5: 增强评分算法
        results['scoring_algorithm'] = self.test_enhanced_button_scoring()

        # 显示测试结果
        self.log("\n📊 综合测试结果汇总:")
        self.log("=" * 40)
        self.log(f"坐标点击:       {'✅ 成功' if results['bounds'] else '❌ 失败'}")
        self.log(f"resource_id:    {'✅ 成功' if results['resource_id'] else '❌ 失败'}")
        self.log(f"文本点击:       {'✅ 成功' if results['text'] else '❌ 失败'}")
        self.log(f"权限管理器:     {'✅ 成功' if results['permission_manager'] else '❌ 失败'}")
        self.log(f"评分算法:       {'✅ 成功' if results['scoring_algorithm'] else '❌ 失败'}")

        success_count = sum(results.values())
        total_tests = len(results)
        self.log(f"\n🎯 总成功率: {success_count}/{total_tests} ({success_count/total_tests*100:.0f}%)")

        # 保存测试结果
        self.save_test_results(results)

        return results

    def save_test_results(self, results):
        """保存测试结果到JSON文件"""
        try:
            os.makedirs("ui_structure_analysis", exist_ok=True)
            timestamp = int(time.time())
            filename = f"ui_structure_analysis/comprehensive_test_results_{timestamp}.json"

            test_summary = {
                "test_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "device_id": self.device_id,
                "test_results": results,
                "success_rate": f"{sum(results.values())}/{len(results)}",
                "permission_manager_available": self.permission_manager is not None
            }

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(test_summary, f, ensure_ascii=False, indent=2)

            self.log(f"💾 测试结果已保存到: {filename}")

        except Exception as e:
            self.log(f"❌ 保存测试结果失败: {e}")

def main():
    """主函数"""
    print("🧪 权限按钮综合点击测试")
    print("测试按钮: '同意' (com.beeplay.card2prepare:id/tv_ok)")
    print("坐标范围: [554,2190][996,2252]")
    print("集成权限管理器功能，提供完整的权限处理解决方案")
    print()

    # 允许用户指定设备ID
    device_id = "5c41023b"  # 默认设备ID
    if len(sys.argv) > 1:
        device_id = sys.argv[1]
        print(f"📱 使用指定设备: {device_id}")
    else:
        print(f"📱 使用默认设备: {device_id}")

    # 创建测试器并运行
    tester = PermissionButtonTester(device_id)
    results = tester.run_all_tests()

    print("\n✅ 测试完成！所有文件已保存到 ui_structure_analysis 目录")

if __name__ == "__main__":
    main()
