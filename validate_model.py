# /Users/helloppx/PycharmProjects/GameAI/validate_model.py
from ultralytics import YOLO
import torch
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_model():
    # 检查 PyTorch 和设备
    logger.info("检查PyTorch版本和设备")
    logger.info(f"PyTorch: {torch.__version__}, MPS: {torch.backends.mps.is_available()}")

    # 选择设备
    device = "mps" if torch.backends.mps.is_available() else "cpu"

    # 加载训练后的模型
    logger.info("开始加载模型")
    model = YOLO("models/card2_ui_model_250328.pt")
    logger.info("模型加载完成")

    # 验证模型
    logger.info("开始验证")
    metrics = model.val(
        data="/Users/helloppx/PycharmProjects/GameAI/datasets/yoloV9-card2/data.yaml",  # 数据集配置文件
        device=device,  # 设备
        imgsz=640,  # 图像大小
        batch=8,  # 批次大小
        split="val"  # 使用验证集
    )
    logger.info("验证完成")

    # 输出验证结果
    logger.info(f"mAP@50: {metrics.box.map50:.4f}")
    logger.info(f"mAP@50:95: {metrics.box.map:.4f}")

    # 获取类别名称
    class_names = metrics.names
    # 输出每个类别的 Precision 和 Recall
    for i, (p, r) in enumerate(zip(metrics.box.p, metrics.box.r)):
        logger.info(f"Class {class_names[i]} - Precision: {p:.4f}, Recall: {r:.4f}")


if __name__ == "__main__":
    validate_model()
