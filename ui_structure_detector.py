#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI结构检测器
用于检测连接设备的UI结构并打印详细信息
支持多种检测方式：UIAutomator XML dump、截图分析、布局分析等
"""

import subprocess
import json
import time
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Any, Optional
import argparse
os.environ['PYTHONIOENCODING'] = 'utf-8'
try:
    from adbutils import adb
    ADB_UTILS_AVAILABLE = True
except ImportError:
    print("警告: adbutils未安装，将使用基础ADB命令")
    ADB_UTILS_AVAILABLE = False

try:
    from airtest.core.api import connect_device, device as current_device
    from airtest.core.android.adb import ADB
    AIRTEST_AVAILABLE = True
except ImportError:
    print("警告: Airtest未安装，将跳过Airtest相关功能")
    AIRTEST_AVAILABLE = False

class UIStructureDetector:
    """UI结构检测器"""

    def __init__(self, device_id: Optional[str] = None, save_files: bool = False):
        self.device_id = device_id
        self.output_dir = "ui_structure_analysis"
        self.save_files = save_files  # 新增参数：是否保存文件

        # 确保输出目录存在（总是创建，因为日志文件需要保存）
        self.ensure_output_dir()

        # 创建日志文件，解决终端中文显示问题
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file_path = os.path.join(self.output_dir, f"ui_detector_log_{timestamp}.txt")
        self.log_file = open(self.log_file_path, "w", encoding="utf-8")

        # 记录开始信息
        self.log("🚀 UI结构检测器启动")
        self.log(f"📝 详细日志文件: {self.log_file_path}")

    def log(self, message: str, show_in_terminal: bool = True):
        """统一的日志输出方法

        Args:
            message: 要输出的消息
            show_in_terminal: 是否在终端显示，默认True
        """
        # 总是写入日志文件
        self.log_file.write(message + "\n")
        self.log_file.flush()

        # 根据参数决定是否在终端显示
        if show_in_terminal:
            print(message)

    def close_log(self):
        """关闭日志文件"""
        if hasattr(self, 'log_file') and self.log_file:
            self.log_file.close()

    def __del__(self):
        """析构函数，确保日志文件被关闭"""
        self.close_log()

    def ensure_output_dir(self):
        """确保输出目录存在"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            self.log(f"📁 创建输出目录: {self.output_dir}")

    def get_connected_devices(self) -> List[str]:
        """获取所有连接的设备"""
        devices = []
        try:
            if ADB_UTILS_AVAILABLE:
                # 使用adbutils
                device_list = adb.device_list()
                for device in device_list:
                    if device.get_state() == "device":
                        devices.append(device.serial)
            else:
                # 使用基础ADB命令
                result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
                lines = result.stdout.strip().split('\n')[1:]
                for line in lines:
                    if line.strip() and '\t' in line:
                        parts = line.split('\t')
                        if len(parts) >= 2 and parts[1].strip() == 'device':
                            devices.append(parts[0].strip())
        except Exception as e:
            self.log(f"❌ 获取设备列表失败: {e}")

        return devices

    def dump_ui_hierarchy(self, device_id: str) -> Optional[str]:
        """获取UI层次结构XML"""
        self.log(f"🔍 正在获取设备 {device_id} 的UI层次结构...")

        try:
            # 使用uiautomator dump命令获取UI结构
            xml_path = f"/sdcard/ui_dump_{int(time.time())}.xml"

            # 在设备上执行UI dump
            dump_cmd = f"adb -s {device_id} shell uiautomator dump {xml_path}"
            result = subprocess.run(dump_cmd, shell=True, capture_output=True, text=True)

            if result.returncode != 0:
                self.log(f"❌ UI dump失败: {result.stderr}")
                return None

            # 只在需要保存文件时才拉取并保存XML
            if self.save_files:
                # 将XML文件拉取到本地
                local_xml_path = os.path.join(self.output_dir, f"ui_hierarchy_{device_id}_{int(time.time())}.xml")
                pull_cmd = f"adb -s {device_id} pull {xml_path} {local_xml_path}"
                pull_result = subprocess.run(pull_cmd, shell=True, capture_output=True, text=True)

                if pull_result.returncode != 0:
                    self.log(f"❌ 拉取XML文件失败: {pull_result.stderr}")
                    local_xml_path = None
                else:
                    self.log(f"✅ UI层次结构已保存到: {local_xml_path}")
            else:
                # 将XML文件拉取到临时目录，仅用于分析，不长期保存
                local_xml_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"temp_ui_{int(time.time())}.xml")
                pull_cmd = f"adb -s {device_id} pull {xml_path} {local_xml_path}"
                pull_result = subprocess.run(pull_cmd, shell=True, capture_output=True, text=True)

                if pull_result.returncode != 0:
                    self.log(f"❌ 拉取XML文件失败: {pull_result.stderr}")
                    local_xml_path = None
                else:
                    self.log(f"✅ UI层次结构已分析 (未保存)")

            # 清理设备上的临时文件
            subprocess.run(f"adb -s {device_id} shell rm {xml_path}", shell=True, check=False)

            return local_xml_path

        except Exception as e:
            self.log(f"❌ 获取UI层次结构失败: {e}")
            return None

    def parse_ui_hierarchy(self, xml_path: str) -> Dict[str, Any]:
        """解析UI层次结构XML"""
        self.log(f"📊 正在解析UI层次结构...")

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            ui_structure = {
                "timestamp": datetime.now().isoformat(),
                "xml_file": xml_path,
                "total_nodes": 0,
                "clickable_nodes": 0,
                "scrollable_nodes": 0,
                "text_nodes": 0,
                "input_nodes": 0,
                "elements": [],
                "hierarchy": self._parse_node(root)
            }

            # 统计各种类型的节点
            self._count_nodes(root, ui_structure)

            return ui_structure

        except Exception as e:
            self.log(f"❌ 解析UI层次结构失败: {e}")
            return {}

    def _parse_node(self, node: ET.Element, level: int = 0) -> Dict[str, Any]:
        """递归解析XML节点"""
        node_info = {
            "tag": node.tag,
            "level": level,
            "attributes": dict(node.attrib),
            "children": []
        }

        # 解析子节点
        for child in node:
            child_info = self._parse_node(child, level + 1)
            node_info["children"].append(child_info)

        return node_info

    def _count_nodes(self, node: ET.Element, stats: Dict[str, Any]):
        """统计节点信息"""
        stats["total_nodes"] += 1

        # 检查节点属性
        clickable = node.get("clickable", "false").lower() == "true"
        scrollable = node.get("scrollable", "false").lower() == "true"
        text = node.get("text", "").strip()
        class_name = node.get("class", "")

        if clickable:
            stats["clickable_nodes"] += 1

        if scrollable:
            stats["scrollable_nodes"] += 1

        if text:
            stats["text_nodes"] += 1

        if "EditText" in class_name or "edit" in class_name.lower():
            stats["input_nodes"] += 1

        # 提取重要元素信息
        if clickable or scrollable or text or "Button" in class_name:
            element_info = {
                "class": class_name,
                "text": text,
                "content_desc": node.get("content-desc", ""),
                "resource_id": node.get("resource-id", ""),
                "bounds": node.get("bounds", ""),
                "clickable": clickable,
                "scrollable": scrollable,
                "enabled": node.get("enabled", "false").lower() == "true",
                "focused": node.get("focused", "false").lower() == "true",
                "package": node.get("package", "")
            }
            stats["elements"].append(element_info)

        # 递归处理子节点
        for child in node:
            self._count_nodes(child, stats)
    def get_screen_info(self, device_id: str) -> Dict[str, Any]:
        """获取屏幕基本信息"""
        self.log(f"📱 正在获取设备 {device_id} 的屏幕信息...")

        screen_info = {
            "device_id": device_id,
            "timestamp": datetime.now().isoformat()
        }

        try:
            # 获取屏幕分辨率
            size_cmd = f"adb -s {device_id} shell wm size"
            size_result = subprocess.run(size_cmd, shell=True, capture_output=True, text=True)
            if size_result.returncode == 0:
                size_output = size_result.stdout.strip()
                if "Physical size:" in size_output:
                    resolution = size_output.split("Physical size:")[1].strip()
                    screen_info["resolution"] = resolution

            # 获取屏幕密度
            density_cmd = f"adb -s {device_id} shell wm density"
            density_result = subprocess.run(density_cmd, shell=True, capture_output=True, text=True)
            if density_result.returncode == 0:
                density_output = density_result.stdout.strip()
                if "Physical density:" in density_output:
                    density = density_output.split("Physical density:")[1].strip()
                    screen_info["density"] = density

            # 获取当前Activity
            activity_cmd = f"adb -s {device_id} shell dumpsys window windows | grep -E 'mCurrentFocus'"
            activity_result = subprocess.run(activity_cmd, shell=True, capture_output=True, text=True)
            if activity_result.returncode == 0:
                activity_output = activity_result.stdout.strip()
                screen_info["current_focus"] = activity_output

            # 获取设备信息
            model_cmd = f"adb -s {device_id} shell getprop ro.product.model"
            model_result = subprocess.run(model_cmd, shell=True, capture_output=True, text=True)
            if model_result.returncode == 0:
                screen_info["device_model"] = model_result.stdout.strip()

            # 获取Android版本
            version_cmd = f"adb -s {device_id} shell getprop ro.build.version.release"
            version_result = subprocess.run(version_cmd, shell=True, capture_output=True, text=True)
            if version_result.returncode == 0:
                screen_info["android_version"] = version_result.stdout.strip()

        except Exception as e:
            self.log(f"⚠️ 获取屏幕信息时出现错误: {e}")

        return screen_info

    def take_screenshot(self, device_id: str) -> Optional[str]:
        """截取屏幕截图"""
        self.log(f"📸 正在截取设备 {device_id} 的屏幕截图...")

        try:
            timestamp = int(time.time())
            remote_path = f"/sdcard/screenshot_{timestamp}.png"

            # 在设备上截图
            screencap_cmd = f"adb -s {device_id} shell screencap -p {remote_path}"
            result = subprocess.run(screencap_cmd, shell=True, capture_output=True, text=True)

            if result.returncode != 0:
                self.log(f"❌ 截图失败: {result.stderr}")
                return None

            # 只在需要保存文件时才执行保存操作
            if self.save_files:
                local_path = os.path.join(self.output_dir, f"screenshot_{device_id}_{timestamp}.png")

                # 拉取截图到本地
                pull_cmd = f"adb -s {device_id} pull {remote_path} {local_path}"
                pull_result = subprocess.run(pull_cmd, shell=True, capture_output=True, text=True)

                if pull_result.returncode != 0:
                    self.log(f"❌ 拉取截图失败: {pull_result.stderr}")
                    local_path = None
                else:
                    self.log(f"✅ 截图已保存到: {local_path}")
            else:
                local_path = None
                self.log(f"✅ 截图已捕获 (未保存)")

            # 清理设备上的临时文件
            subprocess.run(f"adb -s {device_id} shell rm {remote_path}", shell=True, check=False)

            return local_path

        except Exception as e:
            self.log(f"❌ 截图失败: {e}")
            return None

    def analyze_device_ui(self, device_id: str) -> Dict[str, Any]:
        """分析单个设备的UI结构"""
        print(f"\n🔬 开始分析设备 {device_id} 的UI结构")
        print("=" * 60)

        analysis_result = {
            "device_id": device_id,
            "analysis_time": datetime.now().isoformat(),
            "screen_info": {},
            "ui_structure": {},
            "screenshot_path": "",
            "xml_path": "",
            "summary": {}
        }

        # 1. 获取屏幕基本信息
        analysis_result["screen_info"] = self.get_screen_info(device_id)

        # 2. 截取屏幕截图
        screenshot_path = self.take_screenshot(device_id)
        if screenshot_path:
            analysis_result["screenshot_path"] = screenshot_path

        # 3. 获取UI层次结构
        xml_path = self.dump_ui_hierarchy(device_id)
        if xml_path:
            analysis_result["xml_path"] = xml_path
            analysis_result["ui_structure"] = self.parse_ui_hierarchy(xml_path)

            # 如果不保存文件但使用了临时XML文件，分析后删除
            if not self.save_files and os.path.exists(xml_path) and "temp_ui_" in xml_path:
                try:
                    os.remove(xml_path)
                except Exception:
                    pass

        # 4. 生成分析摘要
        self._generate_summary(analysis_result)

        return analysis_result

    def _generate_summary(self, analysis_result: Dict[str, Any]):
        """生成分析摘要"""
        ui_structure = analysis_result.get("ui_structure", {})

        summary = {
            "total_elements": ui_structure.get("total_nodes", 0),
            "interactive_elements": ui_structure.get("clickable_nodes", 0),
            "scrollable_elements": ui_structure.get("scrollable_nodes", 0),
            "text_elements": ui_structure.get("text_nodes", 0),
            "input_elements": ui_structure.get("input_nodes", 0),
            "unique_classes": len(set(elem.get("class", "") for elem in ui_structure.get("elements", []) if elem.get("class"))),
            "has_screenshot": bool(analysis_result.get("screenshot_path")),
            "has_xml": bool(analysis_result.get("xml_path"))
        }

        analysis_result["summary"] = summary

    def print_analysis_result(self, result: Dict[str, Any]):
        """打印分析结果"""
        device_id = result.get("device_id", "未知设备")
        print(f"\n📊 设备 {device_id} UI结构分析结果")
        print("=" * 60)

        # 打印设备基本信息
        screen_info = result.get("screen_info", {})
        print(f"📱 设备信息:")
        print(f"   设备ID: {device_id}")
        print(f"   设备型号: {screen_info.get('device_model', 'N/A')}")
        print(f"   Android版本: {screen_info.get('android_version', 'N/A')}")
        print(f"   屏幕分辨率: {screen_info.get('resolution', 'N/A')}")
        print(f"   屏幕密度: {screen_info.get('density', 'N/A')}")
        print(f"   当前焦点: {screen_info.get('current_focus', 'N/A')}")

        # 打印UI结构统计
        summary = result.get("summary", {})
        print(f"\n🎯 UI结构统计:")
        print(f"   总元素数量: {summary.get('total_elements', 0)}")
        print(f"   可交互元素: {summary.get('interactive_elements', 0)}")
        print(f"   可滚动元素: {summary.get('scrollable_elements', 0)}")
        print(f"   文本元素: {summary.get('text_elements', 0)}")
        print(f"   输入元素: {summary.get('input_elements', 0)}")
        print(f"   唯一类名数: {summary.get('unique_classes', 0)}")

        # 打印重要元素列表（前10个）
        ui_structure = result.get("ui_structure", {})
        elements = ui_structure.get("elements", [])
        if elements:
            print(f"\n🔍 主要UI元素 (显示前10个):")
            for i, element in enumerate(elements[:10]):
                class_name = element.get("class", "").split(".")[-1]  # 只显示类名的最后部分
                text = element.get("text", "")
                resource_id = element.get("resource_id", "").split("/")[-1] if element.get("resource_id") else ""

                print(f"   {i+1:2d}. {class_name}")
                if text:
                    print(f"       文本: '{text}'")
                if resource_id:
                    print(f"       ID: {resource_id}")
                if element.get("clickable"):
                    print(f"       属性: 可点击")
                if element.get("scrollable"):
                    print(f"       属性: 可滚动")
                print()

    def save_analysis_to_json(self, result: Dict[str, Any]):
        """保存分析结果到JSON文件"""
        if not self.save_files:
            print("💾 分析完成 (结果未保存)")
            return

        device_id = result.get("device_id", "unknown")
        timestamp = int(time.time())
        json_path = os.path.join(self.output_dir, f"ui_analysis_{device_id}_{timestamp}.json")

        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"💾 分析结果已保存到: {json_path}")
        except Exception as e:
            print(f"❌ 保存JSON文件失败: {e}")

    def run_analysis(self, target_device: Optional[str] = None):
        """运行UI结构分析"""
        print("🚀 启动UI结构检测器")
        print("=" * 60)

        # 获取连接的设备
        devices = self.get_connected_devices()
        if not devices:
            print("❌ 未发现连接的设备！")
            print("请确保：")
            print("1. 设备已通过USB连接")
            print("2. 设备已开启USB调试")
            print("3. 设备已授权调试权限")
            return

        print(f"🔍 发现 {len(devices)} 个连接的设备:")
        for i, device in enumerate(devices):
            print(f"   {i+1}. {device}")

        # 确定要分析的设备
        target_devices = []
        if target_device:
            if target_device in devices:
                target_devices = [target_device]
            else:
                print(f"❌ 指定的设备 {target_device} 未连接")
                return
        else:
            target_devices = devices

        # 分析每个目标设备
        for device_id in target_devices:
            try:
                result = self.analyze_device_ui(device_id)
                self.print_analysis_result(result)
                self.save_analysis_to_json(result)

                if len(target_devices) > 1:
                    print("\n" + "="*60)

            except Exception as e:
                print(f"❌ 分析设备 {device_id} 时出错: {e}")

        print(f"\n✅ UI结构检测完成！")
        if self.save_files:
            print(f"所有输出文件保存在: {os.path.abspath(self.output_dir)}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="UI结构检测器 - 检测连接设备的UI结构")
    parser.add_argument("--device", "-d", type=str, help="指定要分析的设备ID（如不指定则分析所有连接的设备）")
    parser.add_argument("--output", "-o", type=str, help="指定输出目录（默认: ui_structure_analysis）")
    parser.add_argument("--save", "-s", action="store_true", help="保存分析结果文件（默认不保存）")

    args = parser.parse_args()

    # 创建检测器实例
    detector = UIStructureDetector(save_files=args.save)

    # 设置输出目录
    if args.output:
        detector.output_dir = args.output
        if detector.save_files:
            detector.ensure_output_dir()

    # 运行分析
    detector.run_analysis(args.device)

if __name__ == "__main__":
    main()
