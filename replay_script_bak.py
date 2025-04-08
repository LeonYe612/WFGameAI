#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Author  : HoneyDou
# @Time    : 2025/4/2 17:02
# @File    : replay_script.py
# !/usr/bin/env python3
"""
replay_script.py
作用：读取录制的 scene1.json，使用 best.pt 回放固定场景的操作。
输入：GameAI/outputs/scene1.json, GameAI/outputs/best.pt
输出：屏幕操作日志（打印）
"""

from ultralytics import YOLO
import cv2
import json
import os
import hashlib
import time

# 设置工作目录
os.chdir("GameAI")

# 加载模型和脚本
model = YOLO("outputs/train/weights/best.pt")
with open("outputs/scene1.json", "r") as f:
    script = json.load(f)


def capture_screen():
    """捕获当前屏幕截图"""
    os.system("adb shell screencap /sdcard/screen.png")
    os.system("adb pull /sdcard/screen.png screenshot.png")
    return cv2.imread("screenshot.png")


def generate_fingerprint(img):
    """生成界面指纹"""
    return hashlib.md5(img.tobytes()).hexdigest()


def swipe_to_find_page(target_fingerprint):
    """滑动屏幕查找目标界面"""
    for _ in range(3):  # 最多尝试 3 次
        img = capture_screen()
        if generate_fingerprint(img) == target_fingerprint:
            return True
        os.system("adb shell input swipe 500 1000 500 500 500")  # 示例滑动
        time.sleep(1)
    return False


def replay_action(action):
    """执行单步操作"""
    img = capture_screen()
    current_fingerprint = generate_fingerprint(img)
    if current_fingerprint != action["页面指纹"]:
        if not swipe_to_find_page(action["页面指纹"]):
            print(f"步骤 {action['步骤ID']} 页面未找到")
            return False
        img = capture_screen()

    # 检测目标按钮
    results = model(img)
    target = None
    for r in results:
        cls = model.names[int(r.boxes.cls[0])]
        if cls == f"{action['类别']}-{action['名称']}":
            target = [int(r.boxes.xywh[0][0]), int(r.boxes.xywh[0][1])]  # 动态定位
            break

    # 执行操作
    if target and "-on" in action["名称"]:
        x, y = target
        if action["操作"] == "tap":
            os.system(f"adb shell input tap {x} {y}")
        elif action["操作"] == "swipe":
            os.system(f"adb shell input swipe {x} {y} {x + 50} {y} 1000")
        print(f"步骤 {action['步骤ID']} 执行: {action['备注信息']}")
        return True
    elif not target:
        print(f"步骤 {action['步骤ID']} 未找到 {action['类别']}-{action['名称']}")
    elif "-off" in action["名称"]:
        print(f"步骤 {action['步骤ID']} 按钮不可用，跳过")
    return False


def replay_script(script):
    """回放整个脚本"""
    for step in script["场景1"]["步骤"]:
        replay_action(step)
        time.sleep(1)  # 等待界面响应


# 执行回放
replay_script(script)
print("回放完成")