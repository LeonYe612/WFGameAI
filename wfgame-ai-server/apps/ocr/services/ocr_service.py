"""
OCR识别服务
封装PP-OCRv5引擎，提供图片文字识别功能
"""
import os
import configparser
import logging
from pathlib import Path
from typing import List, Dict, Optional, Union
import datetime
from django.conf import settings
from django.utils import timezone
import json
import re
import time
from paddleocr import PaddleOCR
from .path_utils import PathUtils

# 配置日志
logger = logging.getLogger(__name__)

# 抑制PaddleOCR的警告信息
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="paddle")
warnings.filterwarnings("ignore", category=UserWarning, module="paddleocr")

# 设置所有日志级别为WARNING，抑制DEBUG信息
logging.getLogger("ppocr").setLevel(logging.ERROR)
logging.getLogger("PIL").setLevel(logging.WARNING)
logging.getLogger("paddle").setLevel(logging.ERROR)

# 强制关闭所有第三方库的DEBUG日志
for name in logging.root.manager.loggerDict:
    if any(keyword in name.lower() for keyword in ['ppocr', 'paddle', 'pil', 'opencv']):
        logging.getLogger(name).setLevel(logging.ERROR)

# 读取配置
config = PathUtils.load_config()

# OCR相关路径配置
RESULTS_DIR = PathUtils.get_ocr_results_dir()
UPLOADS_DIR = PathUtils.get_ocr_uploads_dir()
REPOS_DIR = PathUtils.get_ocr_repos_dir()

# OCR引擎配置
GPU_ENABLED = config.getboolean('ocr', 'gpu_enabled', fallback=True)
OCR_DEFAULT_LANG = config.get('ocr', 'ocr_default_lang', fallback='ch')
GPU_ID = config.getint('ocr', 'gpu_id', fallback=0)


# GPU资源管理类
class GPUResourceManager:
    """GPU资源管理类，避免GPU资源冲突"""

    _gpu_locks = {}  # 用于跟踪GPU使用情况的字典

    @classmethod
    def acquire_gpu(cls, gpu_id, timeout=10):
        """
        获取GPU资源锁

        Args:
            gpu_id: GPU ID
            timeout: 超时时间(秒)

        Returns:
            bool: 是否成功获取资源
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            if gpu_id not in cls._gpu_locks or not cls._gpu_locks[gpu_id]:
                cls._gpu_locks[gpu_id] = True
                logger.info(f"获取GPU {gpu_id} 资源成功")
                return True
            logger.debug(f"GPU {gpu_id} 资源被占用，等待...")
            time.sleep(0.5)

        logger.warning(f"获取GPU {gpu_id} 资源超时")
        return False

    @classmethod
    def release_gpu(cls, gpu_id):
        """
        释放GPU资源锁

        Args:
            gpu_id: GPU ID
        """
        if gpu_id in cls._gpu_locks:
            cls._gpu_locks[gpu_id] = False
            logger.info(f"释放GPU {gpu_id} 资源")

    @classmethod
    def get_available_gpu(cls):
        """
        获取可用的GPU ID

        Returns:
            int: 可用的GPU ID，如果都不可用则返回0
        """
        for gpu_id in range(8):  # 假设系统最多有8个GPU
            if gpu_id not in cls._gpu_locks or not cls._gpu_locks[gpu_id]:
                return gpu_id
        return 0  # 默认返回0


class OCRService:
    """OCR识别服务类"""

    def __init__(self, use_gpu: bool = True, lang: str = "ch", gpu_id: int = 0):
        """
        初始化OCR服务

        Args:
            use_gpu: 是否使用GPU
            lang: 语言模型
            gpu_id: GPU设备ID
        """
        self.lang = lang
        device = f"gpu:{gpu_id}" if use_gpu else "cpu"

        try:
            # 设置所有日志级别为WARNING，抑制DEBUG信息
            logging.getLogger("ppocr").setLevel(logging.WARNING)
            logging.getLogger("PIL").setLevel(logging.WARNING)
            logging.getLogger("paddle").setLevel(logging.WARNING)

            # 初始化PaddleOCR
            self.ocr = PaddleOCR(
                use_doc_orientation_classify=False,  # 不使用文档方向分类模型
                use_doc_unwarping=False,            # 不使用文本图像矫正模型
                use_textline_orientation=False,     # 不使用文本行方向分类模型
                lang=lang,
                device=device  # 根据use_gpu参数选择设备
            )

            logger.info(f"PP-OCRv5初始化成功 (GPU: {device}, Lang: {lang})")
        except Exception as e:
            logger.error(f"PP-OCRv5初始化失败: {str(e)}")
            raise

    def __del__(self):
        """析构函数，释放GPU资源"""
        # 由于OCRService对象不再有use_gpu属性，这里不再需要释放GPU资源
        pass

    def initialize(self):
        """检查OCR引擎是否已初始化"""
        return self.ocr is not None

    def recognize_image(self, image_path: str) -> Dict:
        """
        识别单张图片中的文字

        Args:
            image_path: 图片路径

        Returns:
            Dict: 识别结果
        """
        if not self.initialize():
            return {"error": "OCR引擎初始化失败"}

        try:
            start_time = datetime.datetime.now()
            # 使用PaddleOCR的ocr方法而不是recognize_image
            result = self.ocr.ocr(image_path, cls=True)
            end_time = datetime.datetime.now()

            # 提取文本内容
            texts = []
            # PaddleOCR 2.x 返回的是嵌套list
            for res in result:
                if isinstance(res, list):
                    for line in res:
                        if len(line) >= 2 and isinstance(line[1], (list, tuple)):
                            texts.append(line[1][0])

            # 计算耗时
            time_cost = (end_time - start_time).total_seconds()

            return {
                "image_path": image_path,
                "texts": texts,
                "boxes": [],  # 简化处理，不返回坐标信息
                "confidence": 0.95,  # 简化处理，使用固定置信度
                "time_cost": time_cost
            }
        except Exception as e:
            logger.error(f"图片识别失败 {image_path}: {str(e)}")
            return {"error": f"图片识别失败: {str(e)}", "image_path": image_path}

    def recognize_batch(self, image_dir: str, image_formats: List[str] = None) -> List[Dict]:
        """
        批量识别目录下的图片

        Args:
            image_dir: 图片目录
            image_formats: 图片格式列表，默认为['.jpg', '.jpeg', '.png', '.bmp']

        Returns:
            List[Dict]: 识别结果列表
        """
        if not self.initialize():
            return [{"error": "OCR引擎初始化失败"}]

        if image_formats is None:
            image_formats = ['.jpg', '.jpeg', '.png', '.bmp']

        results = []
        try:
            # 获取目录下所有图片
            image_paths = []
            for root, _, files in os.walk(image_dir):
                for file in files:
                    if any(file.lower().endswith(fmt) for fmt in image_formats):
                        image_paths.append(os.path.join(root, file))

            # 批量处理图片
            for image_path in image_paths:
                try:
                    # 使用单张图片识别方法
                    result = self.recognize_image(image_path)
                    results.append(result)
                except Exception as e:
                    logger.error(f"处理失败 {image_path}: {str(e)}")
                    results.append({"image_path": image_path, "error": str(e)})

            return results
        except Exception as e:
            logger.error(f"批量识别失败: {str(e)}")
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

    def get_engine_stats(self) -> Dict:
        """
        获取引擎状态信息

        Returns:
            Dict: 引擎状态信息
        """
        stats = {
            "engine_initialized": self.ocr is not None,
            "use_gpu": True,  # 默认使用GPU
            "gpu_id": 0,      # 默认GPU ID
            "lang": self.lang # 使用实例变量
        }
        return stats

    def get_performance_stats(self) -> Dict:
        """
        获取性能统计信息

        Returns:
            Dict: 性能统计信息
        """
        # 简单实现，返回固定值
        stats = {
            "cpu_usage": 30.5,
            "memory_usage": 1024.5,
            "gpu_usage": 50.2,
            "gpu_memory_usage": 2048.6,
            "processed_images": 100,
            "avg_processing_time": 0.25,
            "total_processing_time": 25.0,
        }
        return stats


# 如果作为独立脚本运行，提供简单的测试功能
if __name__ == "__main__":
    # 初始化OCR服务
    ocr = OCRService(use_gpu=True, lang="ch", gpu_id=0)

    # 解析命令行参数
    import sys
    import argparse

    parser = argparse.ArgumentParser(description='OCR识别服务')
    parser.add_argument('--path', type=str, help='图片路径或目录')
    parser.add_argument('--lang', type=str, default='ch', help='语言代码 (ch, en, vi, ko, ja)')
    parser.add_argument('--gpu', action='store_true', help='是否使用GPU')

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