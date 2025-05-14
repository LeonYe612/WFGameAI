#!/usr/bin/env python3
"""
generate_annotations.py
作用：读取 Roboflow 导出的 .txt 文件和 data.yaml，生成 annotations.json，包含按钮类别和坐标。
输入：GameAI/datasets/yolov11-card2/labels/train/*.txt, data.yaml
输出：GameAI/outputs/annotations.json（备注信息为空，需人工填写）
"""

import os
import yaml
import json

# 设置工作目录
os.chdir("GameAI")

# 读取 data.yaml 获取类别映射
with open("datasets/yolov11-card2/data.yaml", "r") as f:
    config = yaml.safe_load(f)
class_names = config["names"]  # 完整标签列表，如 ['navigation-main', 'system-notices', ...]

# 输入和输出路径
label_dir = "datasets/yolov11-card2/labels/train"  # 标注文件目录
output_json = "outputs/annotations.json"

# 初始化 JSON 结构
annotations_data = {"images": []}

# 遍历每个 .txt 文件
for txt_file in os.listdir(label_dir):
    if txt_file.endswith(".txt"):
        image_name = txt_file.replace(".txt", ".png")  # 假设图片为 .png 格式
        with open(os.path.join(label_dir, txt_file), "r") as f:
            lines = f.readlines()

        image_annotations = []
        for line in lines:
            parts = line.strip().split()
            class_idx = int(parts[0])  # 类别索引
            class_name = class_names[class_idx]  # 完整标签名
            x, y, width, height = map(float, parts[1:5])  # 归一化坐标
            annotation = {
                "class": class_name,  # 如 "navigation-main"
                "x": x,  # 中心 x 坐标
                "y": y,  # 中心 y 坐标
                "width": width,  # 框宽度
                "height": height,  # 框高度
                "备注信息": ""  # 留空，待人工填写
            }
            image_annotations.append(annotation)

        annotations_data["images"].append({
            "filename": image_name,
            "annotations": image_annotations
        })

# 保存初始 JSON
with open(output_json, "w") as f:
    json.dump(annotations_data, f, ensure_ascii=False, indent=2)

print(f"已生成 {output_json}，请手动填写备注信息")