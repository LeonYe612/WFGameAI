#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Author  : HoneyDou
# @Time    : 2025/3/28 16:04
# @File    : predict_result.py
from ultralytics import YOLO
model = YOLO("models/ui_model.pt")
results = model.predict("datasets/yoloV9-card2/valid/images/-2_mp4-0045_jpg.rf.f6ee88368f9937712f3a77091927d15f.jpg")
results[0].show()  # 显示预测结果