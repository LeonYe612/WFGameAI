#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Author  : HoneyDou
# @Time    : 2025/4/2 17:02
# @File    : generate_report.py
# !/usr/bin/env python3
"""
generate_report.py
作用：根据回放结果生成覆盖率报告，统计按钮和步骤的执行情况。
输入：GameAI/outputs/scene1.json, GameAI/outputs/best.pt
输出：GameAI/outputs/coverage_report.json
"""

from ultralytics import YOLO
import json
import time

# 设置工作目录
os.chdir("GameAI")

# 加载模型和脚本
model = YOLO("outputs/train/weights/best.pt")
with open("outputs/scene1.json", "r") as f:
    script = json.load(f)

# 重用 replay_script.py 的函数
from replay_script import capture_screen, generate_fingerprint, swipe_to_find_page, replay_action


def generate_coverage_report(script):
    """生成覆盖率报告"""
    total_steps = len(script["场景1"]["步骤"])
    executed_steps = 0
    unique_buttons = set()
    executed_buttons = set()

    for step in script["场景1"]["步骤"]:
        unique_buttons.add(f"{step['类别']}-{step['名称']}")  # 统计唯一按钮
        if replay_action(step):
            executed_steps += 1
            executed_buttons.add(f"{step['类别']}-{step['名称']}")
        time.sleep(1)

    report = {
        "步骤总数": total_steps,
        "成功步骤数": executed_steps,
        "步骤覆盖率": f"{executed_steps / total_steps * 100:.2f}%",
        "唯一按钮数": len(unique_buttons),
        "执行按钮数": len(executed_buttons),
        "按钮覆盖率": f"{len(executed_buttons) / len(unique_buttons) * 100:.2f}%"
    }

    with open("outputs/coverage_report.json", "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return report


# 生成并打印报告
report = generate_coverage_report(script)
print("覆盖率报告：")
print(json.dumps(report, ensure_ascii=False, indent=2))