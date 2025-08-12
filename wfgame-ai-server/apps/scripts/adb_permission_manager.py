#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
原生ADB UIAutomator权限管理器
不依赖Poco包，直接使用ADB命令
"""

import subprocess
import xml.etree.ElementTree as ET
import time
import logging
import re
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass

from app_permission_patterns import *

logger = logging.getLogger(__name__)


@dataclass
class PermissionDialog:
    """权限弹窗信息"""
    permission_type: str
    dialog_title: str
    dialog_message: str
    available_actions: List[PermissionAction]
    recommended_action: PermissionAction = PermissionAction.ALLOW


class NativeADBPermissionManager:
    """原生ADB权限管理器 - 不依赖Poco"""
    
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.patterns = AndroidPermissionPatterns()
        self.working_path = None  # 缓存可用路径
        self.device_info = self._get_device_info()
        
    def _get_device_info(self) -> Dict[str, str]:
        """获取设备信息用于路径适配"""
        try:
            info = {}
            
            # 获取Android版本
            version_cmd = f"adb -s {self.device_id} shell getprop ro.build.version.release"
            result = subprocess.run(version_cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                info['android_version'] = result.stdout.strip()
                
            # 获取厂商信息
            brand_cmd = f"adb -s {self.device_id} shell getprop ro.product.brand"
            result = subprocess.run(brand_cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                info['brand'] = result.stdout.strip().lower()
                
            # 获取SDK版本
            sdk_cmd = f"adb -s {self.device_id} shell getprop ro.build.version.sdk"
            result = subprocess.run(sdk_cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                info['sdk_version'] = result.stdout.strip()
                
            logger.info(f"设备信息: {info}")
            return info
            
        except Exception as e:
            logger.debug(f"获取设备信息失败: {e}")
            return {}
    
    def _get_optimized_paths(self) -> List[str]:
        """根据设备信息优化路径选择"""
        base_paths = []
        
        # 根据厂商优化路径顺序
        brand = self.device_info.get('brand', '')
        sdk_version = int(self.device_info.get('sdk_version', '0'))
        
        if brand in ['xiaomi', 'redmi']:
            # 小米设备优先路径
            base_paths = [
                "/storage/emulated/0/ui_dump.xml",
                "/sdcard/ui_dump.xml",
                "/data/local/tmp/ui_dump.xml"
            ]
        elif brand in ['huawei', 'honor']:
            # 华为设备优先路径
            base_paths = [
                "/storage/emulated/0/ui_dump.xml", 
                "/sdcard/ui_dump.xml",
                "/storage/sdcard0/ui_dump.xml"
            ]
        elif brand in ['oppo', 'oneplus']:
            # OPPO/一加设备优先路径
            base_paths = [
                "/sdcard/ui_dump.xml",
                "/storage/emulated/0/ui_dump.xml",
                "/data/local/tmp/ui_dump.xml"
            ]
        elif brand in ['vivo']:
            # VIVO设备优先路径
            base_paths = [
                "/storage/emulated/0/ui_dump.xml",
                "/sdcard/ui_dump.xml", 
                "/storage/sdcard0/ui_dump.xml"
            ]
        else:
            # 默认路径顺序
            base_paths = [
                "/sdcard/ui_dump.xml",
                "/storage/emulated/0/ui_dump.xml",
                "/data/local/tmp/ui_dump.xml"
            ]
            
        # Android 10+ (API 29+) 的额外路径
        if sdk_version >= 29:
            base_paths.insert(1, "/storage/emulated/0/Android/data/ui_dump.xml")
            
        # 添加通用备用路径
        base_paths.extend([
            "/sdcard/Download/ui_dump.xml",
            "/external_sd/ui_dump.xml",
            "/storage/sdcard1/ui_dump.xml"
        ])
        
        return base_paths
    
    def _detect_writable_directories(self) -> List[str]:
        """动态检测设备上的可写目录"""
        logger.info("🔍 开始检测设备可写目录...")
        
        # 候选目录列表（按优先级排序）
        candidate_dirs = [
            "/sdcard",
            "/storage/emulated/0", 
            "/data/local/tmp",
            "/sdcard/Download",
            "/sdcard/Documents",
            "/storage/sdcard0",
            "/storage/sdcard1",
            "/external_sd",
            "/mnt/sdcard",
            "/storage/emulated/legacy"
        ]
        
        writable_dirs = []
        
        for directory in candidate_dirs:
            try:
                # 测试目录是否存在且可写
                test_cmd = f"adb -s {self.device_id} shell 'test -d {directory} && touch {directory}/test_write_$$.$$ 2>/dev/null && rm -f {directory}/test_write_$$.$$ && echo writable'"
                result = subprocess.run(test_cmd, shell=True, capture_output=True, text=True, timeout=3)
                
                if result.returncode == 0 and 'writable' in result.stdout:
                    writable_dirs.append(directory)
                    logger.info(f"✅ 可写目录: {directory}")
                else:
                    logger.debug(f"❌ 不可写目录: {directory}")
                    
            except Exception as e:
                logger.debug(f"测试目录失败 {directory}: {e}")
                continue
                
        logger.info(f"📊 检测到 {len(writable_dirs)} 个可写目录")
        return writable_dirs
    
    def _generate_dynamic_paths(self, max_attempts: int = 20) -> List[str]:
        """生成动态UI dump路径列表"""
        import uuid
        import time
        
        # 获取可写目录
        writable_dirs = self._detect_writable_directories()
        
        if not writable_dirs:
            logger.warning("⚠️ 未找到可写目录，使用默认路径")
            writable_dirs = ["/sdcard", "/data/local/tmp"]
        
        dynamic_paths = []
        
        # 为每个可写目录生成多个随机文件名
        for attempt in range(max_attempts):
            for directory in writable_dirs:
                # 生成唯一文件名
                timestamp = int(time.time() * 1000)
                random_id = uuid.uuid4().hex[:8]
                filename = f"ui_dump_{timestamp}_{random_id}_{attempt}.xml"
                
                full_path = f"{directory}/{filename}"
                dynamic_paths.append(full_path)
                
                # 限制总数
                if len(dynamic_paths) >= max_attempts:
                    break
            
            if len(dynamic_paths) >= max_attempts:
                break
                
        logger.info(f"📝 生成了 {len(dynamic_paths)} 个动态路径")
        return dynamic_paths[:max_attempts]
        
    def get_ui_hierarchy(self) -> Optional[str]:
        """获取UI层次结构XML - 动态路径循环策略"""
        max_attempts = 20
        
        # 方法1: 优先尝试缓存路径
        if self.working_path:
            content = self._get_ui_content_via_shell(self.working_path)
            if content:
                logger.info(f"✅ 使用缓存路径成功: {self.working_path}")
                return content
            else:
                logger.info("⚠️ 缓存路径失效，清除缓存")
                self.working_path = None
        
        # 方法2: 尝试无文件方式（最快）
        content = self._get_ui_content_no_file()
        if content:
            logger.info("✅ 无文件方式成功")
            return content
        
        # 方法3: 动态生成路径并循环尝试
        logger.info(f"🔄 开始动态路径循环策略 (最大 {max_attempts} 次)")
        dynamic_paths = self._generate_dynamic_paths(max_attempts)
        
        for attempt, device_path in enumerate(dynamic_paths, 1):
            try:
                logger.info(f"📍 尝试 {attempt}/{len(dynamic_paths)}: {device_path}")
                
                # 优先使用shell方式
                content = self._get_ui_content_via_shell(device_path)
                if content:
                    logger.info(f"✅ shell方式成功，路径: {device_path}")
                    self.working_path = device_path  # 缓存成功路径
                    return content
                
                # 备用pull方式
                content = self._get_ui_content_via_pull(device_path, attempt)
                if content:
                    logger.info(f"✅ pull方式成功，路径: {device_path}")
                    self.working_path = device_path  # 缓存成功路径
                    return content
                    
                # 每5次尝试休息一下，避免过于频繁
                if attempt % 5 == 0:
                    logger.info(f"⏳ 已尝试 {attempt} 次，短暂休息...")
                    time.sleep(0.2)
                    
            except Exception as e:
                logger.debug(f"路径 {device_path} 失败: {e}")
                continue
        
        # 方法4: 如果动态路径都失败，尝试传统固定路径
        logger.warning(f"⚠️ 动态路径尝试完毕，回退到传统路径")
        traditional_paths = self._get_optimized_paths()
        
        for attempt, device_path in enumerate(traditional_paths, 1):
            try:
                logger.info(f"🔙 传统路径 {attempt}/{len(traditional_paths)}: {device_path}")
                
                content = self._get_ui_content_via_shell(device_path)
                if content:
                    logger.info(f"✅ 传统路径shell成功: {device_path}")
                    self.working_path = device_path
                    return content
                    
            except Exception as e:
                logger.debug(f"传统路径失败 {device_path}: {e}")
                continue
                
        logger.error("❌ 所有方法都失败，无法获取UI层次结构")
        return None
    
    def _get_ui_content_no_file(self) -> Optional[str]:
        """方法3: 无文件方式获取UI内容（最后手段）"""
        try:
            logger.info("🔄 尝试无文件方式获取UI内容...")
            
            # 尝试直接输出到stdout
            direct_cmd = f"adb -s {self.device_id} shell 'uiautomator dump /dev/stdout 2>/dev/null || uiautomator dump'"
            result = subprocess.run(direct_cmd, shell=True, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0 and result.stdout.strip():
                content = result.stdout.strip()
                if self._is_valid_xml_content(content):
                    logger.info("✅ 无文件方式成功获取UI内容")
                    return content
                    
            # 尝试使用临时管道
            pipe_cmd = f"adb -s {self.device_id} shell 'uiautomator dump /proc/self/fd/1'"
            result = subprocess.run(pipe_cmd, shell=True, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0 and result.stdout.strip():
                content = result.stdout.strip()
                if self._is_valid_xml_content(content):
                    logger.info("✅ 管道方式成功获取UI内容")
                    return content
                    
            logger.warning("❌ 无文件方式也无法获取UI内容")
            return None
            
        except Exception as e:
            logger.debug(f"无文件方式失败: {e}")
            return None
    
    def _get_ui_content_via_shell(self, device_path: str) -> Optional[str]:
        """方法1: 通过shell直接获取UI内容（无需文件传输）"""
        try:
            # 直接在设备上生成UI dump并通过shell读取
            dump_and_cat_cmd = f"adb -s {self.device_id} shell 'uiautomator dump {device_path} && cat {device_path}'"
            result = subprocess.run(dump_and_cat_cmd, shell=True, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0 and result.stdout.strip():
                content = result.stdout.strip()
                # 验证内容是否为有效XML
                if self._is_valid_xml_content(content):
                    # 清理设备上的临时文件
                    cleanup_cmd = f"adb -s {self.device_id} shell rm -f {device_path}"
                    subprocess.run(cleanup_cmd, shell=True, capture_output=True)
                    return content
                    
            return None
            
        except Exception as e:
            logger.debug(f"Shell方法获取UI失败: {e}")
            return None
    
    def _get_ui_content_via_pull(self, device_path: str, attempt: int) -> Optional[str]:
        """方法2: 传统的dump+pull方式（备用）"""
        try:
            # 导出UI dump到设备
            dump_cmd = f"adb -s {self.device_id} shell uiautomator dump {device_path}"
            result = subprocess.run(dump_cmd, shell=True, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                return None
                
            # 生成唯一的本地文件名，避免冲突
            import uuid
            local_filename = f"ui_dump_temp_{attempt}_{uuid.uuid4().hex[:8]}.xml"
            
            # 拉取UI dump文件
            pull_cmd = f"adb -s {self.device_id} pull {device_path} ./{local_filename}"
            result = subprocess.run(pull_cmd, shell=True, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                return None
                
            # 读取文件内容
            try:
                with open(f"./{local_filename}", "r", encoding="utf-8") as f:
                    content = f.read()
                    
                # 清理本地临时文件
                subprocess.run(f"rm -f ./{local_filename}", shell=True)
                
                # 清理设备上的临时文件
                cleanup_cmd = f"adb -s {self.device_id} shell rm -f {device_path}"
                subprocess.run(cleanup_cmd, shell=True, capture_output=True)
                
                if self._is_valid_xml_content(content):
                    return content
                    
                return None
                
            except Exception as e:
                logger.debug(f"读取本地文件失败: {e}")
                # 确保清理临时文件
                subprocess.run(f"rm -f ./{local_filename}", shell=True)
                return None
                
        except Exception as e:
            logger.debug(f"Pull方法获取UI失败: {e}")
            return None
    
    def _is_valid_xml_content(self, content: str) -> bool:
        """验证XML内容是否有效"""
        try:
            if not content or len(content) < 50:
                return False
                
            # 检查基本XML标签
            if not content.strip().startswith('<?xml') and not content.strip().startswith('<'):
                return False
                
            # 尝试解析XML
            ET.fromstring(content)
            return True
            
        except Exception:
            return False
    
    def detect_permission_dialog(self) -> Optional[PermissionDialog]:
        """检测权限弹窗"""
        try:
            xml_content = self.get_ui_hierarchy()
            if not xml_content:
                return None
                
            # 解析XML
            root = ET.fromstring(xml_content)
            
            # 收集所有文本和可点击元素
            all_texts = []
            clickable_elements = []
            
            self._collect_elements_from_xml(root, all_texts, clickable_elements)
            
            if not all_texts:
                return None
                
            # 分析是否为权限弹窗
            return self._analyze_permission_content(all_texts, clickable_elements)
            
        except Exception as e:
            logger.error(f"检测权限弹窗失败: {e}")
            return None
    
    def _collect_elements_from_xml(self, element: ET.Element, all_texts: List[str], clickable_elements: List[Dict]):
        """从XML元素中收集信息"""
        try:
            # 获取当前元素属性
            text = element.get('text', '').strip()
            clickable = element.get('clickable', 'false') == 'true'
            resource_id = element.get('resource-id', '')
            class_name = element.get('class', '')
            bounds = element.get('bounds', '')
            package = element.get('package', '')
            
            if text:
                all_texts.append(text)
                
            if clickable and text:
                clickable_elements.append({
                    'text': text,
                    'resource_id': resource_id,
                    'class_name': class_name,
                    'package': package,
                    'bounds': bounds
                })
                
            # 递归处理子元素
            for child in element:
                self._collect_elements_from_xml(child, all_texts, clickable_elements)
                
        except Exception as e:
            logger.debug(f"收集XML元素失败: {e}")
    
    def _analyze_permission_content(self, all_texts: List[str], clickable_elements: List[Dict]) -> Optional[PermissionDialog]:
        """分析是否为权限弹窗"""
        try:
            combined_text = ' '.join(all_texts)
            
            # 检查权限关键词
            if not self._has_permission_keywords(combined_text):
                return None
                
            # 检查是否为登录界面
            if self._is_login_screen(combined_text):
                return None
                
            # 识别可用操作
            available_actions = self._identify_available_actions(clickable_elements)
            
            if not available_actions:
                return None
                
            permission_type = self._identify_permission_type(all_texts)
            
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
        """检查权限关键词"""
        text_lower = text.lower()
        
        # 检查各种权限关键词
        all_keywords = (
            self.patterns.APP_CUSTOM_DIALOG_KEYWORDS + 
            self.patterns.PRIVACY_POLICY_KEYWORDS + 
            self.patterns.PERMISSION_REQUEST_KEYWORDS
        )
        
        for keyword in all_keywords:
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
        login_count = sum(1 for keyword in self.patterns.GAME_LOGIN_KEYWORDS 
                         if keyword.lower() in text_lower)
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
    
    def _identify_available_actions(self, clickable_elements: List[Dict]) -> List[PermissionAction]:
        """识别可用操作"""
        actions = []
        
        for element in clickable_elements:
            text = element['text'].strip()
            resource_id = element.get('resource_id', '')
            
            # 匹配操作类型
            for action, patterns in self.patterns.PERMISSION_BUTTON_PATTERNS.items():
                matched = False
                
                # 文本匹配
                if text in patterns['texts']:
                    actions.append(action)
                    matched = True
                    break
                    
                # Resource ID匹配
                if not matched and resource_id in patterns['resource_ids']:
                    actions.append(action)
                    break
                    
        return list(set(actions))
    
    def click_by_text(self, text: str) -> bool:
        """通过文本点击元素"""
        try:
            # 使用UIAutomator直接点击
            click_cmd = f'adb -s {self.device_id} shell uiautomator runtest UIAutomator.jar -c com.android.uiautomator.testrunner.UiAutomatorTestCase'
            
            # 简化版：直接使用input tap点击
            xml_content = self.get_ui_hierarchy()
            if not xml_content:
                return False
                
            root = ET.fromstring(xml_content)
            
            # 查找目标元素
            target_element = self._find_element_by_text(root, text)
            if not target_element:
                logger.warning(f"未找到文本为 '{text}' 的元素")
                return False
                
            # 解析bounds并点击
            bounds = target_element.get('bounds', '')
            if bounds:
                center_x, center_y = self._parse_bounds_center(bounds)
                if center_x and center_y:
                    tap_cmd = f"adb -s {self.device_id} shell input tap {center_x} {center_y}"
                    result = subprocess.run(tap_cmd, shell=True, capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        logger.info(f"✅ 成功点击文本: '{text}'")
                        time.sleep(1)
                        return True
                    else:
                        logger.error(f"点击失败: {result.stderr}")
                        
            return False
            
        except Exception as e:
            logger.error(f"文本点击失败: {e}")
            return False
    
    def _find_element_by_text(self, element: ET.Element, target_text: str) -> Optional[ET.Element]:
        """在XML中查找指定文本的元素"""
        text = element.get('text', '').strip()
        if text == target_text and element.get('clickable', 'false') == 'true':
            return element
            
        for child in element:
            result = self._find_element_by_text(child, target_text)
            if result is not None:
                return result
                
        return None
    
    def _parse_bounds_center(self, bounds: str) -> Tuple[Optional[int], Optional[int]]:
        """解析bounds并返回中心点坐标"""
        try:
            # bounds格式: [x1,y1][x2,y2]
            matches = re.findall(r'\[(\d+),(\d+)\]', bounds)
            if len(matches) == 2:
                x1, y1 = int(matches[0][0]), int(matches[0][1])
                x2, y2 = int(matches[1][0]), int(matches[1][1])
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                return center_x, center_y
        except Exception as e:
            logger.debug(f"解析bounds失败: {e}")
            
        return None, None
    
    def handle_permission_dialog(self, dialog: PermissionDialog, auto_allow: bool = True) -> bool:
        """处理权限弹窗"""
        try:
            target_action = PermissionAction.ALLOW if auto_allow else PermissionAction.DENY
            
            if target_action not in dialog.available_actions:
                if dialog.available_actions:
                    target_action = dialog.available_actions[0]
                else:
                    return False
                    
            # 获取目标按钮文本
            patterns = self.patterns.PERMISSION_BUTTON_PATTERNS.get(target_action, {})
            target_texts = patterns.get('texts', [])
            
            # 尝试点击
            for text in target_texts:
                if self.click_by_text(text):
                    logger.info(f"✅ 成功处理权限弹窗: {target_action.value}")
                    return True
                    
            logger.warning(f"未能点击任何 {target_action.value} 按钮")
            return False
            
        except Exception as e:
            logger.error(f"处理权限弹窗失败: {e}")
            return False
    
    def wait_and_handle_permission_popups(self, max_popups: int = 3, timeout: int = 10) -> bool:
        """等待并处理权限弹窗"""
        logger.info(f"开始ADB权限处理 - 最大弹窗: {max_popups}, 超时: {timeout}秒")
        
        handled_count = 0
        start_time = time.time()
        no_dialog_count = 0
        
        while handled_count < max_popups and (time.time() - start_time) < timeout:
            try:
                dialog = self.detect_permission_dialog()
                
                if dialog:
                    no_dialog_count = 0
                    logger.info(f"ADB检测到权限弹窗: {dialog.permission_type}")
                    
                    if self.handle_permission_dialog(dialog, auto_allow=True):
                        handled_count += 1
                        logger.info(f"ADB成功处理权限弹窗 {handled_count}/{max_popups}")
                        time.sleep(1.5)
                    else:
                        logger.warning("ADB权限弹窗处理失败")
                        time.sleep(1)
                else:
                    no_dialog_count += 1
                    if no_dialog_count >= 3:
                        logger.info("ADB连续3次未检测到权限弹窗，结束")
                        break
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"ADB权限处理异常: {e}")
                time.sleep(1)
                
        logger.info(f"ADB权限处理完成，共处理 {handled_count} 个弹窗")
        return True


# 集成函数
def adb_integrate_with_app_launch(device_id: str, auto_allow: bool = True) -> bool:
    """ADB权限处理集成函数"""
    try:
        manager = NativeADBPermissionManager(device_id)
        return manager.wait_and_handle_permission_popups(max_popups=3, timeout=8)
    except Exception as e:
        logger.warning(f"ADB权限处理异常: {e}")
        return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    device_id = "A3UGVB3210002403"
    manager = NativeADBPermissionManager(device_id)
    
    # 测试
    dialog = manager.detect_permission_dialog()
    if dialog:
        print(f"检测到权限弹窗: {dialog}")
        success = manager.handle_permission_dialog(dialog)
        print(f"处理结果: {'成功' if success else '失败'}")
    else:
        print("未检测到权限弹窗")
