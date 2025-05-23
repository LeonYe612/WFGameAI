#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WFGameAI 路径管理补丁脚本
用于将所有硬编码路径替换为从config.ini获取的动态路径
"""

import os
import sys
import re
import argparse
import configparser

def get_project_root():
    """获取项目根目录"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # 检查当前目录是否为项目根目录
    if os.path.exists(os.path.join(script_dir, "config.ini")):
        return script_dir
    # 向上一级查找
    parent_dir = os.path.dirname(script_dir)
    if os.path.exists(os.path.join(parent_dir, "config.ini")):
        return parent_dir
    return None

def inject_utils_import(file_path):
    """注入utils导入语句"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 查找关键导入位置
    import_section = re.search(r'import.*?\n\n', content, re.DOTALL)
    if not import_section:
        print(f"无法在 {file_path} 中找到正确的导入位置")
        return False

    # 添加utils导入
    utils_import = """
# 导入统一路径管理工具
try:
    # 尝试从项目根目录导入
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
    from utils import get_project_root, get_scripts_dir, get_testcase_dir, load_yolo_model

    # 使用配置文件中的路径
    PROJECT_ROOT = get_scripts_dir() or os.path.dirname(os.path.abspath(__file__))
    TESTCASE_DIR = get_testcase_dir() or os.path.join(PROJECT_ROOT, "testcase")
    print(f"使用路径配置: PROJECT_ROOT={PROJECT_ROOT}, TESTCASE_DIR={TESTCASE_DIR}")
except ImportError:
    # 如果导入失败，使用相对路径
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
    TESTCASE_DIR = os.path.join(PROJECT_ROOT, "testcase")
    print("警告: 未找到配置管理工具，使用相对路径")
"""

    # 检查是否已经添加了utils导入
    if "from utils import get_project_root" in content:
        print(f"{file_path} 已包含统一路径管理导入，跳过")
        return True

    # 插入导入语句
    new_content = content.replace(import_section.group(0), import_section.group(0) + utils_import)

    # 移除原有的PROJECT_ROOT定义
    new_content = re.sub(r'PROJECT_ROOT\s*=\s*os\.path\.dirname\(os\.path\.abspath\(__file__\)\)', '', new_content)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"成功更新 {file_path} 中的导入和路径定义")
    return True

def update_model_loading(file_path):
    """更新模型加载代码，使用统一的load_yolo_model函数"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 查找模型加载代码
    model_loading_pattern = r'model\s*=\s*load_yolo_model\(\s*base_dir=PROJECT_ROOT,\s*model_class=YOLO,.*?\)'
    model_loading_match = re.search(model_loading_pattern, content, re.DOTALL)

    if not model_loading_match:
        print(f"无法在 {file_path} 中找到模型加载代码")
        return False

    # 替换为更兼容的调用方式
    new_model_loading = """model = load_yolo_model(
        base_dir=PROJECT_ROOT,
        model_class=YOLO,
        device=DEVICE
    )"""

    new_content = content.replace(model_loading_match.group(0), new_model_loading)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"成功更新 {file_path} 中的模型加载代码")
    return True

def update_output_path(file_path):
    """更新输出路径定义，确保使用TESTCASE_DIR变量"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 查找输出路径定义
    output_path_pattern = r'output_dir\s*=\s*os\.path\.join\(PROJECT_ROOT,\s*"testcase"\)'
    output_path_match = re.search(output_path_pattern, content)

    if not output_path_match:
        print(f"无法在 {file_path} 中找到输出路径定义")
        return False

    # 替换为使用TESTCASE_DIR
    new_output_path = "output_dir = TESTCASE_DIR"

    new_content = content.replace(output_path_match.group(0), new_output_path)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"成功更新 {file_path} 中的输出路径定义")
    return True

def patch_file(file_path):
    """对单个文件应用所有补丁"""
    print(f"\n正在处理文件: {file_path}")

    # 备份文件
    backup_path = file_path + ".bak"
    if not os.path.exists(backup_path):
        with open(file_path, 'r', encoding='utf-8') as src:
            with open(backup_path, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
        print(f"已创建备份: {backup_path}")

    # 应用补丁
    inject_utils_import(file_path)
    update_model_loading(file_path)
    update_output_path(file_path)

    print(f"文件 {file_path} 处理完成")

def main():
    parser = argparse.ArgumentParser(description="WFGameAI 路径管理补丁脚本")
    parser.add_argument("--restore", action="store_true", help="从备份恢复原始文件")
    args = parser.parse_args()

    project_root = get_project_root()
    if not project_root:
        print("错误: 无法确定项目根目录，请在项目目录内执行此脚本")
        return

    # 定义需要处理的文件
    files_to_patch = [
        os.path.join(project_root, "wfgame-ai-server", "apps", "scripts", "record_script.py"),
        os.path.join(project_root, "wfgame-ai-server", "apps", "scripts", "replay_script.py")
    ]

    if args.restore:
        # 从备份恢复
        for file_path in files_to_patch:
            backup_path = file_path + ".bak"
            if os.path.exists(backup_path):
                with open(backup_path, 'r', encoding='utf-8') as src:
                    with open(file_path, 'w', encoding='utf-8') as dst:
                        dst.write(src.read())
                print(f"已从备份恢复: {file_path}")
            else:
                print(f"备份文件不存在: {backup_path}")
    else:
        # 应用补丁
        for file_path in files_to_patch:
            if os.path.exists(file_path):
                patch_file(file_path)
            else:
                print(f"文件不存在: {file_path}")

    print("\n补丁应用完成！")

if __name__ == "__main__":
    main()
