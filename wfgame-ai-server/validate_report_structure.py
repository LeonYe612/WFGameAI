#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================
Description:
验证统一报告目录结构，确保所有目录正确存在和配置
Author: WFGame AI Team
CreateDate: 2025-05-29
===============================
"""

import os
import sys
import json
from datetime import datetime


def validate_directory_structure():
    """验证统一报告目录结构是否正确存在和配置"""
    print("=== 验证统一报告目录结构 ===")

    # 项目根目录
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # 定义应该存在的目录结构
    STATICFILES_REPORTS_DIR = os.path.join(BASE_DIR, "staticfiles", "reports")
    DEVICE_REPORTS_DIR = os.path.join(STATICFILES_REPORTS_DIR, "ui_run", "WFGameAI.air", "log")
    SUMMARY_REPORTS_DIR = os.path.join(STATICFILES_REPORTS_DIR, "summary_reports")

    # 定义要验证的目录列表
    directories_to_validate = [
        ("根报告目录", STATICFILES_REPORTS_DIR),
        ("UI测试报告子目录", os.path.join(STATICFILES_REPORTS_DIR, "ui_run")),
        ("Airtest报告子目录", os.path.join(STATICFILES_REPORTS_DIR, "ui_run", "WFGameAI.air")),
        ("设备报告目录", DEVICE_REPORTS_DIR),
        ("汇总报告目录", SUMMARY_REPORTS_DIR)
    ]

    # 验证目录是否存在，不存在则创建
    all_valid = True
    for name, dir_path in directories_to_validate:
        if os.path.exists(dir_path):
            print(f"✅ {name} 目录存在: {dir_path}")
        else:
            print(f"❌ {name} 目录不存在: {dir_path}")
            try:
                os.makedirs(dir_path, exist_ok=True)
                print(f"   已自动创建目录: {dir_path}")
            except Exception as e:
                print(f"   创建目录失败: {e}")
                all_valid = False

    # 验证模块导入是否正确
    print("\n=== 验证模块导入 ===")
    try:
        # 添加项目路径到sys.path
        sys.path.append(BASE_DIR)

        # 导入replay_script模块，验证路径配置
        from apps.scripts.replay_script import STATICFILES_REPORTS_DIR as rs_reports_dir
        from apps.scripts.replay_script import DEVICE_REPORTS_DIR as rs_device_dir
        from apps.scripts.replay_script import SUMMARY_REPORTS_DIR as rs_summary_dir

        # 测试路径一致性
        rs_paths = {
            "STATICFILES_REPORTS_DIR": rs_reports_dir,
            "DEVICE_REPORTS_DIR": rs_device_dir,
            "SUMMARY_REPORTS_DIR": rs_summary_dir
        }

        # 验证路径一致性
        for name, path in rs_paths.items():
            expected_path = locals()[name]
            if os.path.normpath(path) == os.path.normpath(expected_path):
                print(f"✅ replay_script中的{name}配置正确")
            else:
                print(f"❌ replay_script中的{name}配置不一致")
                print(f"   预期: {expected_path}")
                print(f"   实际: {path}")
                all_valid = False

        # 导入views模块，验证路径配置
        try:
            from apps.reports.views import STATICFILES_REPORTS_DIR as view_reports_dir
            from apps.reports.views import DEVICE_REPORTS_DIR as view_device_dir
            from apps.reports.views import SUMMARY_REPORTS_DIR as view_summary_dir

            # 测试路径一致性
            view_paths = {
                "STATICFILES_REPORTS_DIR": view_reports_dir,
                "DEVICE_REPORTS_DIR": view_device_dir,
                "SUMMARY_REPORTS_DIR": view_summary_dir
            }

            # 验证路径一致性
            for name, path in view_paths.items():
                expected_path = locals()[name]
                if os.path.normpath(path) == os.path.normpath(expected_path):
                    print(f"✅ reports.views中的{name}配置正确")
                else:
                    print(f"❌ reports.views中的{name}配置不一致")
                    print(f"   预期: {expected_path}")
                    print(f"   实际: {path}")
                    all_valid = False

        except ImportError as e:
            print(f"⚠️ 无法导入apps.reports.views模块: {e}")
            all_valid = False

    except ImportError as e:
        print(f"⚠️ 无法导入apps.scripts.replay_script模块: {e}")
        all_valid = False

    # 验证文件写入权限
    print("\n=== 验证文件写入权限 ===")
    test_filename = datetime.now().strftime("test_%Y%m%d_%H%M%S.txt")

    for name, dir_path in directories_to_validate:
        if not os.path.exists(dir_path):
            continue

        test_file = os.path.join(dir_path, test_filename)
        try:
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write(f"测试文件，验证目录权限 - {datetime.now()}")
            print(f"✅ {name} 目录写入权限正常")

            # 读取测试文件
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"✅ {name} 目录读取权限正常")

            # 清理测试文件
            os.remove(test_file)
        except Exception as e:
            print(f"❌ {name} 目录权限测试失败: {e}")
            all_valid = False

    # 总结
    print("\n=== 验证结果 ===")
    if all_valid:
        print("✅ 统一报告目录结构验证通过！")
    else:
        print("❌ 统一报告目录结构验证存在问题，请修复上述错误。")

    return all_valid


def repair_directory_structure():
    """修复统一报告目录结构"""
    print("\n=== 尝试修复目录结构 ===")

    # 项目根目录
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # 定义应该存在的目录结构
    STATICFILES_REPORTS_DIR = os.path.join(BASE_DIR, "staticfiles", "reports")
    DEVICE_REPORTS_DIR = os.path.join(STATICFILES_REPORTS_DIR, "ui_run", "WFGameAI.air", "log")
    SUMMARY_REPORTS_DIR = os.path.join(STATICFILES_REPORTS_DIR, "summary_reports")

    # 确保所有目录存在
    directories_to_create = [
        STATICFILES_REPORTS_DIR,
        os.path.join(STATICFILES_REPORTS_DIR, "ui_run"),
        os.path.join(STATICFILES_REPORTS_DIR, "ui_run", "WFGameAI.air"),
        DEVICE_REPORTS_DIR,
        SUMMARY_REPORTS_DIR
    ]

    for dir_path in directories_to_create:
        try:
            os.makedirs(dir_path, exist_ok=True)
            print(f"✅ 已确保目录存在: {dir_path}")
        except Exception as e:
            print(f"❌ 创建目录失败: {dir_path} - {e}")

    print("\n修复完成。请再次运行验证功能，确认问题已解决。")


if __name__ == "__main__":
    # 解析命令行参数
    if len(sys.argv) > 1 and sys.argv[1].lower() == 'repair':
        repair_directory_structure()
    else:
        validate_directory_structure()

    print("\n使用方法:")
    print(f"  {sys.argv[0]} - 验证统一报告目录结构")
    print(f"  {sys.argv[0]} repair - 修复统一报告目录结构")
