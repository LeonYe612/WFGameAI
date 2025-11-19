"""
两阶段OCR检测服务
核心业务逻辑
"""

import logging
import os
import re
import shutil
import tempfile
import uuid
from typing import List, Dict, Any, Tuple

from .performance_config import get_performance_config, PARAM_VERSIONS
from .ocr_service import OCRInstancePool

logger = logging.getLogger(__name__)

# 中文字符匹配模式
CHINESE_CHAR_PATTERN = re.compile(r"[\u4e00-\u9fff]")


class TwoStageOCRService:
    """两阶段OCR检测服务"""
    
    def __init__(self, performance_config_name: str = "balanced", enable_detailed_report: bool = False):
        """初始化两阶段OCR服务"""
        self.perf_config = get_performance_config(performance_config_name)
        self.ocr_pool = OCRInstancePool()
        self.shared_pipeline = None
        self.enable_detailed_report = enable_detailed_report
        self.temp_dir = None
        self.path_mapping = {}  # 原始路径 -> 临时路径的映射
    
    def contains_chinese(self, text: str) -> bool:
        """检查文本是否包含中文字符"""
        return bool(CHINESE_CHAR_PATTERN.search(text))
    
    def normalize_texts(self, texts: List[Any]) -> List[str]:
        """标准化文本列表"""
        normalized = []
        for item in texts:
            if isinstance(item, (list, tuple)) and item:
                normalized.append(str(item[0]))
            else:
                normalized.append(str(item))
        return normalized
    
    def normalize_scores(self, scores: List[Any]) -> List[float]:
        """标准化分数列表"""
        normalized = []
        for score in scores:
            try:
                normalized.append(float(score))
            except (TypeError, ValueError):
                continue
        return normalized
    
    def build_record(self, data: Dict[str, Any], stage: str) -> Dict[str, Any]:
        """构建OCR结果记录"""
        texts = self.normalize_texts(data.get("rec_texts", []))
        scores = self.normalize_scores(data.get("rec_scores", []))
        threshold = data.get("text_rec_score_thresh", 0.0)
        
        try:
            threshold_value = float(threshold)
        except (TypeError, ValueError):
            threshold_value = 0.0
            
        record = {
            "input_path": data.get("input_path"),
            "stage": stage,
            "rec_texts": texts,
            "rec_scores": scores,
            "text_rec_score_thresh": threshold_value,
            "max_rec_score": max(scores) if scores else None,
            "has_match": any(self.contains_chinese(text) for text in texts),
        }
        return record
    
    def create_shared_pipeline(self, lang: str = "ch"):
        """创建共享Pipeline实例"""
        if self.shared_pipeline is None:
            config = self.perf_config.get_config()
            use_fast_models = config.get("use_fast_models", False)
            
            self.shared_pipeline = self.ocr_pool.get_ocr_instance(
                lang=lang,
                stage="baseline",
                use_fast_models=use_fast_models
            )
            
        return self.shared_pipeline
    
    def prepare_images_for_ocr(self, input_images: List[str]) -> List[str]:
        """为OCR准备图片，处理中文路径问题"""
        if not input_images:
            return []
            
        # 创建临时目录
        if self.temp_dir is None:
            self.temp_dir = tempfile.mkdtemp(prefix="ocr_temp_")
            logger.debug(f"创建临时目录: {self.temp_dir}")
        
        prepared_images = []
        for original_path in input_images:
            try:
                # 检查路径是否包含中文字符
                if any('\u4e00' <= char <= '\u9fff' for char in original_path):
                    # 包含中文，创建临时副本
                    file_ext = os.path.splitext(original_path)[1]
                    temp_filename = f"{uuid.uuid4().hex}{file_ext}"
                    temp_path = os.path.join(self.temp_dir, temp_filename)
                    
                    # 复制文件到临时路径
                    shutil.copy2(original_path, temp_path)
                    self.path_mapping[temp_path] = original_path
                    prepared_images.append(temp_path)
                    logger.debug(f"中文路径映射: {original_path} -> {temp_path}")
                else:
                    # 不包含中文，直接使用
                    prepared_images.append(original_path)
            except Exception as e:
                logger.warning(f"准备图片失败，跳过: {original_path}, 错误: {e}")
                
        return prepared_images
    
    def cleanup_temp_files(self):
        """清理临时文件"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                logger.debug(f"清理临时目录: {self.temp_dir}")
                self.temp_dir = None
                self.path_mapping.clear()
            except Exception as e:
                logger.warning(f"清理临时文件失败: {e}")
    
    def run_single_stage(self, stage: str, input_images: List[str], 
                        lang: str = "ch") -> Tuple[List[Dict[str, Any]], List[str]]:
        """运行单阶段OCR检测"""
        stage_params = PARAM_VERSIONS[stage]
        
        # 预处理图片路径，处理中文路径问题
        prepared_images = self.prepare_images_for_ocr(input_images)
        if not prepared_images:
            logger.warning("没有有效的图片可以处理")
            return [], input_images
        
        logger.info(f"准备处理 {len(prepared_images)} 张图片（原始: {len(input_images)}）")
        
        # 获取或创建共享Pipeline
        pipeline = self.create_shared_pipeline(lang)
        
        # 获取批处理大小
        batch_size = self.perf_config.get_batch_size(len(prepared_images))
        
        # 预测参数
        predict_params = {
            "use_doc_orientation_classify": stage_params.get("use_doc_orientation_classify", False),
            "use_doc_unwarping": stage_params.get("use_doc_unwarping", False),
            "use_textline_orientation": stage_params.get("use_textline_orientation", False),
            "text_det_limit_side_len": stage_params["text_det_limit_side_len"],
            "text_det_limit_type": stage_params["text_det_limit_type"],
            "text_det_thresh": stage_params["text_det_thresh"],
            "text_det_box_thresh": stage_params["text_det_box_thresh"],
            "text_det_unclip_ratio": stage_params["text_det_unclip_ratio"],
            "text_rec_score_thresh": stage_params["text_rec_score_thresh"],
        }
        
        hits_records = []
        miss_image_paths = []
        
        # 分批处理图片
        for i in range(0, len(prepared_images), batch_size):
            batch_images = prepared_images[i:i + batch_size]
            
            # 现在图片路径已经预处理过，直接使用
            valid_batch = batch_images
                
            try:
                batch_results = list(pipeline.predict(valid_batch, **predict_params))
            except Exception as e:
                logger.error(f"批次 {i//batch_size + 1} 处理失败: {e}")
                # 尝试单张处理
                batch_results = []
                for single_img in valid_batch:
                    try:
                        single_result = list(pipeline.predict([single_img], **predict_params))
                        batch_results.extend(single_result)
                    except Exception as single_e:
                        logger.error(f"单张图片处理失败: {single_img}, 错误: {single_e}")
                        # 创建一个空结果，添加到未命中列表
                        miss_image_paths.append(single_img)
                        continue
            
            # 处理批次结果
            for result in batch_results:
                result_data = result.json["res"]
                
                # 将临时路径映射回原始路径
                temp_path = result_data["input_path"]
                original_path = self.path_mapping.get(temp_path, temp_path)
                result_data["input_path"] = original_path
                
                record = self.build_record(result_data, stage)
                
                if record["has_match"]:
                    hits_records.append(record)
                else:
                    miss_image_paths.append(original_path)
        
        return hits_records, miss_image_paths
    
    def process_two_stage_detection(self, input_images: List[str], 
                                   lang: str = "ch") -> Dict[str, Any]:
        """执行两阶段OCR检测"""
        # 阶段1: baseline检测
        stage1_hits, stage1_miss_paths = self.run_single_stage(
            "baseline", input_images, lang
        )
        
        # 阶段2: balanced_v1检测未命中的图片
        if stage1_miss_paths:
            stage2_hits, final_miss_paths = self.run_single_stage(
                "balanced_v1", stage1_miss_paths, lang
            )
        else:
            stage2_hits = []
            final_miss_paths = []
        
        # 合并最终结果
        all_hits = stage1_hits + stage2_hits
        
        # 清理临时文件
        self.cleanup_temp_files()
        
        # 根据开关决定返回内容
        if self.enable_detailed_report:
            # 返回详细的分析和报告信息
            total_images = len(input_images)
            total_hits = len(all_hits)
            final_miss = len(final_miss_paths)
            overall_hit_rate = (total_hits / total_images * 100) if total_images > 0 else 0
            
            return {
                "detection_strategy": "两阶段检测 (baseline + balanced_v1)",
                "stage1_baseline": {
                    "hits_count": len(stage1_hits),
                    "hits_records": stage1_hits,
                    "version_params": PARAM_VERSIONS["baseline"]
                },
                "stage2_balanced": {
                    "hits_count": len(stage2_hits),
                    "hits_records": stage2_hits,
                    "version_params": PARAM_VERSIONS["balanced_v1"]
                },
                "final_statistics": {
                    "total_images": total_images,
                    "total_hits": total_hits,
                    "final_miss": final_miss,
                    "final_miss_paths": final_miss_paths,
                    "overall_hit_rate": overall_hit_rate,
                    "stage1_contribution": (len(stage1_hits) / total_hits * 100) if total_hits > 0 else 0,
                    "stage2_contribution": (len(stage2_hits) / total_hits * 100) if total_hits > 0 else 0,
                },
                "performance_config": self.perf_config.config_name,
                "all_hits_records": all_hits
            }
        else:
            # 只返回核心数据
            return {
                "all_hits_records": all_hits,
                "final_statistics": {
                    "total_images": len(input_images),
                    "total_hits": len(all_hits),
                    "final_miss": len(final_miss_paths),
                    "final_miss_paths": final_miss_paths,
                }
            }
