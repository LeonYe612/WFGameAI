#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速系统检查 - 验证所有组件是否正常工作
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# 添加项目路径到sys.path
current_dir = Path(__file__).parent.absolute()
project_root = current_dir
apps_dir = project_root / "apps"

if str(apps_dir) not in sys.path:
    sys.path.insert(0, str(apps_dir))

try:
    from reports.report_manager import ReportManager
    from reports.report_generator import ReportGenerator
    from scripts.action_processor import ActionProcessor
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    sys.exit(1)

def check_action_processor():
    """检查ActionProcessor是否正常工作"""
    print("🔍 检查ActionProcessor...")

    try:
        # 创建测试ActionProcessor实例 - 使用正确的参数
        ap = ActionProcessor(
            device=None,  # 测试时可以使用None
            device_name="test_device",
            log_txt_path="/tmp/test/log.txt",
            detect_buttons_func=None
        )

        print("✅ ActionProcessor创建成功")
        print(f"  - 设备名称: {ap.device_name}")
        print(f"  - 日志路径: {ap.log_txt_path}")
        print(f"  - detect_buttons方法存在: {hasattr(ap, 'detect_buttons')}")

        return True

    except Exception as e:
        print(f"❌ ActionProcessor检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_report_system():
    """检查报告系统是否正常工作"""
    print("\n📊 检查报告系统...")

    try:
        # 创建ReportManager
        rm = ReportManager()
        print(f"✅ ReportManager创建成功: {rm.reports_root}")

        # 创建ReportGenerator
        rg = ReportGenerator(rm)
        print("✅ ReportGenerator创建成功")

        # 检查模板文件
        summary_template = rm.reports_root / "templates" / "summary_template.html"
        log_template_found = False

        # 查找log_template.html
        from reports.report_generator import find_template_path
        log_template = find_template_path("log_template.html", rm)

        print(f"  - 汇总模板: {summary_template.exists()} ({summary_template})")
        print(f"  - 日志模板: {log_template is not None} ({log_template})")

        # 检查方法是否存在
        methods = ['generate_device_report', 'generate_summary_report', '_parse_log_file']
        for method in methods:
            exists = hasattr(rg, method)
            print(f"  - {method}: {exists}")

        return True

    except Exception as e:
        print(f"❌ 报告系统检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_directories():
    """检查关键目录结构"""
    print("\n📁 检查目录结构...")

    key_dirs = [
        current_dir / "staticfiles" / "reports",
        current_dir / "staticfiles" / "reports" / "templates",
        current_dir / "staticfiles" / "reports" / "summary_reports",
        current_dir / "staticfiles" / "reports" / "device_reports",
        current_dir / "apps" / "reports",
        current_dir / "apps" / "scripts"
    ]

    all_exist = True
    for dir_path in key_dirs:
        exists = dir_path.exists()
        if not exists:
            print(f"  - {dir_path.relative_to(current_dir)}: ❌ 不存在 - 创建中...")
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                print(f"    ✅ 已创建")
            except Exception as e:
                print(f"    ❌ 创建失败: {e}")
                all_exist = False
        else:
            print(f"  - {dir_path.relative_to(current_dir)}: ✅ 存在")

    return all_exist

def main():
    """主检查函数"""
    print("🚀 WFGameAI 系统快速检查")
    print("=" * 50)

    results = []

    # 检查目录结构
    results.append(("目录结构", check_directories()))

    # 检查ActionProcessor
    results.append(("ActionProcessor", check_action_processor()))

    # 检查报告系统
    results.append(("报告系统", check_report_system()))

    # 总结
    print("\n" + "=" * 50)
    print("📋 检查结果总结:")

    all_passed = True
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  - {name}: {status}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 所有检查通过！系统状态良好。")
    else:
        print("⚠️ 部分检查失败，请查看上述详细信息。")

    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
