#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================
Description: Copy OCR image files listed in a CSV file into a target directory.
Author: WFGame AI Team
CreateDate: 2025-01-27
Version: 1.3
================================
"""

import os
import csv
import shutil
from pathlib import Path
import argparse
from typing import List, Tuple

# ==================== 路径配置区域 - 只需在这里修改 ====================
# 源仓库根目录
SOURCE_BASE = "wfgame-ai-server/media"
# 目标目录
TARGET_DIR = "wfgame-ai-server/media/ocr/repositories/ocr_hit_5pics"
# 默认CSV文件路径
DEFAULT_CSV_PATH = "ocr_hit.csv"
# 默认处理行数限制
DEFAULT_LIMIT = 2000
# ===================================================================


def _read_paths_from_csv(
    csv_path: str,
    limit: int = None,
) -> List[str]:
    """
    Read image relative paths from a CSV file.

    Args:
        csv_path: CSV file path. Each row should contain a relative image path.
        limit: Optional maximum number of rows to load.

    Returns:
        List of relative image paths.
    """
    paths: List[str] = []
    try:
        with open(csv_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f, delimiter=",")
            for row in reader:
                if not row:
                    continue
                if len(row) == 0:
                    continue
                p = (row[0] or "").strip().strip("\"'")
                if not p:
                    continue
                paths.append(p)
                if limit is not None and len(paths) >= limit:
                    break
    except UnicodeDecodeError:
        # 尝试其他编码处理中文路径
        try:
            with open(csv_path, "r", encoding="gbk", newline="") as f:
                reader = csv.reader(f, delimiter=",")
                for row in reader:
                    if not row:
                        continue
                    if len(row) == 0:
                        continue
                    p = (row[0] or "").strip().strip("\"'")
                    if not p:
                        continue
                    paths.append(p)
                    if limit is not None and len(paths) >= limit:
                        break
        except UnicodeDecodeError:
            print(f"错误: 无法读取CSV文件 {csv_path}，编码问题")
            return []
    return paths


def copy_ocr_images(
    csv_path: str,
    limit: int = None,
) -> Tuple[int, int, int]:
    """
    Copy images from the repositories to a target folder according to paths
    listed in a CSV file. If a target file already exists, it will be skipped.

    Args:
        csv_path: CSV file containing relative image paths.
        limit: Maximum number of paths to process in this run.

    Returns:
        Tuple of (copied_count, skipped_exists_count, failed_count).
    """
    # Ensure target directory exists
    os.makedirs(TARGET_DIR, exist_ok=True)

    # Load paths
    image_paths = _read_paths_from_csv(
        csv_path=csv_path,
        limit=limit,
    )

    copied_count = 0
    skipped_exists_count = 0
    failed_count = 0
    failed_files: List[str] = []

    print(f"开始复制 {len(image_paths)} 个图片文件...")
    print(f"源目录: {SOURCE_BASE}")
    print(f"目标目录: {TARGET_DIR}")

    for rel_path in image_paths:
        source_file = os.path.join(SOURCE_BASE, rel_path)
        target_file = os.path.join(TARGET_DIR, os.path.basename(rel_path))
        try:
            # If already exists, skip
            if os.path.exists(target_file):
                skipped_exists_count += 1
                print(f"↷ 已存在，跳过: {os.path.basename(rel_path)}")
                continue

            # Check source file
            if os.path.exists(source_file):
                shutil.copy2(source_file, target_file)
                copied_count += 1
                print(f"✓ 已复制: {os.path.basename(rel_path)}")
            else:
                failed_count += 1
                failed_files.append(rel_path)
                print(f"✗ 源文件不存在: {rel_path}")
        except Exception as e:
            failed_count += 1
            failed_files.append(rel_path)
            print(f"✗ 复制失败: {rel_path} - 错误: {e}")

    print("\n复制完成!")
    print(f"成功复制: {copied_count} 个文件")
    print(f"已存在跳过: {skipped_exists_count} 个文件")
    print(f"失败: {failed_count} 个文件")

    if failed_files:
        print("\n失败的文件列表:")
        for file_path in failed_files:
            print(f"  - {file_path}")

    return copied_count, skipped_exists_count, failed_count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Copy OCR images listed in a CSV file")
    parser.add_argument("--csv", dest="csv_path", default=DEFAULT_CSV_PATH, help="CSV file path")
    parser.add_argument(
        "--limit",
        dest="limit",
        type=int,
        default=DEFAULT_LIMIT,
        help="Max number of rows to process in this run",
    )

    args = parser.parse_args()

    copy_ocr_images(
        csv_path=args.csv_path,
        limit=args.limit,
    ) 