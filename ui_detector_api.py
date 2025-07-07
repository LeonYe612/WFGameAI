#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用UI检测器API包装器
提供简化的API接口，方便其他项目集成使用
"""

from typing import List, Dict, Any, Optional, Union
import tempfile
import os
from universal_ui_detector import UniversalUIDetector


class UIDetectorAPI:
    """通用UI检测器API - 简化接口"""

    def __init__(self,
                 save_files: bool = False,
                 output_dir: Optional[str] = None,
                 timeout: int = 60,
                 max_retries: int = 3):
        """
        初始化UI检测器API

        Args:
            save_files: 是否保存文件
            output_dir: 输出目录，None时使用临时目录
            timeout: 超时时间（秒）
            max_retries: 最大重试次数
        """
        self.save_files = save_files
        self.output_dir = output_dir or (tempfile.mkdtemp() if save_files else None)
        self.timeout = timeout
        self.max_retries = max_retries

    def list_devices(self) -> List[Dict[str, str]]:
        """
        获取连接的设备列表

        Returns:
            设备信息列表，每个设备包含serial, brand, model, android_version等信息
        """
        detector = UniversalUIDetector()
        devices = detector.get_connected_devices()

        # 简化返回信息
        return [{
            'serial': device['serial'],
            'brand': device.get('brand', 'unknown'),
            'model': device.get('model', 'unknown'),
            'android_version': device.get('android_version', 'unknown'),
            'manufacturer': device.get('manufacturer', 'unknown'),
            'resolution': device.get('resolution', 'unknown')
        } for device in devices]

    def take_screenshot(self, device_id: Optional[str] = None) -> Dict[str, Any]:
        """
        截取设备屏幕截图

        Args:
            device_id: 设备ID，None时使用第一个设备

        Returns:
            包含截图结果的字典
        """
        devices = self.list_devices()
        if not devices:
            return {"success": False, "error": "未发现连接的设备"}

        target_device = device_id or devices[0]['serial']

        detector = UniversalUIDetector(
            device_id=target_device,
            save_files=self.save_files,
            output_dir=self.output_dir,
            timeout=self.timeout,
            max_retries=self.max_retries
        )

        # 获取设备详细信息
        device_info = None
        for device in detector.get_connected_devices():
            if device['serial'] == target_device:
                device_info = device
                break

        if not device_info:
            return {"success": False, "error": f"设备 {target_device} 未找到"}

        try:
            screenshot_path = detector.take_screenshot(target_device, device_info)
            return {
                "success": bool(screenshot_path),
                "screenshot_path": screenshot_path,
                "device_id": target_device
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_ui_structure(self, device_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取设备UI结构

        Args:
            device_id: 设备ID，None时使用第一个设备

        Returns:
            包含UI结构的字典
        """
        devices = self.list_devices()
        if not devices:
            return {"success": False, "error": "未发现连接的设备"}

        target_device = device_id or devices[0]['serial']

        detector = UniversalUIDetector(
            device_id=target_device,
            save_files=self.save_files,
            output_dir=self.output_dir,
            timeout=self.timeout,
            max_retries=self.max_retries
        )

        # 获取设备详细信息
        device_info = None
        for device in detector.get_connected_devices():
            if device['serial'] == target_device:
                device_info = device
                break

        if not device_info:
            return {"success": False, "error": f"设备 {target_device} 未找到"}

        try:
            ui_hierarchy_path = detector.dump_ui_hierarchy(target_device, device_info)
            if ui_hierarchy_path:
                ui_structure = detector.parse_ui_hierarchy(ui_hierarchy_path)

                # 清理临时文件
                if not self.save_files and os.path.exists(ui_hierarchy_path):
                    try:
                        os.remove(ui_hierarchy_path)
                    except Exception:
                        pass

                return {
                    "success": True,
                    "device_id": target_device,
                    "ui_structure": ui_structure,
                    "xml_path": ui_hierarchy_path if self.save_files else None
                }
            else:
                return {"success": False, "error": "无法获取UI结构"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def analyze_device(self, device_id: Optional[str] = None) -> Dict[str, Any]:
        """
        完整分析设备（截图 + UI结构）

        Args:
            device_id: 设备ID，None时使用第一个设备

        Returns:
            包含完整分析结果的字典
        """
        devices = self.list_devices()
        if not devices:
            return {"success": False, "error": "未发现连接的设备"}

        target_device = device_id or devices[0]['serial']

        detector = UniversalUIDetector(
            device_id=target_device,
            save_files=self.save_files,
            output_dir=self.output_dir,
            timeout=self.timeout,
            max_retries=self.max_retries
        )

        # 获取设备详细信息
        device_info = None
        for device in detector.get_connected_devices():
            if device['serial'] == target_device:
                device_info = device
                break

        if not device_info:
            return {"success": False, "error": f"设备 {target_device} 未找到"}

        try:
            result = detector.analyze_device(device_info)
            return {
                "success": result["success"],
                "device_info": result["device_info"],
                "screenshot_path": result["screenshot_path"],
                "ui_hierarchy_path": result["ui_hierarchy_path"],
                "ui_structure": result["ui_structure"],
                "analysis_time": result["analysis_time"],
                "errors": result.get("errors", [])
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def find_elements_by_text(self, text: str, device_id: Optional[str] = None) -> Dict[str, Any]:
        """
        根据文本查找UI元素

        Args:
            text: 要查找的文本
            device_id: 设备ID

        Returns:
            包含匹配元素的字典
        """
        ui_result = self.get_ui_structure(device_id)
        if not ui_result["success"]:
            return ui_result

        ui_structure = ui_result["ui_structure"]
        elements = ui_structure.get("elements", [])

        # 查找包含指定文本的元素
        matching_elements = []
        for element in elements:
            element_text = element.get("text", "")
            if text.lower() in element_text.lower():
                matching_elements.append(element)

        return {
            "success": True,
            "device_id": ui_result["device_id"],
            "search_text": text,
            "matching_elements": matching_elements,
            "count": len(matching_elements)
        }

    def find_clickable_elements(self, device_id: Optional[str] = None) -> Dict[str, Any]:
        """
        查找所有可点击元素

        Args:
            device_id: 设备ID

        Returns:
            包含可点击元素的字典
        """
        ui_result = self.get_ui_structure(device_id)
        if not ui_result["success"]:
            return ui_result

        ui_structure = ui_result["ui_structure"]
        elements = ui_structure.get("elements", [])

        # 查找可点击元素
        clickable_elements = [e for e in elements if e.get("clickable")]

        return {
            "success": True,
            "device_id": ui_result["device_id"],
            "clickable_elements": clickable_elements,
            "count": len(clickable_elements)
        }

    def get_device_summary(self, device_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取设备UI摘要信息

        Args:
            device_id: 设备ID

        Returns:
            包含设备UI摘要的字典
        """
        ui_result = self.get_ui_structure(device_id)
        if not ui_result["success"]:
            return ui_result

        ui_structure = ui_result["ui_structure"]
        elements = ui_structure.get("elements", [])

        # 统计信息
        total_elements = ui_structure.get("total_nodes", 0)
        clickable_count = len([e for e in elements if e.get("clickable")])
        text_count = len([e for e in elements if e.get("text")])
        input_count = len([e for e in elements if "edit" in e.get("class", "").lower()])
        button_count = len([e for e in elements if "button" in e.get("class", "").lower()])

        # 主要文本内容
        main_texts = [e.get("text", "") for e in elements if e.get("text") and len(e.get("text", "")) > 5][:5]

        return {
            "success": True,
            "device_id": ui_result["device_id"],
            "summary": {
                "total_elements": total_elements,
                "clickable_elements": clickable_count,
                "text_elements": text_count,
                "input_elements": input_count,
                "button_elements": button_count,
                "main_texts": main_texts
            }
        }

    def batch_analyze(self, device_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        批量分析多个设备

        Args:
            device_ids: 设备ID列表，None时分析所有设备

        Returns:
            分析结果列表
        """
        devices = self.list_devices()
        if not devices:
            return [{"success": False, "error": "未发现连接的设备"}]

        target_devices = device_ids or [d['serial'] for d in devices]
        results = []

        for device_id in target_devices:
            result = self.analyze_device(device_id)
            results.append(result)

        return results


# 便捷函数 - 提供更简单的接口
def quick_screenshot(device_id: Optional[str] = None, save_file: bool = False) -> Dict[str, Any]:
    """快速截图"""
    api = UIDetectorAPI(save_files=save_file)
    return api.take_screenshot(device_id)


def quick_ui_analysis(device_id: Optional[str] = None) -> Dict[str, Any]:
    """快速UI分析"""
    api = UIDetectorAPI(save_files=False)
    return api.get_ui_structure(device_id)


def quick_find_text(text: str, device_id: Optional[str] = None) -> Dict[str, Any]:
    """快速文本查找"""
    api = UIDetectorAPI(save_files=False)
    return api.find_elements_by_text(text, device_id)


def quick_device_info() -> List[Dict[str, str]]:
    """快速获取设备信息"""
    api = UIDetectorAPI()
    return api.list_devices()


# 使用示例
if __name__ == "__main__":
    print("🚀 UI检测器API示例")
    print("=" * 50)

    # 创建API实例
    api = UIDetectorAPI(save_files=False)

    # 1. 获取设备列表
    print("📱 获取设备列表:")
    devices = api.list_devices()
    for device in devices:
        print(f"   - {device['serial']}: {device['brand']} {device['model']} (Android {device['android_version']})")

    if not devices:
        print("❌ 未发现设备")
        exit(1)

    # 2. 截图
    print(f"\n📸 截图设备:")
    screenshot_result = api.take_screenshot()
    print(f"   结果: {'✅ 成功' if screenshot_result['success'] else '❌ 失败'}")

    # 3. 获取UI结构
    print(f"\n🔍 获取UI结构:")
    ui_result = api.get_ui_structure()
    print(f"   结果: {'✅ 成功' if ui_result['success'] else '❌ 失败'}")

    if ui_result['success']:
        ui_structure = ui_result['ui_structure']
        print(f"   总元素: {ui_structure.get('total_nodes', 0)}")
        print(f"   可交互元素: {ui_structure.get('clickable_nodes', 0)}")

    # 4. 查找文本
    print(f"\n🔎 查找文本 '同意':")
    text_result = api.find_elements_by_text("同意")
    if text_result['success']:
        print(f"   找到 {text_result['count']} 个匹配元素")

    # 5. 获取摘要
    print(f"\n📊 设备摘要:")
    summary_result = api.get_device_summary()
    if summary_result['success']:
        summary = summary_result['summary']
        print(f"   可点击元素: {summary['clickable_elements']}")
        print(f"   按钮元素: {summary['button_elements']}")
        print(f"   输入元素: {summary['input_elements']}")

    print("\n✅ API示例完成!")
