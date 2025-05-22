#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================
Description:
检查并验证报告模板文件和URL
Author: WFGame AI Team
CreateDate: 2025-05-22
===============================
"""

import os
import glob
import re
from bs4 import BeautifulSoup
import shutil

# 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 静态文件目录
STATIC_DIR = os.path.join(BASE_DIR, 'staticfiles')
PAGES_DIR = os.path.join(STATIC_DIR, 'pages')

# 报告目录
REPORTS_DIR = os.path.join(BASE_DIR, 'apps', 'reports')
SUMMARY_REPORTS_DIR = os.path.join(REPORTS_DIR, 'summary_reports')

def backup_file(filepath):
    """备份文件"""
    backup_path = filepath + '.bak'
    print(f"备份文件: {filepath} -> {backup_path}")
    shutil.copy2(filepath, backup_path)
    return backup_path

def validate_html_file(filepath):
    """检查HTML文件中是否有未替换的Django模板变量"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 查找Django模板变量 {{ ... }}
    template_vars = re.findall(r'{{(.*?)}}', content)

    if template_vars:
        print(f"在文件 {filepath} 中发现未替换的模板变量:")
        for var in template_vars:
            print(f"  - {var.strip()}")
        return template_vars

    return []

def fix_html_template(filepath):
    """修复HTML文件中未替换的Django模板变量"""
    # 备份原文件
    backup_file(filepath)

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 替换模板变量，例如将 {{ report_id }} 替换为 ${report.report_id}
    modified_content = re.sub(r'{{(\s*report_id\s*)}}', r'${report.report_id}', content)

    # 也可以处理其他模板变量
    # modified_content = re.sub(r'{{(\s*var_name\s*)}}', r'${some.var_name}', modified_content)

    if modified_content != content:
        print(f"修复文件: {filepath}")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(modified_content)
        return True

    return False

def fix_report_urls():
    """修复reports.py中的URL路径"""
    reports_api_file = os.path.join(BASE_DIR, 'api', 'reports.py')

    if not os.path.exists(reports_api_file):
        print(f"错误: 找不到文件 {reports_api_file}")
        return False

    # 备份原文件
    backup_file(reports_api_file)

    with open(reports_api_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 确保URL使用新的目录路径
    modified_content = content.replace(
        "'url': f'/static/reports/{filename}'",
        "'url': f'/static/reports/summary_reports/{filename}'"
    )

    if modified_content != content:
        print(f"修复文件: {reports_api_file}")
        with open(reports_api_file, 'w', encoding='utf-8') as f:
            f.write(modified_content)
        return True

    return False

def main():
    """主函数"""
    print("开始检查报告模板文件和URL...")

    # 1. 检查HTML文件中是否有未替换的Django模板变量
    html_files = []
    html_files.extend(glob.glob(os.path.join(PAGES_DIR, '*.html')))

    files_with_template_vars = []
    for html_file in html_files:
        template_vars = validate_html_file(html_file)
        if template_vars:
            files_with_template_vars.append((html_file, template_vars))

    # 2. 修复HTML文件中未替换的Django模板变量
    if files_with_template_vars:
        print("\n开始修复HTML文件中未替换的模板变量...")
        for filepath, _ in files_with_template_vars:
            fixed = fix_html_template(filepath)
            if fixed:
                print(f"已修复: {filepath}")
            else:
                print(f"未修复: {filepath}")
    else:
        print("\n未发现需要修复的HTML文件")

    # 3. 修复reports.py中的URL路径
    print("\n开始修复reports.py中的URL路径...")
    fixed = fix_report_urls()
    if fixed:
        print("已修复reports.py中的URL路径")
    else:
        print("reports.py中的URL路径不需要修复")

    print("\n检查和修复完成!")

if __name__ == "__main__":
    main()
