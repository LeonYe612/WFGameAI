"""
model_loader.py - 提供兼容的模型加载功能，解决不同版本load_yolo_model函数的兼容问题
"""
import os
import sys
import importlib
import traceback

def load_model(base_dir, model_class, specific_model=None, exit_on_failure=True, device=None):
    """
    兼容版本的模型加载函数，同时支持本地和全局load_yolo_model

    Args:
        base_dir: 项目根目录
        model_class: YOLO模型类（通常为ultralytics.YOLO）
        specific_model: 指定的模型文件名（如果不指定，则按优先级查找）
        exit_on_failure: 加载失败时是否退出程序
        device: 推理设备，如"cuda"、"cpu"或"mps"

    Returns:
        已加载的YOLO模型
    """
    # 尝试从项目根目录导入
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    try:
        # 尝试导入项目根目录中的load_yolo_model
        from utils import load_yolo_model as root_load_yolo_model

        # 使用项目根目录中的load_yolo_model函数（扩展模式）
        print("使用项目根目录中的load_yolo_model函数")
        return root_load_yolo_model(
            model_path=None,
            device=device,
            base_dir=base_dir,
            model_class=model_class,
            specific_model=specific_model,
            exit_on_failure=exit_on_failure
        )
    except (ImportError, AttributeError) as e:
        print(f"从项目根目录导入load_yolo_model失败: {e}")

        # 尝试使用本地的load_yolo_model
        try:
            from utils import load_yolo_model as local_load_yolo_model
            print("使用本地load_yolo_model函数")
            return local_load_yolo_model(
                base_dir=base_dir,
                model_class=model_class,
                specific_model=specific_model,
                exit_on_failure=exit_on_failure,
                device=device
            )
        except ImportError as e2:
            print(f"从本地导入load_yolo_model失败: {e2}")

            if exit_on_failure:
                print("无法加载任何可用的load_yolo_model函数，程序退出")
                sys.exit(1)
            return None
