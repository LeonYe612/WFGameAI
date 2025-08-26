"""
OCR识别服务
封装PP-OCRv5引擎，提供图片文字识别功能
"""
import os
import configparser
import logging
from pathlib import Path
from typing import List, Dict, Optional, Union, Any
import datetime
from django.conf import settings
from django.utils import timezone
import json
import re
import time
import uuid
import numpy as np
import cv2
import sys
import ctypes
import importlib.util
from .path_utils import PathUtils
import threading
from paddleocr import PaddleOCR

# 配置日志
logger = logging.getLogger(__name__)


# 读取配置
# config = PathUtils.load_config()
config = settings.CFG._config

# OCR相关路径配置
RESULTS_DIR = PathUtils.get_ocr_results_dir()
UPLOADS_DIR = PathUtils.get_ocr_uploads_dir()
REPOS_DIR = PathUtils.get_ocr_repos_dir()

# OCR引擎配置（保留参数占位，不在 PaddleOCR 初始化时直接使用 device）
GPU_ENABLED = config.getboolean('ocr', 'gpu_enabled', fallback=True)
OCR_DEFAULT_LANG = config.get('ocr', 'ocr_default_lang', fallback='ch')

# 预先设置CUDA环境变量，确保在任何导入前优先使用NVIDIA显卡
if GPU_ENABLED:
    # 强制使用NVIDIA显卡
    os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
    # 禁用集成显卡
    os.environ["CUDA_VISIBLE_DEVICES"] = "0"  # 假设NVIDIA显卡是设备0
    # 设置Paddle使用GPU
    os.environ["FLAGS_use_gpu"] = "true"
    os.environ["FLAGS_fraction_of_gpu_memory_to_use"] = "0.8"  # 使用80%的GPU显存
    # 禁用TensorFlow可能使用的集成显卡
    os.environ["TF_FORCE_GPU_ALLOW_GROWTH"] = "true"
    # 禁用英特尔集成显卡
    os.environ["OPENCV_DNN_OPENCL_ALLOW_ALL_DEVICES"] = "0"
    # 禁用英特尔MKL
    os.environ["MKL_SERVICE_FORCE_INTEL"] = "0"

    # 检测NVIDIA GPU
    try:
        import subprocess
        nvidia_smi = subprocess.run(['nvidia-smi'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if nvidia_smi.returncode == 0:
            logger.warning(f"NVIDIA GPU信息:\n{nvidia_smi.stdout}")
        else:
            logger.warning(f"无法获取NVIDIA GPU信息: {nvidia_smi.stderr}")
    except Exception as e:
        logger.warning(f"检测NVIDIA GPU失败: {e}")


class OCRService:
    """基于 PP-OCRv5 的 OCR 服务（使用 PaddleOCR.predict 工作流）。"""

    _ocr_instance = None
    _init_lock = threading.Lock()

    def __init__(self, lang: str = "ch"):
        self.lang = lang

        # 初始化OCR模型（与PP-OCRv5官方demo保持一致的核心参数）
        print("正在初始化PaddleOCR模型...")
        # 自动选择设备：优先GPU，否则CPU，并给出清晰提示
        import paddle
        if not paddle.device.is_compiled_with_cuda():
            device_arg = 'cpu'
            print("警告: PaddlePaddle 未编译 CUDA 支持，将使用 CPU 进行推理")
        else:
            device_arg = 'gpu'
            print("使用 GPU 进行推理")

        self.ocr = PaddleOCR(
            use_doc_orientation_classify=False, # 是否加载并使用文档方向分类功能。
            use_doc_unwarping=False, # 是否加载并使用文本图像矫正功能。
            use_textline_orientation=False, # 是否加载并使用文本行方向功能。
            device=device_arg, # 指定使用设备，可选值为 'cpu' 或 'gpu'。
            text_detection_model_name="PP-OCRv5_mobile_det", # 指定文本检测模型名称。
            text_recognition_model_name="PP-OCRv5_mobile_rec", # 指定文本识别模型名称。
            # text_detection_model_name="PP-OCRv5_server_det", # 指定文本检测模型名称。
            # text_recognition_model_name="PP-OCRv5_server_rec", # 指定文本识别模型名称。
            lang=self.lang, # 指定语言，可选值为 'ch' 或 'en'。
        )
        print(f"PaddleOCR模型初始化完成，device={device_arg}")



    def initialize(self):
        return self.ocr is not None

    def _collect_texts_from_json(self, data: Any) -> List[str]:

        texts: List[str] = []

        def _walk(node: Any):
            if isinstance(node, dict):
                for key, value in node.items():
                    key_lower = str(key).lower()
                    if key_lower in {"text", "transcription", "label", "text_content"}:
                        if isinstance(value, str) and value:
                            texts.append(value)
                    _walk(value)
            elif isinstance(node, list):
                for item in node:
                    _walk(item)

        _walk(data)
        seen = set()
        unique_texts: List[str] = []
        for t in texts:
            if t not in seen:
                seen.add(t)
                unique_texts.append(t)
        return unique_texts

    def _load_image_unicode(self, abs_path: str) -> Optional[np.ndarray]:

        try:
            data = np.fromfile(abs_path, dtype=np.uint8)
            if data is None or data.size == 0:
                return None
            img = cv2.imdecode(data, cv2.IMREAD_COLOR)
            return img
        except Exception:
            return None

    def recognize_image(self, image_path: str, predict_save: bool = True) -> Dict:

        if not self.initialize():
            return {"error": "OCR引擎初始化失败"}
        try:
            # Normalize to absolute path under MEDIA_ROOT if relative
            full_image_path = image_path
            if not os.path.isabs(image_path):
                full_image_path = os.path.join(settings.MEDIA_ROOT, image_path)
                logger.debug(f"将相对路径转换为绝对路径: {image_path} -> {full_image_path}")

            if not os.path.exists(full_image_path):
                logger.error(f"图片文件不存在: {full_image_path}")
                return {"error": f"图片文件不存在: {full_image_path}", "image_path": image_path}

            # Robust image loading for Unicode paths
            image_nd = self._load_image_unicode(full_image_path)
            if image_nd is None:
                logger.error(f"图像读取失败(可能为Unicode路径或文件损坏): {full_image_path}")
                return {"error": f"Image read Error: {full_image_path}", "image_path": image_path}

            # 根据配置决定是否保存预测可视化/JSON 结果
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            base_name = os.path.splitext(os.path.basename(full_image_path))[0]
            out_dir = None
            if predict_save:
                out_dir = os.path.join(
                    RESULTS_DIR,
                    "predict",
                    f"{base_name}_{timestamp}_{uuid.uuid4().hex[:8]}"
                )
                os.makedirs(out_dir, exist_ok=True)

            start_time = datetime.datetime.now()
            # Run PP-OCRv5 predict workflow on ndarray
            try:
                results = self.ocr.predict(input=image_nd)
            except Exception as predict_err:
                # Fallback: write to temporary ASCII path then predict by file path
                import tempfile
                tmp_file = None
                try:
                    ok, enc = cv2.imencode('.png', image_nd)
                    if not ok:
                        raise RuntimeError("cv2.imencode failed")
                    with tempfile.NamedTemporaryFile(prefix="ocr_", suffix=".png", delete=False) as tf:
                        tf.write(enc.tobytes())
                        tmp_file = tf.name
                    results = self.ocr.predict(input=tmp_file)
                finally:
                    if tmp_file and os.path.exists(tmp_file):
                        try:
                            os.remove(tmp_file)
                        except Exception:
                            pass
            end_time = datetime.datetime.now()

            # Persist result assets and JSON, then parse texts back
            texts: List[str] = []
            try:
                if predict_save and out_dir:
                    for res in results:
                        try:
                            res.print()
                        except Exception:
                            pass
                        try:
                            res.save_to_img(out_dir)
                        except Exception:
                            pass
                        try:
                            res.save_to_json(out_dir)
                        except Exception:
                            pass

                    # 提取 JSON 中文本
                    for root, _, files in os.walk(out_dir):
                        for f in files:
                            if f.lower().endswith('.json'):
                                p = os.path.join(root, f)
                                try:
                                    with open(p, 'r', encoding='utf-8') as jf:
                                        data = json.load(jf)
                                    texts.extend(self._collect_texts_from_json(data))
                                except Exception as je:
                                    logger.debug(f"解析JSON失败: {p}, {je}")

                # JSON 解析后仍为空时，尝试直接从PaddleOCR返回结构提取 rec_texts
                if not texts:
                    try:
                        for item in results:
                            # PaddleOCR >=3.0 可能返回 dict，或返回 Result 对象，均包含 rec_texts
                            if isinstance(item, dict):
                                # RapidOCR/FastDeploy 风格
                                rec_texts = item.get('rec_texts')
                                if rec_texts:
                                    texts.extend([t for t in rec_texts if isinstance(t, str)])
                            else:
                                # 官方 PaddleOCR.Result 对象
                                if hasattr(item, 'rec_texts'):
                                    texts.extend([t for t in getattr(item, 'rec_texts') if isinstance(t, str)])
                    except Exception as fallback_err:
                        logger.debug(f"从结果对象直接提取文本失败: {fallback_err}")
            except Exception as persist_err:
                logger.debug(f"结果保存或解析失败: {persist_err}")

            time_cost = (end_time - start_time).total_seconds()

            return {
                "image_path": image_path,
                "texts": texts,
                "boxes": [],
                "confidence": 0.95,
                "time_cost": time_cost
            }
        except Exception as e:
            logger.error(f"图片识别失败 {image_path}: {str(e)}")
            return {"error": f"图片识别失败: {str(e)}", "image_path": image_path}

    def recognize_batch(self, image_dir: str, image_formats: List[str] = None) -> List[Dict]:

        if not self.initialize():
            return [{"error": "OCR引擎初始化失败"}]

        if image_formats is None:
            image_formats = ['.jpg', '.jpeg', '.png', '.bmp']

        full_image_dir = image_dir
        if not os.path.isabs(image_dir):
            full_image_dir = os.path.join(settings.MEDIA_ROOT, image_dir)
            logger.debug(f"将相对路径目录转换为绝对路径: {image_dir} -> {full_image_dir}")

        if not os.path.exists(full_image_dir) or not os.path.isdir(full_image_dir):
            logger.error(f"图片目录不存在或不是目录: {full_image_dir}")
            return [{"error": f"图片目录不存在或不是目录: {full_image_dir}"}]

        results = []
        try:
            image_paths = []
            for root, _, files in os.walk(full_image_dir):
                for file in files:
                    if any(file.lower().endswith(fmt) for fmt in image_formats):
                        abs_path = os.path.join(root, file)
                        from django.conf import settings
                        if abs_path.startswith(settings.MEDIA_ROOT):
                            rel_path = os.path.relpath(abs_path, settings.MEDIA_ROOT)
                        else:
                            rel_path = abs_path
                        image_paths.append(rel_path)

            for rel_path in image_paths:
                try:
                    result = self.recognize_image(rel_path)
                    results.append(result)
                except Exception as img_err:
                    logger.error(f"识别失败: {rel_path} 错误: {img_err}")
                    results.append({"error": str(img_err), "image_path": rel_path})

            return results
        except Exception as e:
            logger.error(f"批量识别失败 {image_dir}: {str(e)}")
            return [{"error": f"批量识别失败: {str(e)}"}]

    def extract_text_only(self, image_path: str) -> str:
        """
        仅提取文本内容

        Args:
            image_path: 图片路径

        Returns:
            str: 提取的文本
        """
        result = self.recognize_image(image_path)
        texts = result.get('texts', [])
        return ' '.join(texts)

    def detect_language(self, text: str) -> Dict:
        """
        检测文本语言

        Args:
            text: 待检测文本

        Returns:
            Dict: 语言检测结果
        """
        # 语言检测规则
        languages = {
            'chinese': False,
            'english': False,
            'vietnamese': False,
            'korean': False,
            'japanese': False,
        }

        # 中文字符范围（包括简体和繁体）
        # CJK统一汉字 (U+4E00-U+9FFF)
        # CJK统一汉字扩展A (U+3400-U+4DBF)
        # CJK统一汉字扩展B (U+20000-U+2A6DF)
        # CJK部首扩展 (U+2E80-U+2EFF)
        # CJK笔画 (U+31C0-U+31EF)
        # CJK符号和标点 (U+3000-U+303F)
        if (any('\u4e00' <= ch <= '\u9fff' for ch in text) or  # 基本汉字
            any('\u3400' <= ch <= '\u4dbf' for ch in text) or  # 扩展A
            any('\u2e80' <= ch <= '\u2eff' for ch in text) or  # 部首扩展
            any('\u31c0' <= ch <= '\u31ef' for ch in text) or  # 笔画
            any('\u3000' <= ch <= '\u303f' for ch in text) or  # 符号和标点
            any(ord(ch) >= 0x20000 and ord(ch) <= 0x2a6df for ch in text)):  # 扩展B
            languages['chinese'] = True

        # 英文字符
        if re.search(r'[a-zA-Z]{2,}', text):
            languages['english'] = True

        # 越南文检测 (特殊字符)
        vietnamese_chars = 'ăâêôơưđ'
        vietnamese_chars += vietnamese_chars.upper()
        vietnamese_marks = '\u0300\u0301\u0303\u0309\u0323'  # 声调符号
        if any(ch in vietnamese_chars for ch in text) or any(ch in vietnamese_marks for ch in text):
            languages['vietnamese'] = True

        # 韩文字符范围
        if any('\uac00' <= ch <= '\ud7a3' for ch in text):
            languages['korean'] = True

        # 日文字符范围 (平假名和片假名)
        if any('\u3040' <= ch <= '\u30ff' for ch in text) or any('\u31f0' <= ch <= '\u31ff' for ch in text):
            languages['japanese'] = True

        return languages

    @staticmethod
    def check_language_match(texts: List[str], target_language: str) -> bool:
        """
        检查文本是否包含目标语言

        Args:
            texts: 文本列表
            target_language: 目标语言代码

        Returns:
            bool: 是否包含目标语言
        """
        # 如果没有文本，直接返回False
        if not texts:
            return False

        # 语言代码映射
        language_patterns = {
            'zh': r'[\u4e00-\u9fff]',  # 中文
            'en': r'[a-zA-Z]',         # 英文
            'vi': r'[\u01A0\u01A1\u01AF\u01B0\u1EA0-\u1EF9]',  # 越南语
            'ko': r'[\uac00-\ud7a3]',  # 韩文
            'ja': r'[\u3040-\u30ff]',  # 日文
        }

        # 获取目标语言的正则表达式
        pattern = language_patterns.get(target_language.lower())
        if not pattern:
            # 如果目标语言不在预定义列表中，默认为中文
            pattern = language_patterns['zh']

        # 编译正则表达式
        regex = re.compile(pattern)

        # 检查每个文本是否包含目标语言
        for text in texts:
            if regex.search(text):
                return True

        return False


# 如果作为独立脚本运行，提供简单的测试功能
if __name__ == "__main__":
    # 初始化OCR服务
    ocr = OCRService(lang="ch")

    # 解析命令行参数
    import sys
    import argparse

    parser = argparse.ArgumentParser(description='OCR识别服务')
    parser.add_argument('--path', type=str, help='图片路径或目录')
    parser.add_argument('--lang', type=str, default='ch', help='语言代码 (ch, en, vi, ko, ja)')

    args = parser.parse_args()

    if args.path:
        if os.path.isdir(args.path):
            print(f"批量识别目录: {args.path}")
            results = ocr.recognize_batch(args.path)
            print(f"批量识别完成，共处理 {len(results)} 张图片")

            # 统计包含中文的图片
            zh_count = 0
            for result in results:
                if 'texts' in result and OCRService.check_language_match(result['texts'], 'zh'):
                    zh_count += 1

            print(f"包含中文的图片: {zh_count}/{len(results)}")
        elif os.path.isfile(args.path):
            print(f"识别单张图片: {args.path}")
            result = ocr.recognize_image(args.path)
            print(f"识别结果: {result.get('texts', [])}")
        else:
            print(f"路径不存在: {args.path}")
    else:
        print("请指定图片路径或目录，使用 --path 参数")
        print("示例: python ocr_service.py --path images/test.jpg --lang ch --gpu")