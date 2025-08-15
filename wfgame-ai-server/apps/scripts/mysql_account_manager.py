# -*- coding: utf-8 -*-
"""
MySQL分布式账号管理器
严格按照WFGameAI多设备并发执行优化方案实现
支持原子性事务操作，彻底解决账号分配冲突
"""

import os
import sys
import json
import time
import configparser
from typing import List, Dict, Optional
from datetime import datetime
import pymysql
from pymysql.cursors import DictCursor
from pymysql.connections import Connection
from dbutils.pooled_db import PooledDB
import threading
from django.conf import settings


class AccountAllocationError(Exception):
    """账号分配失败异常"""
    pass


class AccountReleaseError(Exception):
    """账号释放失败异常"""
    pass


class SystemResourceStatus:
    """系统资源状态类"""

    def __init__(self, cpu_usage: float, memory_usage: float,
                 optimal_concurrency: int, max_safe_concurrency: int):
        self.cpu_usage = cpu_usage
        self.memory_usage = memory_usage
        self.optimal_concurrency = optimal_concurrency
        self.max_safe_concurrency = max_safe_concurrency


class MySQLDistributedAccountManager:
    """MySQL分布式账号管理器"""

    def __init__(self, mysql_config: dict = None):
        """
        初始化MySQL分布式账号管理器

        Args:
            mysql_config: MySQL配置字典，如果为None则从config.ini读取
        """
        self.mysql_config = mysql_config or self._load_mysql_config()
        self.connection_pool = self._create_connection_pool()
        self.lock = threading.Lock()

    def _load_mysql_config(self) -> dict:
        """从config.ini加载MySQL配置"""
        try:
            # 获取项目根目录的config.ini
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
            config_path = os.path.join(project_root, 'config.ini')

            if not os.path.exists(config_path):
                raise FileNotFoundError(f"配置文件不存在: {config_path}")

            # config = configparser.ConfigParser()
            # config.read(config_path, encoding='utf-8')
            config = settings.CFG._config
            mysql_config = {
                'host': config.get('database', 'host'),
                'user': config.get('database', 'username'),
                'password': config.get('database', 'password'),
                'database': config.get('database', 'dbname'),
                'charset': 'utf8mb4',
                'cursorclass': DictCursor
            }

            print(f"✅ MySQL配置加载成功: {mysql_config['host']}:{mysql_config['database']}")
            return mysql_config

        except Exception as e:
            print(f"❌ 加载MySQL配置失败: {e}")
            raise

    def _create_connection_pool(self) -> PooledDB:
        """创建MySQL连接池"""
        try:
            pool = PooledDB(
                creator=pymysql,
                maxconnections=20,  # 最大连接数
                mincached=5,        # 最小缓存连接数
                maxcached=10,       # 最大缓存连接数
                maxshared=0,        # 最大共享连接数
                blocking=True,      # 连接池满时是否阻塞
                maxusage=None,      # 单个连接最大使用次数
                setsession=[],      # 连接初始化命令
                ping=1,             # 连接检查间隔
                **self.mysql_config
            )

            # 测试连接
            conn = pool.connection()
            conn.close()

            print("✅ MySQL连接池创建成功")
            return pool

        except Exception as e:
            print(f"❌ 创建MySQL连接池失败: {e}")
            raise

    def allocate_account_batch(self, device_serials: List[str]) -> Dict[str, dict]:
        """
        批量分配账号，原子性操作避免冲突

        Args:
            device_serials: 设备序列号列表

        Returns:
            Dict[str, dict]: {device_serial: account_info, ...}
        """
        with self.lock:
            conn = self.connection_pool.connection()

            try:
                conn.begin()
                cursor = conn.cursor()

                allocations = {}

                for device_serial in device_serials:                    # 检查设备是否已有分配
                    cursor.execute("""
                        SELECT account_id, username, password, phone
                        FROM ai_game_accounts
                        WHERE locked_by = %s AND status = 'in_use'
                    """, (device_serial,))

                    existing_account = cursor.fetchone()

                    if existing_account:
                        # 设备已有分配，返回现有账号
                        allocations[device_serial] = existing_account
                        print(f"✅ 设备 {device_serial} 已分配账号: {existing_account['username']}")
                        continue                    # 查找可用账号
                    cursor.execute("""
                        SELECT account_id, username, password, phone
                        FROM ai_game_accounts
                        WHERE status = 'available'
                        AND locked_by IS NULL
                        ORDER BY account_id
                        LIMIT 1 FOR UPDATE
                    """)

                    account = cursor.fetchone()

                    if account:                        # 锁定账号
                        cursor.execute("""
                            UPDATE ai_game_accounts
                            SET status = 'in_use', locked_by = %s, lock_time = NOW()
                            WHERE account_id = %s
                        """, (device_serial, account['account_id']))

                        allocations[device_serial] = account
                        print(f"✅ 为设备 {device_serial} 分配账号: {account['username']}")

                    else:
                        print(f"❌ 没有可用账号分配给设备 {device_serial}")

                conn.commit()
                print(f"✅ 批量分配完成，成功分配 {len(allocations)} 个账号")
                return allocations

            except Exception as e:
                conn.rollback()
                error_msg = f"账号分配失败: {e}"
                print(f"❌ {error_msg}")
                raise AccountAllocationError(error_msg)

            finally:
                cursor.close()
                conn.close()

    def release_account_batch(self, device_serials: List[str]):
        """
        批量释放账号

        Args:
            device_serials: 设备序列号列表
        """
        with self.lock:
            conn = self.connection_pool.connection()

            try:
                conn.begin()
                cursor = conn.cursor()

                released_count = 0

                for device_serial in device_serials:
                    cursor.execute("""
                        UPDATE ai_game_accounts
                        SET status = 'available', locked_by = NULL, lock_time = NULL
                        WHERE locked_by = %s AND status = 'in_use'
                    """, (device_serial,))

                    if cursor.rowcount > 0:
                        released_count += 1
                        print(f"✅ 释放设备 {device_serial} 的账号")

                conn.commit()
                print(f"✅ 批量释放完成，共释放 {released_count} 个账号")

            except Exception as e:
                conn.rollback()
                error_msg = f"账号释放失败: {e}"
                print(f"❌ {error_msg}")
                raise AccountReleaseError(error_msg)

            finally:
                cursor.close()
                conn.close()

    def allocate_account(self, device_serial: str) -> Optional[Dict]:
        """
        为单个设备分配账号

        Args:
            device_serial: 设备序列号

        Returns:
            Dict: 账号信息或None
        """
        return self.allocate_account_batch([device_serial]).get(device_serial)

    def release_account(self, device_serial: str):
        """
        释放单个设备的账号

        Args:
            device_serial: 设备序列号
        """
        self.release_account_batch([device_serial])

    def get_account(self, device_serial: str) -> Optional[Dict]:
        """
        获取设备已分配的账号

        Args:
            device_serial: 设备序列号

        Returns:
            Dict: 账号信息或None
        """
        conn = self.connection_pool.connection()

        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT account_id, username, password, phone
                FROM ai_game_accounts
                WHERE locked_by = %s AND status = 'in_use'
            """, (device_serial,))

            return cursor.fetchone()

        except Exception as e:
            print(f"❌ 获取设备账号失败: {e}")
            return None

        finally:
            cursor.close()
            conn.close()

    def get_allocation_status(self) -> Dict[str, str]:
        """
        获取当前分配状态

        Returns:
            Dict[str, str]: {device_serial: username, ...}
        """
        conn = self.connection_pool.connection()

        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT locked_by, username
                FROM ai_game_accounts
                WHERE status = 'in_use' AND locked_by IS NOT NULL
            """)

            results = cursor.fetchall()
            return {row['locked_by']: row['username'] for row in results}

        except Exception as e:
            print(f"❌ 获取分配状态失败: {e}")
            return {}

        finally:
            cursor.close()
            conn.close()

    def get_available_accounts_count(self) -> int:
        """
        获取可用账号数量

        Returns:
            int: 可用账号数量
        """
        conn = self.connection_pool.connection()

        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM ai_game_accounts
                WHERE status = 'available' AND locked_by IS NULL
            """)

            result = cursor.fetchone()
            return result['count'] if result else 0

        except Exception as e:
            print(f"❌ 获取可用账号数量失败: {e}")
            return 0

        finally:
            cursor.close()
            conn.close()

    def clear_all_allocations(self):
        """清空所有分配（用于测试和重置）"""
        with self.lock:
            conn = self.connection_pool.connection()

            try:
                conn.begin()
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE ai_game_accounts
                    SET status = 'available', locked_by = NULL, lock_time = NULL
                    WHERE status = 'in_use'
                """)

                conn.commit()
                print(f"✅ 已清空所有账号分配，共释放 {cursor.rowcount} 个账号")

            except Exception as e:
                conn.rollback()
                print(f"❌ 清空分配失败: {e}")

            finally:
                cursor.close()
                conn.close()

    def ensure_accounts_table(self):
        """确保ai_game_accounts表存在"""
        conn = self.connection_pool.connection()

        try:
            cursor = conn.cursor()

            # 创建accounts表
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
                    INDEX `idx_locked_by` (`locked_by`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            conn.commit()
            print("✅ ai_game_accounts表检查/创建完成")

        except Exception as e:
            print(f"❌ 创建accounts表失败: {e}")

        finally:
            cursor.close()
            conn.close()

    def migrate_accounts_from_json(self, json_file_path: str = None):
        """
        从现有JSON文件迁移账号数据到MySQL

        Args:
            json_file_path: JSON文件路径，默认使用accounts_wfgame_pool.json
        """
        if json_file_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            json_file_path = os.path.join(current_dir, 'datasets', 'accounts_info', 'accounts_wfgame_pool.json')

        if not os.path.exists(json_file_path):
            print(f"❌ 账号JSON文件不存在: {json_file_path}")
            return

        conn = self.connection_pool.connection()

        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                accounts_data = json.load(f)

            conn.begin()
            cursor = conn.cursor()

            migrated_count = 0

            for account in accounts_data:
                try:                    # 检查账号是否已存在
                    cursor.execute("""
                        SELECT account_id FROM ai_game_accounts WHERE username = %s
                    """, (account['username'],))

                    if cursor.fetchone():
                        continue  # 账号已存在，跳过

                    # 插入新账号
                    cursor.execute("""
                        INSERT INTO ai_game_accounts (username, password, phone, status)
                        VALUES (%s, %s, %s, 'available')
                    """, (
                        account['username'],
                        account['password'],
                        account.get('phone', None)
                    ))

                    migrated_count += 1

                except Exception as e:
                    print(f"⚠️ 迁移账号 {account['username']} 失败: {e}")
                    continue

            conn.commit()
            print(f"✅ 账号迁移完成，共迁移 {migrated_count} 个账号")

        except Exception as e:
            conn.rollback()
            print(f"❌ 账号迁移失败: {e}")

        finally:
            cursor.close()
            conn.close()


# 全局MySQL账号管理器实例
_mysql_account_manager = None


def get_mysql_account_manager() -> MySQLDistributedAccountManager:
    """获取MySQL账号管理器实例"""
    global _mysql_account_manager

    if _mysql_account_manager is None:
        _mysql_account_manager = MySQLDistributedAccountManager()
        # 确保表结构存在
        _mysql_account_manager.ensure_accounts_table()

    return _mysql_account_manager


if __name__ == "__main__":
    print("=== MySQL分布式账号管理器测试 ===")

    try:
        # 初始化管理器
        manager = get_mysql_account_manager()

        # 迁移现有账号数据（如果需要）
        print("\n🔄 迁移现有账号数据...")
        manager.migrate_accounts_from_json()

        # 清空现有分配
        print("\n🗑️ 清空现有分配...")
        manager.clear_all_allocations()

        # 测试批量分配
        print("\n📱 测试批量分配...")
        device_serials = ["5c41023b", "CWM0222215003786", "test_device"]
        allocations = manager.allocate_account_batch(device_serials)

        print(f"\n📊 分配结果:")
        for device_serial, account in allocations.items():
            if account:
                print(f"   {device_serial} -> {account['username']}")
            else:
                print(f"   {device_serial} -> 分配失败")

        # 获取分配状态
        print(f"\n📊 分配状态: {manager.get_allocation_status()}")
        print(f"📊 可用账号数: {manager.get_available_accounts_count()}")

        # 测试重复分配
        print(f"\n🔁 测试重复分配...")
        account = manager.allocate_account("5c41023b")
        print(f"   5c41023b -> {account['username'] if account else '失败'}")

        # 测试释放
        print(f"\n🗑️ 测试批量释放...")
        manager.release_account_batch(device_serials[:2])

        print(f"📊 释放后分配状态: {manager.get_allocation_status()}")
        print(f"📊 释放后可用账号数: {manager.get_available_accounts_count()}")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
