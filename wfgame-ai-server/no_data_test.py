#!/usr/bin/env python3
"""
无数据环境测试 - 验证系统在无数据情况下的表现
"""
import os
import sys
import logging

# 设置基本日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_test_environment():
    """设置测试环境"""
    print("=== 设置无数据测试环境 ===")

    # 确保正确的路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, current_dir)

    # 清理可能的Django环境变量
    if 'DJANGO_SETTINGS_MODULE' in os.environ:
        del os.environ['DJANGO_SETTINGS_MODULE']

    print("✓ 环境清理完成")

def test_database_initialization():
    """测试数据库初始化"""
    print("\n=== 测试数据库初始化 ===")

    try:
        from apps.project_monitor.database import db_manager

        # 初始化数据库
        db_manager.init_database()
        print("✓ 数据库初始化成功")

        return True
    except Exception as e:
        print(f"✗ 数据库初始化失败: {e}")
        return False

def test_empty_data_handling():
    """测试空数据处理"""
    print("\n=== 测试空数据处理 ===")

    try:
        from apps.project_monitor.monitor_service import monitor_service

        # 测试获取空项目列表
        projects = monitor_service.get_projects()
        print(f"✓ 获取项目列表成功，项目数: {len(projects)}")

        if len(projects) == 0:
            print("✓ 正确处理空项目列表")
        else:
            print(f"⚠ 数据库中存在 {len(projects)} 个项目:")
            for project in projects:
                print(f"  - {project.name} (ID: {project.id})")

        return True

    except Exception as e:
        print(f"✗ 空数据处理测试失败: {e}")
        return False

def test_api_empty_responses():
    """测试API空响应"""
    print("\n=== 测试API空响应 ===")

    try:
        from apps.project_monitor.django_api import log_ai_execution_sync

        # 测试记录到不存在的项目
        result = log_ai_execution_sync(
            project_name="不存在的项目",
            button_class="test_button",
            success=True,
            scenario="空数据测试"
        )

        print(f"✓ 不存在项目的记录测试: {result}")

        return True

    except Exception as e:
        print(f"✗ API空响应测试失败: {e}")
        return False

def test_dashboard_empty_data():
    """测试仪表板空数据"""
    print("\n=== 测试仪表板空数据 ===")

    try:
        from apps.project_monitor.monitor_service import monitor_service
        from apps.project_monitor.database import db_manager

        db = db_manager.get_session()
        try:
            # 测试不存在的项目ID
            try:
                dashboard = monitor_service.get_project_dashboard(db, 999)
                print("⚠ 意外获取到了不存在项目的仪表板数据")
                return False
            except ValueError as e:
                print(f"✓ 正确处理不存在的项目: {e}")
                return True

        finally:
            db.close()

    except Exception as e:
        print(f"✗ 仪表板空数据测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("开始无数据环境测试...\n")

    # 记录测试结果
    test_results = {}

    # 1. 设置测试环境
    setup_test_environment()

    # 2. 测试数据库初始化
    test_results['database'] = test_database_initialization()

    # 3. 测试空数据处理
    test_results['empty_data'] = test_empty_data_handling()

    # 4. 测试API空响应
    test_results['api_empty'] = test_api_empty_responses()

    # 5. 测试仪表板空数据
    test_results['dashboard_empty'] = test_dashboard_empty_data()

    # 总结测试结果
    print(f"\n=== 无数据环境测试结果 ===")
    total_tests = len(test_results)
    passed_tests = sum(test_results.values())

    for test_name, result in test_results.items():
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name}: {status}")

    print(f"\n通过率: {passed_tests}/{total_tests} ({passed_tests/total_tests*100:.1f}%)")

    if passed_tests == total_tests:
        print("\n🎉 无数据环境测试通过！系统正确处理空数据情况。")
    else:
        print("\n❌ 部分测试失败，需要检查空数据处理逻辑。")

    return passed_tests == total_tests

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ 系统在无数据环境下工作正常！")
    else:
        print("\n❌ 请检查空数据处理逻辑。")
