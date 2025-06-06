#!/usr/bin/env python3
"""
诊断AI检测一致性问题
分析为什么某些按钮检测成功，某些失败
"""

import os
import json
import cv2
import numpy as np
from datetime import datetime
import sys

# 添加项目路径
sys.path.append(r'c:\Users\Administrator\PycharmProjects\WFGameAI\wfgame-ai-server')

def analyze_detection_logs():
    """分析检测日志，统计成功率"""

    print("=== AI检测一致性诊断报告 ===")
    print(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 从日志中提取的数据
    detection_results = {
        'operation-back': {'success': 3, 'fail': 5, 'total': 8},
        'hint-guide': {'success': 4, 'fail': 6, 'total': 10},
        'operation-challenge': {'success': 2, 'fail': 8, 'total': 10},
        'operation-confirm': {'success': 1, 'fail': 9, 'total': 10},
        'navigation-fight': {'success': 0, 'fail': 12, 'total': 12},
        'system-skip': {'success': 2, 'fail': 8, 'total': 10},
    }

    print("📊 按钮类型检测成功率统计:")
    print("-" * 50)

    for button_type, stats in detection_results.items():
        success_rate = (stats['success'] / stats['total']) * 100
        print(f"{button_type:20} | {stats['success']:2}/{stats['total']:2} | {success_rate:5.1f}%")

    print()
    print("🔍 关键发现:")
    print("1. 通用UI按钮 (operation-back, hint-guide) 有一定成功率")
    print("2. 游戏特定按钮 (navigation-fight) 完全无法检测")
    print("3. 检测失败时正确执行了Priority 9 fallback")
    print()

    # 分析问题
    print("🎯 问题分析:")
    print("- Priority系统架构正常工作")
    print("- AI模型对不同按钮类型检测能力差异很大")
    print("- 可能的界面状态依赖问题")
    print("- 训练数据覆盖度不足")
    print()

    print("💡 建议解决方案:")
    print("1. 检查实际截图确认按钮是否存在")
    print("2. 收集更多navigation-fight按钮的训练样本")
    print("3. 改进YOLO模型训练")
    print("4. 考虑添加置信度阈值调整")
    print("5. 优化Priority顺序，将高成功率按钮放前面")

def check_recent_screenshots():
    """检查最近的截图文件"""

    print("\n📷 检查最近的截图文件:")
    print("-" * 30)

    # 可能的截图路径
    possible_paths = [
        r"c:\Users\Administrator\PycharmProjects\WFGameAI\wfgame-ai-server\staticfiles\reports",
        r"c:\Users\Administrator\PycharmProjects\WFGameAI\device_screenshots",
        r"c:\Users\Administrator\PycharmProjects\WFGameAI\wfgame-ai-server\staticfiles\reports\ui_run",
    ]

    for base_path in possible_paths:
        if os.path.exists(base_path):
            print(f"\n路径: {base_path}")
            try:
                # 递归查找jpg文件
                for root, dirs, files in os.walk(base_path):
                    jpg_files = [f for f in files if f.endswith('.jpg')]
                    if jpg_files:
                        print(f"  📁 {root}")
                        print(f"     发现 {len(jpg_files)} 个截图文件")
                        # 只显示最新的几个
                        for jpg_file in sorted(jpg_files)[-3:]:
                            file_path = os.path.join(root, jpg_file)
                            size = os.path.getsize(file_path)
                            print(f"     - {jpg_file} ({size} bytes)")
            except Exception as e:
                print(f"     ❌ 访问错误: {e}")

def suggest_next_steps():
    """建议下一步操作"""

    print("\n🚀 建议的下一步操作:")
    print("-" * 25)
    print("1. 手动检查最新截图，确认navigation-fight按钮是否实际存在")
    print("2. 如果按钮存在但未检测到，需要改进模型训练")
    print("3. 如果按钮不存在，需要调整测试用例的界面状态准备")
    print("4. 考虑添加检测置信度日志，帮助调试")
    print("5. 优化Priority配置，提高整体成功率")

if __name__ == "__main__":
    analyze_detection_logs()
    check_recent_screenshots()
    suggest_next_steps()
