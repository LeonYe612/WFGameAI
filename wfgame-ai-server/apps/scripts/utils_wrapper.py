"""
utils_wrapper.py - 提供统一的工具函数导入方式，解决路径问题
"""
import os
import sys
import importlib
import traceback

# 尝试各种可能的导入路径
def get_load_yolo_model_function():
    """获取load_yolo_model函数"""
    # 尝试从主项目utils导入
    try:
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
        from utils import load_yolo_model
        print("已从主项目utils.py导入load_yolo_model函数")
        return load_yolo_model
    except ImportError:
        print("无法从主项目utils.py导入load_yolo_model函数")

    # 尝试从当前目录utils导入
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.append(current_dir)
        from utils import load_yolo_model
        print("已从当前目录utils.py导入load_yolo_model函数")
        return load_yolo_model
    except ImportError:
        print("无法从当前目录utils.py导入load_yolo_model函数")

    # 尝试直接导入当前目录的utils.py
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        utils_path = os.path.join(current_dir, "utils.py")
        if os.path.exists(utils_path):
            spec = importlib.util.spec_from_file_location("local_utils", utils_path)
            local_utils = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(local_utils)
            print("已从utils.py文件直接导入load_yolo_model函数")
            return local_utils.load_yolo_model
    except Exception:
        print("无法从utils.py文件直接导入load_yolo_model函数")
        traceback.print_exc()

    # 所有尝试都失败
    raise ImportError("无法导入load_yolo_model函数，请检查项目路径和导入设置")

# 导出load_yolo_model函数
load_yolo_model = get_load_yolo_model_function()
