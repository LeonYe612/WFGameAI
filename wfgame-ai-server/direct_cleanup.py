#!/usr/bin/env python3
"""
直接清理数据库中的Warframe项目
"""
import sqlite3
import os

def cleanup_warframe_projects():
    """直接从SQLite数据库中删除Warframe项目"""
    db_path = "project_monitor.db"

    if not os.path.exists(db_path):
        print("数据库文件不存在")
        return

    print("=== 直接清理Warframe项目 ===")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 查看当前项目
        cursor.execute("SELECT id, name, description FROM projects")
        projects = cursor.fetchall()

        print(f"当前项目列表：")
        for project in projects:
            print(f"  ID: {project[0]}, 名称: {project[1]}, 描述: {project[2]}")

        # 查找Warframe相关项目
        cursor.execute("SELECT id, name FROM projects WHERE name LIKE '%arframe%' OR name LIKE '%测试%'")
        warframe_projects = cursor.fetchall()

        if warframe_projects:
            print(f"\n找到 {len(warframe_projects)} 个需要删除的项目：")
            for project in warframe_projects:
                print(f"  - ID: {project[0]}, 名称: {project[1]}")

            # 删除相关记录
            for project in warframe_projects:
                project_id = project[0]

                # 删除执行日志
                cursor.execute("DELETE FROM execution_logs WHERE project_id = ?", (project_id,))
                logs_deleted = cursor.rowcount

                # 删除类统计
                cursor.execute("DELETE FROM class_statistics WHERE project_id = ?", (project_id,))
                stats_deleted = cursor.rowcount

                # 删除项目
                cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))

                print(f"  删除项目 {project[1]} (ID: {project_id})")
                print(f"    - 执行日志: {logs_deleted} 条")
                print(f"    - 类统计: {stats_deleted} 条")

            conn.commit()
            print(f"\n✓ 成功删除 {len(warframe_projects)} 个项目及相关数据")

        else:
            print("\n未找到Warframe相关项目")

        # 显示清理后的项目列表
        cursor.execute("SELECT id, name, description FROM projects")
        remaining_projects = cursor.fetchall()

        print(f"\n清理后剩余项目数量: {len(remaining_projects)}")
        if remaining_projects:
            for project in remaining_projects:
                print(f"  - ID: {project[0]}, 名称: {project[1]}")
        else:
            print("  数据库已清空")

        conn.close()

    except Exception as e:
        print(f"清理失败: {e}")

if __name__ == "__main__":
    cleanup_warframe_projects()
