#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
手动PocoService连接器 - 绕过Poco包版本限制
直接与PocoService通信获取UI层次结构
"""

import json
import socket
import time
import logging
import subprocess
from typing import Optional, Dict, Any
import requests

logger = logging.getLogger(__name__)


class ManualPocoConnector:
    """手动连接PocoService的连接器"""
    
    def __init__(self, device_id: str, poco_port: int = 10080):
        self.device_id = device_id
        self.poco_port = poco_port
        self.adb_port = None
        self.base_url = None
        self.connected = False
        
    def connect(self) -> bool:
        """连接到设备上的PocoService"""
        try:
            # 1. 确保PocoService正在运行
            if not self._ensure_poco_service_running():
                logger.error("无法启动PocoService")
                return False
                
            # 2. 设置端口转发
            if not self._setup_port_forward():
                logger.error("端口转发设置失败")
                return False
                
            # 3. 测试连接
            if not self._test_connection():
                logger.error("连接测试失败")
                return False
                
            self.connected = True
            logger.info(f"成功连接到设备 {self.device_id} 的PocoService")
            return True
            
        except Exception as e:
            logger.error(f"连接失败: {e}")
            return False
    
    def _ensure_poco_service_running(self) -> bool:
        """确保PocoService正在运行"""
        try:
            # 检查PocoService是否已安装
            check_cmd = f"adb -s {self.device_id} shell pm list packages | grep pocoservice"
            result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
            
            if "pocoservice" not in result.stdout:
                logger.warning("PocoService未安装，尝试安装...")
                # 这里可以添加自动安装逻辑
                return False
                
            # 启动PocoService
            start_cmd = f"adb -s {self.device_id} shell am instrument -w -e debug false -e class com.netease.open.pocoservice.TestClass com.netease.open.pocoservice.test/android.support.test.runner.AndroidJUnitRunner"
            subprocess.Popen(start_cmd, shell=True)
            
            time.sleep(3)  # 等待服务启动
            
            # 检查服务是否运行
            check_service_cmd = f"adb -s {self.device_id} shell netstat -an | grep {self.poco_port}"
            result = subprocess.run(check_service_cmd, shell=True, capture_output=True, text=True)
            
            return str(self.poco_port) in result.stdout
            
        except Exception as e:
            logger.error(f"确保PocoService运行失败: {e}")
            return False
    
    def _setup_port_forward(self) -> bool:
        """设置ADB端口转发"""
        try:
            # 找一个可用的本地端口
            import socket
            sock = socket.socket()
            sock.bind(('', 0))
            self.adb_port = sock.getsockname()[1]
            sock.close()
            
            # 设置端口转发
            forward_cmd = f"adb -s {self.device_id} forward tcp:{self.adb_port} tcp:{self.poco_port}"
            result = subprocess.run(forward_cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.base_url = f"http://127.0.0.1:{self.adb_port}"
                logger.info(f"端口转发设置成功: {self.adb_port} -> {self.poco_port}")
                return True
            else:
                logger.error(f"端口转发失败: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"端口转发设置异常: {e}")
            return False
    
    def _test_connection(self) -> bool:
        """测试与PocoService的连接"""
        try:
            response = requests.get(f"{self.base_url}/", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"连接测试失败: {e}")
            return False
    
    def get_ui_hierarchy(self) -> Optional[Dict[str, Any]]:
        """获取UI层次结构"""
        if not self.connected:
            logger.error("未连接到PocoService")
            return None
            
        try:
            # 调用PocoService的dump接口
            response = requests.post(
                f"{self.base_url}/dump", 
                json={}, 
                timeout=10
            )
            
            if response.status_code == 200:
                hierarchy_data = response.json()
                logger.info("成功获取UI层次结构")
                return hierarchy_data
            else:
                logger.error(f"获取UI层次结构失败: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"获取UI层次结构异常: {e}")
            return None
    
    def click_element(self, selector: Dict[str, Any]) -> bool:
        """点击元素"""
        if not self.connected:
            logger.error("未连接到PocoService")
            return False
            
        try:
            response = requests.post(
                f"{self.base_url}/click",
                json={"selector": selector},
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"点击元素失败: {e}")
            return False
    
    def find_elements_by_text(self, text: str) -> list:
        """通过文本查找元素"""
        hierarchy = self.get_ui_hierarchy()
        if not hierarchy:
            return []
            
        elements = []
        self._find_elements_recursive(hierarchy, "text", text, elements)
        return elements
    
    def find_elements_by_resource_id(self, resource_id: str) -> list:
        """通过resource_id查找元素"""
        hierarchy = self.get_ui_hierarchy()
        if not hierarchy:
            return []
            
        elements = []
        self._find_elements_recursive(hierarchy, "resourceId", resource_id, elements)
        return elements
    
    def _find_elements_recursive(self, node: Dict, attr_name: str, attr_value: str, elements: list):
        """递归查找元素"""
        try:
            attrs = node.get('attrs', {})
            if attrs.get(attr_name) == attr_value:
                elements.append(node)
                
            children = node.get('children', [])
            for child in children:
                self._find_elements_recursive(child, attr_name, attr_value, elements)
                
        except Exception as e:
            logger.debug(f"递归查找异常: {e}")
    
    def disconnect(self):
        """断开连接"""
        try:
            if self.adb_port:
                # 移除端口转发
                remove_cmd = f"adb -s {self.device_id} forward --remove tcp:{self.adb_port}"
                subprocess.run(remove_cmd, shell=True, capture_output=True)
                logger.info("端口转发已移除")
                
            self.connected = False
            
        except Exception as e:
            logger.error(f"断开连接异常: {e}")


# 使用示例
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    device_id = "A3UGVB3210002403"
    connector = ManualPocoConnector(device_id)
    
    try:
        if connector.connect():
            print("✅ 连接成功")
            
            # 获取UI层次结构
            hierarchy = connector.get_ui_hierarchy()
            if hierarchy:
                print(f"📊 UI层次结构获取成功: {type(hierarchy)}")
                
                # 查找允许按钮
                allow_elements = connector.find_elements_by_text("允许")
                print(f"🔍 找到 {len(allow_elements)} 个'允许'按钮")
                
                # 查找确定按钮
                ok_elements = connector.find_elements_by_text("确定")
                print(f"🔍 找到 {len(ok_elements)} 个'确定'按钮")
            else:
                print("❌ 获取UI层次结构失败")
        else:
            print("❌ 连接失败")
            
    finally:
        connector.disconnect()
