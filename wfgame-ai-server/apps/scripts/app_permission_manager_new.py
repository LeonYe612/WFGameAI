#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# @Time    : 2025/7/3 14:21
# @Author  : Hbuker
# @Email   : 15190300361@163.com
# @File    : app_permission_manager_new.py
# @desc    : 使用 Airtest Poco 的权限弹窗管理器

import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from poco.drivers.android.uiautomation import AndroidUiautomationPoco
from airtest.core.api import connect_device, device
from poco.exceptions import PocoNoSuchNodeException, PocoTargetTimeout

from app_permission_patterns import *

logger = logging.getLogger(__name__)


@dataclass
class PermissionDialog:
    """权限弹窗信息"""
    permission_type: str  # camera, microphone, storage, location, etc.
    dialog_title: str
    dialog_message: str
    available_actions: List[PermissionAction]
    recommended_action: PermissionAction = PermissionAction.ALLOW


class PermissionDialogApi:
    def __init__(self, device_id: Optional[str] = None):
        self.device_id = device_id
        self.device = None
        self.poco = None
        self.patterns = AndroidPermissionPatterns()
        
        if self._setup_device() is None:
            raise Exception("设备连接失败")

    def _setup_device(self):
        """设置设备连接"""
        try:
            if self.device_id:
                # 指定设备连接
                device_uri = f"Android://127.0.0.1:5037/{self.device_id}"
                print(f"🔗 连接设备: {self.device_id}")
            else:
                # 默认设备连接
                device_uri = "Android:///"
                print("🔗 连接默认设备")

            connect_device(device_uri)
            self.device = device()

            # 初始化poco
            self.poco = AndroidUiautomationPoco(device=self.device)
            print("✅ 设备连接成功")
            return True

        except Exception as e:
            print(f"❌ 设备连接失败: {e}")
            return None

    def detect_permission_dialog(self) -> Optional[PermissionDialog]:
        """检测当前屏幕是否有权限弹窗 - 带重试机制"""
        max_attempts = 2
        
        for attempt in range(max_attempts):
            try:
                print(f"🔍 开始检测权限弹窗 (第{attempt + 1}次)")
                
                # 获取当前UI层次结构
                ui_dump = self._get_ui_dump()
                if not ui_dump:
                    print(f"⚠️ 第{attempt + 1}次UI获取失败")
                    if attempt < max_attempts - 1:
                        time.sleep(0.5)
                        continue
                    
                    # 如果hierarchy.dump()失败，尝试简化检测
                    return self._simple_permission_detection()

                # 解析UI并查找权限弹窗
                result = self._parse_permission_dialog(ui_dump)
                if result:
                    print(f"✅ 检测到权限弹窗: {result.permission_type}")
                else:
                    print("ℹ️ 未检测到权限弹窗")
                    
                return result

            except Exception as e:
                logger.error(f"检测权限弹窗时出错 (第{attempt + 1}次): {e}")
                if attempt < max_attempts - 1:
                    print("⏳ 等待后重试...")
                    time.sleep(0.8)
                    continue
                    
        print("❌ 多次尝试后仍无法检测权限弹窗，尝试简化检测")
        return self._simple_permission_detection()

    def _simple_permission_detection(self) -> Optional[PermissionDialog]:
        """简化的权限检测方法 - 当hierarchy.dump()失败时使用"""
        try:
            logger.info("使用简化权限检测方法")
            
            # 直接查找常见的权限按钮
            permission_buttons_found = []
            
            # 检查允许按钮
            allow_texts = self.patterns.PERMISSION_BUTTON_PATTERNS[PermissionAction.ALLOW]['texts']
            for text in allow_texts[:3]:  # 只检查前3个最常见的
                try:
                    if self.poco(text=text).exists():
                        permission_buttons_found.append(PermissionAction.ALLOW)
                        logger.info(f"简化检测找到允许按钮: '{text}'")
                        break
                except:
                    continue
                    
            # 检查拒绝按钮
            deny_texts = self.patterns.PERMISSION_BUTTON_PATTERNS[PermissionAction.DENY]['texts'] 
            for text in deny_texts[:3]:
                try:
                    if self.poco(text=text).exists():
                        permission_buttons_found.append(PermissionAction.DENY)
                        logger.info(f"简化检测找到拒绝按钮: '{text}'")
                        break
                except:
                    continue
                    
            if permission_buttons_found:
                logger.info(f"简化检测成功，找到按钮: {[a.value for a in permission_buttons_found]}")
                return PermissionDialog(
                    permission_type="permission",
                    dialog_title="权限弹窗（简化检测）",
                    dialog_message="通过按钮检测到的权限弹窗",
                    available_actions=permission_buttons_found,
                    recommended_action=PermissionAction.ALLOW
                )
            else:
                logger.info("简化检测未找到权限按钮")
                return None
                
        except Exception as e:
            logger.error(f"简化权限检测失败: {e}")
            return None

    def _get_ui_dump(self) -> Optional[dict]:
        """获取设备UI层次结构 - 带重试机制"""
        max_retries = 3
        retry_delay = 0.5
        
        for attempt in range(max_retries):
            try:
                if not self.poco:
                    print("❌ Poco未初始化")
                    return None

                print(f"🔄 尝试获取UI结构 (第{attempt + 1}次)")
                
                # 在获取UI之前稍作等待，让界面稳定
                time.sleep(0.3)
                
                # 获取UI层次结构
                ui_dump = self.poco.agent.hierarchy.dump()
                print("✅ UI结构获取成功")
                print(f"📊 UI dump类型: {type(ui_dump)}")

                return ui_dump

            except Exception as e:
                print(f"❌ 获取UI层次结构失败 (第{attempt + 1}次): {e}")
                
                # 如果是NodeHasBeenRemovedException，说明界面在变化，稍等再试
                if "NodeHasBeenRemovedException" in str(e) or "Node was no longer alive" in str(e):
                    print("⏳ 界面正在变化，等待稳定后重试...")
                    time.sleep(retry_delay * (attempt + 1))  # 递增等待时间
                    continue
                else:
                    # 其他类型的错误，立即返回
                    print(f"❌ 非界面变化错误，停止重试: {e}")
                    return None
                    
        print("❌ 多次重试后仍无法获取UI结构")
        return None

    def _parse_permission_dialog(self, ui_dump: dict) -> Optional[PermissionDialog]:
        """解析UI dump，查找权限弹窗"""
        try:
            if not ui_dump or 'children' not in ui_dump:
                return None

            # 收集所有文本和可点击元素
            all_texts = []
            clickable_elements = []
            
            self._collect_elements_recursive(ui_dump, all_texts, clickable_elements)
            
            if not all_texts:
                logger.debug("未找到任何文本内容")
                return None

            # 检查是否是权限弹窗
            permission_dialog = self._analyze_permission_content(all_texts, clickable_elements)
            
            return permission_dialog

        except Exception as e:
            logger.error(f"解析权限弹窗失败: {e}")
            return None

    def _collect_elements_recursive(self, node: dict, all_texts: List[str], clickable_elements: List[dict]):
        """递归收集UI元素信息 - 增强异常处理"""
        try:
            # 收集当前节点信息
            attrs = node.get('attrs', {})
            
            # 安全获取属性，避免节点变化导致的异常
            text = attrs.get('text', '').strip() if attrs else ''
            clickable = attrs.get('clickable', False) if attrs else False
            package = attrs.get('package', '') if attrs else ''
            resource_id = attrs.get('resourceId', '') if attrs else ''
            class_name = attrs.get('className', '') if attrs else ''
            
            if text:
                all_texts.append(text)
                
            if clickable and text:
                clickable_elements.append({
                    'text': text,
                    'resource_id': resource_id,
                    'class_name': class_name,
                    'package': package,
                    'bounds': attrs.get('bounds', []) if attrs else [],
                    'pos': attrs.get('pos', []) if attrs else []
                })

            # 递归处理子节点
            children = node.get('children', [])
            if children:
                for child in children:
                    if child and isinstance(child, dict):  # 确保子节点有效
                        self._collect_elements_recursive(child, all_texts, clickable_elements)
                
        except Exception as e:
            logger.debug(f"收集元素信息失败: {e}")
            # 继续处理其他节点，不中断整个流程

    def _analyze_permission_content(self, all_texts: List[str], clickable_elements: List[dict]) -> Optional[PermissionDialog]:
        """分析内容，判断是否为权限弹窗"""
        try:
            combined_text = ' '.join(all_texts)
            logger.info(f"分析文本内容: {combined_text[:200]}...")
            
            # 1. 检查是否包含权限相关关键词
            has_permission_keywords = self._has_permission_keywords(combined_text)
            
            # 2. 检查是否为登录界面（排除）
            is_login_screen = self._is_login_screen(combined_text)
            
            if is_login_screen and not has_permission_keywords:
                logger.info("检测到登录界面，跳过权限处理")
                return None
                
            if not has_permission_keywords:
                logger.debug("未检测到权限相关关键词")
                return None
                
            # 3. 识别权限类型
            permission_type = self._identify_permission_type(all_texts)
            
            # 4. 识别可用操作
            available_actions = self._identify_available_actions(clickable_elements)
            
            if not available_actions:
                logger.debug("未找到可用的权限操作按钮")
                return None
                
            logger.info(f"检测到权限弹窗 - 类型: {permission_type}, 操作: {[a.value for a in available_actions]}")
            
            return PermissionDialog(
                permission_type=permission_type,
                dialog_title="权限弹窗",
                dialog_message=combined_text[:100] + "...",
                available_actions=available_actions,
                recommended_action=PermissionAction.ALLOW
            )
            
        except Exception as e:
            logger.error(f"分析权限内容失败: {e}")
            return None

    def _has_permission_keywords(self, text: str) -> bool:
        """检查是否包含权限相关关键词"""
        text_lower = text.lower()
        
        # 检查权限相关关键词
        permission_keywords = (
            self.patterns.APP_CUSTOM_DIALOG_KEYWORDS + 
            self.patterns.PRIVACY_POLICY_KEYWORDS + 
            self.patterns.PERMISSION_REQUEST_KEYWORDS
        )
        
        for keyword in permission_keywords:
            if keyword.lower() in text_lower:
                return True
                
        # 检查权限按钮文本
        for action, patterns in self.patterns.PERMISSION_BUTTON_PATTERNS.items():
            for button_text in patterns['texts']:
                if button_text.lower() in text_lower:
                    return True
                    
        return False

    def _is_login_screen(self, text: str) -> bool:
        """检查是否为登录界面"""
        text_lower = text.lower()
        
        login_count = 0
        for keyword in self.patterns.GAME_LOGIN_KEYWORDS:
            if keyword.lower() in text_lower:
                login_count += 1
                
        # 如果包含多个登录关键词，很可能是登录界面
        return login_count >= 2

    def _identify_permission_type(self, texts: List[str]) -> str:
        """识别权限类型"""
        combined_text = ' '.join(texts).lower()

        if any(keyword.lower() in combined_text for keyword in self.patterns.PRIVACY_POLICY_KEYWORDS):
            return "privacy_policy"
        elif any(keyword.lower() in combined_text for keyword in self.patterns.PERMISSION_REQUEST_KEYWORDS):
            return "app_permission"
        else:
            return "permission"

    def _identify_available_actions(self, clickable_elements: List[dict]) -> List[PermissionAction]:
        """识别可用的权限操作"""
        actions = []
        
        logger.info(f"分析 {len(clickable_elements)} 个可点击元素")
        
        for element in clickable_elements:
            text = element['text'].strip()
            resource_id = element.get('resource_id', '')
            
            logger.debug(f"分析按钮: '{text}', resource_id: '{resource_id}'")
            
            # 遍历所有操作类型进行匹配
            for action, patterns in self.patterns.PERMISSION_BUTTON_PATTERNS.items():
                matched = False
                
                # 文本匹配
                for text_pattern in patterns['texts']:
                    if text == text_pattern:
                        actions.append(action)
                        matched = True
                        logger.info(f"文本匹配: '{text}' -> {action.value}")
                        break
                        
                # Resource ID匹配
                if not matched and resource_id:
                    for resource_pattern in patterns['resource_ids']:
                        if resource_id == resource_pattern:
                            actions.append(action)
                            matched = True
                            logger.info(f"Resource ID匹配: '{resource_id}' -> {action.value}")
                            break
                            
                if matched:
                    break
                    
        return list(set(actions))  # 去重

    def click_permission_button(self, action: PermissionAction) -> bool:
        """点击权限按钮 - 增强稳定性"""
        try:
            if not self.poco:
                logger.error("Poco未初始化")
                return False
                
            patterns = self.patterns.PERMISSION_BUTTON_PATTERNS.get(action, {})
            target_texts = patterns.get('texts', [])
            target_resource_ids = patterns.get('resource_ids', [])
            
            logger.info(f"尝试点击 {action.value} 按钮")
            
            # 方法1: 通过文本点击
            for text in target_texts:
                try:
                    # 等待元素出现
                    time.sleep(0.2)
                    
                    element = self.poco(text=text)
                    if element.exists():
                        logger.info(f"找到文本按钮: '{text}'")
                        element.click()
                        time.sleep(1.0)  # 增加等待时间
                        
                        # 验证点击是否成功（元素是否消失）
                        if not element.exists():
                            logger.info(f"✅ 文本点击成功，按钮已消失")
                            return True
                        else:
                            logger.info(f"⚠️ 按钮点击后仍存在，可能点击未生效")
                            
                except PocoNoSuchNodeException:
                    continue
                except Exception as e:
                    logger.debug(f"文本点击失败: {e}")
                    continue
                    
            # 方法2: 通过resource_id点击
            for resource_id in target_resource_ids:
                try:
                    time.sleep(0.2)
                    
                    element = self.poco(resourceId=resource_id)
                    if element.exists():
                        logger.info(f"找到resource_id按钮: '{resource_id}'")
                        element.click()
                        time.sleep(1.0)
                        
                        if not element.exists():
                            logger.info(f"✅ Resource ID点击成功，按钮已消失")
                            return True
                            
                except PocoNoSuchNodeException:
                    continue
                except Exception as e:
                    logger.debug(f"Resource ID点击失败: {e}")
                    continue
                    
            # 方法3: 模糊匹配点击
            for text in target_texts:
                try:
                    time.sleep(0.2)
                    
                    # 查找包含目标文本的元素
                    elements = self.poco(textMatches=f".*{text}.*")
                    for element in elements:
                        if element.exists():
                            logger.info(f"模糊匹配找到按钮: '{text}'")
                            element.click()
                            time.sleep(1.0)
                            
                            if not element.exists():
                                logger.info(f"✅ 模糊匹配点击成功")
                                return True
                                
                except Exception as e:
                    logger.debug(f"模糊匹配点击失败: {e}")
                    continue
                    
            # 方法4: 查找所有可点击元素，匹配文本
            try:
                logger.info("尝试遍历所有可点击元素...")
                clickable_elements = self.poco("android.widget.TextView").filter(lambda elem: elem.attr("clickable") == True)
                
                for element in clickable_elements:
                    try:
                        elem_text = element.get_text()
                        if elem_text in target_texts:
                            logger.info(f"遍历找到匹配按钮: '{elem_text}'")
                            element.click()
                            time.sleep(1.0)
                            return True
                    except:
                        continue
                        
            except Exception as e:
                logger.debug(f"遍历点击失败: {e}")
                    
            logger.warning(f"未能找到 {action.value} 按钮")
            return False
            
        except Exception as e:
            logger.error(f"点击权限按钮失败: {e}")
            return False

    def handle_permission_dialog(self, dialog: PermissionDialog, auto_allow: bool = True) -> bool:
        """处理权限弹窗"""
        try:
            target_action = PermissionAction.ALLOW if auto_allow else PermissionAction.DENY
            
            # 如果目标操作不可用，选择备选操作
            if target_action not in dialog.available_actions:
                if dialog.available_actions:
                    # 按优先级选择
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
                    
            # 执行点击
            return self.click_permission_button(target_action)
            
        except Exception as e:
            logger.error(f"处理权限弹窗失败: {e}")
            return False

    def wait_and_handle_permission_popups(self, max_popups: int = 3, timeout: int = 10) -> bool:
        """等待并处理权限弹窗 - 优化版"""
        logger.info(f"开始等待权限弹窗，最大处理数量: {max_popups}, 超时: {timeout}秒")
        
        handled_count = 0
        start_time = time.time()
        no_dialog_count = 0  # 连续无弹窗计数
        max_no_dialog = 3    # 连续3次无弹窗则退出
        
        while handled_count < max_popups and (time.time() - start_time) < timeout:
            try:
                elapsed = time.time() - start_time
                logger.info(f"权限检测轮次，已耗时: {elapsed:.1f}秒")
                
                # 检测权限弹窗
                dialog = self.detect_permission_dialog()
                
                if dialog:
                    no_dialog_count = 0  # 重置计数
                    logger.info(f"检测到权限弹窗: {dialog.permission_type}")
                    
                    # 处理权限弹窗
                    if self.handle_permission_dialog(dialog, auto_allow=True):
                        handled_count += 1
                        logger.info(f"成功处理权限弹窗 {handled_count}/{max_popups}")
                        
                        # 等待界面更新
                        time.sleep(1.5)
                    else:
                        logger.warning("权限弹窗处理失败")
                        # 即使处理失败也继续，可能是界面变化导致的
                        time.sleep(1.0)
                else:
                    no_dialog_count += 1
                    logger.debug(f"未检测到权限弹窗 (连续第{no_dialog_count}次)")
                    
                    # 连续多次无弹窗，提前退出
                    if no_dialog_count >= max_no_dialog:
                        logger.info(f"连续{max_no_dialog}次未检测到权限弹窗，提前结束")
                        break
                    
                    # 没有权限弹窗，短暂等待
                    time.sleep(1.0)
                    
            except Exception as e:
                logger.error(f"权限处理异常: {e}")
                time.sleep(1.0)
                
        total_time = time.time() - start_time
        logger.info(f"权限处理完成，共处理 {handled_count} 个弹窗，耗时 {total_time:.1f}秒")
        return True  # 即使没有处理到弹窗也返回True，避免阻塞主流程


def integrate_with_app_launch(device_id: Optional[str] = None, auto_allow: bool = True) -> bool:
    """与应用启动流程集成的权限处理函数"""
    try:
        logger.info(f"开始权限处理 - 设备: {device_id}")
        
        permission_api = PermissionDialogApi(device_id)
        result = permission_api.wait_and_handle_permission_popups(max_popups=3, timeout=8)
        
        logger.info(f"权限处理完成，结果: {result}")
        return result
        
    except Exception as e:
        logger.warning(f"权限处理异常: {e}")
        logger.info("假设无权限弹窗，继续执行")
        return True


if __name__ == '__main__':
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    device_id = "A3UGVB3210002403"  # 替换为实际设备ID
    
    try:
        api = PermissionDialogApi(device_id)
        
        # 检测权限弹窗
        dialog = api.detect_permission_dialog()
        if dialog:
            print(f"检测到权限弹窗: {dialog}")
            
            # 处理权限弹窗
            success = api.handle_permission_dialog(dialog)
            print(f"权限处理结果: {'成功' if success else '失败'}")
        else:
            print("没有检测到权限弹窗")
            
        # 或者使用集成函数
        # result = integrate_with_app_launch(device_id)
        # print(f"集成权限处理结果: {'成功' if result else '失败'}")
        
    except Exception as e:
        print(f"运行失败: {e}")
