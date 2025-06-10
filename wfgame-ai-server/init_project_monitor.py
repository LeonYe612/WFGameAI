#!/usr/bin/env python3
"""
项目监控系统初始化脚本
创建数据库表和默认项目
"""
import os
import sys
import django
from pathlib import Path

# 设置Django环境
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = current_dir
sys.path.insert(0, project_root)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wfgame_ai_server_main.settings')
django.setup()

def initialize_project_monitor():
    """初始化项目监控系统"""
    print("=== 项目监控系统初始化 ===")

    try:
        # 导入非Django模式API
        from apps.project_monitor.django_api import _get_database_manager, _get_monitor_service

        print("1. 初始化数据库...")
        db_manager = _get_database_manager()
        if not db_manager:
            print("❌ 数据库管理器初始化失败")
            return False

        # 检查数据库连接
        if not db_manager.check_connection():
            print("❌ 数据库连接失败")
            return False

        # 初始化数据库表
        if not db_manager.init_database():
            print("❌ 数据库表创建失败")
            return False

        print("✅ 数据库初始化成功")

        print("2. 初始化监控服务...")
        monitor_service = _get_monitor_service()
        if not monitor_service:
            print("❌ 监控服务初始化失败")
            return False

        print("✅ 监控服务初始化成功")

        print("3. 创建默认项目...")
        db = db_manager.get_session()
        try:
            # 检查是否已有项目
            projects = monitor_service.get_projects()
            if projects and len(projects) > 0:
                print(f"✅ 已存在 {len(projects)} 个项目")
                for project in projects:            print(f"   - ID: {project.id}, 名称: {project.name}")
            else:
                print("✅ 无数据：当前没有项目，等待用户创建项目")

        except Exception as e:
            print(f"❌ 创建默认项目失败: {e}")
            return False
        finally:
            db.close()

        print("\n🎉 项目监控系统初始化完成!")
        print("现在可以访问 http://127.0.0.1:8000/pages/project_monitor.html 查看监控界面")
        return True

    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = initialize_project_monitor()
    sys.exit(0 if success else 1)
