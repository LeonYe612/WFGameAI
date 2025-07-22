"""
WFGameAI账号管理器
功能：基于设备连接顺序分配账号
作者：WFGameAI开发团队
"""

import os
import threading
from typing import Optional, Tuple, Dict


class AccountManager:
    """账号管理器：基于设备顺序分配账号"""
    def __init__(self, accounts_file: str = None):
        """
        初始化账号管理器

        Args:
            accounts_file: 账号文件路径，默认使用datasets/accounts_info/accounts.txt
        """
        if accounts_file is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            accounts_file = os.path.join(current_dir, "datasets", "accounts_info", "accounts.txt")

        self.accounts_file = accounts_file
        self.accounts = []
        self.device_allocations = {}  # device_serial -> (username, password)
        self.allocation_lock = threading.Lock()

        self._load_accounts()

    def _load_accounts(self):
        """从文件加载账号信息"""
        try:
            if not os.path.exists(self.accounts_file):
                raise FileNotFoundError(f"账号文件不存在: {self.accounts_file}")

            with open(self.accounts_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            self.accounts = []
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                # 跳过注释行和空行
                if line.startswith('#') or not line:
                    continue

                # 解析用户名和密码
                parts = line.split(',')
                if len(parts) != 2:
                    print(f"警告: 账号文件第{line_num}行格式错误，跳过: {line}")
                    continue

                username, password = parts[0].strip(), parts[1].strip()
                if not username or not password:
                    print(f"警告: 账号文件第{line_num}行用户名或密码为空，跳过: {line}")
                    continue

                self.accounts.append((username, password))

            print(f"成功加载 {len(self.accounts)} 个账号")

        except Exception as e:
            print(f"加载账号文件失败: {e}")
            self.accounts = []

    def allocate_account(self, device_serial: str) -> Optional[Tuple[str, str]]:
        """
        为设备分配账号

        Args:
            device_serial: 设备序列号

        Returns:
            (username, password) 或 None (如果无可用账号)
        """
        with self.allocation_lock:
            # 如果设备已经分配过账号，返回之前的分配（静默模式）
            if device_serial in self.device_allocations:
                username, password = self.device_allocations[device_serial]
                # 静默返回，避免重复打印
                return username, password            # 基于顺序分配账号，保证从第一个账号开始使用# 找到第一个未分配的账号
            allocated_accounts = set(self.device_allocations.values())
            available_accounts = [acc for acc in self.accounts if acc not in allocated_accounts]

            if not available_accounts:
                print(f"错误: 账号不足，无法为设备 {device_serial} 分配账号")
                print(f"当前已分配: {len(self.device_allocations)}, 总账号数: {len(self.accounts)}")
                return None

            # 使用顺序分配策略：分配第一个可用账号
            username, password = available_accounts[0]
            self.device_allocations[device_serial] = (username, password)

            print(f"为设备 {device_serial} 分配账号: {username} (顺序分配算法)")
            return username, password

    def get_account(self, device_serial: str) -> Optional[Tuple[str, str]]:
        """
        获取设备的账号信息

        Args:
            device_serial: 设备序列号

        Returns:
            (username, password) 或 None (如果设备未分配账号)
        """
        with self.allocation_lock:
            if device_serial in self.device_allocations:
                return self.device_allocations[device_serial]
            return None

    def release_account(self, device_serial: str):
        """
        释放设备的账号分配

        Args:
            device_serial: 设备序列号
        """
        with self.allocation_lock:
            if device_serial in self.device_allocations:
                username, password = self.device_allocations[device_serial]
                del self.device_allocations[device_serial]
                print(f"account_manager 释放设备： {device_serial} 的账号分配: [{username}], [{password}]")

    def get_allocation_status(self) -> Dict[str, str]:
        """
        获取当前分配状态

        Returns:
            {device_serial: username, ...}
        """
        with self.allocation_lock:
            return {device: allocation[0] for device, allocation in self.device_allocations.items()}

    def get_available_accounts_count(self) -> int:
        """
        获取可用账号数量

        Returns:
            可用账号数量
        """
        with self.allocation_lock:
            return len(self.accounts) - len(self.device_allocations)


# 全局账号管理器实例
_global_account_manager = None


def get_account_manager() -> AccountManager:
    """获取全局账号管理器实例"""
    global _global_account_manager
    if _global_account_manager is None:
        _global_account_manager = AccountManager()
    return _global_account_manager
