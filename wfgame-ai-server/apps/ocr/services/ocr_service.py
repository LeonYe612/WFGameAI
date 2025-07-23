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

# 模拟OCR引擎依赖，实际项目中应替换为真实引擎导入
try:
    from ocr_core import SimpleOCR
except ImportError:
    # 开发测试时可能无法导入真实OCR引擎
    class SimpleOCR:
        def __init__(self, use_gpu=True, lang='ch', gpu_id=0):
            self.use_gpu = use_gpu
            self.lang = lang
            self.gpu_id = gpu_id

        def recognize_image(self, image_path, save_results=False):
            # 模拟OCR结果
            return {
                'image_path': image_path,
                'texts': [f'Sample OCR text from {Path(image_path).name}', '测试文本'],
                'boxes': [],
                'confidence': 0.95
            }

# 配置日志
logger = logging.getLogger(__name__)

# 读取配置
config = configparser.ConfigParser()
config.read(settings.BASE_DIR.parent / 'config.ini', encoding='utf-8')

# OCR相关路径配置
RESULTS_DIR = config.get('paths', 'ocr_results_dir', fallback='output/ocr/results')
UPLOADS_DIR = config.get('paths', 'ocr_uploads_dir', fallback='media/ocr/uploads')
REPOS_DIR = config.get('paths', 'ocr_repos_dir', fallback='media/ocr/repositories')

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

    def __init__(self, use_gpu: bool = None, lang: str = None, gpu_id: int = None):
        """
        初始化OCR识别服务

        Args:
            use_gpu: 是否使用GPU
            lang: 语言
            gpu_id: GPU设备ID
        """
        self.use_gpu = GPU_ENABLED if use_gpu is None else use_gpu
        self.lang = OCR_DEFAULT_LANG if lang is None else lang
        self.gpu_id = GPU_ID if gpu_id is None else gpu_id

        # 如果使用GPU，尝试获取GPU资源
        if self.use_gpu:
            # 如果指定的GPU不可用，尝试获取其他GPU
            if not GPUResourceManager.acquire_gpu(self.gpu_id):
                self.gpu_id = GPUResourceManager.get_available_gpu()
                GPUResourceManager.acquire_gpu(self.gpu_id)
                logger.info(f"指定的GPU {gpu_id} 不可用，使用GPU {self.gpu_id}")

        self.ocr = None

    def __del__(self):
        """析构函数，释放资源"""
        if self.use_gpu:
            GPUResourceManager.release_gpu(self.gpu_id)

    def initialize(self):
        """初始化OCR引擎"""
        if self.ocr is None:
            try:
                logger.info(f"初始化OCR引擎 (GPU: {self.use_gpu}, Lang: {self.lang}, GPU_ID: {self.gpu_id})")
                self.ocr = SimpleOCR(use_gpu=self.use_gpu, lang=self.lang, gpu_id=self.gpu_id)
                return True
            except Exception as e:
                logger.error(f"OCR引擎初始化失败: {str(e)}")
                return False
        return True

    def recognize_image(self, image_path: str) -> Dict:
        """
        识别单张图片

        Args:
            image_path: 图片路径

        Returns:
            Dict: 识别结果
        """
        if not self.initialize():
            return {"error": "OCR引擎初始化失败"}

        try:
            start_time = datetime.datetime.now()
            result = self.ocr.recognize_image(image_path, save_results=False)
            end_time = datetime.datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            # 保存结果文件
            self._save_result_file(image_path, result)

            # 添加处理时间
            result['processing_time'] = processing_time
            return result

        except Exception as e:
            logger.error(f"图片识别失败 {image_path}: {str(e)}")
            return {"error": f"图片识别失败: {str(e)}", "image_path": image_path}

    def recognize_batch(self, image_dir: str, image_formats: List[str] = None) -> List[Dict]:
        """
        批量识别图片

        Args:
            image_dir: 图片目录
            image_formats: 图片格式列表

        Returns:
            List[Dict]: 识别结果列表
        """
        if not self.initialize():
            return [{"error": "OCR引擎初始化失败"}]

        if image_formats is None:
            image_formats = ['jpg', 'jpeg', 'png', 'bmp', 'tiff', 'tif', 'webp']

        try:
            # 构建图片扩展名集合
            image_extensions = set()
            for ext in image_formats:
                image_extensions.add(f".{ext.lower()}")
                image_extensions.add(f".{ext.upper()}")

            # 递归获取所有子目录中的图片文件
            image_paths = []
            for path in Path(image_dir).rglob("*"):
                if path.is_file() and path.suffix in image_extensions:
                    image_paths.append(str(path))

            logger.info(f"在 {image_dir} 及其子目录中找到 {len(image_paths)} 张图片")

            results = []
            for i, image_path in enumerate(image_paths, 1):
                try:
                    logger.info(f"正在处理 ({i}/{len(image_paths)}): {image_path}")
                    result = self.recognize_image(image_path)
                    results.append(result)
                except Exception as e:
                    logger.error(f"处理失败 {image_path}: {str(e)}")
                    results.append({"image_path": image_path, "error": str(e)})

            return results

        except Exception as e:
            logger.error(f"批量识别失败: {str(e)}")
            return [{"error": f"批量识别失败: {str(e)}"}]

    def _save_result_file(self, image_path: str, result: Dict):
        """
        保存识别结果到文件

        Args:
            image_path: 图片路径
            result: 识别结果
        """
        try:
            # 创建结果目录
            date_str = timezone.now().strftime("%Y%m%d")
            result_dir = Path(RESULTS_DIR) / date_str
            result_dir.mkdir(parents=True, exist_ok=True)

            # 提取图片文件名
            image_name = Path(image_path).name
            base_name = Path(image_path).stem

            # 保存结果文件
            result_file = result_dir / f"{base_name}_result.json"
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            logger.debug(f"结果已保存到 {result_file}")

        except Exception as e:
            logger.error(f"保存结果文件失败: {str(e)}")

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
        if any('\u4e00' <= ch <= '\u9fff' for ch in text) or any('\u3400' <= ch <= '\u4dbf' for ch in text):
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

    def check_language_match(self, texts: List[str], target_languages: List[str]) -> bool:
        """
        检查文本是否包含目标语言

        Args:
            texts: 文本列表
            target_languages: 目标语言列表

        Returns:
            bool: 是否匹配
        """
        if not texts or not target_languages:
            return False

        language_mapping = {
            'ch': 'chinese',
            'en': 'english',
            'vi': 'vietnamese',
            'ko': 'korean',
            'jp': 'japanese',
        }

        # 转换目标语言代码
        target_lang_full = [language_mapping.get(lang, lang) for lang in target_languages]

        # 检查每个文本
        for text in texts:
            languages = self.detect_language(text)
            for lang in target_lang_full:
                if languages.get(lang, False):
                    return True

        return False

    def get_ocr_stats(self) -> Dict:
        """
        获取OCR统计信息

        Returns:
            Dict: 统计信息
        """
        stats = {
            "engine_initialized": self.ocr is not None,
            "use_gpu": self.use_gpu,
            "gpu_id": self.gpu_id,
            "lang": self.lang,
        }
        return stats