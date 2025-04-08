#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Author  : HoneyDou
# @Time    : 2025/4/7 13:38
# @File    : infer.py
from ultralytics import YOLO
import os

# 加载模型
model = YOLO("/Users/helloppx/PycharmProjects/GameAI/outputs/train/weights/best.pt")

# 设置测试数据路径（替换为您的实际路径）
source_dir = "/Users/helloppx/PycharmProjects/GameAI/datasets/yolov11-card2/test/images"

# 推理
results = model.predict(source=source_dir, device="mps", imgsz=320, conf=0.25)

# 确保输出目录存在
save_dir = "/Users/helloppx/PycharmProjects/GameAI/outputs/infer_results"
os.makedirs(save_dir, exist_ok=True)


# 推理并保存结果
results = model.predict(source=source_dir, device="mps", imgsz=320, conf=0.25)
for i, result in enumerate(results):
    save_path = f"{save_dir}/result_{i}.jpg"
    result.save(filename=save_path)
    print(f"保存推理结果: {save_path}")

# 检查检测结果
for result in results:
    print(f"检测到: {result.boxes.cls.tolist()}")  # 类别 ID
    print(f"置信度: {result.boxes.conf.tolist()}")  # 置信度
    print(f"坐标: {result.boxes.xyxy.tolist()}")  # 边界框