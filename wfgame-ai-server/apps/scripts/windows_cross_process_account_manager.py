#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows兼容的跨进程账号管理器 - 数据库迁移版
支持从文件系统迁移到数据库的混合模式
保持向后兼容的同时提供数据库优化
"""

import os
import json
import time
import threading
import msvcrt  # Windows文件锁
from typing import Optional, Tuple, Dict, List
from datetime import datetime

# 数据库迁移支持
try:
    from .windows_database_account_manager import WindowsDatabaseAccountManager
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    print("⚠️ 数据库账号管理器不可用，将使用文件模式")


class WindowsCrossProcessAccountManager:
    """Windows跨进程账号管理器 - 支持数据库迁移的混合模式"""

    def __init__(self, accounts_file: str = None, state_file: str = None,
                 enable_database: bool = True, auto_migrate: bool = True):
        """
        初始化跨进程账号管理器

        Args:
            accounts_file: 账号文件路径
            state_file: 状态文件路径（用于进程间共享）
            enable_database: 是否启用数据库模式
            auto_migrate: 是否自动迁移到数据库
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

        # 数据库模式设置
        self.enable_database = enable_database and DATABASE_AVAILABLE
        self.db_manager = None
        self.migration_completed = False

        if self.enable_database:
            try:
                self.db_manager = WindowsDatabaseAccountManager()
                print("✅ 数据库账号管理器初始化成功")

                if auto_migrate:
                    self._attempt_migration()
            except Exception as e:
                print(f"⚠️ 数据库初始化失败，回退到文件模式: {e}")
                self.enable_database = False

        # 文件模式初始化
        if not self.enable_database or not self.migration_completed:
            self._load_accounts()
            self._ensure_state_file()
            print("✅ 文件模式账号管理器初始化完成")

    def _attempt_migration(self):
        """尝试从文件迁移到数据库"""
        try:
            if not os.path.exists(self.accounts_file):
                print("⚠️ 账号文件不存在，跳过迁移")
                return

            # 检查是否已经迁移过
            if hasattr(self, '_migration_marker_file'):
                migration_marker = os.path.join(
                    os.path.dirname(self.state_file),
                    '.migration_completed'
                )
                if os.path.exists(migration_marker):
                    print("✅ 数据库迁移已完成")
                    self.migration_completed = True
                    return

            print("🚀 开始从文件系统迁移到数据库...")
            stats = self.db_manager.migrate_from_files(
                accounts_file=self.accounts_file,
                state_file=self.state_file
            )

            if stats['accounts_migrated'] > 0 or stats['allocations_migrated'] > 0:
                # 创建迁移完成标记
                migration_marker = os.path.join(
                    os.path.dirname(self.state_file),
                    '.migration_completed'
                )
                with open(migration_marker, 'w') as f:
                    f.write(f"Migration completed at {datetime.now().isoformat()}\n")
                    f.write(f"Stats: {stats}\n")

                self.migration_completed = True
                print(f"✅ 数据库迁移完成: {stats}")
            else:
                print("ℹ️ 没有需要迁移的数据")

        except Exception as e:
            print(f"❌ 数据库迁移失败: {e}")

    def _load_accounts(self):
        """从文件加载账号信息"""
        try:
            if not os.path.exists(self.accounts_file):
                raise FileNotFoundError(f"账号文件不存在: {self.accounts_file}")

            with open(self.accounts_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                self.accounts = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('//'):
                    # 支持制表符和逗号分隔
                    if '\t' in line:
                        parts = line.split('\t')
                    elif ',' in line:
                        parts = line.split(',')
                    else:
                        continue

                    if len(parts) >= 2:
                        account = {
                            'username': parts[0].strip(),
                            'password': parts[1].strip(),
                            'name': parts[2].strip() if len(parts) > 2 else parts[0].strip()
                        }
                        self.accounts.append(account)

            print(f"✅ 加载了 {len(self.accounts)} 个账号")

        except Exception as e:
            print(f"❌ 加载账号文件失败: {e}")
            self.accounts = []

    def _ensure_state_file(self):
        """确保状态文件存在"""
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            if not os.path.exists(self.state_file):
                initial_state = {
                    'allocations': {},
                    'last_updated': datetime.now().isoformat()
                }
                with open(self.state_file, 'w', encoding='utf-8') as f:
                    json.dump(initial_state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ 创建状态文件失败: {e}")

    def _acquire_lock(self, timeout: float = 10.0) -> Optional[object]:
        """获取文件锁 (Windows版本)"""
        try:
            # 创建锁文件
            lock_fd = os.open(self.lock_file, os.O_CREAT | os.O_TRUNC | os.O_RDWR)

            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    # 尝试锁定文件
                    msvcrt.locking(lock_fd, msvcrt.LK_NBLCK, 1)
                    return lock_fd
                except OSError:
                    # 锁被占用，等待
                    time.sleep(0.1)

            # 超时，关闭文件
            os.close(lock_fd)
            return None

        except Exception as e:
            print(f"⚠️ 获取文件锁失败: {e}")
            return None

    def _release_lock(self, lock_fd):
        """释放文件锁"""
        try:
            if lock_fd is not None:
                msvcrt.locking(lock_fd, msvcrt.LK_UNLCK, 1)
                os.close(lock_fd)
                # 删除锁文件
                if os.path.exists(self.lock_file):
                    os.unlink(self.lock_file)
        except Exception as e:
            print(f"⚠️ 释放文件锁失败: {e}")

    def _load_state(self) -> Dict:
        """加载分配状态"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {'allocations': {}, 'last_updated': datetime.now().isoformat()}
        except Exception as e:
            print(f"⚠️ 加载状态文件失败: {e}")
            return {'allocations': {}, 'last_updated': datetime.now().isoformat()}

    def _save_state(self, state: Dict):
        """保存分配状态"""
        try:
            state['last_updated'] = datetime.now().isoformat()
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ 保存状态文件失败: {e}")

    def allocate_account(self, device_serial: str) -> Optional[Dict]:
        """
        为设备分配账号（混合模式）

        Args:
            device_serial: 设备序列号

        Returns:
            分配的账号信息，如果失败返回None
        """
        # 优先使用数据库模式
        if self.enable_database and self.migration_completed:
            return self._allocate_account_database(device_serial)
        else:
            return self._allocate_account_file(device_serial)

    def _allocate_account_database(self, device_serial: str) -> Optional[Dict]:
        """数据库模式分配账号"""
        try:
            account_info = self.db_manager.allocate_account(device_serial)
            if account_info:
                return {
                    'username': account_info['username'],
                    'password': account_info['password'],
                    'name': account_info['display_name'],
                    'session_id': account_info['session_id']
                }
            return None
        except Exception as e:
            print(f"❌ 数据库分配失败，回退到文件模式: {e}")
            return self._allocate_account_file(device_serial)    def _allocate_account_file(self, device_serial: str) -> Optional[Dict]:
        """文件模式分配账号（原有逻辑）"""
        lock_fd = self._acquire_lock()
        if lock_fd is None:
            print(f"❌ 无法获取锁，设备 {device_serial} 账号分配失败")
            return None

        try:
            state = self._load_state()
            allocations = state.get('allocations', {})

            # 检查设备是否已经分配了账号
            if device_serial in allocations:
                existing_account = allocations[device_serial]
                print(f"✅ 设备 {device_serial} 已分配账号: {existing_account.get('username')}")
                return existing_account

            # 找到未分配的账号
            allocated_usernames = {alloc.get('username') for alloc in allocations.values()}

            for account in self.accounts:
                if account['username'] not in allocated_usernames:
                    # 分配这个账号
                    allocations[device_serial] = account.copy()
                    state['allocations'] = allocations
                    self._save_state(state)

                    print(f"✅ 为设备 {device_serial} 分配账号: {account['username']}")
                    return account.copy()

            print(f"❌ 没有可用账号分配给设备 {device_serial}")
            return None

        except Exception as e:
            print(f"❌ 分配账号时发生异常: {e}")
            return None

        finally:
            self._release_lock(lock_fd)

    def release_account(self, device_serial: str) -> bool:
        """
        释放设备的账号分配（混合模式）

        Args:
            device_serial: 设备序列号

        Returns:
            是否成功释放
        """
        # 优先使用数据库模式
        if self.enable_database and self.migration_completed:
            return self._release_account_database(device_serial)
        else:
            return self._release_account_file(device_serial)

    def _release_account_database(self, device_serial: str) -> bool:
        """数据库模式释放账号"""
        try:
            return self.db_manager.release_account(device_serial=device_serial)
        except Exception as e:
            print(f"❌ 数据库释放失败，回退到文件模式: {e}")
            return self._release_account_file(device_serial)

    def _release_account_file(self, device_serial: str) -> bool:
        """文件模式释放账号（原有逻辑）"""
        lock_fd = self._acquire_lock()
        if lock_fd is None:
            print(f"❌ 无法获取锁，设备 {device_serial} 账号释放失败")
            return False

        try:
            state = self._load_state()
            allocations = state.get('allocations', {})

            if device_serial in allocations:
                released_account = allocations.pop(device_serial)
                state['allocations'] = allocations
                self._save_state(state)
                print(f"✅ 设备 {device_serial} 的账号 {released_account.get('username')} 已释放")
                return True
            else:
                print(f"⚠️ 设备 {device_serial} 没有分配的账号")
                return False

        except Exception as e:
            print(f"❌ 释放账号时发生异常: {e}")
            return False

        finally:
            self._release_lock(lock_fd)

    def get_allocation_status(self) -> Dict:
        """获取当前分配状态（混合模式）"""
        if self.enable_database and self.migration_completed:
            return self._get_allocation_status_database()
        else:
            return self._get_allocation_status_file()

    def _get_allocation_status_database(self) -> Dict:
        """数据库模式获取分配状态"""
        try:
            return self.db_manager.get_allocation_status()
        except Exception as e:
            print(f"❌ 数据库获取状态失败，回退到文件模式: {e}")
            return self._get_allocation_status_file()

    def _get_allocation_status_file(self) -> Dict:
        """文件模式获取分配状态"""
        lock_fd = self._acquire_lock()
        if lock_fd is None:
            print("❌ 无法获取锁，获取分配状态失败")
            return {}

        try:
            state = self._load_state()
            return state.get('allocations', {})
        finally:
            self._release_lock(lock_fd)

    def get_available_accounts_count(self) -> int:
        """获取可用账号数量（混合模式）"""
        if self.enable_database and self.migration_completed:
            return self._get_available_accounts_count_database()
        else:
            return self._get_available_accounts_count_file()

    def _get_available_accounts_count_database(self) -> int:
        """数据库模式获取可用账号数量"""
        try:
            return self.db_manager.get_available_accounts_count()
        except Exception as e:
            print(f"❌ 数据库获取可用账号数失败，回退到文件模式: {e}")
            return self._get_available_accounts_count_file()

    def _get_available_accounts_count_file(self) -> int:
        """文件模式获取可用账号数量"""
        lock_fd = self._acquire_lock()
        if lock_fd is None:
            return 0

        try:
            state = self._load_state()
            allocations = state.get('allocations', {})
            allocated_usernames = {alloc.get('username') for alloc in allocations.values()}

            available_count = 0
            for account in self.accounts:
                if account['username'] not in allocated_usernames:
                    available_count += 1

            return available_count
        finally:
            self._release_lock(lock_fd)

    def release_account(self, device_serial: str) -> bool:
        """
        释放设备的账号分配（跨进程安全）

        Args:
            device_serial: 设备序列号

        Returns:
            是否释放成功
        """
        lock_fd = self._acquire_lock()
        if lock_fd is None:
            print(f"❌ 无法获取锁，设备 {device_serial} 账号释放失败")
            return False

        try:
            state = self._load_state()
            allocations = state.get('allocations', {})

            if device_serial in allocations:
                released_account = allocations.pop(device_serial)
                state['allocations'] = allocations
                self._save_state(state)

                print(f"✅ 释放设备 {device_serial} 的账号: {released_account.get('username')}")
                return True
            else:
                print(f"⚠️ 设备 {device_serial} 没有分配账号")
                return True  # 没有分配也算释放成功

        except Exception as e:
            print(f"❌ 释放账号时发生异常: {e}")
            return False

        finally:
            self._release_lock(lock_fd)

    def get_allocation_status(self) -> Dict:
        """获取当前分配状态"""
        lock_fd = self._acquire_lock()
        if lock_fd is None:
            print("❌ 无法获取锁，获取分配状态失败")
            return {}

        try:
            state = self._load_state()
            return state.get('allocations', {})
        finally:
            self._release_lock(lock_fd)

    def get_available_accounts_count(self) -> int:
        """获取可用账号数量"""
        lock_fd = self._acquire_lock()
        if lock_fd is None:
            return 0

        try:
            state = self._load_state()
            allocations = state.get('allocations', {})
            allocated_usernames = {alloc.get('username') for alloc in allocations.values()}

            available_count = 0
            for account in self.accounts:
                if account['username'] not in allocated_usernames:
                    available_count += 1

            return available_count
        finally:
            self._release_lock(lock_fd)

    def clear_all_allocations(self):
        """清空所有分配（用于测试）"""
        lock_fd = self._acquire_lock()
        if lock_fd is None:
            print("❌ 无法获取锁，清空分配失败")
            return

        try:
            state = {
                'allocations': {},
                'last_updated': datetime.now().isoformat()
            }
            self._save_state(state)
            print("✅ 已清空所有账号分配")
        finally:
            self._release_lock(lock_fd)


# 全局单例实例
_windows_account_manager_instance = None
_windows_account_manager_lock = threading.Lock()

def get_windows_cross_process_account_manager() -> WindowsCrossProcessAccountManager:
    """获取Windows跨进程账号管理器单例实例"""
    global _windows_account_manager_instance

    if _windows_account_manager_instance is None:
        with _windows_account_manager_lock:
            if _windows_account_manager_instance is None:
                _windows_account_manager_instance = WindowsCrossProcessAccountManager()

    return _windows_account_manager_instance


if __name__ == "__main__":
    # 测试代码
    print("=== Windows跨进程账号管理器测试 ===")

    manager = get_windows_cross_process_account_manager()

    # 清空现有分配
    manager.clear_all_allocations()

    # 测试分配
    devices = ["5c41023b", "CWM0222215003786", "test_device"]

    print("\n📊 测试账号分配:")
    for device in devices:
        account = manager.allocate_account(device)
        if account:
            print(f"   {device} -> {account.get('username')}")
        else:
            print(f"   {device} -> 分配失败")

    print(f"\n📊 分配状态: {manager.get_allocation_status()}")
    print(f"📊 可用账号数: {manager.get_available_accounts_count()}")

    # 测试重复分配
    print(f"\n🔁 测试重复分配:")
    account = manager.allocate_account("5c41023b")
    print(f"   5c41023b -> {account.get('username') if account else '失败'}")

    # 测试释放
    print(f"\n🗑️ 测试账号释放:")
    manager.release_account("5c41023b")
    print(f"   释放后可用账号数: {manager.get_available_accounts_count()}")
