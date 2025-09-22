"""
OCR识别服务
封装PP-OCRv5引擎，提供图片文字识别功能
"""
import os
import configparser
import logging
from pathlib import Path
from typing import List, Dict, Optional, Union, Any, Tuple
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
import shutil

import warnings
warnings.filterwarnings("ignore", message="iCCP: known incorrect sRGB profile")

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


class OCRInstancePool:
    """OCR实例池，用于缓存不同参数组合的OCR实例，避免频繁重建"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not getattr(self, '_initialized', False):
            # OCR实例缓存：键为参数组合的hash，值为OCR实例
            self._cache = {}
            # 缓存访问锁
            self._cache_lock = threading.Lock()
            # 最大缓存数量（避免内存占用过多）
            self._max_cache_size = 12
            # 使用统计，用于LRU淘汰
            self._usage_stats = {}
            self._initialized = True
            logger.info("OCR实例池初始化完成")

    def _generate_cache_key(self, lang: str, limit_type: str,
                            use_textline_orientation: bool,
                            use_doc_unwarping: bool) -> str:
        """生成缓存键（语言、方向分类、去畸变）。
        注意：不再将 limit_type 纳入缓存键，缩放策略通过强制写入预处理参数实现，
        避免相同模型因不同 limit_type 被重复创建。
        """
        orientation_flag = 'cls1' if use_textline_orientation else 'cls0'
        unwarp_flag = 'warp1' if use_doc_unwarping else 'warp0'
        return f"{lang}_{orientation_flag}_{unwarp_flag}"

    def get_ocr_instance(self, lang: str = "ch", limit_type: str = "max",
                         text_det_thresh: float = 0.3, text_det_box_thresh: float = 0.6,
                         text_det_unclip_ratio: float = 1.5, text_det_limit_side_len: int = 960,
                         **other_params) -> PaddleOCR:
        """获取OCR实例，如果缓存中没有则创建新实例"""
        use_textline_orientation = other_params.get('use_textline_orientation', False)
        use_doc_unwarping = other_params.get('use_doc_unwarping', False)
        cache_key = self._generate_cache_key(
            lang, limit_type, use_textline_orientation, use_doc_unwarping
        )

        with self._cache_lock:
            # 检查缓存中是否存在
            if cache_key in self._cache:
                self._usage_stats[cache_key] = time.time()
                logger.debug(f"从缓存中获取OCR实例: {cache_key}")
                return self._cache[cache_key]

            # 缓存中不存在，创建新实例
            logger.info(f"创建新的OCR实例并缓存: {cache_key}")

            # 如果缓存已满，使用LRU策略淘汰最久未使用的实例
            if len(self._cache) >= self._max_cache_size:
                self._evict_lru_instance()

            # 创建新的OCR实例（避免将阈值参与实例构建，阈值使用后续强制写入）
            ocr_instance = self._create_ocr_instance(
                lang, limit_type, text_det_limit_side_len,
                use_textline_orientation=use_textline_orientation,
                use_doc_unwarping=use_doc_unwarping
            )

            # 添加到缓存
            self._cache[cache_key] = ocr_instance
            self._usage_stats[cache_key] = time.time()

            return ocr_instance

    def _evict_lru_instance(self):
        """淘汰最久未使用的OCR实例"""
        if not self._usage_stats:
            return

        # 找到最久未使用的实例
        lru_key = min(self._usage_stats, key=self._usage_stats.get)

        # 删除缓存
        if lru_key in self._cache:
            del self._cache[lru_key]
        del self._usage_stats[lru_key]

        logger.info(f"淘汰LRU OCR实例: {lru_key}")

    def _create_ocr_instance(self, lang: str, limit_type: str,
                             text_det_limit_side_len: int,
                             **other_params) -> PaddleOCR:
        """创建新的OCR实例"""

        # 强制GPU环境配置
        os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
        os.environ["CUDA_VISIBLE_DEVICES"] = "0"
        os.environ["FLAGS_use_gpu"] = "true"
        os.environ["FLAGS_fraction_of_gpu_memory_to_use"] = "0.8"

        # 基本参数
        init_kwargs = {
            'device': 'gpu' if GPU_ENABLED else 'cpu',
            'lang': lang,
            'use_doc_orientation_classify': False,
            'use_doc_unwarping': other_params.get('use_doc_unwarping', False),
            'use_textline_orientation': other_params.get('use_textline_orientation', False),
            'text_detection_model_name': "PP-OCRv5_server_det",
            'text_recognition_model_name': "PP-OCRv5_server_rec",
        }

        try:
            ocr_instance = PaddleOCR(**init_kwargs)
            logger.info(f"成功创建OCR实例: {lang}_shared")
            return ocr_instance
        except TypeError as e:
            # 回退：不传入可能不支持的参数
            logger.warning(f"创建OCR实例失败，回退到基础参数: {e}")
            ocr_instance = PaddleOCR(**{'device': 'gpu' if GPU_ENABLED else 'cpu', 'lang': lang})
            return ocr_instance

    def clear_cache(self):
        """清空缓存"""
        with self._cache_lock:
            self._cache.clear()
            self._usage_stats.clear()
            logger.info("OCR实例池缓存已清空")

    def get_cache_info(self) -> Dict:
        """获取缓存信息"""
        with self._cache_lock:
            return {
                'cached_instances': len(self._cache),
                'max_cache_size': self._max_cache_size,
                'cache_keys': list(self._cache.keys())
            }


class OCRService:

    _ocr_instance = None
    _init_lock = threading.Lock()
    # 添加日志参数输出标记，用于控制公共参数只输出一次
    _common_params_logged = False
    _common_params_task_id = None

    def __init__(self, lang: str = "ch"):
        """
        初始化OCR服务
        
        Args:
            lang: 识别语言，默认为中文
        """
        self.lang = lang

        # 初始化OCR实例池
        self.ocr_pool = OCRInstancePool()
        

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
            # 通过封装的 imdecode 调用
            imread_color = getattr(cv2, 'IMREAD_COLOR', 1)
            img = self._cv_imdecode(data, imread_color)
            return img
        except Exception:
            return None

    def _cv_polylines(self, img: np.ndarray, pts: np.ndarray,
                       closed: bool, color: tuple, thickness: int) -> None:
        """包装 cv2.polylines，避免静态分析器告警。"""
        try:
            fn = getattr(cv2, 'polylines', None)
            if fn is not None:
                fn(img, [pts], closed, color, thickness)
        except Exception:
            pass

    def _cv_put_text(self, img: np.ndarray, text: str, org: tuple,
                      font: int, font_scale: float,
                      color: tuple, thickness: int, line_type: int) -> None:
        """包装 cv2.putText，避免静态分析器告警。"""
        try:
            fn = getattr(cv2, 'putText', None)
            if fn is not None:
                fn(img, text, org, font, font_scale, color, thickness, line_type)
        except Exception:
            pass

    def _cv_imwrite(self, path: str, img: np.ndarray) -> None:
        """包装 cv2.imwrite，避免静态分析器告警。"""
        try:
            fn = getattr(cv2, 'imwrite', None)
            if fn is not None:
                fn(path, img)
        except Exception:
            pass

    def _draw_visualization(self,
                            img: np.ndarray,
                            items: List[Tuple[Any, Any, Any]],
                            out_path: str,
                            annotate: bool = False) -> None:
        """绘制识别可视化结果并保存到指定路径。

        Args:
            img: 原始图像数组
            items: 三元组列表 (poly, text, score)
            out_path: 输出文件完整路径
            annotate: 是否在图上标注文本与分数
        """
        try:
            vis = img.copy()
            for (poly, t, s) in items:
                try:
                    pts = np.array(poly, dtype=np.int32)
                    if pts.ndim == 2 and pts.shape[0] >= 4:
                        self._cv_polylines(vis, pts, True, (0, 255, 0), 2)
                        x = int(np.min(pts[:, 0]))
                        y = int(np.min(pts[:, 1]))
                    else:
                        x, y = 2, 20
                    if annotate:
                        label = f"{t} ({float(s):.2f})"
                        font = getattr(cv2, 'FONT_HERSHEY_SIMPLEX', 0)
                        line_aa = getattr(cv2, 'LINE_AA', 16)
                        self._cv_put_text(
                            vis, label, (x, max(0, y - 5)),
                            font, 0.5, (0, 0, 255), 1, line_aa
                        )
                except Exception:
                    continue
            try:
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
            except Exception:
                pass
            self._cv_imwrite(out_path, vis)
        except Exception:
            pass

    def _cv_imdecode(self, data: np.ndarray, flags: int) -> Optional[np.ndarray]:
        """包装 cv2.imdecode。"""
        try:
            fn = getattr(cv2, 'imdecode', None)
            if fn is None or not callable(fn):
                return None
            return fn(data, flags)
        except Exception:
            return None

    def _cv_resize(self, img: np.ndarray, size: tuple) -> np.ndarray:
        """包装 cv2.resize。"""
        try:
            fn = getattr(cv2, 'resize', None)
            if fn is None or not callable(fn):
                return img
            return fn(img, size)
        except Exception:
            return img

    def _log_effective_round_params(self, ocr_obj: PaddleOCR, rp: Dict[str, Any], ridx: int) -> None:
        """打印OCR实例内部真正生效的关键参数，用于核对是否与本轮参数一致。
        仅日志，不抛异常。"""
        try:
            eff = {
                'det_limit_type': None,
                'det_limit_side_len': None,
                'det_thresh': None,
                'det_box_thresh': None,
                'det_unclip_ratio': None,
                'rec_score_thresh': None,
            }
            det = getattr(ocr_obj, 'text_detector', None)
            if det is not None:
                pre = getattr(det, 'preprocess_op', None)
                if pre is not None:
                    eff['det_limit_type'] = getattr(pre, 'limit_type', None)
                    eff['det_limit_side_len'] = getattr(pre, 'limit_side_len', None)
                post = getattr(det, 'postprocess_op', None)
                if post is not None:
                    eff['det_thresh'] = getattr(post, 'thresh', None)
                    eff['det_box_thresh'] = getattr(post, 'box_thresh', None)
                    eff['det_unclip_ratio'] = getattr(post, 'unclip_ratio', None)
            rec = getattr(ocr_obj, 'text_recognizer', None)
            if rec is not None:
                post = getattr(rec, 'postprocess_op', None)
                if post is not None:
                    eff['rec_score_thresh'] = getattr(post, 'score_thresh', None)
            logger.warning(
                "参数生效校验|轮次=%s | 期望: lt=%s side=%s det=%.2f box=%.2f unclip=%.2f rec=%.2f | 实际: lt=%s side=%s det=%s box=%s unclip=%s rec=%s",
                ridx,
                rp.get('text_det_limit_type'), rp.get('text_det_limit_side_len'),
                float(rp.get('text_det_thresh')), float(rp.get('text_det_box_thresh')),
                float(rp.get('text_det_unclip_ratio')), float(rp.get('text_rec_score_thresh')),
                eff['det_limit_type'], eff['det_limit_side_len'], eff['det_thresh'],
                eff['det_box_thresh'], eff['det_unclip_ratio'], eff['rec_score_thresh']
            )
        except Exception:
            pass

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
            target_language: 目标语言代码（支持官方与内部代码）

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


    @staticmethod
    def _text_is_chinese_only(text: str) -> bool:
        """仅保留包含中文且不含英文字母和数字的文本。"""
        if not text:
            return False
        has_cn = any('\u4e00' <= ch <= '\u9fff' for ch in text)
        has_ascii_alnum = any((ord(ch) < 128) and (ch.isalpha() or ch.isdigit()) for ch in text)
        return has_cn and not has_ascii_alnum

    @staticmethod
    def _text_contains_chinese(text: str) -> bool:
        """判断文本是否包含中文字符。"""
        if not text:
            return False
        return any('\u4e00' <= ch <= '\u9fff' for ch in text)

    def _text_passes_language_filter(self, text: str, strategy: str) -> bool:
        """根据配置的语言过滤策略判断文本是否通过。

        参数:
            text: 待判断文本
            strategy: 过滤策略，支持 chinese_only/contains_chinese/none
        返回:
            bool: 是否通过过滤
        """
        try:
            mode = str(strategy or '').strip().lower()
        except Exception:
            mode = 'chinese_only'
        if mode == 'none':
            return bool(text)
        if mode == 'contains_chinese':
            return self._text_contains_chinese(text)
        # 默认 chinese_only
        return self._text_is_chinese_only(text)

    def _resolve_text_filter_strategy(self) -> str:
        """基于现有语言配置推导文本过滤策略。

        规则：
        - 若当前语言为中文(ch/zh/zh-cn等)，使用 contains_chinese（包含中文即可）
        - 其它语言或未知，返回 none（不过滤，仅用分数阈值）
        说明：不新增配置项，直接沿用 ocr_default_lang/default_language
        """
        try:
            # 优先使用实例语言，其次使用配置
            cur_lang = str(self.lang or '').strip().lower()
            if not cur_lang:
                cfg = settings.CFG._config
                cur_lang = (cfg.get('ocr', 'ocr_default_lang', fallback='')
                            or cfg.get('ocr', 'default_language', fallback=''))
                cur_lang = str(cur_lang or '').strip().lower()
        except Exception:
            cur_lang = 'ch'
        if cur_lang in {'ch', 'zh', 'zh-cn', 'zh_cn', 'chinese'}:
            return 'contains_chinese'
        return 'none'

    @staticmethod
    def _parse_predict_items(res: Any) -> List[Any]:
        """解析 PaddleOCR.predict 的返回，输出 (poly, text, score) 列表。

        为简化仅返回三元组，poly 可为空列表。"""
        items: List[Any] = []
        if res is None:
            return items
        try:
            if isinstance(res, list) and res:
                first = res[0]
                if isinstance(first, dict):
                    raw = first
                    texts = raw.get('rec_texts') or raw.get('texts') or []
                    scores = raw.get('rec_scores') or []
                    polys = (raw.get('rec_polys') or raw.get('dt_polys')
                             or raw.get('boxes') or [])
                    if texts and not isinstance(texts, list):
                        texts = [texts]
                    if scores and not isinstance(scores, list):
                        scores = [scores]
                    if polys is None:
                        polys = []
                    n = max(len(texts), len(scores), len(polys))
                    for i in range(n):
                        t = texts[i] if i < len(texts) else ""
                        try:
                            s = float(scores[i]) if i < len(scores) else 0.0
                        except Exception:
                            s = 0.0
                        p = polys[i] if i < len(polys) else []
                        items.append((p, str(t), float(s)))
                    return items
                if isinstance(first, list):
                    for itm in first:
                        if (isinstance(itm, list) and len(itm) >= 2 and
                                isinstance(itm[0], (list, np.ndarray)) and
                                isinstance(itm[1], (list, tuple))):
                            poly = itm[0]
                            text = str(itm[1][0])
                            try:
                                score = float(itm[1][1])
                            except Exception:
                                score = 0.0
                            items.append((poly, text, score))
                    return items
            if isinstance(res, dict):
                raw = res
                texts = raw.get('rec_texts') or raw.get('texts') or []
                scores = raw.get('rec_scores') or []
                polys = (raw.get('rec_polys') or raw.get('dt_polys')
                         or raw.get('boxes') or [])
                if texts and not isinstance(texts, list):
                    texts = [texts]
                if scores and not isinstance(scores, list):
                    scores = [scores]
                if polys is None:
                    polys = []
                n = max(len(texts), len(scores), len(polys))
                for i in range(n):
                    t = texts[i] if i < len(texts) else ""
                    try:
                        s = float(scores[i]) if i < len(scores) else 0.0
                    except Exception:
                        s = 0.0
                    p = polys[i] if i < len(polys) else []
                    items.append((p, str(t), float(s)))
        except Exception:
            return items
        return items

    @staticmethod
    def _compute_scaled_resolution(h: int, w: int, limit_type: str,
                                   side_len: int) -> str:
        """根据 limit_type 与 side_len 估算等比缩放后的分辨率字符串。
        逻辑与 helper 保持一致。"""
        try:
            h = int(h); w = int(w); side = int(side_len)
            if h <= 0 or w <= 0 or side <= 0:
                return f"{w}x{h}"
            lt = str(limit_type)
            cur_max = float(max(h, w))
            cur_min = float(min(h, w))
            if lt == 'max':
                if cur_max > side:
                    r = float(side) / cur_max
                    sw = int(round(w * r)); sh = int(round(h * r))
                    return f"{max(1, sw)}x{max(1, sh)}"
                return f"{w}x{h}"
            if lt == 'min':
                if cur_min < side:
                    r = float(side) / cur_min
                    sw = int(round(w * r)); sh = int(round(h * r))
                    return f"{max(1, sw)}x{max(1, sh)}"
                return f"{w}x{h}"
            denom = float(min(h, w)) if lt == 'min' else float(max(h, w))
            if denom <= 0:
                return f"{w}x{h}"
            r = float(side) / denom
            sw = int(round(w * r)); sh = int(round(h * r))
            return f"{max(1, sw)}x{max(1, sh)}"
        except Exception:
            return f"{w}x{h}"

    @staticmethod
    def _resize_image_for_round(img: np.ndarray, limit_type: str,
                                side_len: int) -> np.ndarray:
        """按轮次参数进行前置等比缩放，确保缩放策略稳定生效。

        说明：不依赖底层引擎的预处理开关，直接对输入图片做等比缩放，
        与 _compute_scaled_resolution 的逻辑保持一致。
        """
        try:
            h, w = img.shape[:2]
            if h <= 0 or w <= 0 or side_len <= 0:
                return img
            lt = str(limit_type)
            cur_max = float(max(h, w))
            cur_min = float(min(h, w))
            if lt == 'max':
                if cur_max <= side_len:
                    return img
                r = float(side_len) / cur_max
            else:
                if cur_min >= side_len:
                    return img
                r = float(side_len) / cur_min
            new_w = max(1, int(round(w * r)))
            new_h = max(1, int(round(h * r)))
            # 使用封装的 resize
            return OCRService._cv_resize(OCRService, img, (new_w, new_h))
        except Exception:
            return img

    @staticmethod
    def _validate_round_params(p: Dict[str, Any]) -> Dict[str, Any]:
        """校验并规范化每轮参数，仅接受官方字段名。"""
        required = [
            'text_det_limit_type',
            'text_det_limit_side_len',
            'text_det_thresh',
            'text_det_box_thresh',
            'text_det_unclip_ratio',
            'text_rec_score_thresh',
        ]
        for k in required:
            if k not in p or p.get(k) is None or str(p.get(k)).strip() == '':
                raise ValueError(f"缺少必要参数: {k}")
        out: Dict[str, Any] = dict(p)
        out['text_det_limit_type'] = str(p.get('text_det_limit_type'))
        out['text_det_limit_side_len'] = int(float(p.get('text_det_limit_side_len')))
        out['text_det_thresh'] = float(p.get('text_det_thresh'))
        out['text_det_box_thresh'] = float(p.get('text_det_box_thresh'))
        out['text_det_unclip_ratio'] = float(p.get('text_det_unclip_ratio'))
        out['text_rec_score_thresh'] = float(p.get('text_rec_score_thresh'))
        out['use_doc_unwarping'] = bool(p.get('use_doc_unwarping', False))
        out['use_textline_orientation'] = bool(
            p.get('use_textline_orientation', False)
        )
        return out

    @staticmethod
    def _default_round_param_sets() -> List[Dict[str, Any]]:
        return [
        #第1轮
        {
            'text_det_limit_type': 'min',
            'text_det_limit_side_len': 736,
            'text_det_thresh': 0.30,
            'text_det_box_thresh': 0.60,
            'text_det_unclip_ratio': 1.5,
            'text_rec_score_thresh': 0.90,
            'use_textline_orientation': False,
            'use_doc_unwarping': False,
        },
        #第2轮
        {
            'text_det_limit_type': 'min',
            'text_det_limit_side_len': 680,
            'text_det_thresh': 0.3,
            'text_det_box_thresh': 0.6,
            'text_det_unclip_ratio': 1.5,
            'text_rec_score_thresh': 0.8,
            'use_textline_orientation': False,
            'use_doc_unwarping': False,
        },
        #第3轮 小图 
        {
            'text_det_limit_type': 'min',
            'text_det_limit_side_len': 960,
            'text_det_thresh': 0.3,
            'text_det_box_thresh': 0.6,
            'text_det_unclip_ratio': 1.5,
            'text_rec_score_thresh': 0.8,
            'use_textline_orientation': False,
            'use_doc_unwarping': False,
        },
        #第4轮
        {
            'text_det_limit_type': 'max',
            'text_det_limit_side_len': 960,
            'text_det_thresh': 0.3,
            'text_det_box_thresh': 0.6,
            'text_det_unclip_ratio': 2.0,
            'text_rec_score_thresh': 0.8,
            'use_textline_orientation': False,
            'use_doc_unwarping': False,
        },
        #第5轮
        {
            'text_det_limit_type': 'min',
            'text_det_limit_side_len': 1280,
            'text_det_thresh': 0.25,
            'text_det_box_thresh': 0.45,
            'text_det_unclip_ratio': 2.0,
            'text_rec_score_thresh': 0.8,
            'use_textline_orientation': False,
            'use_doc_unwarping': False,
        },
        #第6轮
        {
            'text_det_limit_type': 'max',
            'text_det_limit_side_len': 960,
            'text_det_thresh': 0.3,
            'text_det_box_thresh': 0.6,
            'text_det_unclip_ratio': 2.0,
            'text_rec_score_thresh': 0.7,
            'use_textline_orientation': True,
            'use_doc_unwarping': True,
        },
        #第7轮。
        {
            'text_det_limit_type': 'max',
            'text_det_limit_side_len': 1280,
            'text_det_thresh': 0.3,
            'text_det_box_thresh': 0.6,
            'text_det_unclip_ratio': 2.0,
            'text_rec_score_thresh': 0.5,
            'use_textline_orientation': False,
            'use_doc_unwarping': True,
        },
        ]

    def _load_rounds_from_config(self) -> List[Dict[str, Any]]:
        """从配置加载多轮参数，支持两种方式：
        1) [ocr_rounds] section: round1=..., round2=...（JSON字符串）
        2) [ocr] rounds_json=... （JSON数组字符串）
        若都不存在，返回默认集。
        """
        try:
            cfg = settings.CFG._config
            # 方式2：ocr.rounds_json
            try:
                rounds_json = cfg.get('ocr', 'rounds_json', fallback='').strip()
            except Exception:
                rounds_json = ''
            if rounds_json:
                arr = json.loads(rounds_json)
                if isinstance(arr, list) and arr:
                    return [self._validate_round_params(x) for x in arr]
            # 方式1：独立 section
            if cfg.has_section('ocr_rounds'):
                parser: configparser.SectionProxy = cfg['ocr_rounds']
                collected: List[Dict[str, Any]] = []
                for key in sorted(parser.keys()):
                    try:
                        val = parser.get(key)
                        obj = json.loads(val)
                        if isinstance(obj, dict):
                            collected.append(self._validate_round_params(obj))
                    except Exception:
                        continue
                if collected:
                    return collected
        except Exception as e:
            logger.warning(f"读取多轮参数失败，使用默认集: {e}")
        # 默认
        return [self._validate_round_params(x)
                for x in self._default_round_param_sets()]

    @staticmethod
    def _force_apply_params_to_instance(ocr_obj: PaddleOCR,
                                        params: Dict[str, Any]) -> None:
        """将 text_* 阈值与预处理策略强制写入已创建的 OCR 实例。"""
        try:
            det = getattr(ocr_obj, 'text_detector', None)
            if det and hasattr(det, 'postprocess_op'):
                post = det.postprocess_op
                if hasattr(post, 'thresh'):
                    setattr(post, 'thresh', float(params['text_det_thresh']))
                if hasattr(post, 'box_thresh'):
                    setattr(post, 'box_thresh', float(params['text_det_box_thresh']))
                if hasattr(post, 'unclip_ratio'):
                    setattr(post, 'unclip_ratio', float(params['text_det_unclip_ratio']))
            if det and hasattr(det, 'preprocess_op'):
                pre = det.preprocess_op
                if hasattr(pre, 'limit_type'):
                    setattr(pre, 'limit_type', str(params['text_det_limit_type']))
                if hasattr(pre, 'limit_side_len'):
                    setattr(pre, 'limit_side_len', int(params['text_det_limit_side_len']))
            rec = getattr(ocr_obj, 'text_recognizer', None)
            if rec and hasattr(rec, 'postprocess_op'):
                post = rec.postprocess_op
                if hasattr(post, 'score_thresh'):
                    setattr(post, 'score_thresh', float(params['text_rec_score_thresh']))
        except Exception as e:
            logger.debug(f"强制写入参数失败(忽略)：{e}")

    def _get_ocr_for_round(self, params: Dict[str, Any]) -> PaddleOCR:
        """依据轮次参数获取/创建 OCR 实例，并强制写入阈值。"""
        use_textline_orientation = bool(params.get('use_textline_orientation', False))
        ocr_inst = self.ocr_pool.get_ocr_instance(
            lang=self.lang,
            limit_type=str(params['text_det_limit_type']),
            text_det_thresh=float(params['text_det_thresh']),
            text_det_box_thresh=float(params['text_det_box_thresh']),
            text_det_unclip_ratio=float(params['text_det_unclip_ratio']),
            text_det_limit_side_len=int(params['text_det_limit_side_len']),
            text_rec_score_thresh=float(params['text_rec_score_thresh']),
            use_textline_orientation=use_textline_orientation,
            use_doc_unwarping=bool(params.get('use_doc_unwarping', False))
        )
        self._force_apply_params_to_instance(ocr_inst, params)
        return ocr_inst

    @staticmethod
    def _round_signature(p: Dict[str, Any]) -> str:
        """基于轮次参数生成稳定签名，用于报表与日志对齐实际轮次。
        仅包含会影响识别口径的关键字段。
        """
        try:
            lt = str(p.get('text_det_limit_type'))
            side = int(float(p.get('text_det_limit_side_len')))
            det = float(p.get('text_det_thresh'))
            box = float(p.get('text_det_box_thresh'))
            unclip = float(p.get('text_det_unclip_ratio'))
            rec = float(p.get('text_rec_score_thresh'))
            unwarp = 1 if bool(p.get('use_doc_unwarping', False)) else 0
            textline = 1 if bool(p.get('use_textline_orientation', False)) else 0
            return (
                f"lt={lt}|side={side}|det={det:.2f}|box={box:.2f}|"
                f"unclip={unclip:.2f}|rec={rec:.2f}|unwarp={unwarp}|textline={textline}"
            )
        except Exception:
            return "lt=?|side=?|det=?|box=?|unclip=?|rec=?|unwarp=?|textline=?"

    def recognize_rounds_batch(self,
                               image_dir: str,
                               image_formats: Optional[List[str]] = None,
                               enable_draw: Optional[bool] = None,
                               enable_copy: Optional[bool] = None,
                               enable_annotate: Optional[bool] = None
                               ) -> Dict[str, Any]:
        """多轮参数识别（命中即剔除），与 helper 行为保持一致的核心流程。

        返回批次统计与每图首轮命中信息，便于上层落盘。
        新增：在进入默认多轮识别之前，支持按配置对极小图进行预过滤，
        当启用开关时，短边像素小于阈值的图片会被丢弃以减少误检。
        """
        # 固定启用多轮识别（不再从配置读取开关）

        img_exts = image_formats or ['.jpg', '.jpeg', '.png']
        full_image_dir = image_dir
        if not os.path.isabs(image_dir):
            full_image_dir = os.path.join(settings.MEDIA_ROOT, image_dir)
        if not os.path.exists(full_image_dir) or not os.path.isdir(full_image_dir):
            return {"error": f"图片目录不存在或不是目录: {full_image_dir}"}

        image_paths: List[str] = []
        for root_dir, _, files in os.walk(full_image_dir):
            for fname in files:
                if any(fname.lower().endswith(ext) for ext in img_exts):
                    image_paths.append(os.path.join(root_dir, fname))
        if not image_paths:
            return {"error": "未发现图片"}

        # 预处理：基于配置抛弃过小分辨率图片（按短边像素阈值）
        try:
            cfg = settings.CFG._config
            pre_enabled = cfg.getboolean(
                'ocr', 'prefilter_small_images_enabled', fallback=False
            )
            pre_min_side = cfg.getint('ocr', 'prefilter_min_side_px', fallback=55)
        except Exception:
            pre_enabled = False
            pre_min_side = 55
        # 明确打印配置来源与读到的值，便于排查“阈值显示为50”的问题
        try:
            cfg_path = getattr(settings.CFG, '_config_path', '')
            logger.warning(
                "预过滤配置来源: file=%s enabled=%s min_side=%s",
                cfg_path, pre_enabled, pre_min_side
            )
        except Exception:
            pass
        if pre_enabled:
            kept_paths: List[str] = []
            dropped = 0
            for p in image_paths:
                try:
                    img = self._load_image_unicode(p)
                    if img is None:
                        # 无法读取的图片交由后续流程处理，不在此阶段丢弃
                        kept_paths.append(p)
                        continue
                    h, w = img.shape[:2]
                    if min(h, w) < int(pre_min_side):
                        dropped += 1
                        continue
                    kept_paths.append(p)
                except Exception:
                    # 读取失败不影响主流程，保留以便后续统一按 miss 处理
                    kept_paths.append(p)
            try:
                logger.warning(
                    "预过滤：按短边阈值丢弃=%s 张，阈值=%s像素，保留=%s 张",
                    int(dropped), int(pre_min_side), int(len(kept_paths))
                )
            except Exception:
                pass
            image_paths = kept_paths
            if not image_paths:
                return {
                    "error": (
                        f"预过滤后未发现图片(短边阈值={int(pre_min_side)})"
                    )
                }

        # 预分流：按 min_side 的 P95
        try:
            min_sides: List[int] = []
            name_to_path: Dict[str, str] = {}
            for p in image_paths:
                try:
                    img = self._load_image_unicode(p)
                    if img is None:
                        continue
                    h, w = img.shape[:2]
                    min_sides.append(int(min(h, w)))
                    name_to_path[os.path.basename(p)] = p
                except Exception:
                    continue
            th_small = None
            if min_sides:
                arr = np.array(min_sides, dtype=np.float32)
                th_small = int(np.percentile(arr, 95))
            small_images: List[str] = []
            rest_images: List[str] = []
            if th_small is not None:
                for p in image_paths:
                    try:
                        img = self._load_image_unicode(p)
                        if img is None:
                            rest_images.append(p)
                            continue
                        h, w = img.shape[:2]
                        if min(h, w) <= th_small:
                            small_images.append(p)
                        else:
                            rest_images.append(p)
                    except Exception:
                        rest_images.append(p)
        except Exception as e:
            logger.warning(f"预分流失败: {e}")
            small_images, rest_images = [], list(image_paths)

        # 第一轮输入采用预过滤后的全部图片，P95预分流仅用于统计与可视化，不影响输入集合
        cur_inputs = list(image_paths)

        # 通过配置控制绘制与标注的默认值；函数参数为显式覆盖
        try:
            cfg = settings.CFG._config
            cfg_draw = cfg.getboolean('ocr', 'draw_enabled', fallback=False)
            cfg_annotate = cfg.getboolean('ocr', 'annotate_enabled', fallback=False)
        except Exception:
            cfg_draw = False
            cfg_annotate = False
        
        logger.info(f"enable_draw: {enable_draw}, cfg_draw: {cfg_draw}")
        logger.info(f"enable_copy: {enable_copy}, cfg_annotate: {cfg_annotate}")

        # 通过函数参数控制：未显式传入则使用配置默认
        enable_draw = bool(enable_draw) if enable_draw is not None else bool(cfg_draw)
        enable_copy = bool(enable_copy) if enable_copy is not None else False
        enable_annotate = bool(enable_annotate) if enable_annotate is not None else bool(cfg_annotate)
 
        # 可视化根目录（仅在开启绘制时创建）
        if enable_draw:
            ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            rounds_root = os.path.join(PathUtils.get_ocr_results_dir(), f"rounds_eval_{ts}")
            try:
                os.makedirs(rounds_root, exist_ok=True)
            except Exception:
                rounds_root = ""
        else:
            rounds_root = ""
 
        # 固定使用内置6轮参数，不从配置读取
        rounds = [self._validate_round_params(x)
                  for x in self._default_round_param_sets()]
        
        logger.warning(f"多轮识别：使用内置参数集，轮数={len(rounds)}")

        # 预先打印每一轮的参数生效一次，避免在图片循环里反复穿插日志
        try:
            for ridx, rp in enumerate(rounds, start=1):
                try:
                    ocr_tmp = self._get_ocr_for_round(rp)
                    self._log_effective_round_params(ocr_tmp, rp, ridx)
                except Exception:
                    continue
        except Exception:
            pass
 
        # 由现有语言配置推导过滤策略（不新增配置项）
        text_lang_filter = self._resolve_text_filter_strategy()
        try:
            logger.warning(
                f"语言过滤策略(由语言配置推导): {text_lang_filter} | lang={self.lang}"
            )
        except Exception:
            pass
 
        # 统计结构
        total_hit = 0
        first_hit_info: Dict[str, Dict[str, Any]] = {}
        # 记录各轮命中数，便于和旧日志口径对齐
        round_hit_counter: Dict[int, int] = {i: 0 for i in range(1, len(rounds) + 1)}

        # 改为“按图片逐轮尝试”：每张图仅解码一次，命中立即早停
        remain_inputs = list(cur_inputs)
        final_miss_paths: List[str] = []

        for p in remain_inputs:
            try:
                img = self._load_image_unicode(p)
                if img is None:
                    final_miss_paths.append(p)
                    continue
            except Exception:
                final_miss_paths.append(p)
                continue

            hit_round = 0
            for ridx, rp in enumerate(rounds, start=1):
                try:
                    rp = self._validate_round_params(rp)
                except Exception as ve:
                    logger.debug(f"参数非法(第{ridx}轮，跳过)：{ve}")
                    continue

                # 懒创建可视化目录（按需）
                vis_hit_dir, vis_miss_dir = "", ""
                if enable_draw and rounds_root:
                    vis_hit_dir = os.path.join(rounds_root, f"vis_r{ridx}", 'hit')
                    vis_miss_dir = os.path.join(rounds_root, f"vis_r{ridx}", 'miss')
                    try:
                        os.makedirs(vis_hit_dir, exist_ok=True)
                        os.makedirs(vis_miss_dir, exist_ok=True)
                    except Exception:
                        enable_draw = False

                # 获取实例（不再在此重复打印参数生效日志）
                try:
                    ocr_inst = self._get_ocr_for_round(rp)
                except Exception:
                    continue

                # 前置缩放，确保每轮 limit_type/side_len 生效
                try:
                    img_proc = self._resize_image_for_round(
                        img,
                        str(rp['text_det_limit_type']),
                        int(rp['text_det_limit_side_len'])
                    )
                except Exception:
                    img_proc = img

                try:
                    res = ocr_inst.predict(input=img_proc)
                    items = self._parse_predict_items(res)
                except Exception as pe:
                    items = []
                    logger.debug(f"预测失败(第{ridx}轮，跳过)：{pe}")

                # 语言与分数阈值过滤
                kept: List[Any] = []
                for (poly, t, s) in items:
                    if self._text_passes_language_filter(t, text_lang_filter):
                        kept.append((poly, t, s))
                try:
                    score_thresh = float(rp.get('text_rec_score_thresh', 0.0))
                except Exception:
                    score_thresh = 0.0
                kept_scored = [
                    (poly, t, s) for (poly, t, s) in kept if float(s) >= score_thresh
                ]

                if kept_scored:
                    hit_round = ridx
                    round_hit_counter[ridx] = round_hit_counter.get(ridx, 0) + 1
                    total_hit += 1
                    if os.path.basename(p) not in first_hit_info:
                        try:
                            texts = [t for (_, t, s) in kept_scored]
                            scores = [float(s) for (_, t, s) in kept_scored]
                        except Exception:
                            texts, scores = [], []
                        first_hit_info[os.path.basename(p)] = {
                            'round': ridx,
                            'hit_texts': '|'.join(texts[:10]),
                            'hit_scores': '|'.join([f"{x:.4f}" for x in scores[:10]])
                        }
                    if enable_draw and rounds_root and vis_hit_dir:
                        try:
                            self._draw_visualization(
                                img, kept_scored,
                                os.path.join(vis_hit_dir, os.path.basename(p))
                            )
                        except Exception:
                            pass
                    break  # 命中即早停，切换到下一张图片
                else:
                    if enable_draw and rounds_root and vis_miss_dir:
                        try:
                            self._draw_visualization(
                                img, [],
                                os.path.join(vis_miss_dir, os.path.basename(p))
                            )
                        except Exception:
                            pass

            if hit_round == 0:
                final_miss_paths.append(p)

            # 每张图片仅输出一条日志：命中轮次或未命中
            try:
                name_only = os.path.basename(p)
                if hit_round > 0:
                    logger.warning(f"图片命中 | 轮次={hit_round} | {name_only}")
                else:
                    logger.warning(f"图片未命中 | {name_only}")
            except Exception:
                pass

        # 输出与旧日志口径兼容的分轮统计（取消显示，仅保留调试级别）
        # for ridx in range(1, len(rounds) + 1):
        #     try:
        #         logger.debug(
        #             f"多轮迭代：第{ridx}轮结束，hit={round_hit_counter.get(ridx, 0)}"
        #         )
        #     except Exception:
        #         pass

        return {
            'rounds_root': rounds_root, 
            'total_hit': int(total_hit),
            'final_miss': int(len(final_miss_paths)),
            'first_hit_info': first_hit_info,
        }


# 如果作为独立脚本运行，提供简单的测试功能
if __name__ == "__main__":
    # 该模块仅作为服务被调用，不提供命令行入口
    print("OCRService 模块：作为服务组件使用，无命令行入口。")