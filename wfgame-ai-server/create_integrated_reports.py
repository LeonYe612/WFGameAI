#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================
Description:
创建集成式报告页面，将详细内容直接嵌入主报告中
Author: WFGame AI Team
CreateDate: 2025-05-22
===============================
"""

import os
import re
import sys
import shutil
from bs4 import BeautifulSoup
import glob

# 项目路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 报告相关路径
REPORTS_DIR = os.path.join(BASE_DIR, 'apps', 'reports', 'summary_reports')
UI_REPORTS_DIR = os.path.join(BASE_DIR, 'apps', 'reports', 'ui_run', 'WFGameAI.air', 'log')
STATIC_REPORTS_DIR = os.path.join(BASE_DIR, 'staticfiles', 'reports', 'summary_reports')
STATIC_UI_REPORTS_DIR = os.path.join(BASE_DIR, 'staticfiles', 'reports', 'ui_run', 'WFGameAI.air', 'log')

def ensure_dir(dir_path):
    """确保目录存在"""
    os.makedirs(dir_path, exist_ok=True)
    return dir_path

def copy_device_reports():
    """复制设备报告到静态目录"""
    if not os.path.exists(UI_REPORTS_DIR):
        print(f"设备报告目录不存在: {UI_REPORTS_DIR}")
        return 0

    # 确保静态目录存在
    ensure_dir(STATIC_UI_REPORTS_DIR)

    # 复制所有设备报告目录
    copied = 0
    for device_dir in glob.glob(os.path.join(UI_REPORTS_DIR, "*")):
        if os.path.isdir(device_dir):
            device_name = os.path.basename(device_dir)
            target_dir = os.path.join(STATIC_UI_REPORTS_DIR, device_name)

            # 如果目标目录已存在，先删除
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir)

            # 复制整个目录
            shutil.copytree(device_dir, target_dir)
            copied += 1
            print(f"已复制设备报告: {device_name}")

    return copied

def fix_summary_reports():
    """修复汇总报告中的链接并复制到静态目录"""
    if not os.path.exists(REPORTS_DIR):
        print(f"汇总报告目录不存在: {REPORTS_DIR}")
        return 0

    # 确保静态目录存在
    ensure_dir(STATIC_REPORTS_DIR)

    # 处理所有汇总报告
    fixed = 0
    for report_file in glob.glob(os.path.join(REPORTS_DIR, "summary_report_*.html")):
        try:
            filename = os.path.basename(report_file)
            with open(report_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 修复设备报告的链接
            soup = BeautifulSoup(content, 'html.parser')
            links_fixed = 0

            for link in soup.find_all('a'):
                href = link.get('href')
                if href and '../ui_run/' in href:
                    new_href = href.replace('../ui_run/', '/static/reports/ui_run/')
                    link['href'] = new_href
                    links_fixed += 1

            # 保存修改后的文件到静态目录
            target_file = os.path.join(STATIC_REPORTS_DIR, filename)
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write(str(soup))

            fixed += 1
            print(f"已修复并复制汇总报告: {filename} (修改了 {links_fixed} 个链接)")

        except Exception as e:
            print(f"处理文件 {report_file} 时出错: {e}")

    return fixed

def create_integrated_report():
    """为每个汇总报告创建集成式版本"""
    if not os.path.exists(STATIC_REPORTS_DIR):
        print(f"静态汇总报告目录不存在: {STATIC_REPORTS_DIR}")
        return 0

    integrated = 0
    for report_file in glob.glob(os.path.join(STATIC_REPORTS_DIR, "summary_report_*.html")):
        try:
            filename = os.path.basename(report_file)
            integrated_filename = filename.replace('summary_report_', 'integrated_report_')
            integrated_file = os.path.join(STATIC_REPORTS_DIR, integrated_filename)

            with open(report_file, 'r', encoding='utf-8') as f:
                content = f.read()

            soup = BeautifulSoup(content, 'html.parser')

            # 修改标题
            title = soup.find('title')
            if title:
                title.string = title.string + ' (集成版)'

            # 为每个设备报告添加嵌入框架
            for device in soup.select('.device'):
                link = device.find('a')
                if link and link.get('href'):
                    device_report_url = link.get('href')

                    # 创建iframe元素
                    iframe = soup.new_tag('iframe')
                    iframe['src'] = device_report_url
                    iframe['width'] = '100%'
                    iframe['height'] = '600'
                    iframe['frameborder'] = '0'
                    iframe['allowfullscreen'] = True

                    # 添加折叠面板
                    details = soup.new_tag('details')
                    summary = soup.new_tag('summary')
                    summary.string = '点击展开/折叠详细报告'
                    details.append(summary)
                    details.append(iframe)

                    # 将折叠面板添加到设备区域
                    device.append(details)

            # 保存集成式报告
            with open(integrated_file, 'w', encoding='utf-8') as f:
                f.write(str(soup))

            integrated += 1
            print(f"已创建集成式报告: {integrated_filename}")

        except Exception as e:
            print(f"创建集成式报告 {report_file} 时出错: {e}")

    return integrated

def main():
    """主函数"""
    print("=" * 60)
    print("WFGame AI 报告系统增强工具")
    print("=" * 60)

    # 1. 复制设备报告
    print("\n1. 复制设备报告到静态目录")
    device_reports = copy_device_reports()
    print(f"共复制了 {device_reports} 个设备报告目录")

    # 2. 修复并复制汇总报告
    print("\n2. 修复并复制汇总报告")
    summary_reports = fix_summary_reports()
    print(f"共修复了 {summary_reports} 个汇总报告")

    # 3. 创建集成式报告
    print("\n3. 创建集成式报告")
    integrated_reports = create_integrated_report()
    print(f"共创建了 {integrated_reports} 个集成式报告")

    print("\n所有操作已完成!")
    print("=" * 60)
    print("提示:")
    print("1. 汇总报告URL: /static/reports/summary_reports/summary_report_*.html")
    print("2. 集成式报告URL: /static/reports/summary_reports/integrated_report_*.html")
    print("=" * 60)

if __name__ == "__main__":
    main()
