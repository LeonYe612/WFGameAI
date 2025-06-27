#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨进程账号管理器
解决多进程环境下账号重复分配的问题
"""

import os
import fcntl
import json
import time
import threading
from typing import Optional, Tuple, Dict, List
from datetime import datetime


class CrossProcessAccountManager:
    """跨进程账号管理器 - 使用文件锁实现进程间同步"""

    def __init__(self, accounts_file: str = None, state_file: str = None):
        """
        初始化跨进程账号管理器

        Args:
            accounts_file: 账号文件路径
            state_file: 状态文件路径（用于进程间共享）
        """
        if accounts_file is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            accounts_file = os.path.join(current_dir, "datasets", "accounts_info", "accounts.txt")

        if state_file is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            state_file = os.path.join(current_dir, "datasets", "accounts_info", "allocation_state.json")

        self.accounts_file = accounts_file
        self.state_file = state_file
        self.lock_file = state_file + ".lock"
        self.accounts = []

        self._load_accounts()
        self._ensure_state_file()

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
                if line.startswith('#') or not line:
                    continue

                parts = line.split(',')
                if len(parts) != 2:
                    print(f"警告: 账号文件第{line_num}行格式错误，跳过: {line}")
                    continue

                username, password = parts[0].strip(), parts[1].strip()
                if not username or not password:
                    print(f"警告: 账号文件第{line_num}行用户名或密码为空，跳过: {line}")
                    continue

                self.accounts.append((username, password))

            print(f"✅ 跨进程账号管理器加载 {len(self.accounts)} 个账号")

        except Exception as e:
            print(f"❌ 加载账号文件失败: {e}")
            self.accounts = []

    def _ensure_state_file(self):
        """确保状态文件存在"""
        if not os.path.exists(self.state_file):
            initial_state = {
                "device_allocations": {},
                "last_allocated_index": -1,
                "created_time": datetime.now().isoformat(),
                "process_count": 0
            }
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(initial_state, f, indent=2, ensure_ascii=False)

    def _acquire_lock(self, timeout: float = 10.0) -> Optional[object]:
        """获取文件锁"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                lock_fd = os.open(self.lock_file, os.O_CREAT | os.O_WRONLY | os.O_TRUNC)
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return lock_fd
            except (OSError, IOError):
                time.sleep(0.1)
        return None

    def _release_lock(self, lock_fd):
        """释放文件锁"""
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)
        except Exception:
            pass

    def _read_state(self) -> Dict:
        """读取状态文件"""
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {
                "device_allocations": {},
                "last_allocated_index": -1,
                "created_time": datetime.now().isoformat(),
                "process_count": 0
            }

    def _write_state(self, state: Dict):
        """写入状态文件"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ 写入状态文件失败: {e}")

    def allocate_account(self, device_serial: str) -> Optional[Tuple[str, str]]:
        """
        为设备分配账号（跨进程安全）

        Args:
            device_serial: 设备序列号

        Returns:
            (username, password) 或 None
        """
        lock_fd = self._acquire_lock()
        if lock_fd is None:
            print(f"❌ 无法获取锁，设备 {device_serial} 账号分配失败")
            return None

        try:
            # 读取当前状态
            state = self._read_state()
            device_allocations = state.get("device_allocations", {})
            last_allocated_index = state.get("last_allocated_index", -1)

            # 如果设备已经分配过账号，静默返回
            if device_serial in device_allocations:
                username, password = device_allocations[device_serial]
                return username, password

            # 寻找下一个可用账号
            allocated_accounts = set(device_allocations.values())
            available_accounts = [acc for acc in self.accounts if acc not in allocated_accounts]

            if not available_accounts:
                print(f"❌ 无账号可分配给设备 {device_serial}，当前已分配: {len(device_allocations)}")
                return None

            # 顺序分配：使用第一个可用账号
            username, password = available_accounts[0]

            # 更新状态
            device_allocations[device_serial] = (username, password)
            state["device_allocations"] = device_allocations
            state["last_allocated_index"] = self.accounts.index((username, password))
            state["last_update"] = datetime.now().isoformat()

            # 写入状态
            self._write_state(state)

            print(f"✅ 跨进程分配账号: 设备 {device_serial} -> {username}")
            return username, password

        finally:
            self._release_lock(lock_fd)

    def release_account(self, device_serial: str):
        """
        释放设备的账号分配（跨进程安全）

        Args:
            device_serial: 设备序列号
        """
        lock_fd = self._acquire_lock()
        if lock_fd is None:
            print(f"❌ 无法获取锁，设备 {device_serial} 账号释放失败")
            return

        try:
            state = self._read_state()
            device_allocations = state.get("device_allocations", {})

            if device_serial in device_allocations:
                username, password = device_allocations[device_serial]
                del device_allocations[device_serial]

                state["device_allocations"] = device_allocations
                state["last_update"] = datetime.now().isoformat()

                self._write_state(state)

                print(f"✅ 跨进程释放账号: 设备 {device_serial} -> {username}")
            else:
                print(f"⚠️ 设备 {device_serial} 没有分配的账号")

        finally:
            self._release_lock(lock_fd)

    def get_account(self, device_serial: str) -> Optional[Tuple[str, str]]:
        """
        获取设备的账号信息

        Args:
            device_serial: 设备序列号

        Returns:
            (username, password) 或 None
        """
        lock_fd = self._acquire_lock()
        if lock_fd is None:
            return None

        try:
            state = self._read_state()
            device_allocations = state.get("device_allocations", {})
            return device_allocations.get(device_serial)
        finally:
            self._release_lock(lock_fd)

    def get_allocation_status(self) -> Dict[str, str]:
        """
        获取当前分配状态

        Returns:
            {device_serial: username, ...}
        """
        lock_fd = self._acquire_lock()
        if lock_fd is None:
            return {}

        try:
            state = self._read_state()
            device_allocations = state.get("device_allocations", {})
            return {device: allocation[0] for device, allocation in device_allocations.items()}
        finally:
            self._release_lock(lock_fd)

    def get_available_accounts_count(self) -> int:
        """
        获取可用账号数量

        Returns:
            可用账号数量
        """
        lock_fd = self._acquire_lock()
        if lock_fd is None:
            return 0

        try:
            state = self._read_state()
            device_allocations = state.get("device_allocations", {})
            return len(self.accounts) - len(device_allocations)
        finally:
            self._release_lock(lock_fd)

    def clear_all_allocations(self):
        """清空所有分配（用于测试和重置）"""
        lock_fd = self._acquire_lock()
        if lock_fd is None:
            print("❌ 无法获取锁，清空分配失败")
            return

        try:
            state = self._read_state()
            state["device_allocations"] = {}
            state["last_allocated_index"] = -1
            state["last_update"] = datetime.now().isoformat()

            self._write_state(state)
            print("✅ 已清空所有账号分配")

        finally:
            self._release_lock(lock_fd)


# 全局跨进程账号管理器实例
_cross_process_account_manager = None


def get_cross_process_account_manager() -> CrossProcessAccountManager:
    """获取跨进程账号管理器实例"""
    global _cross_process_account_manager
    if _cross_process_account_manager is None:
        _cross_process_account_manager = CrossProcessAccountManager()
    return _cross_process_account_manager


if __name__ == "__main__":
    # 测试代码
    print("=== 跨进程账号管理器测试 ===")

    manager = get_cross_process_account_manager()

    # 清空现有分配
    manager.clear_all_allocations()

    # 测试分配
    devices = ["5c41023b", "CWM0222215003786", "test_device"]

    print("\n📊 测试账号分配:")
    for device in devices:
        account = manager.allocate_account(device)
        if account:
            print(f"   {device} -> {account[0]}")
        else:
            print(f"   {device} -> 分配失败")

    print(f"\n📊 分配状态: {manager.get_allocation_status()}")
    print(f"📊 可用账号数: {manager.get_available_accounts_count()}")

    # 测试重复分配
    print(f"\n🔁 测试重复分配:")
    account = manager.allocate_account("5c41023b")
    print(f"   5c41023b -> {account[0] if account else '失败'}")

    # 测试释放
    print(f"\n🗑️ 测试账号释放:")
    manager.release_account("5c41023b")
    print(f"   释放后可用账号数: {manager.get_available_accounts_count()}")
