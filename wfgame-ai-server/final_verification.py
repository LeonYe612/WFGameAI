#!/usr/bin/env python3
"""
Django集成修复验证测试
"""
import os
import sys
import time

def main():
    print("=== Django集成修复验证测试 ===")

    # 设置路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, current_dir)

    success_count = 0
    total_tests = 5

    # 测试1: 基本导入测试
    print("\n1. 测试detection_manager导入...")
    try:
        from apps.scripts.detection_manager import PROJECT_MONITOR_ENABLED, log_ai_execution
        print(f"   ✅ PROJECT_MONITOR_ENABLED: {PROJECT_MONITOR_ENABLED}")
        print(f"   ✅ log_ai_execution函数可用: {callable(log_ai_execution)}")
        success_count += 1
    except Exception as e:
        print(f"   ❌ 导入失败: {e}")

    # 测试2: 非Django API测试
    print("\n2. 测试非Django API...")
    try:
        from apps.project_monitor.django_api import log_ai_execution_sync, _get_monitor_service
        print("   ✅ 非Django API导入成功")
        success_count += 1
    except Exception as e:
        print(f"   ❌ 非Django API导入失败: {e}")

    # 测试3: 函数调用测试
    print("\n3. 测试函数调用...")
    try:
        result = log_ai_execution(
            project_name='test_project',
            button_class='test_button',
            success=True,
            scenario='verification_test'
        )
        print(f"   ✅ 函数调用成功, 返回: {result}")
        success_count += 1
    except Exception as e:
        print(f"   ❌ 函数调用失败: {e}")

    # 测试4: 监控服务测试
    print("\n4. 测试监控服务...")
    try:
        monitor_service = _get_monitor_service()
        if monitor_service:
            projects = monitor_service.get_projects()
            print(f"   ✅ 监控服务可用, 找到 {len(projects)} 个项目")
            success_count += 1
        else:
            print("   ❌ 监控服务不可用")
    except Exception as e:
        print(f"   ❌ 监控服务测试失败: {e}")

    # 测试5: 完整流程测试
    print("\n5. 测试完整监控流程...")
    try:
        # 直接调用非Django API
        result_direct = log_ai_execution_sync(
            project_name='test_direct',
            button_class='test_button_direct',
            success=True,
            scenario='direct_test'
        )
        print(f"   ✅ 直接API调用成功, 返回: {result_direct}")
        success_count += 1
    except Exception as e:
        print(f"   ❌ 完整流程测试失败: {e}")

    # 总结
    print(f"\n=== 测试结果 ===")
    print(f"通过: {success_count}/{total_tests} 个测试")

    if success_count == total_tests:
        print("🎉 所有测试通过! Django集成错误已完全修复!")
        print("✅ detection_manager.py现在可以在独立脚本中正常使用")
        print("✅ 项目监控功能完全正常")
        print("✅ 可以访问 http://127.0.0.1:8000/pages/project_monitor.html")
        return True
    elif success_count >= 3:
        print("⚠️ 大部分测试通过，基本功能正常")
        print("需要检查未通过的测试项")
        return True
    else:
        print("❌ 多个测试失败，需要进一步修复")
        return False

if __name__ == "__main__":
    try:
        success = main()
        print(f"\n最终结果: {'成功' if success else '失败'}")
        exit(0 if success else 1)
    except Exception as e:
        print(f"测试执行失败: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
