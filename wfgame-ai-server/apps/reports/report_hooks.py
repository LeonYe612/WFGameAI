#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================
Description:
自动创建集成报告的挂钩脚本
Author: WFGame AI Team
CreateDate: 2025-05-22
===============================
"""

import os
import sys
import shutil
import time
import subprocess
import argparse
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 工作目录
WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 集成报告生成脚本
INTEGRATED_REPORTS_SCRIPT = os.path.join(WORKSPACE_DIR, 'create_integrated_reports.py')

def run_integrated_reports():
    """运行集成报告生成脚本"""
    if not os.path.exists(INTEGRATED_REPORTS_SCRIPT):
        logger.error(f"集成报告脚本不存在: {INTEGRATED_REPORTS_SCRIPT}")
        return False

    try:
        logger.info(f"正在运行集成报告脚本: {INTEGRATED_REPORTS_SCRIPT}")
        result = subprocess.run(
            [sys.executable, INTEGRATED_REPORTS_SCRIPT],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info(f"集成报告脚本执行成功: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"集成报告脚本执行失败: {e}")
        logger.error(f"错误输出: {e.stderr}")
        return False

def hook_summary_report():
    """挂钩汇总报告生成过程，在生成后自动创建集成报告"""
    summary_reports_dir = os.path.join(WORKSPACE_DIR, 'apps', 'reports', 'summary_reports')
    static_dir = os.path.join(WORKSPACE_DIR, 'staticfiles', 'reports', 'summary_reports')

    # 确保静态目录存在
    os.makedirs(static_dir, exist_ok=True)

    # 复制所有汇总报告到静态目录
    for filename in os.listdir(summary_reports_dir):
        if filename.startswith('summary_report_') and filename.endswith('.html'):
            source = os.path.join(summary_reports_dir, filename)
            target = os.path.join(static_dir, filename)
            shutil.copy2(source, target)
            logger.info(f"已复制报告: {filename}")

    # 运行集成报告脚本
    if run_integrated_reports():
        logger.info("集成报告创建成功")
    else:
        logger.error("集成报告创建失败")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='WFGame AI 报告挂钩脚本')
    parser.add_argument('--hook', action='store_true', help='在汇总报告生成后自动运行')
    parser.add_argument('--manual', action='store_true', help='手动运行集成报告生成')

    args = parser.parse_args()

    if args.hook:
        logger.info("正在挂钩汇总报告生成过程...")
        hook_summary_report()
    elif args.manual:
        logger.info("手动运行集成报告生成...")
        run_integrated_reports()
    else:
        logger.info("默认模式：运行集成报告生成...")
        run_integrated_reports()

if __name__ == "__main__":
    main()
