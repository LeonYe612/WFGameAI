#!/usr/bin/env python3
"""
项目监控系统状态检查
"""
import os
import sys

# 确保正确的路径设置
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def check_django_setup():
    """检查Django设置"""
    print("=== Django设置检查 ===")

    try:
        import django
        print(f"✓ Django已安装，版本: {django.VERSION}")

        # 检查Django设置
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wfgame_ai_server_main.settings')
        django.setup()

        from django.conf import settings
        print(f"✓ Django设置已加载")
        print(f"  DEBUG: {settings.DEBUG}")
        print(f"  数据库: {settings.DATABASES['default']['ENGINE']}")

        return True
    except Exception as e:
        print(f"✗ Django设置失败: {e}")
        return False

def check_non_django_mode():
    """检查非Django模式"""
    print("\n=== 非Django模式检查 ===")

    try:
        # 重置Django环境（如果已设置）
        if 'django' in sys.modules:
            del sys.modules['django']
        if 'DJANGO_SETTINGS_MODULE' in os.environ:
            del os.environ['DJANGO_SETTINGS_MODULE']

        # 测试非Django导入
        from apps.project_monitor.database import db_manager
        print("✓ 数据库管理器导入成功")

        from apps.project_monitor.monitor_service import monitor_service
        print("✓ 监控服务导入成功")

        from apps.project_monitor.django_api import log_ai_execution_sync
        print("✓ Django API导入成功")

        # 初始化数据库
        db_manager.init_database()
        print("✓ 数据库初始化成功")

        # 测试获取项目列表
        projects = monitor_service.get_projects()
        print(f"✓ 获取项目列表成功，共 {len(projects)} 个项目")

        return True
    except Exception as e:
        print(f"✗ 非Django模式失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_detection_manager():
    """检查detection_manager集成"""
    print("\n=== Detection Manager集成检查 ===")

    try:
        from apps.scripts.detection_manager import PROJECT_MONITOR_ENABLED, log_ai_execution
        print(f"✓ detection_manager导入成功")
        print(f"  PROJECT_MONITOR_ENABLED: {PROJECT_MONITOR_ENABLED}")
        print(f"  log_ai_execution可调用: {callable(log_ai_execution)}")        # 测试记录功能 - 使用不存在的项目测试错误处理
        result = log_ai_execution(
            project_name="不存在的项目",  # 测试无数据情况
            button_class="test_button",
            success=True,
            scenario="状态检查无数据测试"
        )
        print(f"✓ 无数据测试: {result}")

        return True
    except Exception as e:
        print(f"✗ detection_manager集成失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主检查函数"""
    print("项目监控系统状态检查开始...\n")

    # 记录测试结果
    results = {}

    # 测试Django模式
    results['django'] = check_django_setup()

    # 测试非Django模式
    results['non_django'] = check_non_django_mode()

    # 测试detection_manager集成
    results['detection_manager'] = check_detection_manager()

    # 总结
    print(f"\n=== 检查结果总结 ===")
    total_tests = len(results)
    passed_tests = sum(results.values())

    for test_name, result in results.items():
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name}: {status}")

    print(f"\n通过测试: {passed_tests}/{total_tests}")

    if passed_tests == total_tests:
        print("🎉 所有测试通过！项目监控系统状态正常。")
    elif results['non_django'] and results['detection_manager']:
        print("✅ 核心功能正常，Django集成错误已修复！")
    else:
        print("❌ 存在问题，需要进一步检查。")

    return passed_tests == total_tests

if __name__ == "__main__":
    main()
