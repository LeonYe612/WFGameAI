# /Users/helloppx/PycharmProjects/GameAI/train_model.py
from ultralytics import YOLO
import torch
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



# 检查 PyTorch 和设备
logger.info("检查PyTorch版本和设备")
logger.info(f"PyTorch: {torch.__version__}, MPS: {torch.backends.mps.is_available()}")

# 选择设备（优先使用 MPS）
device = "mps" if torch.backends.mps.is_available() else "cpu"

# 加载模型
logger.info("开始加载模型")
model = YOLO("models/yolo11m.pt")  # 使用预训练模型
logger.info("模型加载完成")

# 开始训练
logger.info("开始训练")
model.train(
    data="/Users/helloppx/PycharmProjects/GameAI/datasets/yolov11-card2/data.yaml",  # 数据集配置文件
    epochs=50,  # 训练轮次
    batch=10,  # 批次大小。控制每次训练的样本量，过大可能导致内存不足
    workers=15,  # 数据加载线程数
    device=device,  # 设备
    imgsz=640,  # 图像大小
    patience=10,  # 早停耐心, 如果验证损失在 patience 个 epoch 内没有改进，则训练会自动停止
    amp=True if device == "mps" else False,  # 混合精度训练（MPS 支持）
    save_period=2,  # 每 10 个 epoch 保存一次
    project="runs/train",  # 保存训练结果的目录
    name="exp",  # 实验名称
    exist_ok=True        # 如果目录存在则覆盖
)
logger.info("训练完成")

# 验证模型性能
model.val()

# 导出最佳模型
model.export(format="pt")  # 保存为 best.pt
print("训练完成，模型已保存至 outputs/train/weights/best.pt")
