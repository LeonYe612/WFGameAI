#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Author  : HoneyDou
# @Time    : 2025/3/28 13:53
# @File    : test.py
import cv2
import numpy as np
windows = ["Device 1", "Device 2", "Device 3"]
frames = {w: np.random.randint(0, 255, (640, 360, 3), dtype=np.uint8) for w in windows}
for w in windows:
    cv2.namedWindow(w, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(w, 360, 640)
while True:
    for w in windows:
        cv2.imshow(w, frames[w])
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
cv2.destroyAllWindows()

