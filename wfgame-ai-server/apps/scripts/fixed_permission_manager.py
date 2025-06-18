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
"""

import time
import subprocess
import logging
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

# 将现有的代码复制到这个文件，并修正_click_by_simplified_method函数的实现
# 完整的函数实现将替换旧版本

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
                                    logger.info(f"📏 理想按钮尺寸加分: +{size_score}")

                                # 4.3 过小元素惩罚 - 可能是图标或装饰元素
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
                        best_match = element

        # 找到最佳匹配的按钮
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
