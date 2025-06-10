#!/usr/bin/env python3
"""
清理数据库中的Warframe项目和无效数据
"""
import os
import sys

# 设置路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def cleanup_projects():
    """清理项目数据"""
    print("=== 项目数据清理 ===")

    try:
        from apps.project_monitor.database import db_manager
        from apps.project_monitor.models import Project, ExecutionLog, ClassStatistics

        # 初始化数据库
        db_manager.init_database()
        db = db_manager.get_session()

        try:
            # 查找所有项目
            all_projects = db.query(Project).all()
            print(f"找到 {len(all_projects)} 个项目")

            # 删除Warframe相关项目
            warframe_projects = db.query(Project).filter(
                Project.name.ilike('%warframe%')
            ).all()

            for project in warframe_projects:
                print(f"删除项目: {project.name} (ID: {project.id})")

                # 删除相关的执行日志
                logs_deleted = db.query(ExecutionLog).filter(
                    ExecutionLog.project_id == project.id
                ).delete()
                print(f"  删除了 {logs_deleted} 条执行日志")

                # 删除相关的类统计
                stats_deleted = db.query(ClassStatistics).filter(
                    ClassStatistics.project_id == project.id
                ).delete()
                print(f"  删除了 {stats_deleted} 条类统计")

                # 删除项目
                db.delete(project)

            # 删除测试项目
            test_projects = db.query(Project).filter(
                Project.name.ilike('%测试%')
            ).all()

            for project in test_projects:
                print(f"删除测试项目: {project.name} (ID: {project.id})")

                # 删除相关数据
                db.query(ExecutionLog).filter(
                    ExecutionLog.project_id == project.id
                ).delete()

                db.query(ClassStatistics).filter(
                    ClassStatistics.project_id == project.id
                ).delete()

                db.delete(project)

            # 提交更改
            db.commit()

            # 查看剩余项目
            remaining_projects = db.query(Project).all()
            print(f"\n清理后剩余 {len(remaining_projects)} 个项目:")
            for project in remaining_projects:
                print(f"  - {project.name} (ID: {project.id})")

            if len(remaining_projects) == 0:
                print("✓ 所有项目已清理完毕")

        finally:
            db.close()

        return True

    except Exception as e:
        print(f"✗ 清理失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def cleanup_orphan_data():
    """清理孤立数据"""
    print("\n=== 清理孤立数据 ===")

    try:
        from apps.project_monitor.database import db_manager
        from apps.project_monitor.models import ExecutionLog, ClassStatistics

        db = db_manager.get_session()

        try:
            # 清理没有对应项目的执行日志
            orphan_logs = db.query(ExecutionLog).filter(
                ~ExecutionLog.project_id.in_(
                    db.query(Project.id)
                )
            ).delete(synchronize_session=False)

            print(f"删除了 {orphan_logs} 条孤立执行日志")

            # 清理没有对应项目的类统计
            orphan_stats = db.query(ClassStatistics).filter(
                ~ClassStatistics.project_id.in_(
                    db.query(Project.id)
                )
            ).delete(synchronize_session=False)

            print(f"删除了 {orphan_stats} 条孤立类统计")

            db.commit()
            print("✓ 孤立数据清理完成")

        finally:
            db.close()

        return True

    except Exception as e:
        print(f"✗ 孤立数据清理失败: {e}")
        return False

def main():
    """主函数"""
    print("开始数据库清理...")

    success1 = cleanup_projects()
    success2 = cleanup_orphan_data()

    if success1 and success2:
        print("\n🎉 数据库清理完成！")
        print("现在数据库中只有真实的项目数据，没有虚假数据。")
    else:
        print("\n❌ 数据库清理失败，请检查错误信息。")

if __name__ == "__main__":
    main()
