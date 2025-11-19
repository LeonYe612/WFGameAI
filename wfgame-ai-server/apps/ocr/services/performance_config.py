"""
OCR性能优化配置模块
根据硬件配置动态调整OCR参数以获得最佳性能
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# 性能配置选项
PERFORMANCE_CONFIGS = {
    "super_high_performance": {
        "batch_size": 90,
        "use_fast_models": False,  # 使用server模型保持精度
        "max_workers": 8,
        "description": "超高性能配置，需要大量GPU内存"
    },
    
    "high_performance": {
        "batch_size": 64,
        "use_fast_models": False,  # 使用server模型保持精度
        "max_workers": 12,
        "description": "高性能配置，需要更多GPU内存"
    },
    
    "balanced": {
        "batch_size": 32,
        "use_fast_models": False,
        "max_workers": 8,
        "description": "平衡配置，推荐使用"
    },
    
    "fast": {
        "batch_size": 12,
        "use_fast_models": True,  # 使用mobile模型
        "max_workers": 6,
        "description": "快速配置，牺牲一些精度换取速度"
    },
    
    "low_memory": {
        "batch_size": 8,
        "use_fast_models": True,
        "max_workers": 4,
        "description": "低内存配置，适合资源受限环境"
    }
}

# 两阶段检测参数配置
PARAM_VERSIONS = {
    "baseline": {
        "version_name": "官方默认版本（基线）",
        "text_det_thresh": 0.3,
        "text_det_box_thresh": 0.6,
        "text_det_unclip_ratio": 1.5,
        "text_det_limit_side_len": 736,
        "text_det_limit_type": "min",
        "use_doc_preprocessor": False,  # 关键修复：禁用文档预处理
        "use_textline_orientation": False,  # 关键修复：禁用文本行方向分类
        "use_doc_orientation_classify": False,  # 新增：禁用文档方向分类
        "use_doc_unwarping": False,  # 新增：禁用文档去畸变
        "text_rec_score_thresh": 0.0,  # 关键修复：降低识别阈值
    },
    
    "balanced_v1": {
        "version_name": "官方默认版本-边长max",
        "text_det_thresh": 0.3,
        "text_det_box_thresh": 0.6,
        "text_det_unclip_ratio": 1.5,
        "text_det_limit_side_len": 736,
        "text_det_limit_type": "max",  # 修改：使用max边长类型
        "use_doc_preprocessor": False,  # 禁用文档预处理
        "use_textline_orientation": False,  # 禁用文本行方向分类
        "use_doc_orientation_classify": False,  # 禁用文档方向分类
        "use_doc_unwarping": False,  # 禁用文档去畸变
        "text_rec_score_thresh": 0.0,  # 降低识别阈值
    }
}

class PerformanceConfig:
    """性能配置管理类"""
    
    def __init__(self, config_name: str = "balanced"):
        """
        初始化性能配置
        
        Args:
            config_name: 配置名称，默认为balanced
        """
        self.config_name = config_name
        self._config = self._load_config(config_name)
        
    def _load_config(self, config_name: str) -> Dict[str, Any]:
        """加载指定的性能配置"""
        if config_name not in PERFORMANCE_CONFIGS:
            logger.warning(f"未找到配置 {config_name}，使用默认配置 balanced")
            config_name = "balanced"
            
        config = PERFORMANCE_CONFIGS[config_name].copy()
        logger.info(f"加载性能配置: {config_name} - {config.get('description', '')}")
        return config
    
    def get_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        return self._config.copy()
    
    def get_batch_size(self, image_count: int = None) -> int:
        """
        获取优化后的批处理大小
        
        Args:
            image_count: 图片数量，用于动态调整批大小
            
        Returns:
            优化后的批处理大小
        """
        original_batch_size = self._config["batch_size"]
        
        if image_count is None:
            return original_batch_size
            
        # 根据图片数量优化批大小
        if image_count <= 50:
            optimal_batch_size = min(32, image_count)  # 小批量使用较小批大小
        else:
            optimal_batch_size = original_batch_size
            
        return optimal_batch_size
    
    def get_model_names(self) -> tuple[str, str]:
        """
        根据配置选择模型
        
        Returns:
            (检测模型名, 识别模型名)
        """
        use_fast_models = self._config.get("use_fast_models", False)
        
        if use_fast_models:
            # 使用mobile版本，速度更快但精度略低
            return "PP-OCRv5_mobile_det", "PP-OCRv5_mobile_rec"
        else:
            # 使用server版本，精度更高但速度较慢
            return "PP-OCRv5_server_det", "PP-OCRv5_server_rec"
    
    def get_stage_params(self, stage: str) -> Dict[str, Any]:
        """
        获取指定阶段的参数配置
        
        Args:
            stage: 阶段名称 (baseline 或 balanced_v1)
            
        Returns:
            阶段参数配置
        """
        if stage not in PARAM_VERSIONS:
            logger.warning(f"未找到阶段配置 {stage}，使用默认配置 baseline")
            stage = "baseline"
            
        return PARAM_VERSIONS[stage].copy()
    
    def should_use_two_stage(self) -> bool:
        """
        判断是否应该使用两阶段检测
        
        Returns:
            是否使用两阶段检测
        """
        # 可以根据配置或其他条件决定是否启用两阶段检测
        return True  # 默认启用两阶段检测
    
    @staticmethod
    def list_available_configs() -> Dict[str, str]:
        """
        列出所有可用配置
        
        Returns:
            配置名称到描述的映射
        """
        return {name: config.get("description", "") for name, config in PERFORMANCE_CONFIGS.items()}
    
    @staticmethod
    def get_optimal_config_for_hardware() -> str:
        """
        根据硬件自动选择最优配置
        
        Returns:
            推荐的配置名称
        """
        try:
            import paddle
            import psutil
            
            # 检查GPU内存
            if paddle.device.is_compiled_with_cuda() and paddle.device.cuda.device_count() > 0:
                # 这里可以添加GPU内存检测逻辑
                # 暂时返回平衡配置
                return "balanced"
            else:
                # 没有GPU，使用低内存配置
                return "low_memory"
                
        except Exception as e:
            logger.warning(f"硬件检测失败，使用默认配置: {e}")
            return "balanced"


def get_performance_config(config_name: str = None) -> PerformanceConfig:
    """
    获取性能配置实例
    
    Args:
        config_name: 配置名称，如果为None则自动选择
        
    Returns:
        性能配置实例
    """
    if config_name is None:
        config_name = PerformanceConfig.get_optimal_config_for_hardware()
        
    return PerformanceConfig(config_name)


if __name__ == "__main__":
    # 测试代码
    print("可用的性能配置:")
    for name, desc in PerformanceConfig.list_available_configs().items():
        print(f"  {name}: {desc}")
    
    print(f"\n推荐配置: {PerformanceConfig.get_optimal_config_for_hardware()}")
    
    # 测试配置实例
    config = get_performance_config()
    print(f"\n当前配置: {config.config_name}")
    print(f"批处理大小: {config.get_batch_size()}")
    print(f"模型选择: {config.get_model_names()}")
