#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
清理报告目录中的多余空目录
"""

import os
import shutil
from pathlib import Path

def clean_empty_log_dirs():
    """清理空的log子目录"""
    reports_root = Path(r"c:\Users\Administrator\PycharmProjects\WFGameAI\wfgame-ai-server\staticfiles\reports\ui_run\WFGameAI.air\log")
    
    print("🧹 开始清理多余的空log目录...")
    
    if not reports_root.exists():
        print("❌ 报告根目录不存在")
        return
        
    cleaned_count = 0
    
    # 遍历所有设备报告目录
    for device_dir in reports_root.iterdir():
        if device_dir.is_dir():
            log_subdir = device_dir / "log"
            if log_subdir.exists() and log_subdir.is_dir():
                # 检查log子目录是否为空
                try:
                    if not any(log_subdir.iterdir()):  # 目录为空
                        print(f"🗑️  删除空目录: {log_subdir}")
                        log_subdir.rmdir()
                        cleaned_count += 1
                    else:
                        print(f"⚠️  保留非空目录: {log_subdir}")
                        # 列出目录内容
                        for item in log_subdir.iterdir():
                            print(f"     - {item.name}")
                except Exception as e:
                    print(f"❌ 处理目录 {log_subdir} 时出错: {e}")
    
    print(f"✅ 清理完成，共删除 {cleaned_count} 个空目录")

if __name__ == "__main__":
    clean_empty_log_dirs()
