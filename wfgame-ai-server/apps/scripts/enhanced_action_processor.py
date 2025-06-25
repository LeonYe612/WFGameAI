"""
增强的 ActionProcessor 包装器
确保设备账号正确分配
"""

import os
import sys

# 添加当前目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from action_processor import ActionProcessor as OriginalActionProcessor
from account_manager import get_account_manager

class EnhancedActionProcessor(OriginalActionProcessor):
    """增强的 ActionProcessor，确保账号分配"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ensure_device_account()

    def _ensure_device_account(self):
        """确保设备有账号分配"""
        if self.device_account:
            print(f"✅ 设备已有账号分配: {self.device_account[0]}")
            return

        try:
            # 尝试获取设备序列号
            device_serial = getattr(self.device, 'serial', self.device_name)
            if not device_serial:
                print("⚠️ 无法获取设备序列号，跳过账号分配")
                return

            # 获取账号管理器并分配账号
            account_manager = get_account_manager()
            device_account = account_manager.allocate_account(device_serial)

            if device_account:
                self.set_device_account(device_account)
                username, password = device_account
                print(f"✅ 自动为设备 {device_serial} 分配账号: {username}")
            else:
                print(f"⚠️ 无法为设备 {device_serial} 分配账号，账号池可能已满")

        except Exception as e:
            print(f"❌ 自动账号分配失败: {e}")

    def _handle_input(self, step, step_idx):
        """重写输入处理，增加账号检查"""
        # 在处理输入前再次确认账号分配
        input_text = step.get("text", "")

        # 如果需要账号参数但没有分配，尝试重新分配
        if ("${account:username}" in input_text or "${account:password}" in input_text):
            if not self.device_account:
                print("🔄 检测到需要账号参数但未分配，尝试重新分配...")
                self._ensure_device_account()

            # 如果仍然没有账号，给出详细的错误信息
            if not self.device_account:
                device_serial = getattr(self.device, 'serial', self.device_name)
                print(f"❌ 错误: 设备 {device_serial} 没有分配账号，无法替换账号参数")
                print("💡 可能的原因:")
                print("   1. 账号池已满，所有账号都已分配")
                print("   2. 账号文件不存在或格式错误")
                print("   3. 账号管理器初始化失败")
                print("💡 建议解决方案:")
                print("   1. 检查 datasets/accounts_info/accounts.txt 文件")
                print("   2. 运行账号分配诊断工具")
                print("   3. 释放不使用的设备账号分配")
                return True, False, True

        # 调用原始方法
        return super()._handle_input(step, step_idx)

# 替换原始的 ActionProcessor
ActionProcessor = EnhancedActionProcessor
