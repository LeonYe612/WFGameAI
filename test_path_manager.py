#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试统一路径管理
"""
import os
import sys

# 添加项目根目录到sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入路径管理函数
from utils import (
    get_project_root,
    get_server_dir,
    get_scripts_dir,
    get_testcase_dir,
    get_reports_dir,
    get_weights_dir,
    get_weights_path,
    get_model_path
)

def test_paths():
    """测试各个路径函数"""
    print("项目根目录:", get_project_root())
    print("服务器目录:", get_server_dir())
    print("脚本目录:", get_scripts_dir())
    print("测试用例目录:", get_testcase_dir())
    print("报告目录:", get_reports_dir())
    print("权重目录:", get_weights_dir())
    print("权重文件路径:", get_weights_path())
    print("模型文件路径:", get_model_path())

if __name__ == "__main__":
    test_paths()
