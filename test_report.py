import os
import json
import time
import shutil
import numpy as np
import cv2
from replay_script import run_one_report

def create_test_log():
    """创建测试日志和截图，用于测试报告生成"""
    # 创建测试目录
    test_log_dir = os.path.join("outputs", "test_logs")
    os.makedirs(test_log_dir, exist_ok=True)
    
    # 创建测试报告目录
    test_report_dir = os.path.join("outputs", "test_reports")
    os.makedirs(test_report_dir, exist_ok=True)
    
    # 清空测试目录
    for item in os.listdir(test_log_dir):
        item_path = os.path.join(test_log_dir, item)
        if os.path.isdir(item_path):
            shutil.rmtree(item_path)
        else:
            os.remove(item_path)
    
    # 创建log.txt文件
    log_txt_path = os.path.join(test_log_dir, "log.txt")
    
    # 创建测试截图
    timestamp = int(time.time() * 1000)
    
    # 创建一个空白图像作为测试截图
    img = np.ones((1080, 2400, 3), dtype=np.uint8) * 255
    # 添加一些文本和矩形作为视觉元素
    cv2.putText(img, "Test Screenshot", (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 5)
    cv2.rectangle(img, (500, 500), (700, 700), (0, 255, 0), 3)
    
    # 保存截图和缩略图
    screenshot_filename = f"{timestamp}.jpg"
    screenshot_path = os.path.join(test_log_dir, screenshot_filename)
    cv2.imwrite(screenshot_path, img)
    
    thumbnail_filename = f"{timestamp}_small.jpg"
    thumbnail_path = os.path.join(test_log_dir, thumbnail_filename)
    small_img = cv2.resize(img, (0, 0), fx=0.3, fy=0.3)
    cv2.imwrite(thumbnail_path, small_img, [cv2.IMWRITE_JPEG_QUALITY, 60])
    
    # 创建screen对象
    screen_object = {
        "src": f"log/{screenshot_filename}",
        "_filepath": f"log/{screenshot_filename}",
        "thumbnail": f"log/{thumbnail_filename}",
        "resolution": [2400, 1080],
        "pos": [[1200, 540]],
        "vector": [],
        "confidence": 0.85,
        "rect": [{"left": 1150, "top": 490, "width": 100, "height": 100}]
    }
    
    # 创建日志条目
    entries = []
    
    # 1. 添加snapshot操作
    snapshot_entry = {
        "tag": "function",
        "depth": 0,
        "time": time.time(),
        "data": {
            "name": "snapshot",
            "call_args": {},
            "start_time": time.time() - 0.002,
            "ret": screenshot_filename,
            "end_time": time.time(),
            "screen": screen_object
        }
    }
    entries.append(snapshot_entry)
    
    # 2. 添加touch操作
    touch_entry = {
        "tag": "function",
        "depth": 0,
        "time": time.time() + 0.001,
        "data": {
            "name": "touch",
            "call_args": {
                "v": [1200, 540]
            },
            "start_time": time.time() + 0.001,
            "ret": [1200, 540],
            "end_time": time.time() + 0.002,
            "screen": screen_object
        }
    }
    entries.append(touch_entry)
    
    # 写入日志
    with open(log_txt_path, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    print(f"测试日志和截图已创建在 {test_log_dir}")
    return test_log_dir, test_report_dir

def test_report_generation():
    """测试报告生成"""
    # 创建测试日志
    test_log_dir, test_report_dir = create_test_log()
    
    # 生成报告
    success = run_one_report(test_log_dir, test_report_dir)
    
    if success:
        print(f"报告生成成功，请查看: {os.path.join(test_report_dir, 'log.html')}")
    else:
        print("报告生成失败")

if __name__ == "__main__":
    test_report_generation() 