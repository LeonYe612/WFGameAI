#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Author  : HoneyDou
# @Time    : 2025/3/28 13:53
# @File    : test.py
import subprocess
from PIL import Image

# 使用 ADB 截图
subprocess.run(["adb", "-s", "65WGZT7P9XHEKN7D", "shell", "screencap", "-p", "/sdcard/screen.png"])
subprocess.run(["adb", "-s", "65WGZT7P9XHEKN7D", "pull", "/sdcard/screen.png", "./screen.png"])

# 读取并显示图像
img = Image.open("screen.png")
img.show()



