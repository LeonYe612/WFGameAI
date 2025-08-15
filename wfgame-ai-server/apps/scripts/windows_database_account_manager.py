# -*- coding: utf-8 -*-
"""
Windows 优化的数据库账号管理器
专门为 Windows 环境优化，使用 MySQL 数据库替代文件存储
支持自动数据迁移和高并发分配
"""

import os
import sys
import json
import time
import hashlib
import secrets
import threading
import configparser
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from pathlib import Path

# Windows 特定导入
import winsound
import win32api
import win32con
import win32event
import win32security

# 数据库相关导入
import pymysql
from pymysql.cursors import DictCursor
from dbutils.pooled_db import PooledDB

from django.conf import settings


@dataclass
class AccountInfo:
    """账号信息数据类"""
    id: int
    username: str
    password: str
    display_name: str
    status: str
    created_at: datetime
    last_used: Optional[datetime] = None


@dataclass
class AllocationInfo:
    """分配信息数据类"""
    id: int
    device_serial: str
    account_id: int
    session_id: str
    allocated_at: datetime
    last_heartbeat: datetime
    status: str


class WindowsDatabaseAccountManager:
    """Windows 优化的数据库账号管理器"""

    def __init__(self, config_path: str = None):
        """
        初始化 Windows 数据库账号管理器

        Args:
            config_path: 配置文件路径，默认使用项目根目录的 config.ini
        """
        self.config = self._load_config(config_path)
        self.db_pool = self._create_db_pool()
        self.session_timeout = self.config.get('session_timeout', 3600)  # 1小时
        self.cleanup_interval = self.config.get('cleanup_interval', 300)  # 5分钟
        self.lock = threading.RLock()

        # Windows 特定初始化
        self._init_windows_features()

        # 启动后台清理线程
        self._start_cleanup_thread()

        print("✅ Windows 数据库账号管理器初始化完成")

    def _load_config(self, config_path: str = None) -> Dict[str, any]:
        """加载配置文件"""
        if config_path is None:
            # 获取项目根目录的 config.ini
            current_dir = Path(__file__).parent
            project_root = current_dir.parent.parent.parent
            config_path = project_root / 'config.ini'

        if not Path(config_path).exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        # config = configparser.ConfigParser()
        # config.read(config_path, encoding='utf-8')
        config = settings.CFG._config
        # 数据库配置
        db_config = {
            'host': config.get('database', 'host'),
            'user': config.get('database', 'username'),
            'password': config.get('database', 'password'),
            'database': config.get('database', 'dbname'),
            'port': config.getint('database', 'port', fallback=3306),
            'charset': 'utf8mb4'
        }

        # 其他配置
        other_config = {
            'session_timeout': config.getint('account_manager', 'session_timeout', fallback=3600),
            'cleanup_interval': config.getint('account_manager', 'cleanup_interval', fallback=300),
            'max_concurrent_sessions': config.getint('account_manager', 'max_concurrent_sessions', fallback=100),
            'enable_sound_alerts': config.getboolean('account_manager', 'enable_sound_alerts', fallback=True)
        }

        return {**db_config, **other_config}

    def _create_db_pool(self) -> PooledDB:
        """创建数据库连接池"""
        try:
            pool_config = {
                'creator': pymysql,
                'maxconnections': 20,
                'mincached': 5,
                'maxcached': 15,
                'maxshared': 0,
                'blocking': True,
                'maxusage': None,
                'setsession': [],
                'ping': 1,
                'host': self.config['host'],
                'user': self.config['user'],
                'password': self.config['password'],
                'database': self.config['database'],
                'port': self.config['port'],
                'charset': self.config['charset'],
                'cursorclass': DictCursor,
                'autocommit': False
            }

            pool = PooledDB(**pool_config)

            # 测试连接
            conn = pool.connection()
            self._ensure_tables_exist(conn)
            conn.close()

            print("✅ 数据库连接池创建成功")
            return pool

        except Exception as e:
            print(f"❌ 创建数据库连接池失败: {e}")
            raise

    def _init_windows_features(self):
        """初始化 Windows 特定功能"""
        try:
            # 创建 Windows 事件对象用于进程同步
            self.sync_event = win32event.CreateEvent(None, False, False, "WFGameAI_AccountManager")

            # 设置进程优先级
            handle = win32api.GetCurrentProcess()
            win32api.SetPriorityClass(handle, win32con.HIGH_PRIORITY_CLASS)

            print("✅ Windows 特性初始化完成")

        except Exception as e:
            print(f"⚠️ Windows 特性初始化部分失败: {e}")    def _ensure_tables_exist(self, conn):
        """确保数据库表存在 - 使用现有的ai_game_accounts表"""
        cursor = conn.cursor()

        try:
            # 确保ai_game_accounts表存在 (使用现有的表结构)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS `ai_game_accounts` (
                `account_id` INT PRIMARY KEY AUTO_INCREMENT,
                `username` VARCHAR(100) NOT NULL UNIQUE,
                `password` VARCHAR(255) NOT NULL,
                `phone` VARCHAR(20) DEFAULT NULL,
                `status` ENUM('available', 'in_use', 'disabled') DEFAULT 'available',
                `locked_by` VARCHAR(100) NULL,
                `lock_time` TIMESTAMP NULL,
                `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX `idx_status_locked` (`status`, `locked_by`),
                INDEX `idx_locked_by` (`locked_by`),
                INDEX `idx_username` (`username`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            # 创建操作日志表 (使用ai_前缀)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_account_operations (
                id INT PRIMARY KEY AUTO_INCREMENT,
                operation_type ENUM('allocate', 'release', 'heartbeat', 'expire', 'migrate') NOT NULL,
                device_serial VARCHAR(255) NOT NULL,
                account_id INT,
                session_id VARCHAR(100),
                operation_result ENUM('success', 'failure') NOT NULL,
                error_message TEXT NULL,
                operation_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (account_id) REFERENCES ai_game_accounts(account_id) ON DELETE SET NULL,
                INDEX idx_operation_time (operation_time),
                INDEX idx_device_serial (device_serial),
                INDEX idx_operation_type (operation_type)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)

            conn.commit()
            print("✅ 数据库表结构检查完成 (使用ai_game_accounts表)")

        except Exception as e:
            conn.rollback()
            print(f"❌ 创建数据库表失败: {e}")
            raise
        finally:
            cursor.close()

    def migrate_from_files(self, accounts_file: str = None, state_file: str = None) -> Dict[str, int]:
        """
        从文件系统迁移数据到数据库

        Args:
            accounts_file: 账号文件路径
            state_file: 状态文件路径

        Returns:
            迁移统计信息
        """
        if accounts_file is None:
            accounts_file = Path(__file__).parent / 'datasets' / 'accounts_info' / 'accounts.txt'

        if state_file is None:
            state_file = Path(__file__).parent / 'datasets' / 'accounts_info' / 'allocation_state.json'

        stats = {'accounts_migrated': 0, 'allocations_migrated': 0, 'errors': 0}

        conn = self.db_pool.connection()
        try:
            conn.begin()

            # 迁移账号数据
            if Path(accounts_file).exists():
                stats['accounts_migrated'] = self._migrate_accounts(conn, accounts_file)

            # 迁移分配状态
            if Path(state_file).exists():
                stats['allocations_migrated'] = self._migrate_allocations(conn, state_file)

            conn.commit()

            # 记录迁移操作
            self._log_operation(conn, 'migrate', 'system', None, None, 'success',
                              f"Migrated {stats['accounts_migrated']} accounts, {stats['allocations_migrated']} allocations")

            print(f"✅ 数据迁移完成: {stats}")

            # Windows 通知音效
            if self.config.get('enable_sound_alerts', True):
                winsound.MessageBeep(winsound.MB_OK)

            return stats

        except Exception as e:
            conn.rollback()
            stats['errors'] += 1
            print(f"❌ 数据迁移失败: {e}")
            raise
        finally:
            conn.close()

    def _migrate_accounts(self, conn, accounts_file: str) -> int:
        """迁移账号数据"""
        cursor = conn.cursor()
        migrated_count = 0

        try:
            with open(accounts_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    parts = line.split('\t')
                    if len(parts) < 3:
                        print(f"⚠️ 第 {line_num} 行格式错误，跳过: {line}")
                        continue

                    username, password, display_name = parts[:3]
                    password_hash = self._hash_password(password)

                    # 检查账号是否已存在
                    cursor.execute("SELECT id FROM wf_accounts WHERE username = %s", (username,))
                    if cursor.fetchone():
                        print(f"⚠️ 账号 {username} 已存在，跳过")
                        continue

                    # 插入账号
                    cursor.execute("""
                    INSERT INTO wf_accounts (username, password_hash, display_name, status)
                    VALUES (%s, %s, %s, 'active')
                    """, (username, password_hash, display_name))

                    migrated_count += 1
                    print(f"✅ 迁移账号: {username}")

            return migrated_count

        except Exception as e:
            print(f"❌ 迁移账号文件失败: {e}")
            raise
        finally:
            cursor.close()

    def _migrate_allocations(self, conn, state_file: str) -> int:
        """迁移分配状态"""
        cursor = conn.cursor()
        migrated_count = 0

        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                state_data = json.load(f)

            allocations = state_data.get('allocations', {})

            for device_serial, account_info in allocations.items():
                username = account_info.get('username')
                if not username:
                    continue

                # 获取账号ID
                cursor.execute("SELECT id FROM wf_accounts WHERE username = %s", (username,))
                account_row = cursor.fetchone()
                if not account_row:
                    print(f"⚠️ 账号 {username} 不存在，跳过分配迁移")
                    continue

                account_id = account_row['id']
                session_id = self._generate_session_id()

                # 检查分配是否已存在
                cursor.execute("""
                SELECT id FROM wf_account_allocations
                WHERE device_serial = %s AND status = 'active'
                """, (device_serial,))

                if cursor.fetchone():
                    print(f"⚠️ 设备 {device_serial} 已有活跃分配，跳过")
                    continue

                # 创建分配记录
                cursor.execute("""
                INSERT INTO wf_account_allocations
                (device_serial, account_id, session_id, status)
                VALUES (%s, %s, %s, 'active')
                """, (device_serial, account_id, session_id))

                migrated_count += 1
                print(f"✅ 迁移分配: {device_serial} -> {username}")

            return migrated_count

        except Exception as e:
            print(f"❌ 迁移分配状态失败: {e}")
            raise
        finally:
            cursor.close()

    def allocate_account(self, device_serial: str) -> Optional[Dict[str, any]]:
        """
        为设备分配账号 (事务安全)

        Args:
            device_serial: 设备序列号

        Returns:
            分配的账号信息
        """
        with self.lock:
            conn = self.db_pool.connection()

            try:
                conn.begin()
                cursor = conn.cursor()

                # 1. 检查现有分配
                cursor.execute("""
                SELECT a.id, a.username, a.password_hash, a.display_name,
                       al.session_id, al.allocated_at
                FROM wf_account_allocations al
                JOIN wf_accounts a ON al.account_id = a.id
                WHERE al.device_serial = %s AND al.status = 'active'
                """, (device_serial,))

                existing = cursor.fetchone()
                if existing:
                    # 更新心跳时间
                    cursor.execute("""
                    UPDATE wf_account_allocations
                    SET last_heartbeat = NOW()
                    WHERE device_serial = %s AND status = 'active'
                    """, (device_serial,))

                    conn.commit()

                    result = {
                        'username': existing['username'],
                        'password': self._decrypt_password(existing['password_hash']),
                        'display_name': existing['display_name'],
                        'session_id': existing['session_id'],
                        'allocated_at': existing['allocated_at']
                    }

                    print(f"✅ 设备 {device_serial} 使用现有分配: {result['username']}")
                    return result

                # 2. 查找可用账号
                cursor.execute("""
                SELECT a.id, a.username, a.password_hash, a.display_name
                FROM wf_accounts a
                LEFT JOIN wf_account_allocations al ON a.id = al.account_id AND al.status = 'active'
                WHERE a.status = 'active' AND al.id IS NULL
                ORDER BY a.last_used ASC, a.id ASC
                LIMIT 1
                FOR UPDATE
                """)

                account = cursor.fetchone()
                if not account:
                    conn.rollback()
                    self._log_operation(conn, 'allocate', device_serial, None, None, 'failure', '没有可用账号')
                    print(f"❌ 没有可用账号分配给设备 {device_serial}")
                    return None

                # 3. 创建分配记录
                session_id = self._generate_session_id()
                expected_release = datetime.now() + timedelta(seconds=self.session_timeout)

                cursor.execute("""
                INSERT INTO wf_account_allocations
                (device_serial, account_id, session_id, expected_release_at, status)
                VALUES (%s, %s, %s, %s, 'active')
                """, (device_serial, account['id'], session_id, expected_release))

                # 4. 更新账号最后使用时间
                cursor.execute("""
                UPDATE wf_accounts SET last_used = NOW() WHERE id = %s
                """, (account['id'],))

                conn.commit()

                result = {
                    'username': account['username'],
                    'password': self._decrypt_password(account['password_hash']),
                    'display_name': account['display_name'],
                    'session_id': session_id,
                    'allocated_at': datetime.now()
                }

                # 记录操作日志
                self._log_operation(conn, 'allocate', device_serial, account['id'], session_id, 'success')

                print(f"✅ 为设备 {device_serial} 分配账号: {result['username']}")
                return result

            except Exception as e:
                conn.rollback()
                self._log_operation(conn, 'allocate', device_serial, None, None, 'failure', str(e))
                print(f"❌ 分配账号失败: {e}")
                raise

            finally:
                cursor.close()
                conn.close()

    def release_account(self, device_serial: str = None, session_id: str = None) -> bool:
        """
        释放账号分配

        Args:
            device_serial: 设备序列号
            session_id: 会话ID

        Returns:
            是否释放成功
        """
        if not device_serial and not session_id:
            raise ValueError("必须提供 device_serial 或 session_id")

        with self.lock:
            conn = self.db_pool.connection()

            try:
                conn.begin()
                cursor = conn.cursor()

                # 构建查询条件
                where_clause = []
                params = []

                if device_serial:
                    where_clause.append("device_serial = %s")
                    params.append(device_serial)

                if session_id:
                    where_clause.append("session_id = %s")
                    params.append(session_id)

                where_clause.append("status = 'active'")

                # 更新分配状态
                cursor.execute(f"""
                UPDATE wf_account_allocations
                SET status = 'released'
                WHERE {' AND '.join(where_clause)}
                """, params)

                released_count = cursor.rowcount
                conn.commit()

                if released_count > 0:
                    print(f"✅ 释放了 {released_count} 个账号分配")
                    self._log_operation(conn, 'release', device_serial or 'unknown', None, session_id, 'success')
                    return True
                else:
                    print(f"⚠️ 没有找到要释放的分配")
                    return False

            except Exception as e:
                conn.rollback()
                print(f"❌ 释放账号失败: {e}")
                self._log_operation(conn, 'release', device_serial or 'unknown', None, session_id, 'failure', str(e))
                return False

            finally:
                cursor.close()
                conn.close()

    def update_heartbeat(self, device_serial: str = None, session_id: str = None) -> bool:
        """更新心跳时间"""
        if not device_serial and not session_id:
            return False

        conn = self.db_pool.connection()
        try:
            cursor = conn.cursor()

            where_clause = []
            params = []

            if device_serial:
                where_clause.append("device_serial = %s")
                params.append(device_serial)

            if session_id:
                where_clause.append("session_id = %s")
                params.append(session_id)

            where_clause.append("status = 'active'")

            cursor.execute(f"""
            UPDATE wf_account_allocations
            SET last_heartbeat = NOW()
            WHERE {' AND '.join(where_clause)}
            """, params)

            conn.commit()
            return cursor.rowcount > 0

        except Exception as e:
            print(f"❌ 更新心跳失败: {e}")
            return False
        finally:
            cursor.close()
            conn.close()

    def get_allocation_status(self) -> Dict[str, Dict[str, any]]:
        """获取所有分配状态"""
        conn = self.db_pool.connection()
        try:
            cursor = conn.cursor()

            cursor.execute("""
            SELECT al.device_serial, a.username, a.display_name,
                   al.session_id, al.allocated_at, al.last_heartbeat,
                   al.expected_release_at, al.status
            FROM wf_account_allocations al
            JOIN wf_accounts a ON al.account_id = a.id
            WHERE al.status = 'active'
            ORDER BY al.allocated_at DESC
            """)

            allocations = {}
            for row in cursor.fetchall():
                allocations[row['device_serial']] = {
                    'username': row['username'],
                    'display_name': row['display_name'],
                    'session_id': row['session_id'],
                    'allocated_at': row['allocated_at'],
                    'last_heartbeat': row['last_heartbeat'],
                    'expected_release_at': row['expected_release_at'],
                    'status': row['status']
                }

            return allocations

        except Exception as e:
            print(f"❌ 获取分配状态失败: {e}")
            return {}
        finally:
            cursor.close()
            conn.close()

    def get_available_accounts_count(self) -> int:
        """获取可用账号数量"""
        conn = self.db_pool.connection()
        try:
            cursor = conn.cursor()

            cursor.execute("""
            SELECT COUNT(*) as count
            FROM wf_accounts a
            LEFT JOIN wf_account_allocations al ON a.id = al.account_id AND al.status = 'active'
            WHERE a.status = 'active' AND al.id IS NULL
            """)

            result = cursor.fetchone()
            return result['count'] if result else 0

        except Exception as e:
            print(f"❌ 获取可用账号数量失败: {e}")
            return 0
        finally:
            cursor.close()
            conn.close()

    def cleanup_expired_allocations(self) -> int:
        """清理过期分配"""
        conn = self.db_pool.connection()
        try:
            conn.begin()
            cursor = conn.cursor()

            # 标记过期分配
            cursor.execute("""
            UPDATE wf_account_allocations
            SET status = 'expired'
            WHERE status = 'active'
            AND (
                last_heartbeat < DATE_SUB(NOW(), INTERVAL %s SECOND)
                OR expected_release_at < NOW()
            )
            """, (self.session_timeout,))

            expired_count = cursor.rowcount
            conn.commit()

            if expired_count > 0:
                print(f"✅ 清理了 {expired_count} 个过期分配")

                # Windows 通知音效
                if self.config.get('enable_sound_alerts', True):
                    winsound.MessageBeep(winsound.MB_ICONINFORMATION)

            return expired_count

        except Exception as e:
            conn.rollback()
            print(f"❌ 清理过期分配失败: {e}")
            return 0
        finally:
            cursor.close()
            conn.close()

    def _start_cleanup_thread(self):
        """启动后台清理线程"""
        def cleanup_worker():
            while True:
                try:
                    time.sleep(self.cleanup_interval)
                    self.cleanup_expired_allocations()
                except Exception as e:
                    print(f"❌ 清理线程异常: {e}")

        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
        print("✅ 后台清理线程已启动")

    def _hash_password(self, password: str) -> str:
        """密码哈希"""
        salt = secrets.token_hex(16)
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}:{password_hash}"

    def _decrypt_password(self, password_hash: str) -> str:
        """密码解密（这里实际是返回原始密码，生产环境需要真正的加密）"""
        # 注意：这里只是演示，实际应该使用可逆加密或安全存储原始密码
        # 在生产环境中，应该考虑使用 AES 等对称加密算法
        if ':' in password_hash:
            # 这是新格式的哈希密码，无法直接解密
            # 需要在迁移时处理原始密码
            return "******"  # 返回占位符
        return password_hash  # 兜底返回

    def _generate_session_id(self) -> str:
        """生成会话ID"""
        return f"ws_{int(time.time())}_{secrets.token_hex(8)}"

    def _log_operation(self, conn, operation_type: str, device_serial: str,
                      account_id: int = None, session_id: str = None,
                      result: str = 'success', error_msg: str = None):
        """记录操作日志"""
        try:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO wf_account_operations
            (operation_type, device_serial, account_id, session_id, operation_result, error_message)
            VALUES (%s, %s, %s, %s, %s, %s)
            """, (operation_type, device_serial, account_id, session_id, result, error_msg))
            conn.commit()
            cursor.close()
        except Exception as e:
            print(f"⚠️ 记录操作日志失败: {e}")


def get_windows_database_account_manager() -> WindowsDatabaseAccountManager:
    """获取 Windows 数据库账号管理器单例"""
    if not hasattr(get_windows_database_account_manager, '_instance'):
        get_windows_database_account_manager._instance = WindowsDatabaseAccountManager()
    return get_windows_database_account_manager._instance


# 测试代码
if __name__ == "__main__":
    print("🚀 Windows 数据库账号管理器测试")

    try:
        # 创建管理器实例
        manager = get_windows_database_account_manager()

        # 从文件迁移数据
        print("\n📥 开始数据迁移...")
        stats = manager.migrate_from_files()
        print(f"📊 迁移统计: {stats}")

        # 测试分配
        test_devices = ["test_device_1", "test_device_2", "test_device_3"]

        print("\n📱 测试账号分配:")
        allocations = {}
        for device in test_devices:
            account = manager.allocate_account(device)
            if account:
                allocations[device] = account
                print(f"   ✅ {device} -> {account['username']}")
            else:
                print(f"   ❌ {device} -> 分配失败")

        # 查看分配状态
        print(f"\n📊 当前分配状态:")
        status = manager.get_allocation_status()
        for device, info in status.items():
            print(f"   {device}: {info['username']} (会话: {info['session_id']})")

        print(f"\n📈 可用账号数量: {manager.get_available_accounts_count()}")

        # 测试心跳更新
        print(f"\n💓 测试心跳更新...")
        for device in allocations.keys():
            if manager.update_heartbeat(device_serial=device):
                print(f"   ✅ {device} 心跳更新成功")

        # 测试释放
        print(f"\n🗑️ 测试账号释放...")
        if test_devices:
            device_to_release = test_devices[0]
            if manager.release_account(device_serial=device_to_release):
                print(f"   ✅ {device_to_release} 释放成功")

        print(f"\n📈 释放后可用账号数量: {manager.get_available_accounts_count()}")

        print("\n✅ 测试完成")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
