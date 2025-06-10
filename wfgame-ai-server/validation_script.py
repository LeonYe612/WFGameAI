#!/usr/bin/env python3
"""
验证无假数据规则遵循情况
检查所有文件是否包含硬编码数据
"""
import os
import re

def check_hardcoded_data():
    """检查硬编码数据"""
    print("=== 检查硬编码数据遵循情况 ===")

    # 需要检查的硬编码关键词
    hardcoded_patterns = [
        r'["\'`]Warframe["`\']',
        r'["\'`]warframe["`\']',
        r'["\'`]测试项目["`\']',
        r'["\'`]测试数据["`\']',
        r'["\'`]WFGame AI 测试项目["`\']',
        r'["\'`]临时.*项目["`\']',
        r'["\'`]默认.*项目["`\']'
    ]

    # 排除的文件
    exclude_files = [
        'direct_cleanup.py',  # 清理脚本本身可以包含这些词
        'cleanup_database.py',  # 清理脚本本身可以包含这些词
        'WFGameAI-Coding-Standards.md',  # 编码规范文档
        'validation_script.py',  # 本文件
        'no_data_test.py'  # 无数据测试文件
    ]

    # 检查的目录
    check_dirs = [
        'apps',
        'staticfiles',
        '.'  # 根目录的py文件
    ]

    violations = []

    for check_dir in check_dirs:
        if not os.path.exists(check_dir):
            continue

        for root, dirs, files in os.walk(check_dir):
            for file in files:
                if not file.endswith('.py'):
                    continue

                if file in exclude_files:
                    continue

                file_path = os.path.join(root, file)

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    for pattern in hardcoded_patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        if matches:
                            violations.append({
                                'file': file_path,
                                'pattern': pattern,
                                'matches': matches
                            })

                except Exception as e:
                    print(f"⚠ 无法读取文件 {file_path}: {e}")

    # 报告结果
    if violations:
        print(f"❌ 发现 {len(violations)} 个硬编码数据违规:")
        for violation in violations:
            print(f"  文件: {violation['file']}")
            print(f"  模式: {violation['pattern']}")
            print(f"  匹配: {violation['matches']}")
            print()
    else:
        print("✅ 未发现硬编码数据违规")

    return len(violations) == 0

def check_database_content():
    """检查数据库是否包含假数据"""
    print("\n=== 检查数据库内容 ===")

    try:
        import sqlite3

        db_path = "project_monitor.db"
        if not os.path.exists(db_path):
            print("✅ 数据库文件不存在（正常状态）")
            return True

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 检查项目表
        cursor.execute("SELECT COUNT(*) FROM projects")
        project_count = cursor.fetchone()[0]

        if project_count == 0:
            print("✅ 数据库为空，没有假数据")
            result = True
        else:
            print(f"⚠ 数据库中有 {project_count} 个项目:")
            cursor.execute("SELECT id, name, description FROM projects")
            projects = cursor.fetchall()

            fake_data_found = False
            for project in projects:
                project_id, name, description = project
                print(f"  - ID: {project_id}, 名称: {name}")

                # 检查是否为假数据
                if any(keyword in name.lower() for keyword in ['warframe', '测试', 'test', '临时', '默认']):
                    fake_data_found = True
                    print(f"    ❌ 疑似假数据: {name}")

            result = not fake_data_found
            if result:
                print("✅ 项目数据看起来是真实数据")

        conn.close()
        return result

    except Exception as e:
        print(f"❌ 检查数据库失败: {e}")
        return False

def main():
    """主函数"""
    print("验证无假数据规则遵循情况...")

    code_check = check_hardcoded_data()
    db_check = check_database_content()

    print("\n=== 验证结果 ===")
    print(f"代码检查: {'✅ 通过' if code_check else '❌ 失败'}")
    print(f"数据库检查: {'✅ 通过' if db_check else '❌ 失败'}")

    if code_check and db_check:
        print("\n🎉 完全符合无假数据规则！")
    else:
        print("\n❌ 存在违规，需要修复")

    return code_check and db_check

if __name__ == "__main__":
    main()
