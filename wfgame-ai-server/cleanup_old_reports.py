#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================
Description:
定期清理旧的报告文件，防止占用过多磁盘空间
Author: WFGame AI Team
CreateDate: 2025-05-29
===============================
"""

import os
import sys
import glob
import argparse
from datetime import datetime, timedelta
import shutil


def cleanup_old_reports(retention_days=30, dry_run=False):
    """
    清理指定天数前的报告文件

    Args:
        retention_days (int): 保留最近多少天的报告
        dry_run (bool): 如果为True，只显示要删除的文件但不实际删除
    """
    print(f"{'[模拟]' if dry_run else ''} 清理 {retention_days} 天前的报告文件...")

    # 项目根目录
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # 统一报告目录
    STATICFILES_REPORTS_DIR = os.path.join(BASE_DIR, "staticfiles", "reports")
    DEVICE_REPORTS_DIR = os.path.join(STATICFILES_REPORTS_DIR, "ui_run", "WFGameAI.air", "log")
    SUMMARY_REPORTS_DIR = os.path.join(STATICFILES_REPORTS_DIR, "summary_reports")

    # 检查目录是否存在
    if not os.path.exists(STATICFILES_REPORTS_DIR):
        print(f"统一报告目录不存在: {STATICFILES_REPORTS_DIR}")
        return

    # 计算截止日期
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    print(f"将删除 {cutoff_date.strftime('%Y-%m-%d')} 之前的报告文件")

    # 1. 清理设备报告目录
    if os.path.exists(DEVICE_REPORTS_DIR):
        device_dirs = [d for d in os.listdir(DEVICE_REPORTS_DIR)
                       if os.path.isdir(os.path.join(DEVICE_REPORTS_DIR, d))]

        deleted_device_dirs = 0
        for device_dir in device_dirs:
            # 设备目录名格式: DeviceName_YYYY-MM-DD-HH-MM-SS
            try:
                # 提取日期部分
                date_part = device_dir.split('_')[-1]
                if len(date_part) != 19:  # YYYY-MM-DD-HH-MM-SS 长度为19
                    continue

                # 解析日期
                dir_date = datetime.strptime(date_part, '%Y-%m-%d-%H-%M-%S')

                # 检查是否应该删除
                if dir_date < cutoff_date:
                    full_path = os.path.join(DEVICE_REPORTS_DIR, device_dir)
                    if dry_run:
                        print(f"[将删除] 设备报告目录: {full_path}")
                    else:
                        print(f"删除设备报告目录: {full_path}")
                        shutil.rmtree(full_path)
                    deleted_device_dirs += 1
            except (ValueError, IndexError):
                # 如果目录名不符合预期格式，跳过
                pass

        print(f"{'[将删除]' if dry_run else '已删除'} {deleted_device_dirs} 个设备报告目录")

    # 2. 清理汇总报告文件
    if os.path.exists(SUMMARY_REPORTS_DIR):
        # 查找所有汇总报告HTML文件
        summary_files = glob.glob(os.path.join(SUMMARY_REPORTS_DIR, "summary_report_*.html"))

        deleted_summary_files = 0
        for summary_file in summary_files:
            try:
                # 获取文件名
                filename = os.path.basename(summary_file)

                # 提取日期部分 (summary_report_YYYY-MM-DD-HH-MM-SS.html)
                date_part = filename.replace("summary_report_", "").replace(".html", "")

                # 解析日期
                file_date = datetime.strptime(date_part, '%Y-%m-%d-%H-%M-%S')

                # 检查是否应该删除
                if file_date < cutoff_date:
                    if dry_run:
                        print(f"[将删除] 汇总报告: {summary_file}")
                    else:
                        print(f"删除汇总报告: {summary_file}")
                        os.remove(summary_file)
                    deleted_summary_files += 1
            except (ValueError, IndexError):
                # 如果文件名不符合预期格式，跳过
                pass

        print(f"{'[将删除]' if dry_run else '已删除'} {deleted_summary_files} 个汇总报告文件")

    # 汇总
    print(f"\n{'[模拟]' if dry_run else ''} 清理完成!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='清理指定天数前的报告文件')
    parser.add_argument('--days', type=int, default=30,
                      help='保留最近多少天的报告 (默认: 30)')
    parser.add_argument('--dry-run', action='store_true',
                      help='只显示要删除的文件但不实际删除')

    args = parser.parse_args()

    cleanup_old_reports(retention_days=args.days, dry_run=args.dry_run)
