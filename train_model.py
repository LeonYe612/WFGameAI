# /Users/helloppx/PycharmProjects/GameAI/train_model.py
from ultralytics import YOLO
import torch
import logging
import os
import platform
import psutil

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 获取当前目录作为项目根目录
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# 检查系统和设备
logger.info(f"操作系统: {platform.system()}")
logger.info(f"PyTorch版本: {torch.__version__}")
logger.info(f"CUDA是否可用: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    logger.info(f"CUDA设备: {torch.cuda.get_device_name(0)}")
    logger.info(f"CUDA版本: {torch.version.cuda}")
    logger.info(f"显存总量: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
    
# 获取系统内存信息
system_ram = psutil.virtual_memory().total / (1024**3)  # GB
logger.info(f"系统内存: {system_ram:.2f} GB")

# 设备选择优先级：CUDA > MPS > CPU
if torch.cuda.is_available():
    device = "cuda"
    # 设置CUDA性能优化参数
    torch.backends.cudnn.benchmark = True  # 启用cuDNN自动调优
    torch.backends.cudnn.deterministic = False  # 关闭确定性模式以提高性能
    torch.backends.cuda.matmul.allow_tf32 = True  # 启用TF32
    torch.backends.cudnn.allow_tf32 = True  # 启用cuDNN TF32
elif torch.backends.mps.is_available():
    device = "mps"
else:
    device = "cpu"

logger.info(f"使用设备: {device}")

# 计算最佳batch_size和workers数量
if device == "cuda":
    gpu_name = torch.cuda.get_device_name(0).lower()
    gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1024**3  # 转换为GB
    
    # 为RTX 4090特别优化
    if "4090" in gpu_name:
        batch_size = 64  # RTX 4090有24GB显存，可以使用更大的batch size
        num_workers = min(32, os.cpu_count() or 1)  # 增加工作线程数
        logger.info("检测到RTX 4090，使用优化配置")
    else:
        # 其他GPU的默认配置
        batch_size = int(min(32, max(8, gpu_mem // 2)))
        num_workers = min(16, os.cpu_count() or 1)
else:
    batch_size = 8
    num_workers = min(8, os.cpu_count() or 1)

logger.info(f"Batch size: {batch_size}")
logger.info(f"Number of workers: {num_workers}")

# 加载模型
logger.info("开始加载模型")
model = YOLO("models/yolo11m.pt")  # 使用预训练模型
logger.info("模型加载完成")

# 数据集路径
data_yaml = os.path.join(PROJECT_ROOT, "datasets", "yolov11-card2", "data.yaml")
if not os.path.exists(data_yaml):
    raise FileNotFoundError(f"数据集配置文件不存在: {data_yaml}")

# 开始训练
logger.info("开始训练")
try:
    model.train(
        data=data_yaml,  # 数据集配置文件
        epochs=50,  # 训练轮次
        batch=batch_size,  # 动态批次大小
        workers=num_workers,  # 动态工作线程数
        device=device,  # 设备
        imgsz=640,  # 图像大小
        patience=10,  # 早停耐心
        amp=True,  # 混合精度训练
        save_period=2,  # 每2个epoch保存一次
        project=os.path.join(PROJECT_ROOT, "runs", "train"),  # 保存训练结果的目录
        name="exp",  # 实验名称
        exist_ok=True,  # 如果目录存在则覆盖
        cache="ram" if system_ram > 24 else True,  # 如果系统内存大于24GB，使用RAM缓存
        optimizer="AdamW",  # 使用AdamW优化器
        lr0=0.002,  # 提高初始学习率
        lrf=0.01,  # 最终学习率（相对于初始学习率）
        momentum=0.937,  # SGD动量
        weight_decay=0.0005,  # 权重衰减
        warmup_epochs=2.0,  # 由于更大的batch size，可以减少预热轮次
        warmup_momentum=0.8,  # 预热动量
        warmup_bias_lr=0.1,  # 预热偏置学习率
        box=7.5,  # 框损失增益
        cls=0.5,  # 分类损失增益
        dfl=1.5,  # DFL损失增益
        plots=True,  # 绘制训练图表
        save=True,  # 保存检查点
        multi_scale=True,  # 启用多尺度训练
        overlap_mask=True,  # 启用mask重叠
        nbs=64,  # 标称batch size，用于学习率缩放
        close_mosaic=10,  # 最后10个epoch关闭mosaic增强
    )
    logger.info("训练完成")

    # 验证模型性能
    logger.info("开始验证模型")
    model.val()
    logger.info("验证完成")

    # 导出最佳模型
    output_path = os.path.join(PROJECT_ROOT, "outputs", "train", "weights", "best.pt")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    model.export(format="pt", save_dir=os.path.dirname(output_path))
    logger.info(f"训练完成，模型已保存至: {output_path}")

except Exception as e:
    logger.error(f"训练过程中出现错误: {str(e)}", exc_info=True)
    raise
