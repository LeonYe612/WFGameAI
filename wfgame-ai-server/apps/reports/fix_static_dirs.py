#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
fix_static_dirs.py
该脚本用于整理报告相关目录结构，将报告文件统一迁移至正确的位置，
并修改代码中的路径引用，确保测试报告生成与展示的正确性。
"""

import os
import shutil
import sys
from pathlib import Path

# 设置根目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent

def ensure_dirs():
    """确保所有必要的目录都存在"""
    dirs = [
        # 汇总报告目录
        os.path.join(BASE_DIR, 'apps', 'reports', 'summary_reports'),
        # 单设备报告目录
        os.path.join(BASE_DIR, 'apps', 'reports', 'ui_run', 'WFGameAI.air', 'log'),
        # 静态资源目录及子目录
        os.path.join(BASE_DIR, 'apps', 'reports', 'staticfiles'),
        os.path.join(BASE_DIR, 'apps', 'reports', 'staticfiles', 'css'),
        os.path.join(BASE_DIR, 'apps', 'reports', 'staticfiles', 'js'),
        os.path.join(BASE_DIR, 'apps', 'reports', 'staticfiles', 'fonts'),
        os.path.join(BASE_DIR, 'apps', 'reports', 'staticfiles', 'image'),
    ]

    for dir_path in dirs:
        os.makedirs(dir_path, exist_ok=True)
        print(f"确保目录存在: {dir_path}")

def copy_existing_reports():
    """复制现有报告到新目录结构"""
    # 查找现有的汇总报告
    old_reports_dir = os.path.join(BASE_DIR, 'apps', 'staticfiles', 'reports')
    new_reports_dir = os.path.join(BASE_DIR, 'apps', 'reports', 'summary_reports')

    if os.path.exists(old_reports_dir):
        for item in os.listdir(old_reports_dir):
            src = os.path.join(old_reports_dir, item)
            dst = os.path.join(new_reports_dir, item)
            if os.path.isfile(src):
                shutil.copy2(src, dst)
                print(f"复制报告文件: {src} -> {dst}")

    # 查找现有的设备报告
    old_device_reports = os.path.join(BASE_DIR, 'apps', 'staticfiles', 'ui_run', 'WFGameAI.air', 'log')
    new_device_reports = os.path.join(BASE_DIR, 'apps', 'reports', 'ui_run', 'WFGameAI.air', 'log')

    if os.path.exists(old_device_reports):
        for device_dir in os.listdir(old_device_reports):
            src_dir = os.path.join(old_device_reports, device_dir)
            dst_dir = os.path.join(new_device_reports, device_dir)
            if os.path.isdir(src_dir):
                # 如果目标目录已存在，先删除
                if os.path.exists(dst_dir):
                    shutil.rmtree(dst_dir)
                shutil.copytree(src_dir, dst_dir)
                print(f"复制设备报告目录: {src_dir} -> {dst_dir}")

def copy_static_resources():
    """复制静态资源文件"""
    # 查找Airtest安装目录中的报告静态资源
    try:
        import airtest
        airtest_path = os.path.dirname(airtest.__file__)
        report_path = os.path.join(airtest_path, "report")

        static_dirs = ['css', 'js', 'fonts', 'image']
        target_static_dir = os.path.join(BASE_DIR, 'apps', 'reports', 'staticfiles')

        for res_dir in static_dirs:
            src_dir = os.path.join(report_path, res_dir)
            dst_dir = os.path.join(target_static_dir, res_dir)

            if os.path.exists(src_dir):
                # 清空目标目录
                if os.path.exists(dst_dir):
                    for item in os.listdir(dst_dir):
                        item_path = os.path.join(dst_dir, item)
                        if os.path.isfile(item_path):
                            os.remove(item_path)
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path)

                # 复制文件
                for item in os.listdir(src_dir):
                    s = os.path.join(src_dir, item)
                    d = os.path.join(dst_dir, item)
                    if os.path.isfile(s):
                        shutil.copy2(s, d)
                        print(f"复制静态资源: {s} -> {d}")
                    elif os.path.isdir(s):
                        if os.path.exists(d):
                            shutil.rmtree(d)
                        shutil.copytree(s, d)
                        print(f"复制静态资源目录: {s} -> {d}")

                print(f"静态资源 {res_dir} 已复制")
            else:
                print(f"警告：找不到Airtest静态资源目录: {src_dir}")

    except ImportError:
        print("警告：未找到Airtest模块，无法复制静态资源文件")
    except Exception as e:
        print(f"复制静态资源文件时出错: {e}")

def main():
    """主函数"""
    print("开始整理报告目录结构...")

    # 确保目录结构存在
    ensure_dirs()

    # 复制现有报告
    copy_existing_reports()

    # 复制静态资源
    copy_static_resources()

    print("报告目录结构整理完成。")

if __name__ == "__main__":
    main()
