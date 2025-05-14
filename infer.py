#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Author  : HoneyDou
# @Time    : 2025/4/7 13:38
# @File    : infer.py
"""
YOLO模型推理脚本

此脚本用于加载训练好的YOLOv8模型并对UI自动化测试场景中的图像进行目标检测推理。

主要功能：
1. 支持批量处理多张测试图像
2. 自动选择最佳可用设备(CUDA/MPS/CPU)进行推理
3. 实现自适应阈值机制，根据图像质量和UI元素类型动态调整检测阈值
4. 生成可视化结果和结构化JSON数据
5. 提供完整的性能和检测统计数据

自适应阈值是本脚本的核心创新点：
- 针对不同UI元素类型(按钮、文本、图标等)使用不同的基础置信度要求
- 根据图像质量(清晰度、对比度、亮度)动态调整检测阈值
- 在低质量图像中降低阈值，提高召回率；在高质量图像中提高阈值，增强精度

使用方法：
python infer.py --model path/to/model.pt --source path/to/images --device cuda

高级参数：
--img-size: 输入图像尺寸(默认640)
--conf: 基础置信度阈值(默认0.25) 
--no-adaptive: 禁用自适应阈值(默认启用)
--batch-size: 批处理大小(默认16)

输出结果：
- 可视化检测结果图像
- 每张图像的检测结果JSON文件
- 包含所有检测统计数据的汇总JSON文件
"""
from ultralytics import YOLO
import os
import sys
import cv2
import numpy as np
import torch
from pathlib import Path
import logging
import time
import json
from datetime import datetime

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 获取项目根目录
ROOT_DIR = Path(__file__).resolve().parent

# 定义不同UI元素类型的自适应阈值配置
UI_ADAPTIVE_THRESHOLDS = {
    # 按钮元素配置
    # - 特点：通常有清晰的边界、固定的形状和位置
    # - 由于特征明显，可以使用较高的基础置信度(0.45)
    # - 自适应因子中等(0.20)，在图像质量下降时适度降低阈值
    # - 最低阈值(0.25)保证基本检测准确性
    'button': {
        'base_conf': 0.45,      # 理想条件下的置信度阈值
        'min_conf': 0.25,       # 允许的最低置信度阈值
        'adaptive_factor': 0.20  # 图像质量下降时的阈值调整因子
    },
    
    # 文本元素配置
    # - 特点：小字体、可变长度、有时对比度不高
    # - 基础置信度(0.40)略低于按钮，因为文本识别难度较大
    # - 自适应因子较大(0.25)，对图像质量变化更敏感
    # - 最低阈值(0.20)较低，避免在质量较差时漏检文本
    'text': {
        'base_conf': 0.40,
        'min_conf': 0.20,
        'adaptive_factor': 0.25
    },
    
    # 图标元素配置
    # - 特点：小尺寸、高对比度、独特形状
    # - 需要高基础置信度(0.50)以避免误检
    # - 自适应因子小(0.15)，因为图标通常对比度高，受图像质量影响较小
    # - 较高的最低阈值(0.30)，确保高精度识别
    'icon': {
        'base_conf': 0.50,
        'min_conf': 0.30,
        'adaptive_factor': 0.15
    },
    
    # 菜单元素配置
    # - 特点：包含多个子元素、结构复杂、有层次关系
    # - 基础置信度高(0.48)，因为菜单误检会影响交互流程
    # - 自适应因子中等(0.18)，平衡精度和召回率
    # - 最低阈值适中(0.28)，确保在不同图像质量下的检测稳定性
    'menu': {
        'base_conf': 0.48,
        'min_conf': 0.28,
        'adaptive_factor': 0.18
    },
    
    # 对话框元素配置
    # - 特点：大尺寸、包含多种子元素、通常有醒目边框
    # - 基础置信度中等(0.42)，考虑到对话框内部复杂性
    # - 自适应因子较大(0.22)，允许在图像质量变化时更灵活调整
    # - 最低阈值(0.22)设置较低，确保在关键场景不会漏检对话框
    'dialog': {
        'base_conf': 0.42,
        'min_conf': 0.22,
        'adaptive_factor': 0.22
    },
    
    # 默认配置，用于未专门定义的UI元素类型
    # - 采用平衡的参数设置，适用于大多数未特别定义的元素类型
    # - 中等基础置信度(0.40)，平衡准确率和召回率
    # - 中等自适应因子(0.20)，提供适度的图像质量适应能力
    # - 最低阈值(0.25)保证基本检测准确性
    'default': {
        'base_conf': 0.40,
        'min_conf': 0.25,
        'adaptive_factor': 0.20
    }
}

def get_adaptive_threshold(element_type, image_quality):
    """
    根据UI元素类型和图像质量获取自适应阈值。
    
    自适应阈值机制的核心思想：
    1. 不同UI元素因复杂度和特征明显程度不同，需要不同的置信度阈值
    2. 图像质量(清晰度、对比度、亮度)会影响检测的可靠性
    3. 通过动态调整阈值，在保证检测准确性的同时提高召回率
    
    计算公式: threshold = base_conf - (adaptive_factor * (1 - image_quality))
    - 图像质量高时(接近1)，使用接近base_conf的阈值
    - 图像质量低时，适当降低阈值，但不低于min_conf
    
    Args:
        element_type (str): UI元素类型(button, text, icon等)
        image_quality (float): 图像质量评估值(0.0~1.0)
        
    Returns:
        float: 计算后的自适应阈值
    """
    # 获取指定UI元素类型的阈值配置，如果不存在则使用默认配置
    config = UI_ADAPTIVE_THRESHOLDS.get(element_type, UI_ADAPTIVE_THRESHOLDS['default'])
    
    # 基础置信度阈值
    base_conf = config['base_conf']
    # 最小置信度阈值(下限)
    min_conf = config['min_conf']
    # 自适应调整因子(控制对图像质量的敏感度)
    adaptive_factor = config['adaptive_factor']
    
    # 根据图像质量动态计算阈值
    # 当图像质量为1.0时，阈值等于base_conf
    # 当图像质量降低时，阈值相应减小但不低于min_conf
    threshold = max(min_conf, base_conf - (adaptive_factor * (1 - image_quality)))
    
    return threshold

def estimate_image_quality(image):
    """
    估计图像质量，用于自适应阈值调整。
    
    图像质量评估算法原理：
    1. 清晰度评估：通过拉普拉斯算子计算图像的边缘清晰度
    2. 对比度评估：计算图像标准差与均值的比率
    3. 亮度评估：确保图像亮度在合理范围内(不过亮或过暗)
    
    这三个因素综合决定图像质量分数，范围为0.0到1.0
    - 分数越高，表示图像质量越好，检测结果越可靠
    - 分数越低，表示图像质量越差，需要适当降低阈值
    
    Args:
        image (numpy.ndarray): 输入图像(BGR格式)
        
    Returns:
        float: 图像质量评分(0.0~1.0)
    """
    # 转换为灰度图
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # 计算拉普拉斯变换(评估清晰度)
    lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    # 归一化清晰度评分(0.0~1.0)
    sharpness = min(1.0, lap_var / 500)
    
    # 计算对比度(标准差除以均值)
    mean, std = cv2.meanStdDev(gray)
    if mean[0][0] > 0:
        contrast = min(1.0, std[0][0] / mean[0][0] / 0.5)
    else:
        contrast = 0.0
    
    # 计算亮度适宜性
    # 理想亮度应在中间范围(约128)，过亮或过暗都不理想
    mean_brightness = mean[0][0]
    brightness_score = 1.0 - abs(mean_brightness - 128) / 128
    brightness_score = max(0.0, brightness_score)
    
    # 综合加权得出最终质量评分
    # 清晰度占比最高(50%)，对比度次之(30%)，亮度适宜性再次(20%)
    quality = sharpness * 0.5 + contrast * 0.3 + brightness_score * 0.2
    
    # 确保质量分数在0.0到1.0之间
    quality = max(0.1, min(1.0, quality))
    
    return quality

def apply_adaptive_thresholds(results, classes, images, conf_base=0.25):
    """
    对检测结果应用自适应阈值
    
    自适应阈值应用流程：
    1. 对每张图像：
       - 评估图像质量
       - 根据质量因子动态调整每种UI元素的检测阈值
    
    2. 对每个检测结果：
       - 获取元素类型(类别名称)
       - 为该类型计算特定的自适应阈值
       - 根据阈值过滤低置信度检测
    
    3. 优势：
       - 质量较差的图像可以使用更宽松的阈值，提高召回率
       - 质量较好的图像可以使用更严格的阈值，提高精确率
       - 不同类型UI元素使用针对性阈值，提高整体检测效果
    
    注意：此函数会直接修改YOLO结果对象，过滤掉不符合自适应阈值的检测框
    
    Args:
        results: YOLO模型检测结果
        classes: 类别名称列表
        images: 原始图像列表
        conf_base: 基础置信度阈值
        
    Returns:
        filtered_results: 应用自适应阈值后的结果
    """
    filtered_results = []
    
    for i, result in enumerate(results):
        # 获取图像质量
        image = images[i]
        image_quality = estimate_image_quality(image)
        logger.info(f"图像 {i} 质量因子: {image_quality:.2f}")
        
        # 获取检测结果
        boxes = result.boxes
        filtered_boxes = []
        
        for j in range(len(boxes)):
            # 获取类别
            cls_id = int(boxes.cls[j].item())
            cls_name = classes[cls_id] if cls_id < len(classes) else "unknown"
            
            # 获取置信度
            conf = boxes.conf[j].item()
            
            # 获取自适应阈值
            adaptive_threshold = get_adaptive_threshold(cls_name, image_quality)
            
            # 应用自适应阈值
            if conf >= adaptive_threshold:
                filtered_boxes.append(j)
                logger.debug(f"保留 {cls_name} 检测结果，置信度 {conf:.2f} >= 阈值 {adaptive_threshold:.2f}")
            else:
                logger.debug(f"过滤 {cls_name} 检测结果，置信度 {conf:.2f} < 阈值 {adaptive_threshold:.2f}")
        
        # 创建过滤后的结果
        if len(filtered_boxes) > 0:
            # 筛选保留的检测框
            filtered_result = result
            filtered_result.boxes = result.boxes[filtered_boxes]
        else:
            filtered_result = result
        
        filtered_results.append(filtered_result)
    
    return filtered_results

def run_inference(
    model_path=None, 
    source_dir=None, 
    save_dir=None,
    device=None,  # 自动选择最佳设备
    img_size=640,  # 提高默认分辨率
    conf_threshold=0.25,
    use_adaptive_threshold=True,
    class_names=None,
    save_results=True,
    batch_size=16
):
    """
    运行YOLO模型推理并保存结果
    
    此函数是推理流程的主入口，包含以下主要步骤：
    1. 初始化参数和环境：设置默认值，创建输出目录，选择合适的推理设备
    2. 加载模型和类别信息：使用ultralytics YOLO API加载训练好的模型
    3. 准备图像数据：读取源目录中的图像，准备批量处理
    4. 执行模型推理：使用YOLOv8进行目标检测，获取原始结果
    5. 应用自适应阈值（可选）：根据图像质量动态调整检测阈值
    6. 保存和分析结果：生成可视化结果、JSON数据，输出统计信息
    
    自适应阈值机制是一个关键特性，它能够：
    - 根据图像质量动态调整每种UI元素的阈值
    - 提高在低质量图像中的检测召回率
    - 在高质量图像中保持高精度
    
    Args:
        model_path (str, optional): 模型路径，默认使用训练好的最佳模型(best.pt)
        source_dir (str, optional): 测试图片目录，默认使用内置测试集
        save_dir (str, optional): 结果保存目录，默认使用时间戳命名的目录
        device (str, optional): 推理设备，默认自动选择(cuda/mps/cpu)
        img_size (int): 输入图像大小，更高的值提高精度但降低速度
        conf_threshold (float): 基础置信度阈值，低于此值的检测将被过滤
        use_adaptive_threshold (bool): 是否使用自适应阈值机制
        class_names (dict, optional): 类别ID到名称的映射，默认从模型中提取
        save_results (bool): 是否保存可视化结果和JSON数据
        batch_size (int): 批处理大小，更大的值提高吞吐量但需要更多内存
    
    Returns:
        list: 模型推理结果列表，每个元素对应一张图像的检测结果
    
    示例:
        ```python
        # 基本用法
        results = run_inference()
        
        # 自定义参数
        results = run_inference(
            model_path="models/custom.pt",
            source_dir="data/test_images",
            device="cuda",
            conf_threshold=0.3,
            use_adaptive_threshold=True
        )
        ```
    """
    start_time = time.time()
    
    # 设置默认参数
    if model_path is None:
        model_path = ROOT_DIR / "datasets" / "train" / "weights" / "best_20250430_140732.pt"
    
    if source_dir is None:
        source_dir = ROOT_DIR / "datasets" / "My First Project.v3i.yolov11" / "test" / "images"
    
    if save_dir is None:
        # 创建按日期和时间命名的结果文件夹
        # 格式为: YYYYMMDD_HHMMSS，例如: 20230415_143022
        # 使用此命名方式的优点:
        # 1. 确保每次推理的结果目录名称唯一，不会发生覆盖
        # 2. 按照创建时间自然排序，便于管理和查找
        # 3. 通过时间戳可以快速识别推理执行的时间
        # 4. 与训练实验目录命名方式保持一致(exp_YYYYMMDD_HHMMSS)，便于关联
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_dir = ROOT_DIR / "outputs" / "infer_results" / current_time
    
    # 确保输出目录存在
    os.makedirs(save_dir, exist_ok=True)
    
    # 创建存储识别结果数据的子目录
    detection_data_dir = save_dir / "detection_data"
    os.makedirs(detection_data_dir, exist_ok=True)
    
    # 自动选择设备
    if device is None:
        if torch.cuda.is_available():
            device = "cuda"
            logger.info("使用CUDA加速进行推理")
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            device = "mps"
            logger.info("使用MPS加速进行推理(Apple Silicon)")
        else:
            device = "cpu"
            logger.info("使用CPU进行推理")
    
    logger.info(f"模型路径: {model_path}")
    logger.info(f"测试数据路径: {source_dir}")
    logger.info(f"结果保存路径: {save_dir}")
    logger.info(f"使用设备: {device}")
    logger.info(f"图像尺寸: {img_size}")
    logger.info(f"基础置信度阈值: {conf_threshold}")
    logger.info(f"是否使用自适应阈值: {use_adaptive_threshold}")
    
    # 加载模型
    try:
        logger.info("加载模型中...")
        model = YOLO(str(model_path))
        logger.info(f"成功加载模型: {model_path}")
        
        # 如果没有提供类别名称，从模型中提取
        if class_names is None and hasattr(model, 'names'):
            class_names = model.names
            logger.info(f"从模型中提取类别名称: {class_names}")
        elif class_names is None:
            class_names = {i: f"class_{i}" for i in range(1000)}  # 默认占位符
            logger.warning("无法从模型中获取类别名称，使用默认占位符")
    except Exception as e:
        logger.error(f"模型加载失败: {e}")
        sys.exit(1)
    
    # 获取图像列表
    if os.path.isdir(source_dir):
        image_files = [os.path.join(source_dir, f) for f in os.listdir(source_dir) 
                      if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff'))]
        image_files.sort()  # 确保顺序一致
        logger.info(f"找到 {len(image_files)} 个图像文件")
    else:
        image_files = [source_dir]
        logger.info("使用单个图像文件进行推理")
    
    # 加载原始图像用于质量评估
    if use_adaptive_threshold:
        logger.info("加载图像用于质量评估...")
        raw_images = []
        for img_path in image_files:
            img = cv2.imread(img_path)
            if img is None:
                logger.warning(f"无法读取图像: {img_path}，使用空白图像代替")
                img = np.zeros((640, 640, 3), dtype=np.uint8)
            raw_images.append(img)
    
    # 推理并保存结果
    try:
        logger.info("开始推理...")
        results = model.predict(
            source=image_files,
            device=device,
            imgsz=img_size,
            conf=conf_threshold if not use_adaptive_threshold else 0.01,  # 使用较低的初始阈值如果启用自适应
            iou=0.6,  # NMS IoU阈值
            half=True,  # 使用半精度推理提高速度
            augment=False,  # 不使用测试时增强
            batch=batch_size,
            verbose=False,  # 关闭YOLOv8的内置日志
            save=False,   # 不使用内置保存
            max_det=300   # 每张图像的最大检测框数量
        )
        
        # 应用自适应阈值
        if use_adaptive_threshold and raw_images:
            logger.info("应用自适应阈值...")
            results = apply_adaptive_thresholds(results, class_names, raw_images, conf_base=conf_threshold)
        
        # 保存总结果信息到JSON文件
        summary_data = {
            "inference_time": time.time() - start_time,
            "model_path": str(model_path),
            "source_dir": str(source_dir),
            "device": device,
            "image_size": img_size,
            "conf_threshold": conf_threshold,
            "use_adaptive_threshold": use_adaptive_threshold,
            "total_images": len(results),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 保存并打印结果
        if save_results:
            logger.info("保存结果...")
            all_detections = []
            
            for i, result in enumerate(results):
                file_name = os.path.basename(image_files[i] if i < len(image_files) else f"image_{i}")
                base_name = os.path.splitext(file_name)[0]
                
                # 保存带检测框的图像
                save_path = str(save_dir / f"{base_name}_result.jpg")
                result.save(filename=save_path)
                logger.info(f"保存推理结果图像: {save_path}")
                
                # 提取并保存检测数据
                boxes = result.boxes
                num_objects = len(boxes)
                
                # 准备当前图像的检测数据
                image_detections = {
                    "image_file": file_name,
                    "image_path": str(image_files[i]),
                    "num_detections": num_objects,
                    "detections": []
                }
                
                # 添加每个检测框的详细信息
                if num_objects > 0:
                    for j in range(num_objects):
                        cls_id = int(boxes.cls[j].item())
                        cls_name = class_names[cls_id] if cls_id in class_names else f"未知类别({cls_id})"
                        conf = float(boxes.conf[j].item())  # 转换为Python浮点数以便JSON序列化
                        box = boxes.xyxy[j].tolist()
                        
                        # 保存检测数据
                        detection = {
                            "class_id": cls_id,
                            "class_name": cls_name,
                            "confidence": conf,
                            "box": [int(box[0]), int(box[1]), int(box[2]), int(box[3])]
                        }
                        image_detections["detections"].append(detection)
                
                # 将当前图像的检测数据添加到总列表
                all_detections.append(image_detections)
                
                # 为每个图像单独保存一个JSON文件
                detection_json_path = detection_data_dir / f"{base_name}_detections.json"
                with open(detection_json_path, 'w', encoding='utf-8') as f:
                    json.dump(image_detections, f, ensure_ascii=False, indent=2)
            
            # 将所有检测数据保存到一个汇总JSON文件
            summary_data["detections"] = all_detections
            summary_json_path = save_dir / "inference_results.json"
            with open(summary_json_path, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"保存检测结果数据: {summary_json_path}")
        
        # 计算并打印总推理时间
        inference_time = time.time() - start_time
        if results and len(results) > 0:
            logger.info(f"推理完成，总耗时: {inference_time:.2f} 秒，平均每张: {inference_time/len(results):.3f} 秒")
            
            # 检查检测结果
            total_objects = 0
            for i, result in enumerate(results):
                boxes = result.boxes
                num_objects = len(boxes)
                total_objects += num_objects
                
                logger.info(f"\n图像 {i} 检测结果: 检测到 {num_objects} 个对象")
                if num_objects > 0:
                    for j in range(num_objects):
                        cls_id = int(boxes.cls[j].item())
                        cls_name = class_names[cls_id] if cls_id in class_names else f"未知类别({cls_id})"
                        conf = boxes.conf[j].item()
                        box = boxes.xyxy[j].tolist()
                        logger.info(f"  - {cls_name}: 置信度={conf:.2f}, 位置=[{int(box[0])}, {int(box[1])}, {int(box[2])}, {int(box[3])}]")
            
            logger.info(f"总共检测到 {total_objects} 个对象，平均每张图像 {total_objects/len(results):.1f} 个")
        else:
            logger.warning("未检测到任何有效结果")
            logger.info(f"推理完成，总耗时: {inference_time:.2f} 秒")
        
        logger.info(f"结果已保存到目录: {save_dir}")
        
        return results
    
    except Exception as e:
        logger.error(f"推理过程中出错: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    # 命令行参数解析器，用于配置推理过程
    import argparse
    
    # 创建参数解析器，定义脚本功能描述
    parser = argparse.ArgumentParser(
        description='YOLO模型推理工具 - 用于UI自动化测试的目标检测',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter  # 在帮助文本中显示默认值
    )
    
    # 添加参数分组：基本参数
    group_basic = parser.add_argument_group('基本参数')
    group_basic.add_argument('--model', type=str, 
                      help='模型路径，如不指定则使用训练好的最佳模型(best.pt)')
    group_basic.add_argument('--source', type=str, 
                      help='测试图片目录或单个图片路径，如不指定则使用默认测试集')
    group_basic.add_argument('--save-dir', type=str, 
                      help='结果保存目录，默认使用时间戳命名(outputs/infer_results/YYYYMMDD_HHMMSS)')
    
    # 添加参数分组：模型配置
    group_model = parser.add_argument_group('模型配置')
    group_model.add_argument('--img-size', type=int, default=640, 
                      help='输入图像尺寸，较大的值可提高检测精度但会降低速度')
    group_model.add_argument('--conf', type=float, default=0.25, 
                      help='置信度阈值(0.0-1.0)，值越高过滤越严格')
    group_model.add_argument('--no-adaptive', action='store_true', 
                      help='禁用自适应阈值机制，使用固定阈值')
    
    # 添加参数分组：性能选项
    group_perf = parser.add_argument_group('性能选项')
    group_perf.add_argument('--device', type=str, choices=['cuda', 'cpu', 'mps'], 
                      help='指定推理设备(cuda/cpu/mps)，默认自动选择最佳设备')
    group_perf.add_argument('--batch-size', type=int, default=16, 
                      help='批处理大小，较大的值可提高吞吐量但需要更多GPU内存')
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 打印配置信息
    logger.info("=" * 50)
    logger.info("YOLO UI元素检测器 - 推理模式")
    logger.info("-" * 50)
    logger.info(f"• 模型路径:     {args.model or '默认最佳模型'}")
    logger.info(f"• 输入来源:     {args.source or '默认测试集'}")
    logger.info(f"• 输出目录:     {args.save_dir or '自动生成时间戳目录'}")
    logger.info(f"• 推理设备:     {args.device or '自动选择最佳设备'}")
    logger.info(f"• 图像尺寸:     {args.img_size}px")
    logger.info(f"• 阈值模式:     {'固定阈值 '+str(args.conf) if args.no_adaptive else '自适应阈值(基础:'+str(args.conf)+')'}")
    logger.info(f"• 批处理大小:   {args.batch_size}")
    logger.info("=" * 50)
    
    # 执行推理
    run_inference(
        model_path=args.model,
        source_dir=args.source,
        save_dir=args.save_dir,
        device=args.device,
        img_size=args.img_size,
        conf_threshold=args.conf,
        use_adaptive_threshold=not args.no_adaptive,
        batch_size=args.batch_size
    )