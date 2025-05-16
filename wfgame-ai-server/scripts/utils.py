#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================
Description:
模型加载工具函数
Author: Honey Dou
===============================
"""

import os
import sys
import shutil
import time
import glob

def update_best_model(base_dir):
    """
    查找最新的模型文件，并将其更新为best.pt
    
    Args:
        base_dir (str): 项目根目录路径
        
    Returns:
        str: 更新后的best.pt模型路径，如果失败则返回None
        
    功能:
        1. 查找weights目录下的所有.pt模型文件
        2. 按修改时间排序找到最新的模型
        3. 备份当前的best.pt文件(如果存在)
        4. 将最新的模型文件复制为best.pt
    """
    weights_dir = os.path.join(base_dir, "datasets", "train", "weights")
    if not os.path.exists(weights_dir):
        os.makedirs(weights_dir, exist_ok=True)
        print(f"创建weights目录: {weights_dir}")
        return None
    
    # 查找所有.pt文件(除了best.pt)
    pt_files = []
    best_path = os.path.join(weights_dir, "best.pt")
    
    for file_path in glob.glob(os.path.join(weights_dir, "*.pt")):
        if os.path.basename(file_path) != "best.pt":
            # 获取文件修改时间
            mod_time = os.path.getmtime(file_path)
            pt_files.append((file_path, mod_time))
    
    if not pt_files:
        print("未找到任何模型文件(.pt)")
        return None
    
    # 按修改时间排序(从新到旧)
    pt_files.sort(key=lambda x: x[1], reverse=True)
    latest_model = pt_files[0][0]
    print(f"找到最新的模型文件: {latest_model}")
    
    try:
        # 备份当前的best.pt(如果存在)
        if os.path.exists(best_path):
            # 使用时间戳创建备份文件名
            timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
            backup_name = f"best_backup_{timestamp}.pt"
            backup_path = os.path.join(weights_dir, backup_name)
            
            # 复制为备份
            shutil.copy2(best_path, backup_path)
            print(f"已将当前best.pt备份为: {backup_name}")
            
            # 删除原来的best.pt
            os.remove(best_path)
            print("已删除原来的best.pt")
        
        # 将最新模型复制为best.pt
        shutil.copy2(latest_model, best_path)
        print(f"已将{os.path.basename(latest_model)}更新为best.pt")
        
        return best_path
    except Exception as e:
        print(f"更新best.pt时出错: {e}")
        return None

def find_best_model(base_dir, specific_model=None, exit_on_failure=True):
    """
    查找最佳可用的YOLO模型文件
    
    Args:
        base_dir (str): 项目根目录路径
        specific_model (str, optional): 指定的模型文件名
        exit_on_failure (bool): 如果找不到模型是否退出程序
        
    Returns:
        str: 模型文件的完整路径
    
    Raises:
        SystemExit: 如果找不到模型且exit_on_failure为True
    """
    weights_dir = os.path.join(base_dir, "datasets", "train", "weights")
    
    # 1. 如果提供了特定模型名称，首先尝试加载它
    if specific_model:
        specific_path = os.path.join(weights_dir, specific_model)
        if os.path.exists(specific_path):
            print(f"找到指定模型: {specific_path}")
            return specific_path
    
    # 2. 默认优先使用best.pt
    best_model_path = os.path.join(weights_dir, "best.pt")
    if os.path.exists(best_model_path):
        print(f"找到best.pt模型: {best_model_path}")
        return best_model_path
    
    # 3. 按修改时间查找最新的.pt文件
    print("未找到best.pt模型，尝试查找其他模型文件...")
    pt_files = []
    if os.path.exists(weights_dir):
        for file in os.listdir(weights_dir):
            if file.endswith(".pt"):
                file_path = os.path.join(weights_dir, file)
                # 获取文件修改时间
                mod_time = os.path.getmtime(file_path)
                pt_files.append((file_path, mod_time))
    
    # 按修改时间排序（从新到旧）
    if pt_files:
        pt_files.sort(key=lambda x: x[1], reverse=True)
        print(f"找到最新模型: {pt_files[0][0]}")
        return pt_files[0][0]
    
    # 4. 尝试备用路径
    print("在主目录未找到模型，尝试备用路径...")
    alternate_paths = [
        os.path.join(base_dir, "..", "GameAI", "outputs", "train", "weights", "best.pt")
    ]
    
    for alt_path in alternate_paths:
        if os.path.exists(alt_path):
            print(f"找到备用模型: {alt_path}")
            return alt_path
    
    # 5. 如果所有尝试都失败
    if exit_on_failure:
        print("错误：未找到可用的模型文件")
        print("请确保至少一个模型文件位于正确的位置")
        print(f"已尝试路径: {weights_dir}")
        sys.exit(1)
    
    return None

def load_yolo_model(base_dir, model_class, specific_model=None, exit_on_failure=True, device=None):
    """
    加载YOLO模型

    Args:
        base_dir: 项目根目录
        model_class: YOLO模型类（通常为ultralytics.YOLO）
        specific_model: 指定的模型文件名（如果不指定，则按优先级查找）
        exit_on_failure: 加载失败时是否退出程序
        device: 推理设备，如"cuda"、"cpu"或"mps"

    Returns:
        已加载的YOLO模型
    """
    # 设置模型目录
    weights_dir = os.path.join(base_dir, "datasets", "train", "weights")
    os.makedirs(weights_dir, exist_ok=True)

    # 搜索模型文件
    if specific_model:
        # 如果指定了特定模型，直接使用
        model_path = os.path.join(weights_dir, specific_model)
        if not os.path.exists(model_path):
            model_path = os.path.join(base_dir, specific_model)  # 尝试从根目录查找
        if not os.path.exists(model_path):
            print(f"指定的模型 {specific_model} 不存在")
            if exit_on_failure:
                sys.exit(1)
            return None
    else:
        # 按优先级查找模型: best.pt > last.pt > *.pt (最新)
        best_model = os.path.join(weights_dir, "best.pt")
        if os.path.exists(best_model):
            print(f"找到best.pt模型: {best_model}")
            model_path = best_model
        else:
            # 尝试找last.pt
            last_model = os.path.join(weights_dir, "last.pt")
            if os.path.exists(last_model):
                print(f"找到last.pt模型: {last_model}")
                model_path = last_model
            else:
                # 查找所有.pt文件并选择最新的
                pt_files = [os.path.join(weights_dir, f) for f in os.listdir(weights_dir) if f.endswith('.pt') and not f.startswith('best_')]
                if pt_files:
                    latest_model = max(pt_files, key=os.path.getmtime)
                    print(f"使用最新的模型: {latest_model}")
                    model_path = latest_model
                else:
                    print(f"未找到任何.pt模型文件")
                    if exit_on_failure:
                        sys.exit(1)
                    return None

    try:
        # 加载模型（不在构造函数中使用device参数）
        model = model_class(model_path)
        
        # 加载后设置设备
        if device:
            try:
                print(f"将模型移至设备: {device}")
                model.to(device)  # 使用.to()方法设置设备
            except Exception as dev_err:
                print(f"设置模型设备失败: {dev_err}，使用默认设备")
        
        print(f"模型加载成功: {model_path}")
        return model
    except Exception as e:
        print(f"模型加载失败: {e}")
        if exit_on_failure:
            sys.exit(1)
        return None

def demo_update_best_model():
    """
    更新best.pt模型的使用示例
    
    这个函数展示了如何使用update_best_model功能将最新训练的模型更新为best.pt
    
    使用示例:
    ```python
    # 在训练完成后更新best.pt
    from utils import update_best_model
    
    # 方式1: 自动获取项目根目录并更新
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
    update_best_model(PROJECT_ROOT)
    
    # 方式2: 指定目录更新
    update_best_model("/path/to/project")
    ```
    """
    # 获取当前文件所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"当前目录: {current_dir}")
    
    # 更新best.pt模型
    result = update_best_model(current_dir)
    
    if result:
        print(f"更新成功! best.pt路径: {result}")
    else:
        print("更新失败，请确保weights目录中有至少一个.pt模型文件")

# 如果直接运行此文件，则执行演示
if __name__ == "__main__":
    demo_update_best_model() 