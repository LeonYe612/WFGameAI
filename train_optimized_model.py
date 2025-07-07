#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型重新训练脚本 - 专门用于28类优化数据集的训练
基于原始train_model.py进行优化
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def train_optimized_model():
    """使用28类优化数据集训练模型"""

    # 获取项目根目录
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

    # 检查是否存在重构的数据集
    restructured_dataset_path = os.path.join(PROJECT_ROOT, "datasets", "restructured_dataset", "data.yaml")

    if not os.path.exists(restructured_dataset_path):
        logger.error(f"未找到重构的数据集配置文件: {restructured_dataset_path}")
        logger.error("请先运行 implement_dataset_restructure.py 创建优化的数据集")
        return False

    logger.info(f"使用重构的数据集: {restructured_dataset_path}")

    # 导入train_model模块并修改其默认数据集路径
    try:
        # 动态修改train_model.py中的数据集路径
        import importlib.util
        spec = importlib.util.spec_from_file_location("train_model", os.path.join(PROJECT_ROOT, "train_model.py"))
        train_module = importlib.util.module_from_spec(spec)

        # 修改sys.argv以传递数据集路径（如果train_model.py支持--data参数）
        original_argv = sys.argv.copy()
        sys.argv = [sys.argv[0]]  # 保留脚本名称

        # 执行训练模块
        spec.loader.exec_module(train_module)

        # 检查是否有main函数
        if hasattr(train_module, 'main'):
            # 临时修改train_model中的data_yaml路径
            train_module.data_yaml = restructured_dataset_path
            logger.info("开始使用28类优化数据集训练模型...")
            train_module.main()
            logger.info("训练完成!")
            return True
        else:
            logger.error("train_model.py中未找到main函数")
            return False

    except Exception as e:
        logger.error(f"训练过程中出现错误: {e}")
        return False
    finally:
        # 恢复原始命令行参数
        sys.argv = original_argv

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='使用28类优化数据集重新训练YOLO模型')
    parser.add_argument('--check-only', action='store_true', help='只检查数据集是否存在，不进行训练')

    args = parser.parse_args()

    if args.check_only:
        # 只检查数据集
        PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
        restructured_dataset_path = os.path.join(PROJECT_ROOT, "datasets", "restructured_dataset", "data.yaml")

        if os.path.exists(restructured_dataset_path):
            logger.info(f"✅ 找到重构的数据集: {restructured_dataset_path}")

            # 显示数据集信息
            try:
                import yaml
                with open(restructured_dataset_path, 'r') as f:
                    data_config = yaml.safe_load(f)

                logger.info(f"数据集名称: {data_config.get('name', 'Unknown')}")
                logger.info(f"类别数量: {data_config.get('nc', 'Unknown')}")
                logger.info(f"类别列表: {data_config.get('names', 'Unknown')}")

            except Exception as e:
                logger.warning(f"读取数据集配置时出错: {e}")
        else:
            logger.error(f"❌ 未找到重构的数据集: {restructured_dataset_path}")
            logger.error("请先运行: python implement_dataset_restructure.py")
            return False

        return True

    # 开始训练
    logger.info("=" * 60)
    logger.info("WFGameAI 模型重新训练")
    logger.info("使用28类优化数据集训练新模型")
    logger.info("=" * 60)

    success = train_optimized_model()

    if success:
        logger.info("🎉 训练完成! 请检查以下内容:")
        logger.info("1. 新模型大小是否恢复到80-100MB范围")
        logger.info("2. 模型位置: train_results/train/exp_YYYYMMDD_HHMMSS/weights/best.pt")
        logger.info("3. 运行精度测试验证模型效果")
    else:
        logger.error("❌ 训练失败，请检查错误信息")
        return False

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
