#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================
Description:
修复报告中的链接路径问题
Author: WFGame AI Team
CreateDate: 2025-05-22
===============================
"""

import os
import re
from bs4 import BeautifulSoup
import sys

def fix_report_links(report_file):
    """修复报告中的相对链接为绝对链接"""
    try:
        print(f"正在处理文件: {report_file}")

        with open(report_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 使用BeautifulSoup解析HTML
        soup = BeautifulSoup(content, 'html.parser')

        # 修复设备报告链接
        all_links = soup.find_all('a')
        fixed_count = 0

        for link in all_links:
            href = link.get('href')
            if href and '../ui_run/' in href:
                # 转换相对路径为绝对路径
                new_href = href.replace('../ui_run/', '/static/reports/ui_run/')
                link['href'] = new_href
                fixed_count += 1

        if fixed_count > 0:
            print(f"修复了 {fixed_count} 个链接")

            # 保存修改后的文件
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(str(soup))

            print(f"文件已保存: {report_file}")
            return True
        else:
            print("未发现需要修复的链接")
            return False

    except Exception as e:
        print(f"处理文件时出错: {e}")
        return False

def process_all_reports(reports_dir):
    """处理指定目录下的所有报告文件"""
    report_files = [
        os.path.join(reports_dir, f)
        for f in os.listdir(reports_dir)
        if f.startswith('summary_report_') and f.endswith('.html')
    ]

    print(f"找到 {len(report_files)} 个报告文件")

    fixed_count = 0
    for report_file in report_files:
        if fix_report_links(report_file):
            fixed_count += 1

    print(f"总共修复了 {fixed_count} 个文件")
    return fixed_count

if __name__ == "__main__":
    # 设置报告目录
    reports_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'apps', 'reports', 'summary_reports'
    )

    static_reports_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'staticfiles', 'reports', 'summary_reports'
    )

    print(f"报告目录: {reports_dir}")
    print(f"静态报告目录: {static_reports_dir}")

    # 先修复原始报告
    processed = process_all_reports(reports_dir)

    # 然后复制到静态目录
    import shutil
    os.makedirs(static_reports_dir, exist_ok=True)

    for f in os.listdir(reports_dir):
        if f.startswith('summary_report_') and f.endswith('.html'):
            src = os.path.join(reports_dir, f)
            dst = os.path.join(static_reports_dir, f)
            shutil.copy2(src, dst)
            print(f"已复制: {src} -> {dst}")

    print("处理完成!")
