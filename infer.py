#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Author  : HoneyDou
# @Time    : 2025/4/7 13:38
# @File    : infer.py
"""
YOLO模型推理脚本
用于加载训练好的模型并对测试数据集进行推理
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

# 导入UI元素自适应阈值配置
# 为不同UI元素定义自适应阈值配置
UI_ADAPTIVE_THRESHOLDS = {
    # 按钮元素
    'button': {
        'base_conf': 0.25,          # 基础置信度阈值
        'min_conf': 0.20,           # 最小置信度阈值
        'adaptive_factor': 0.05,    # 自适应调整因子
    },
    # 文本元素
    'text': {
        'base_conf': 0.30,
        'min_conf': 0.25, 
        'adaptive_factor': 0.03,
    },
    # 图标元素
    'icon': {
        'base_conf': 0.35,
        'min_conf': 0.30,
        'adaptive_factor': 0.04,
    },
    # 菜单元素
    'menu': {
        'base_conf': 0.40,
        'min_conf': 0.30,
        'adaptive_factor': 0.05,
    },
    # 对话框元素
    'dialog': {
        'base_conf': 0.45,
        'min_conf': 0.35,
        'adaptive_factor': 0.05,
    },
    # 默认值(用于未指定的元素类型)
    'default': {
        'base_conf': 0.30,
        'min_conf': 0.25,
        'adaptive_factor': 0.04,
    }
}

def get_adaptive_threshold(element_type, image_quality=1.0):
    """
    根据UI元素类型和图像质量获取自适应阈值
    
    Args:
        element_type: UI元素类型 ('button', 'text', 'icon', 'menu', 'dialog')
        image_quality: 图像质量因子(0.0-1.0)，值越小表示图像质量越差
        
    Returns:
        适合该元素类型的检测阈值
    """
    # 如果元素类型不在配置中，使用默认值
    if element_type not in UI_ADAPTIVE_THRESHOLDS:
        element_type = 'default'
    
    # 获取该元素类型的阈值配置    
    threshold_config = UI_ADAPTIVE_THRESHOLDS[element_type]
    
    # 根据图像质量调整阈值
    quality_factor = max(0.0, min(1.0, image_quality))  # 确保在0-1范围内
    quality_adjustment = threshold_config['adaptive_factor'] * (1.0 - quality_factor)
    
    # 计算最终阈值 (质量越低，阈值越低)
    final_threshold = threshold_config['base_conf'] - quality_adjustment
    
    # 确保不低于最小阈值
    final_threshold = max(final_threshold, threshold_config['min_conf'])
    
    return final_threshold

def estimate_image_quality(image):
    """
    估计图像质量，用于自适应阈值调整
    
    Args:
        image: 输入图像(numpy数组)
        
    Returns:
        image_quality: 图像质量因子(0.0-1.0)，值越大表示质量越好
    """
    # 转为灰度图
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    # 计算拉普拉斯方差(图像清晰度)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    
    # 计算对比度(使用像素标准差作为简单度量)
    contrast = gray.std()
    
    # 计算亮度(使用平均像素值)
    brightness = gray.mean() / 255.0
    
    # 亮度适中得分(亮度接近0.5时最高)
    brightness_score = 1.0 - 2.0 * abs(brightness - 0.5)
    
    # 综合得分，归一化到0-1范围
    # 清晰度、对比度越高越好，亮度适中最佳
    quality_score = (
        0.6 * min(1.0, laplacian_var / 500.0) +  # 清晰度权重60%
        0.3 * min(1.0, contrast / 80.0) +        # 对比度权重30%
        0.1 * brightness_score                    # 亮度适中性权重10%
    )
    
    # 确保在0-1范围内
    return max(0.0, min(1.0, quality_score))

def apply_adaptive_thresholds(results, classes, images, conf_base=0.25):
    """
    对检测结果应用自适应阈值
    
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
    运行模型推理并保存结果
    
    Args:
        model_path: 模型路径，默认使用训练好的最佳模型
        source_dir: 测试图片目录，默认使用测试集图片
        save_dir: 结果保存目录，默认保存到outputs/infer_results/YYYY-MM-DD_HH-MM-SS
        device: 推理设备，默认自动选择(cuda/mps/cpu)
        img_size: 输入图像大小，默认640提高精度
        conf_threshold: 置信度阈值
        use_adaptive_threshold: 是否使用自适应阈值
        class_names: 类别名称列表(如果为None，将从模型中提取)
        save_results: 是否保存结果
        batch_size: 批处理大小
    
    Returns:
        results: 模型推理结果列表
    """
    start_time = time.time()
    
    # 设置默认参数
    if model_path is None:
        model_path = ROOT_DIR / "datasets" / "train" / "weights" / "best.pt"
    
    if source_dir is None:
        source_dir = ROOT_DIR / "datasets" / "yolov11-card2" / "test" / "images"
    
    if save_dir is None:
        # 创建按日期和时间命名的结果文件夹
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
    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(description='YOLO模型推理工具')
    parser.add_argument('--model', type=str, help='模型路径')
    parser.add_argument('--source', type=str, help='测试图片目录或图片路径')
    parser.add_argument('--save-dir', type=str, help='结果保存目录')
    parser.add_argument('--device', type=str, help='推理设备(cuda/mps/cpu)')
    parser.add_argument('--img-size', type=int, default=640, help='输入图像大小')
    parser.add_argument('--conf', type=float, default=0.25, help='置信度阈值')
    parser.add_argument('--no-adaptive', action='store_true', help='禁用自适应阈值')
    parser.add_argument('--batch-size', type=int, default=16, help='批处理大小')
    args = parser.parse_args()
    
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