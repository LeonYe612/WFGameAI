#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================
Description:
验证并修复静态文件配置
Author: WFGame AI Team
CreateDate: 2025-05-22
===============================
"""

import os
import sys
import django

# 设置Django环境
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wfgame_ai_server_main.settings')
django.setup()

from django.conf import settings
import shutil

def check_static_files_config():
    """检查静态文件配置"""
    print("\n=== 静态文件配置 ===")
    print(f"BASE_DIR = {settings.BASE_DIR}")
    print(f"STATIC_URL = {settings.STATIC_URL}")
    print(f"STATICFILES_DIRS = {settings.STATICFILES_DIRS}")

    # 检查报告目录是否在STATICFILES_DIRS中
    reports_dir = os.path.join(settings.BASE_DIR, 'apps', 'reports')
    reports_in_dirs = any(reports_dir in str(d) for d in settings.STATICFILES_DIRS)
    print(f"报告目录在STATICFILES_DIRS中: {reports_in_dirs}")

    return reports_in_dirs

def copy_reports_to_static():
    """复制报告文件到静态文件目录"""
    source_dir = os.path.join(settings.BASE_DIR, 'apps', 'reports', 'summary_reports')
    target_dir = os.path.join(settings.BASE_DIR, 'staticfiles', 'reports', 'summary_reports')

    print(f"\n=== 复制报告文件 ===")
    print(f"源目录: {source_dir}")
    print(f"目标目录: {target_dir}")

    # 确保目标目录存在
    os.makedirs(target_dir, exist_ok=True)

    # 复制文件
    file_count = 0
    for file in os.listdir(source_dir):
        if file.startswith('summary_report_') and file.endswith('.html'):
            source_path = os.path.join(source_dir, file)
            target_path = os.path.join(target_dir, file)

            shutil.copy2(source_path, target_path)
            file_count += 1

    print(f"复制了 {file_count} 个报告文件")
    return file_count > 0

def main():
    """主函数"""
    print("开始验证并修复静态文件配置...")

    # 1. 检查静态文件配置
    config_ok = check_static_files_config()

    # 2. 复制报告文件
    copied = copy_reports_to_static()

    print("\n=== 验证结果 ===")
    print(f"静态文件配置: {'✅ 正常' if config_ok else '❌ 有问题'}")
    print(f"报告文件复制: {'✅ 已复制' if copied else '❌ 复制失败'}")

    if config_ok and copied:
        print("\n✅ 静态文件配置已修复!")
    else:
        print("\n⚠️ 仍然存在一些问题，请查看上面的日志")

if __name__ == "__main__":
    main()
