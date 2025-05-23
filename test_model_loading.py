#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试模型加载功能
"""
import os
import sys

# 添加项目根目录到sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入路径管理和模型加载函数
from utils import (
    get_project_root,
    get_scripts_dir,
    get_testcase_dir,
    get_weights_path,
    get_model_path,
    load_yolo_model
)

def test_model_loading():
    """测试模型加载功能"""
    print("项目根目录:", get_project_root())
    print("脚本目录:", get_scripts_dir())
    print("测试用例目录:", get_testcase_dir())
    print("权重文件路径:", get_weights_path())
    print("模型文件路径:", get_model_path())

    print("\n开始测试模型加载:")

    # 尝试加载模型 - 使用旧版调用模式
    try:
        from ultralytics import YOLO
        print("\n测试旧版调用模式:")
        model = load_yolo_model(
            base_dir=get_scripts_dir(),
            model_class=YOLO,
            device="cpu"
        )
        if model:
            print("✅ 模型加载成功!")
            print(f"模型类型: {type(model)}")
            print(f"可用类别: {model.names if hasattr(model, 'names') else 'N/A'}")
        else:
            print("❌ 模型加载失败!")
    except Exception as e:
        print(f"❌ 模型加载异常: {e}")

    # 尝试加载模型 - 使用新版调用模式
    try:
        print("\n测试新版调用模式:")
        model = load_yolo_model(
            model_path=get_model_path(),
            device="cpu"
        )
        if model:
            print("✅ 模型加载成功!")
            print(f"模型类型: {type(model)}")
            print(f"可用类别: {model.names if hasattr(model, 'names') else 'N/A'}")
        else:
            print("❌ 模型加载失败!")
    except Exception as e:
        print(f"❌ 模型加载异常: {e}")

if __name__ == "__main__":
    test_model_loading()
