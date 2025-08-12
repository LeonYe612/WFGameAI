import logging
logger = logging.getLogger(__name__)

def setup_nvidia_gpu():
    """
    设置使用NVIDIA显卡进行OCR处理

    Returns:
        bool: 是否成功设置NVIDIA显卡
    """
    try:
        import torch

        # 检查是否有NVIDIA GPU可用
        if torch.cuda.is_available():
            # 默认使用第一个NVIDIA GPU
            # 设置环境变量，确保使用此GPU
            import os
            os.environ["CUDA_VISIBLE_DEVICES"] = "0"
            gpu_properties = torch.cuda.get_device_properties(0)
            total_memory = gpu_properties.total_memory / (1024 * 1024)  # 转换为MB

            logger.warning(f"使用NVIDIA GPU: {gpu_properties.name}，显存: {total_memory:.0f}MB")

            return total_memory
        else:
            logger.warning("未检测到NVIDIA GPU")
            return False
    except Exception as e:
        logger.warning(f"设置NVIDIA GPU失败: {str(e)}")
        return False

setup_nvidia_gpu()