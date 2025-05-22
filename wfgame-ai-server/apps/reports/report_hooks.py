#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================
Description:
概要报告处理脚本
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
WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".."))

def hook_summary_report():
    """处理汇总报告"""
    # 更精确的路径定义
    summary_reports_dir = os.path.join(WORKSPACE_DIR, 'apps', 'reports', 'summary_reports')
    static_dir = os.path.join(WORKSPACE_DIR, 'staticfiles', 'reports', 'summary_reports')

    # 打印路径信息，方便调试
    logger.info(f"源目录: {summary_reports_dir}")
    logger.info(f"目标目录: {static_dir}")

    # 确保目录存在
    if not os.path.exists(summary_reports_dir):
        logger.error(f"源目录不存在: {summary_reports_dir}")
        return

    # 确保静态目录存在
    os.makedirs(static_dir, exist_ok=True)# 复制所有汇总报告到静态目录
    for filename in os.listdir(summary_reports_dir):
        if filename.startswith('summary_report_') and filename.endswith('.html'):
            source = os.path.join(summary_reports_dir, filename)
            target = os.path.join(static_dir, filename)
            shutil.copy2(source, target)
            logger.info(f"已复制报告: {filename}")

    logger.info("概要报告处理完成")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='WFGame AI 报告挂钩脚本')
    parser.add_argument('--hook', action='store_true', help='在汇总报告生成后自动运行')
    parser.add_argument('--manual', action='store_true', help='手动处理概要报告')

    args = parser.parse_args()

    if args.hook:
        logger.info("正在处理概要报告...")
        hook_summary_report()
    elif args.manual:
        logger.info("手动处理概要报告...")
        hook_summary_report()
    else:
        logger.info("默认模式：处理概要报告...")
        hook_summary_report()

if __name__ == "__main__":
    main()
