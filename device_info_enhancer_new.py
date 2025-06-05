#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设备信息增强工具
优化设备型号显示，提供商品名映射和品牌识别功能
"""

import json
import os
import re
import subprocess
from typing import Dict, Optional, Tuple, Union


class DeviceInfoEnhancer:
    """设备信息增强器"""

    def __init__(self, mapping_file_path: Optional[str] = None):
        """初始化设备信息增强器"""
        if mapping_file_path is None:
            mapping_file_path = os.path.join(os.path.dirname(__file__), 'device_model_mapping.json')

        self.mapping_file_path = mapping_file_path
        self.device_mapping = self._load_device_mapping()

    def _load_device_mapping(self) -> Dict:
        """加载设备型号映射数据"""
        try:
            if os.path.exists(self.mapping_file_path):
                with open(self.mapping_file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                print(f"警告: 设备映射文件不存在: {self.mapping_file_path}")
                return self._get_default_mapping()
        except Exception as e:
            print(f"加载设备映射文件失败: {e}")
            return self._get_default_mapping()

    def _get_default_mapping(self) -> Dict:
        """获取默认的设备映射数据"""
        return {
            "device_model_mapping": {},
            "brand_mapping": {
                "vivo": "vivo",
                "OPPO": "OPPO",
                "HUAWEI": "HUAWEI",
                "Xiaomi": "Xiaomi",
                "samsung": "samsung"
            },
            "fallback_detection": {
                "model_patterns": {}
            }
        }

    def enhance_device_info(self, device_id: str, raw_model: Optional[str] = None, raw_brand: Optional[str] = None) -> Dict:
        """增强设备信息，返回包含商品名的完整信息"""
        try:
            # 获取基础设备信息
            if not raw_model or not raw_brand:
                detected_model, detected_brand = self._detect_device_info(device_id)
                raw_model = raw_model or detected_model
                raw_brand = raw_brand or detected_brand

            # 查找商品名映射（优先使用设备ID映射，然后使用型号映射）
            commercial_info = self._get_commercial_info_by_device_id(device_id, raw_model, raw_brand)

            # 获取商品名（型号字段应显示商品名，如S16）
            full_commercial_name = commercial_info.get('commercial_name', raw_model)

            # 品牌字段优先使用映射配置中的正确品牌，否则使用原始检测的品牌
            mapped_brand = commercial_info.get('brand')
            brand_display = mapped_brand or raw_brand or 'Unknown'

            # 如果商品名包含品牌，提取型号部分用于型号字段显示
            if full_commercial_name and brand_display and full_commercial_name.startswith(brand_display):
                model_display = full_commercial_name.replace(brand_display, '').strip()
            else:
                model_display = full_commercial_name

            return {
                'device_id': device_id,
                'raw_model': raw_model or 'Unknown',
                'raw_brand': raw_brand or 'Unknown',
                'commercial_name': model_display,  # 用于型号字段显示（如S16）
                'enhanced_brand': brand_display,   # 用于品牌字段显示（如OPPO，优先使用映射配置中的正确品牌）
                'series': commercial_info.get('series', '未知系列'),
                'category': commercial_info.get('category', '未知分类'),
                'display_name': f"{brand_display} {model_display}" if model_display else brand_display,
                'full_name': f"{brand_display} {full_commercial_name}" if full_commercial_name else brand_display
            }

        except Exception as e:
            print(f"增强设备信息失败 {device_id}: {e}")
            return self._get_fallback_info(device_id, raw_model, raw_brand)

    def _detect_device_info(self, device_id: str) -> Tuple[Optional[str], Optional[str]]:
        """通过ADB检测设备型号和品牌"""
        try:
            # 获取设备型号
            model_result = subprocess.run(
                f"adb -s {device_id} shell getprop ro.product.model",
                shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore'
            )
            model = model_result.stdout.strip() if model_result.returncode == 0 else None

            # 获取设备品牌
            brand_result = subprocess.run(
                f"adb -s {device_id} shell getprop ro.product.brand",
                shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore'
            )
            brand = brand_result.stdout.strip() if brand_result.returncode == 0 else None

            # 如果品牌为空，尝试获取厂商信息
            if not brand:
                manufacturer_result = subprocess.run(
                    f"adb -s {device_id} shell getprop ro.product.manufacturer",
                    shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore'
                )
                brand = manufacturer_result.stdout.strip() if manufacturer_result.returncode == 0 else None

            return model, brand

        except Exception as e:
            print(f"检测设备信息失败 {device_id}: {e}")
            return None, None

    def _get_commercial_info_by_device_id(self, device_id: str, model: Optional[str], brand: Optional[str]) -> Dict:
        """通过设备ID获取商品名信息"""
        device_mappings = self.device_mapping.get('device_model_mapping', {})

        # 首先尝试通过设备ID查找
        if device_id in device_mappings:
            return device_mappings[device_id]

        # 然后尝试通过型号查找
        return self._get_commercial_info(model, brand)

    def _get_commercial_info(self, model: Optional[str], brand: Optional[str]) -> Dict:
        """获取商品名信息"""
        device_mappings = self.device_mapping.get('device_model_mapping', {})

        # 首先尝试通过型号查找
        if model and model in device_mappings:
            return device_mappings[model]

        # 模式匹配查找
        if model:
            fallback_patterns = self.device_mapping.get('fallback_detection', {}).get('model_patterns', {})
            for pattern, info in fallback_patterns.items():
                if re.match(pattern, model):
                    return {
                        'commercial_name': f"{info.get('brand', brand)} {model}",
                        'brand': info.get('brand', brand),
                        'series': info.get('series', '未知系列'),
                        'category': '智能手机'
                    }

        # 无匹配时的回退
        return {
            'commercial_name': f"{brand} {model}" if brand else model,
            'brand': brand or '未知品牌',
            'series': '未知系列',
            'category': '未知分类'
        }

    def _get_fallback_info(self, device_id: str, raw_model: Optional[str], raw_brand: Optional[str]) -> Dict:
        """获取回退信息"""
        return {
            'device_id': device_id,
            'raw_model': raw_model or 'Unknown',
            'raw_brand': raw_brand or 'Unknown',
            'commercial_name': raw_model or 'Unknown',
            'enhanced_brand': raw_brand or 'Unknown',
            'series': '未知系列',
            'category': '未知分类',
            'display_name': f"{raw_brand} {raw_model}" if raw_brand and raw_model else 'Unknown Device',
            'full_name': f"{raw_brand} {raw_model}" if raw_brand and raw_model else 'Unknown Device'
        }

    def enhance_batch_devices(self, devices: list) -> list:
        """批量增强设备信息"""
        enhanced_devices = []
        for device in devices:
            if isinstance(device, dict):
                device_id = device.get('device_id') or device.get('id')
                if not device_id:
                    enhanced_devices.append(device)
                    continue

                raw_model = device.get('model') or device.get('raw_model')
                raw_brand = device.get('brand') or device.get('raw_brand')

                enhanced_info = self.enhance_device_info(device_id, raw_model, raw_brand)

                # 合并原设备信息和增强信息
                enhanced_device = {**device, **enhanced_info}
                enhanced_devices.append(enhanced_device)
            else:
                enhanced_devices.append(device)

        return enhanced_devices

    def update_mapping_file(self, new_mappings: Dict):
        """更新映射文件"""
        try:
            # 合并新映射到现有映射
            device_mappings = self.device_mapping.get('device_model_mapping', {})
            device_mappings.update(new_mappings)

            # 更新内存中的映射
            self.device_mapping['device_model_mapping'] = device_mappings

            # 保存到文件
            with open(self.mapping_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.device_mapping, f, ensure_ascii=False, indent=2)

            print(f"成功更新设备映射文件: {self.mapping_file_path}")
            return True

        except Exception as e:
            print(f"更新映射文件失败: {e}")
            return False

    def get_device_info(self, device_id: str) -> Dict:
        """获取设备的完整信息"""
        return self.enhance_device_info(device_id)

    def print_device_info(self, device_id: str):
        """打印设备信息（用于调试）"""
        info = self.get_device_info(device_id)
        print(f"\n设备信息 ({device_id}):")
        print(f"  原始型号: {info['raw_model']}")
        print(f"  原始品牌: {info['raw_brand']}")
        print(f"  商品名: {info['commercial_name']}")
        print(f"  增强品牌: {info['enhanced_brand']}")
        print(f"  系列: {info['series']}")
        print(f"  分类: {info['category']}")
        print(f"  显示名称: {info['display_name']}")
        print(f"  完整名称: {info['full_name']}")


def test_device_enhancer():
    """测试设备信息增强器"""
    print("开始测试设备信息增强器...")

    enhancer = DeviceInfoEnhancer()

    # 测试数据
    test_devices = [
        {'device_id': 'test1', 'model': 'V2244A', 'brand': 'vivo'},
        {'device_id': 'test2', 'model': 'KB2000', 'brand': 'OnePlus'},  # 应该映射为OPPO
        {'device_id': 'test3', 'model': 'NOH-AL10', 'brand': 'HUAWEI'},
        {'device_id': 'test4', 'model': '22041216C', 'brand': 'Redmi'},  # 应该映射为Xiaomi
        {'device_id': '5c41023b', 'model': '', 'brand': 'OnePlus'},  # 实际案例：应该映射为OPPO
        {'device_id': '65WGZT7P9XHEKN7D', 'model': '', 'brand': 'Redmi'},  # 实际案例：应该映射为Xiaomi
    ]

    print("\n测试设备信息增强:")
    for device in test_devices:
        print(f"\n--- 测试设备: {device['device_id']} ---")
        print(f"输入: 型号={device['model']}, 品牌={device['brand']}")

        enhanced_info = enhancer.enhance_device_info(
            device['device_id'],
            device['model'],
            device['brand']
        )

        print(f"输出: 商品名={enhanced_info['commercial_name']}, 增强品牌={enhanced_info['enhanced_brand']}")
        print(f"      系列={enhanced_info['series']}, 显示名称={enhanced_info['display_name']}")


if __name__ == "__main__":
    test_device_enhancer()
