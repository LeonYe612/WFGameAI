#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Author  : HoneyDou
# @Time    : 2025/4/1 17:16
# @File    : json_gen.py
import os
import yaml
import json

# 读取 data.yaml 获取完整标签映射
with open("datasets/yoloV9-card2/data.yaml", "r") as f:
    config = yaml.safe_load(f)
class_names = config["names"]  # 假设包含 53 个标签，如 ['navigation-main', 'navigation-station-on', ...]

label_dir = "datasets/yoloV9-card2/train/labels"
annotations_data = {"images": []}

for txt_file in os.listdir(label_dir):
    if txt_file.endswith(".txt"):
        image_name = txt_file.replace(".txt", ".png")
        with open(os.path.join(label_dir, txt_file), "r") as f:
            lines = f.readlines()
        image_annotations = []
        for line in lines:
            parts = line.strip().split()
            class_idx = int(parts[0])
            class_name = class_names[class_idx]  # 直接获取完整标签名
            x, y, width, height = map(float, parts[1:5])
            image_annotations.append({
                "class": class_name,
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "备注信息": ""
            })
        annotations_data["images"].append({
            "filename": image_name,
            "annotations": image_annotations
        })

with open("annotations.json", "w") as f:
    json.dump(annotations_data, f, ensure_ascii=False, indent=2)

print("已生成 annotations.json，请手动填写备注信息")