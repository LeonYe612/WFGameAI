#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试统一路径管理 - 简化版
"""
import os
import sys

# 添加项目根目录到sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    # 导入单个函数，确保不会因为其他函数导致失败
    from utils import get_project_root
    print("项目根目录:", get_project_root())

    # 逐个导入其他函数并测试
    from utils import get_server_dir
    print("服务器目录:", get_server_dir())

    from utils import get_scripts_dir
    print("脚本目录:", get_scripts_dir())

    from utils import get_testcase_dir
    print("测试用例目录:", get_testcase_dir())

    from utils import get_reports_dir
    print("报告目录:", get_reports_dir())

    from utils import get_weights_dir
    print("权重目录:", get_weights_dir())

    from utils import get_weights_path
    print("权重文件路径:", get_weights_path())

    from utils import get_model_path
    print("模型文件路径:", get_model_path())

except Exception as e:
    print(f"测试失败: {e}")
    import traceback
    traceback.print_exc()
