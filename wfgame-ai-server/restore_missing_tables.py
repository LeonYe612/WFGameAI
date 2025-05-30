#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
恢复缺失的数据库表
"""

import mysql.connector
import re
import sys
from pathlib import Path

# 数据库配置
DB_CONFIG = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': 'qa123456',
    'database': 'gogotest_data',
    'charset': 'utf8mb4'
}

def get_current_tables():
    """获取当前数据库中的所有表"""
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    tables = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return set(tables)

def parse_backup_file(backup_file):
    """解析备份文件，提取表的DDL语句"""
    tables_ddl = {}
    tables_data = {}

    with open(backup_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # 分割成不同的表段
    table_sections = re.split(r'-- Table structure for table `([^`]+)`', content)

    for i in range(1, len(table_sections), 2):
        if i+1 < len(table_sections):
            table_name = table_sections[i]
            table_content = table_sections[i+1]

            # 提取CREATE TABLE语句
            create_match = re.search(r'CREATE TABLE `' + table_name + '`[^;]+;', table_content, re.DOTALL)
            if create_match:
                tables_ddl[table_name] = create_match.group(0)

            # 提取INSERT语句
            insert_statements = re.findall(r'INSERT INTO `' + table_name + '`[^;]+;', table_content, re.DOTALL)
            if insert_statements:
                tables_data[table_name] = insert_statements

    return tables_ddl, tables_data

def create_table_safe(table_name, ddl_statement):
    """安全地创建表"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # 先删除表（如果存在）
        cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`")

        # 创建表
        cursor.execute(ddl_statement)

        cursor.close()
        conn.close()
        return True, None
    except Exception as e:
        return False, str(e)

def insert_data_safe(table_name, insert_statements):
    """安全地插入数据"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        for stmt in insert_statements:
            try:
                cursor.execute(stmt)
            except Exception as e:
                print(f"插入数据失败 {table_name}: {str(e)}")
                # 继续尝试其他插入语句

        conn.commit()
        cursor.close()
        conn.close()
        return True, None
    except Exception as e:
        return False, str(e)

def main():
    print("开始执行恢复脚本...")
    backup_file = Path("gogotest_data_backup.sql")
    print(f"检查备份文件: {backup_file.absolute()}")
    if not backup_file.exists():
        print("备份文件不存在!")
        return

    print("正在解析备份文件...")
    tables_ddl, tables_data = parse_backup_file(backup_file)
    print(f"备份文件中找到 {len(tables_ddl)} 个表定义")

    print("正在获取当前数据库表...")
    current_tables = get_current_tables()
    print(f"当前数据库中有 {len(current_tables)} 个表")

    # 找出缺失的表
    backup_tables = set(tables_ddl.keys())
    missing_tables = backup_tables - current_tables
    print(f"缺失的表: {len(missing_tables)} 个")

    if not missing_tables:
        print("没有缺失的表!")
        return

    # 按类别分组显示缺失的表
    categories = {
        'tb_tools_': [],
        'tb_ui_': [],
        'tb_webportal_': [],
        'tb_zentao_': [],
        'tb_version_': [],
        'tb_user_': [],
        'others': []
    }

    for table in missing_tables:
        categorized = False
        for prefix in categories:
            if prefix != 'others' and table.startswith(prefix):
                categories[prefix].append(table)
                categorized = True
                break
        if not categorized:
            categories['others'].append(table)

    print("\n缺失的表按类别分组:")
    for category, tables in categories.items():
        if tables:
            print(f"  {category}: {len(tables)} 个表")

    # 开始恢复表
    print(f"\n开始恢复 {len(missing_tables)} 个缺失的表...")

    success_tables = []
    failed_tables = []
    data_failed_tables = []

    for table_name in sorted(missing_tables):
        print(f"正在创建表: {table_name}")

        if table_name in tables_ddl:
            # 创建表结构
            success, error = create_table_safe(table_name, tables_ddl[table_name])

            if success:
                print(f"  ✓ 表结构创建成功: {table_name}")
                success_tables.append(table_name)

                # 尝试插入数据
                if table_name in tables_data:
                    print(f"  正在插入数据: {table_name}")
                    data_success, data_error = insert_data_safe(table_name, tables_data[table_name])

                    if not data_success:
                        print(f"  ⚠ 数据插入失败: {table_name} - {data_error}")
                        data_failed_tables.append(table_name)
                    else:
                        print(f"  ✓ 数据插入成功: {table_name}")
                else:
                    print(f"  ℹ 无数据需要插入: {table_name}")
            else:
                print(f"  ✗ 表创建失败: {table_name} - {error}")
                failed_tables.append(table_name)

    # 输出结果
    print(f"\n恢复完成!")
    print(f"成功创建表: {len(success_tables)} 个")
    print(f"创建失败表: {len(failed_tables)} 个")
    print(f"数据插入失败表: {len(data_failed_tables)} 个")

    if failed_tables:
        print(f"\n创建失败的表:")
        for table in failed_tables:
            print(f"  - {table}")

    if data_failed_tables:
        print(f"\n数据插入失败的表(但表结构已创建):")
        for table in data_failed_tables:
            print(f"  - {table}")

    # 最终验证
    final_tables = get_current_tables()
    print(f"\n最终数据库表数量: {len(final_tables)} 个")
    remaining_missing = backup_tables - final_tables
    if remaining_missing:
        print(f"仍然缺失的表: {len(remaining_missing)} 个")
    else:
        print("所有表都已成功恢复!")

if __name__ == "__main__":
    main()
