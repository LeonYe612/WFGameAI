#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================
Description:
修复报告路径问题，确保系统能够找到报告文件
Author: WFGame AI Team
CreateDate: 2025-05-22
Version: 1.0
===============================
"""

import os
import shutil
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 获取项目根目录
BASE_DIR = Path(__file__).resolve().parent

def ensure_report_dir_structure():
    """确保报告目录结构正确"""
    # 定义路径
    source_reports_dir = os.path.join(BASE_DIR, 'apps', 'reports', 'summary_reports')
    target_base_dir = os.path.join(BASE_DIR, 'outputs', 'WFGameAI-reports')
    target_reports_dir = os.path.join(target_base_dir, 'ui_reports')

    # 确保目标目录存在
    os.makedirs(target_reports_dir, exist_ok=True)

    # 检查目录是否存在
    if not os.path.exists(source_reports_dir):
        logger.warning(f"源报告目录不存在: {source_reports_dir}")
        return

    # 获取源目录中的所有报告文件
    report_files = [f for f in os.listdir(source_reports_dir)
                    if f.startswith('summary_report_') and f.endswith('.html')]

    if not report_files:
        logger.warning(f"源目录中未找到报告文件: {source_reports_dir}")
        return

    # 将报告文件从源目录复制到目标目录
    for report_file in report_files:
        source_file = os.path.join(source_reports_dir, report_file)
        target_file = os.path.join(target_reports_dir, report_file)

        # 如果目标文件已存在且与源文件相同，则跳过
        if os.path.exists(target_file) and os.path.getsize(source_file) == os.path.getsize(target_file):
            logger.info(f"目标文件已存在且大小相同，跳过复制: {report_file}")
            continue

        try:
            # 复制文件
            shutil.copy2(source_file, target_file)
            logger.info(f"已复制报告文件: {report_file}")
        except Exception as e:
            logger.error(f"复制报告文件失败: {report_file}, 错误: {str(e)}")

    logger.info(f"已将 {len(report_files)} 个报告文件从 {source_reports_dir} 复制到 {target_reports_dir}")

def create_symlink_alternative():
    """创建符号链接（仅适用于支持符号链接的系统）"""
    try:
        # 定义路径
        source_reports_dir = os.path.join(BASE_DIR, 'apps', 'reports', 'summary_reports')
        target_base_dir = os.path.join(BASE_DIR, 'outputs', 'WFGameAI-reports')
        target_reports_dir = os.path.join(target_base_dir, 'ui_reports')

        # 如果目标是文件夹，则先删除
        if os.path.isdir(target_reports_dir):
            # 检查是否为符号链接
            if os.path.islink(target_reports_dir):
                os.unlink(target_reports_dir)
            else:
                logger.warning(f"目标目录已存在且不是符号链接，请手动处理: {target_reports_dir}")
                return

        # 创建父目录
        os.makedirs(target_base_dir, exist_ok=True)

        # 创建符号链接
        os.symlink(source_reports_dir, target_reports_dir, target_is_directory=True)
        logger.info(f"已创建符号链接: {source_reports_dir} -> {target_reports_dir}")
    except Exception as e:
        logger.error(f"创建符号链接失败: {str(e)}")
        logger.info("将使用文件复制方式代替符号链接")
        ensure_report_dir_structure()

if __name__ == "__main__":
    logger.info("开始修复报告路径")

    # 优先尝试创建符号链接，失败则复制文件
    try:
        create_symlink_alternative()
    except Exception as e:
        logger.error(f"创建符号链接失败: {str(e)}")
        logger.info("将使用文件复制方式代替符号链接")
        ensure_report_dir_structure()

    logger.info("报告路径修复完成")
