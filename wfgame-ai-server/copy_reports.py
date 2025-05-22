#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================
Description:
复制报告文件到staticfiles目录
Author: WFGame AI Team
CreateDate: 2025-05-22
===============================
"""

import os
import shutil

# 项目路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def copy_reports_to_staticfiles():
    """复制报告文件到静态文件目录"""
    # 源目录 - apps/reports/summary_reports
    source_dir = os.path.join(BASE_DIR, 'apps', 'reports', 'summary_reports')

    # 目标目录 - staticfiles/reports/summary_reports
    target_dir = os.path.join(BASE_DIR, 'staticfiles', 'reports', 'summary_reports')

    print(f"从 {source_dir} 复制到 {target_dir}")

    # 检查源目录是否存在
    if not os.path.exists(source_dir):
        print(f"错误: 源目录不存在: {source_dir}")
        return 0

    # 列出源目录中的文件
    all_files = os.listdir(source_dir)
    report_files = [f for f in all_files if f.startswith('summary_report_') and f.endswith('.html')]

    print(f"源目录中找到 {len(all_files)} 个文件，其中 {len(report_files)} 个是报告文件")

    if not report_files:
        print("警告: 没有找到报告文件")
        return 0

    # 确保目标目录存在
    try:
        os.makedirs(target_dir, exist_ok=True)
        print(f"已创建目标目录: {target_dir}")
    except Exception as e:
        print(f"创建目标目录时出错: {e}")
        return 0

    # 复制文件
    copied_files = []
    for file in report_files:
        try:
            source_path = os.path.join(source_dir, file)
            target_path = os.path.join(target_dir, file)

            print(f"复制: {source_path} -> {target_path}")
            shutil.copy2(source_path, target_path)
            copied_files.append(file)
        except Exception as e:
            print(f"复制文件 {file} 时出错: {e}")

    print(f"总共复制了 {len(copied_files)} 个文件")
    for i, f in enumerate(copied_files, 1):
        print(f"  {i}. {f}")

    # 验证文件是否已复制
    if os.path.exists(target_dir):
        target_files = os.listdir(target_dir)
        print(f"目标目录中现有 {len(target_files)} 个文件")
    else:
        print("错误: 目标目录不存在")

    return len(copied_files)

if __name__ == "__main__":
    print("=" * 60)
    print("开始复制报告文件...")
    print(f"BASE_DIR = {BASE_DIR}")
    print("=" * 60)

    count = copy_reports_to_staticfiles()

    print("=" * 60)
    print(f"完成！复制了 {count} 个文件")
    print("=" * 60)
