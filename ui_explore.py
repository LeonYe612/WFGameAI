#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Author  : HoneyDou
# @Time    : 2025/3/28 10:26
# @File    : ui_explore.py
# /Users/helloppx/PycharmProjects/GameAI/ui_explore.py
# 作用：使用训练好的YOLOv11m模型进行UI自动化探索

from ultralytics import YOLO
from airtest.core.api import *
import json


def ui_explore(model_path="runs/train/ui_exp/weights/best.pt", max_clicks=100, wait_time=2):
    # 初始化Airtest设备
    auto_setup(__file__, devices=["Android:///"])

    # 加载YOLO模型
    model = YOLO(model_path)
    paths = []
    clicked = set()

    for _ in range(max_clicks):
        # 截取当前屏幕
        img = snapshot(filename="screen.png")

        # 检测按钮
        results = model(img)
        for r in results:
            btn = {
                "x": int(r.boxes.xywh[0][0]),  # 中心x坐标
                "y": int(r.boxes.xywh[0][1]),  # 中心y坐标
                "type": r.names[int(r.boxes.cls[0])]  # 按钮类别
            }
            btn_id = f"{btn['x']}_{btn['y']}"
            if btn_id not in clicked:
                touch((btn["x"], btn["y"]))
                sleep(wait_time)
                paths.append({"from": "prev_ui", "action": btn, "to": "next_ui"})
                clicked.add(btn_id)
                break

        # 保存探索路径
        with open("ui_explore_result.json", "w") as f:
            json.dump(paths, f)
    return paths


if __name__ == "__main__":
    ui_explore()