#!/usr/bin/env python3
"""
测试统一目录结构
验证新的报告目录结构是否正确工作
"""

import os
import sys
import json
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_unified_directory_structure():
    """测试统一目录结构"""
    print("=== 测试统一目录结构 ===")

    try:
        # 导入配置
        from apps.scripts.replay_script import STATICFILES_REPORTS_DIR, DEVICE_REPORTS_DIR, SUMMARY_REPORTS_DIR

        print(f"✓ 成功导入目录配置")
        print(f"  STATICFILES_REPORTS_DIR: {STATICFILES_REPORTS_DIR}")
        print(f"  DEVICE_REPORTS_DIR: {DEVICE_REPORTS_DIR}")
        print(f"  SUMMARY_REPORTS_DIR: {SUMMARY_REPORTS_DIR}")

        # 检查目录是否存在
        print("\n=== 检查目录存在性 ===")
        dirs_to_check = [
            ("根报告目录", STATICFILES_REPORTS_DIR),
            ("设备报告目录", DEVICE_REPORTS_DIR),
            ("汇总报告目录", SUMMARY_REPORTS_DIR)
        ]

        for name, path in dirs_to_check:
            exists = os.path.exists(path)
            print(f"  {name}: {'✓' if exists else '✗'} {path}")
            if not exists:
                os.makedirs(path, exist_ok=True)
                print(f"    → 已创建目录")

        # 测试写入文件
        print("\n=== 测试文件写入 ===")
        test_files = [
            (DEVICE_REPORTS_DIR, "test_device_report.html", "<html><body>Test Device Report</body></html>"),
            (SUMMARY_REPORTS_DIR, "test_summary_report.html", "<html><body>Test Summary Report</body></html>"),
            (STATICFILES_REPORTS_DIR, "test_config.json", '{"test": "unified_structure"}')
        ]

        for dir_path, filename, content in test_files:
            test_file = os.path.join(dir_path, filename)
            try:
                with open(test_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"  ✓ 成功写入: {test_file}")

                # 验证读取
                with open(test_file, 'r', encoding='utf-8') as f:
                    read_content = f.read()
                    if read_content == content:
                        print(f"  ✓ 成功验证: {test_file}")
                    else:
                        print(f"  ✗ 验证失败: {test_file}")

                # 删除测试文件
                os.remove(test_file)
                print(f"  ✓ 清理完成: {test_file}")

            except Exception as e:
                print(f"  ✗ 写入失败: {test_file} - {e}")

        print("\n=== 验证Web访问路径 ===")
        # 验证Web访问路径的正确性
        static_base = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'staticfiles')
        relative_paths = [
            ("设备报告相对路径", os.path.relpath(DEVICE_REPORTS_DIR, static_base)),
            ("汇总报告相对路径", os.path.relpath(SUMMARY_REPORTS_DIR, static_base)),
        ]

        for name, rel_path in relative_paths:
            web_path = f"/static/{rel_path.replace(os.sep, '/')}"
            print(f"  {name}: {web_path}")

        print("\n=== 测试完成 ===")
        print("✓ 统一目录结构测试通过")
        return True

    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_path_consistency():
    """测试路径一致性"""
    print("\n=== 测试路径一致性 ===")

    try:
        # 从不同模块导入路径配置
        from apps.scripts.replay_script import STATICFILES_REPORTS_DIR as script_static
        from apps.scripts.replay_script import DEVICE_REPORTS_DIR as script_device
        from apps.scripts.replay_script import SUMMARY_REPORTS_DIR as script_summary

        from apps.scripts.views import STATICFILES_REPORTS_DIR as views_static
        from apps.scripts.views import DEVICE_REPORTS_DIR as views_device
        from apps.scripts.views import SUMMARY_REPORTS_DIR as views_summary

        # 检查路径一致性
        consistency_checks = [
            ("STATICFILES_REPORTS_DIR", script_static, views_static),
            ("DEVICE_REPORTS_DIR", script_device, views_device),
            ("SUMMARY_REPORTS_DIR", script_summary, views_summary),
        ]

        all_consistent = True
        for name, path1, path2 in consistency_checks:
            if path1 == path2:
                print(f"  ✓ {name}: 路径一致")
            else:
                print(f"  ✗ {name}: 路径不一致")
                print(f"    replay_script: {path1}")
                print(f"    views: {path2}")
                all_consistent = False

        if all_consistent:
            print("✓ 所有模块路径配置一致")
        else:
            print("✗ 存在路径配置不一致问题")

        return all_consistent

    except Exception as e:
        print(f"✗ 路径一致性测试失败: {e}")
        return False

if __name__ == "__main__":
    print("开始测试统一目录结构...")

    # 运行测试
    test1_result = test_unified_directory_structure()
    test2_result = test_path_consistency()

    print(f"\n=== 总结 ===")
    print(f"统一目录结构测试: {'✓ 通过' if test1_result else '✗ 失败'}")
    print(f"路径一致性测试: {'✓ 通过' if test2_result else '✗ 失败'}")

    if test1_result and test2_result:
        print("🎉 所有测试通过！统一目录结构实现成功。")
        sys.exit(0)
    else:
        print("❌ 存在问题需要修复。")
        sys.exit(1)
