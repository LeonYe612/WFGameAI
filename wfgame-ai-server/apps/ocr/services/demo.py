import json
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List

import paddle
from PIL import Image

from paddlex import create_pipeline

'''
两阶段OCR检测方案：
1. 第一阶段：使用baseline版本检测所有图片，获得高质量中文识别结果
2. 第二阶段：使用balanced_v1版本检测baseline未命中的图片，补充识别
3. 合并两阶段结果作为最终输出

./output/
├── stage1_baseline/        # 第一阶段baseline结果
│   ├── hits/              # baseline命中图片
│   ├── miss/              # baseline未命中原图
│   └── *.json             # baseline分析报告
├── stage2_balanced/       # 第二阶段balanced结果
│   ├── hits/              # balanced补充命中图片
│   ├── miss/              # 最终未命中原图
│   └── *.json             # balanced分析报告
├── final_results/         # 最终合并结果
│   ├── hits/              # 所有命中图片（baseline + balanced）
│   ├── miss/              # 最终未命中原图
│   └── final_summary.json # 最终汇总报告
└── comparison_report.json  # 两阶段对比报告
'''

# 参数配置版本管理
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
    "balanced_v1": {    # 弥补基线版本对长方形图识别率低的缺陷
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

# 两阶段检测配置
TWO_STAGE_CONFIG = {
    "device": "gpu:0",
    "dataset_dir": Path("../ocr_det_dataset"),  # 修复：指向上级目录的数据集
    "output_base_dir": Path("../output"),
    "stage1_dir": Path("../output/stage1_baseline"),
    "stage2_dir": Path("../output/stage2_balanced"),
    "final_dir": Path("../output/final_results"),
    "text_detection_model_name": "PP-OCRv5_server_det",
    "text_recognition_model_name": "PP-OCRv5_server_rec",
}


CHINESE_CHAR_PATTERN = re.compile(r"[\u4e00-\u9fff]")


def ensure_gpu(device_name: str) -> str:
    if not paddle.device.is_compiled_with_cuda():
        raise EnvironmentError("未启用GPU，请安装GPU版PaddlePaddle")
    if paddle.device.cuda.device_count() <= 0:
        raise EnvironmentError("未检测到可用GPU，请检查驱动与CUDA环境")
    paddle.device.set_device(device_name)
    return device_name


def prepare_output_dir(path: Path) -> Path:
    resolved = Path(path)
    if resolved.exists():
        for child in resolved.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def build_pipeline(config: Dict[str, Any]) -> object:
    device_name = ensure_gpu(config["device"])
    return create_pipeline(
        "OCR",
        device=device_name,
        use_doc_preprocessor=config["use_doc_preprocessor"],
        use_textline_orientation=config["use_textline_orientation"],
        text_detection_model_name=config["text_detection_model_name"],
        text_recognition_model_name=config["text_recognition_model_name"],
    )


def contains_chinese(text: str) -> bool:
    return bool(CHINESE_CHAR_PATTERN.search(text))


def normalize_texts(texts: List[Any]) -> List[str]:
    normalized = []
    for item in texts:
        if isinstance(item, (list, tuple)) and item:
            normalized.append(str(item[0]))
        else:
            normalized.append(str(item))
    return normalized


def normalize_scores(scores: List[Any]) -> List[float]:
    normalized = []
    for score in scores:
        try:
            normalized.append(float(score))
        except (TypeError, ValueError):
            continue
    return normalized


def build_record(data: Dict[str, Any]) -> Dict[str, Any]:
    texts = normalize_texts(data.get("rec_texts", []))
    scores = normalize_scores(data.get("rec_scores", []))
    threshold = data.get("text_rec_score_thresh", 0.0)
    try:
        threshold_value = float(threshold)
    except (TypeError, ValueError):
        threshold_value = 0.0
    record = {
        "input_path": data.get("input_path"),
        "page_index": data.get("page_index"),
        "rec_texts": texts,
        "rec_scores": scores,
        "text_rec_score_thresh": threshold_value,
        "max_rec_score": max(scores) if scores else None,
    }
    return record


def analyze_ocr_modules(data: Dict[str, Any]) -> Dict[str, Any]:
    """分析OCR各模块效果，用于问题诊断"""
    analysis = {
        "input_path": data.get("input_path"),
        "module_analysis": {},
        "problem_diagnosis": []
    }
    
    # 1. 文档预处理模块分析
    doc_preprocessor_res = data.get("doc_preprocessor_res", {})
    if isinstance(doc_preprocessor_res, dict):
        angle = doc_preprocessor_res.get("angle", 0)
        analysis["module_analysis"]["doc_orientation"] = {
            "detected_angle": angle,
            "status": "正常" if angle in [0, 90, 180, 270] else "异常"
        }
        if angle not in [0, 90, 180, 270]:
            analysis["problem_diagnosis"].append("整图旋转矫正不准 - 需微调文档图像方向分类模块")
    
    # 2. 文本检测模块分析
    dt_polys = data.get("dt_polys", [])
    text_det_params = data.get("text_det_params", {})
    detection_count = len(dt_polys) if dt_polys is not None else 0
    analysis["module_analysis"]["text_detection"] = {
        "detected_boxes_count": detection_count,
        "detection_thresh": text_det_params.get("thresh", "未知"),
        "box_thresh": text_det_params.get("box_thresh", "未知"),
        "status": "正常" if detection_count > 0 else "可能漏检"
    }
    if detection_count == 0:
        analysis["problem_diagnosis"].append("文本存在漏检 - 需微调文本检测模块")
    
    # 3. 文本行方向分类模块分析
    textline_angles = data.get("textline_orientation_angles", [])
    if textline_angles is not None and len(textline_angles) > 0:
        analysis["module_analysis"]["textline_orientation"] = {
            "textline_angles": textline_angles.tolist() if hasattr(textline_angles, 'tolist') else textline_angles,
            "rotated_lines_count": sum(1 for angle in textline_angles if angle != 0),
            "status": "正常"
        }
    
    # 4. 文本识别模块分析
    rec_texts = data.get("rec_texts", [])
    rec_scores = data.get("rec_scores", [])
    threshold = data.get("text_rec_score_thresh", 0.0)
    
    low_confidence_count = 0
    empty_text_count = 0
    for i, (text, score) in enumerate(zip(rec_texts, rec_scores)):
        if not text or text.strip() == "":
            empty_text_count += 1
        elif score < threshold:
            low_confidence_count += 1
    
    analysis["module_analysis"]["text_recognition"] = {
        "total_texts": len(rec_texts),
        "empty_texts": empty_text_count,
        "low_confidence_texts": low_confidence_count,
        "avg_confidence": sum(rec_scores) / len(rec_scores) if rec_scores else 0,
        "threshold": threshold,
        "status": "正常" if empty_text_count == 0 and low_confidence_count < len(rec_texts) * 0.3 else "识别效果差"
    }
    
    if empty_text_count > 0 or low_confidence_count > len(rec_texts) * 0.5:
        analysis["problem_diagnosis"].append("文本内容都不准 - 需微调文本识别模块")
    
    return analysis


def write_json_file(path: Path, content: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(content, file, ensure_ascii=False, indent=2)


def copy_original_image(input_path: str, target_dir: Path) -> str:
    """复制原始图片到目标目录"""
    source_path = Path(input_path)
    if not source_path.exists():
        return ""
    
    # 确保目标目录存在
    target_dir.mkdir(parents=True, exist_ok=True)
    
    target_path = target_dir / source_path.name
    shutil.copy2(source_path, target_path)
    return str(target_path)


def run_single_stage(version_name: str, input_images: List[str], stage_dir: Path) -> tuple[List[Dict[str, Any]], List[str]]:
    """运行单阶段OCR检测
    
    Args:
        version_name: 版本名称 (baseline 或 balanced_v1)
        input_images: 输入图片路径列表
        stage_dir: 阶段输出目录
        
    Returns:
        tuple: (命中记录列表, 未命中图片路径列表)
    """
    print(f"\n[OCR] 运行阶段: {PARAM_VERSIONS[version_name]['version_name']} ({version_name})")
    print(f"输入图片数: {len(input_images)}")
    print(f"输出目录: {stage_dir}")
    print("检测参数:")
    for key, value in PARAM_VERSIONS[version_name].items():
        if key != "version_name":
            print(f"   {key}: {value}")
    print("-" * 50)
    
    # 准备目录
    hits_dir = prepare_output_dir(stage_dir / "hits")
    miss_dir = prepare_output_dir(stage_dir / "miss")
    prepare_output_dir(stage_dir)
    
    # 构建pipeline配置
    current_params = PARAM_VERSIONS[version_name]
    pipeline_config = {
        "device": TWO_STAGE_CONFIG["device"],
        "text_detection_model_name": TWO_STAGE_CONFIG["text_detection_model_name"],
        "text_recognition_model_name": TWO_STAGE_CONFIG["text_recognition_model_name"],
        "use_doc_preprocessor": current_params.get("use_doc_preprocessor", False),
        "use_textline_orientation": current_params.get("use_textline_orientation", False),
        "use_doc_orientation_classify": current_params.get("use_doc_orientation_classify", False),
        "use_doc_unwarping": current_params.get("use_doc_unwarping", False),
    }
    
    pipeline = build_pipeline(pipeline_config)
    
    # 预测参数
    predict_params = {
        "use_doc_orientation_classify": current_params.get("use_doc_orientation_classify", False),
        "use_doc_unwarping": current_params.get("use_doc_unwarping", False),
        "use_textline_orientation": current_params.get("use_textline_orientation", False),
        "text_det_limit_side_len": current_params["text_det_limit_side_len"],
        "text_det_limit_type": current_params["text_det_limit_type"],
        "text_det_thresh": current_params["text_det_thresh"],
        "text_det_box_thresh": current_params["text_det_box_thresh"],
        "text_det_unclip_ratio": current_params["text_det_unclip_ratio"],
        "text_rec_score_thresh": current_params["text_rec_score_thresh"],
    }
    
    hits_records: List[Dict[str, Any]] = []
    miss_records: List[Dict[str, Any]] = []
    miss_image_paths: List[str] = []
    module_analysis_records: List[Dict[str, Any]] = []
    
    # 处理输入图片
    for result in pipeline.predict(input_images, **predict_params):
        result.print()
        result_data = result.json["res"]
        record = build_record(result_data)
        
        # 进行模块效果分析
        module_analysis = analyze_ocr_modules(result_data)
        module_analysis_records.append(module_analysis)
        
        texts = record["rec_texts"]
        if any(contains_chinese(text) for text in texts):
            # 命中：保存OCR结果图到hits目录
            result.save_to_img(str(hits_dir))
            hits_records.append(record)
        else:
            # 未命中：保存OCR结果图到stage目录，保存原图到miss目录
            result.save_to_img(str(stage_dir))
            original_image_path = copy_original_image(result_data["input_path"], miss_dir)
            record["original_image_saved_path"] = original_image_path
            miss_records.append(record)
            miss_image_paths.append(result_data["input_path"])
    
    # 保存阶段结果
    write_json_file(hits_dir / "hits_summary.json", hits_records)
    write_json_file(stage_dir / "miss_summary.json", miss_records)
    write_json_file(stage_dir / "module_analysis.json", module_analysis_records)
    
    # 生成问题诊断
    all_problems = []
    for analysis in module_analysis_records:
        all_problems.extend(analysis["problem_diagnosis"])
    
    problem_summary = {
        "stage": version_name,
        "total_images": len(module_analysis_records),
        "hits_count": len(hits_records),
        "miss_count": len(miss_records),
        "problem_statistics": {},
        "recommendations": []
    }
    
    for problem in all_problems:
        problem_summary["problem_statistics"][problem] = problem_summary["problem_statistics"].get(problem, 0) + 1
    
    write_json_file(stage_dir / "problem_diagnosis.json", problem_summary)
    
    # 输出阶段结果摘要
    print(f"\n[阶段结果] {PARAM_VERSIONS[version_name]['version_name']}:")
    print(f"   处理图片数: {len(module_analysis_records)}")
    print(f"   命中图片: {len(hits_records)}")
    print(f"   未命中图片: {len(miss_records)}")
    if len(module_analysis_records) > 0:
        hit_rate = len(hits_records) / len(module_analysis_records) * 100
        print(f"   命中率: {hit_rate:.1f}%")
    print(f"   结果保存至: {stage_dir}")
    print("-" * 50)
    
    return hits_records, miss_image_paths


def merge_final_results(stage1_hits: List[Dict[str, Any]], stage2_hits: List[Dict[str, Any]], 
                       final_miss_paths: List[str]) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """合并两阶段结果生成最终报告"""
    final_dir = prepare_output_dir(TWO_STAGE_CONFIG["final_dir"])
    final_hits_dir = prepare_output_dir(final_dir / "hits")
    final_miss_dir = prepare_output_dir(final_dir / "miss")
    
    # 合并命中记录
    all_hits = stage1_hits + stage2_hits
    
    # 复制命中图片到最终目录
    stage1_hits_dir = TWO_STAGE_CONFIG["stage1_dir"] / "hits"
    stage2_hits_dir = TWO_STAGE_CONFIG["stage2_dir"] / "hits"
    
    # 复制stage1命中的图片
    if stage1_hits_dir.exists():
        for file in stage1_hits_dir.iterdir():
            if file.is_file():
                shutil.copy2(file, final_hits_dir / f"stage1_{file.name}")
    
    # 复制stage2命中的图片
    if stage2_hits_dir.exists():
        for file in stage2_hits_dir.iterdir():
            if file.is_file():
                shutil.copy2(file, final_hits_dir / f"stage2_{file.name}")
    
    # 复制最终未命中的原图
    for miss_path in final_miss_paths:
        copy_original_image(miss_path, final_miss_dir)
    
    # 生成最终汇总报告
    total_images = len(all_hits) + len(final_miss_paths)
    final_summary = {
        "detection_strategy": "两阶段检测 (baseline + balanced_v1)",
        "stage1_baseline": {
            "hits_count": len(stage1_hits),
            "version_params": PARAM_VERSIONS["baseline"]
        },
        "stage2_balanced": {
            "hits_count": len(stage2_hits),
            "version_params": PARAM_VERSIONS["balanced_v1"]
        },
        "final_statistics": {
            "total_images": total_images,
            "total_hits": len(all_hits),
            "final_miss": len(final_miss_paths),
            "overall_hit_rate": len(all_hits) / total_images * 100 if total_images > 0 else 0,
            "stage1_contribution": len(stage1_hits) / len(all_hits) * 100 if len(all_hits) > 0 else 0,
            "stage2_contribution": len(stage2_hits) / len(all_hits) * 100 if len(all_hits) > 0 else 0,
        },
        "all_hits_records": all_hits
    }
    
    write_json_file(final_dir / "final_summary.json", final_summary)
    
    # 生成对比报告
    comparison_report = {
        "comparison_analysis": {
            "baseline_only_hits": len(stage1_hits),
            "balanced_补充_hits": len(stage2_hits),
            "improvement_by_stage2": len(stage2_hits) / total_images * 100 if total_images > 0 else 0,
            "final_miss_rate": len(final_miss_paths) / total_images * 100 if total_images > 0 else 0
        },
        "strategy_effectiveness": {
            "baseline_hit_rate": len(stage1_hits) / total_images * 100 if total_images > 0 else 0,
            "combined_hit_rate": len(all_hits) / total_images * 100 if total_images > 0 else 0,
            "improvement_percentage": len(stage2_hits) / total_images * 100 if total_images > 0 else 0
        }
    }
    
    write_json_file(TWO_STAGE_CONFIG["output_base_dir"] / "comparison_report.json", comparison_report)
    
    return final_summary, comparison_report


def main() -> None:
    """两阶段OCR检测主函数"""
    print("=" * 60)
    print("两阶段OCR检测方案启动")
    print("阶段1: baseline版本 (高质量基线检测)")
    print("阶段2: balanced_v1版本 (补充检测)")
    print("=" * 60)
    
    # 准备基础目录
    prepare_output_dir(TWO_STAGE_CONFIG["output_base_dir"])
    
    # 获取所有输入图片
    dataset_dir = TWO_STAGE_CONFIG["dataset_dir"]
    all_images = []
    if dataset_dir.exists():
        for img_path in dataset_dir.rglob("*"):
            if img_path.is_file() and img_path.suffix.lower() in ['.png', '.jpg', '.jpeg']:
                all_images.append(str(img_path))
    
    print(f"总输入图片数: {len(all_images)}")
    
    # 阶段1: baseline检测
    print("\n" + "="*30 + " 阶段1: BASELINE检测 " + "="*30)
    stage1_hits, stage1_miss_paths = run_single_stage(
        "baseline", 
        all_images, 
        TWO_STAGE_CONFIG["stage1_dir"]
    )
    
    # 阶段2: balanced_v1检测未命中的图片
    print("\n" + "="*30 + " 阶段2: BALANCED补充检测 " + "="*30)
    if stage1_miss_paths:
        stage2_hits, final_miss_paths = run_single_stage(
            "balanced_v1", 
            stage1_miss_paths, 
            TWO_STAGE_CONFIG["stage2_dir"]
        )
    else:
        print("阶段1已检测到所有图片，无需阶段2补充检测")
        stage2_hits = []
        final_miss_paths = []
    
    # 合并最终结果
    print("\n" + "="*30 + " 合并最终结果 " + "="*30)
    final_summary, comparison_report = merge_final_results(stage1_hits, stage2_hits, final_miss_paths)
    
    # 输出最终统计
    print(f"\n{'='*20} 最终检测结果统计 {'='*20}")
    print(f"总图片数: {final_summary['final_statistics']['total_images']}")
    print(f"阶段1命中: {len(stage1_hits)} 张")
    print(f"阶段2补充: {len(stage2_hits)} 张")
    print(f"总命中数: {final_summary['final_statistics']['total_hits']} 张")
    print(f"最终未命中: {final_summary['final_statistics']['final_miss']} 张")
    print(f"整体命中率: {final_summary['final_statistics']['overall_hit_rate']:.1f}%")
    print(f"阶段2改进: {comparison_report['strategy_effectiveness']['improvement_percentage']:.1f}%")
    print(f"\n结果保存至: {TWO_STAGE_CONFIG['final_dir']}")
    print("=" * 60)


if __name__ == "__main__":
    main()