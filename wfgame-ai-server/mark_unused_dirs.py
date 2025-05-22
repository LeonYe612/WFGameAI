#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mark_unused_dirs.py
标记不再使用的目录，添加_useless后缀，以便用户手动检查和删除
"""

import os
import sys

def mark_unused_directories():
    """
    遍历指定的目录，查找并标记不再使用的文件夹
    """
    # 获取项目根目录
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # 要标记的目录列表 (相对于项目根目录)
    unused_dirs = [
        os.path.join('apps', 'staticfiles', 'reports'),
        os.path.join('apps', 'staticfiles', 'ui_run'),
        os.path.join('outputs', 'WFGameAI-reports'),
        os.path.join('outputs', 'device_reports')
    ]

    marked_count = 0

    print("开始标记不再使用的目录...")

    for dir_path in unused_dirs:
        # 将相对路径转换为绝对路径
        abs_path = os.path.join(base_dir, dir_path)

        # 检查目录是否存在
        if os.path.exists(abs_path) and os.path.isdir(abs_path):
            # 构造新名称
            new_name = abs_path + '_useless'

            try:
                # 重命名目录
                os.rename(abs_path, new_name)
                print(f"已重命名: {abs_path} -> {new_name}")
                marked_count += 1
            except Exception as e:
                print(f"重命名失败 {abs_path}: {e}")

    print(f"\n标记完成，共处理 {marked_count} 个目录。")
    print("请手动检查这些标记为_useless的目录是否确实不再使用，确认后可以手动删除它们。")

if __name__ == "__main__":
    mark_unused_directories()
    input("\n按回车键退出...")
