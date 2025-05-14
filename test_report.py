#!/usr/bin/env python
# -*- coding: utf-8 -*-

from replay_script import run_summary
import os
from datetime import datetime
import shutil

# 创建测试目录和文件 - 使用与汇总报告相同的目录
test_base_dir = 'outputs/WFGameAI-reports/ui_reports'
device1_dir = os.path.join(test_base_dir, 'OnePlus-KB2000-1080x2400_2025-04-18-14-30-00')
device2_dir = os.path.join(test_base_dir, 'test-device-2_2025-04-18-14-30-00')

# 创建目录结构
os.makedirs(device1_dir, exist_ok=True)
os.makedirs(device2_dir, exist_ok=True)

# 创建简单的HTML文件
with open(os.path.join(device1_dir, 'log.html'), 'w') as f:
    f.write('<html><body><h1>设备1测试报告</h1></body></html>')

with open(os.path.join(device2_dir, 'log.html'), 'w') as f:
    f.write('<html><body><h1>设备2测试报告</h1></body></html>')

# 模拟测试数据
data = {
    'tests': {
        'OnePlus-KB2000-1080x2400': os.path.join(os.getcwd(), device1_dir, 'log.html'),
        '模拟设备1': None,  # 测试失败的设备
        '模拟设备2': os.path.join(os.getcwd(), device2_dir, 'log.html'),
    }
}

# 生成汇总报告
summary_report = run_summary(data)
print(f"汇总报告生成: {summary_report}")

# 检查生成的报告
print("\n检查报告中的链接:")
with open(summary_report, 'r') as f:
    content = f.read()
    import re
    links = re.findall(r'href="([^"]+)"', content)
    for link in links:
        print(f"找到链接: {link}")
        
# 尝试在浏览器中打开报告
print("\n请在浏览器中打开汇总报告，并点击链接测试是否能正确打开设备报告")
print(f"汇总报告路径: file://{os.path.abspath(summary_report)}") 