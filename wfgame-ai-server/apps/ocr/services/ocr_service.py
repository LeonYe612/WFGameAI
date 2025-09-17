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
import shutil

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

    def _generate_cache_key(self, lang: str, limit_type: str, use_textline_orientation: bool) -> str:
        """生成缓存键（仅与语言、尺寸限制类型、方向分类开关相关）"""
        orientation_flag = 'cls1' if use_textline_orientation else 'cls0'
        return f"{lang}_{limit_type}_{orientation_flag}"

    def get_ocr_instance(self, lang: str = "ch", limit_type: str = "max",
                         text_det_thresh: float = 0.3, text_det_box_thresh: float = 0.6,
                         text_det_unclip_ratio: float = 1.5, text_det_limit_side_len: int = 960,
                         **other_params) -> PaddleOCR:
        """获取OCR实例，如果缓存中没有则创建新实例"""
        use_textline_orientation = other_params.get('use_textline_orientation', False)
        cache_key = self._generate_cache_key(
            lang, limit_type, use_textline_orientation
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
                use_textline_orientation=use_textline_orientation
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
            'use_doc_unwarping': False,
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

        # 从配置文件读取OCR参数
        self.text_det_thresh = config.getfloat('ocr', 'text_det_thresh', fallback=0.3)
        self.text_det_box_thresh = config.getfloat('ocr', 'text_det_box_thresh', fallback=0.6)
        self.text_det_unclip_ratio = config.getfloat('ocr', 'text_det_unclip_ratio', fallback=1.5)
        self.text_det_limit_side_len = config.getint('ocr', 'text_det_limit_side_len', fallback=960)
        self.text_det_limit_type = config.get('ocr', 'text_det_limit_type', fallback='max')
        self.text_rec_score_thresh = config.getfloat('ocr', 'text_rec_score_thresh', fallback=0.0)

        # 智能切换配置
        self.smart_ocr_dynamic_limit_enabled = config.getboolean('ocr', 'smart_ocr_dynamic_limit_enabled', fallback=True)
        self.ocr_cache_enabled = config.getboolean('ocr', 'ocr_cache_enabled', fallback=True)

        # 当前使用的limit_type
        self._current_limit_type = self.text_det_limit_type

        # 读取默认预设模式
        default_preset = config.get('ocr', 'default_preset', fallback="balanced")
        # 记录当前模式（全局设定）与实际生效子模式
        self.smart_ocr_preset = default_preset
        self._effective_preset = None

        # 召回优先双通道策略配置
        self.dual_channel_recall_boost_enabled = config.getboolean(
            'ocr', 'dual_channel_recall_boost_enabled', fallback=False
        )
        self.recall_det_limit_type = config.get(
            'ocr', 'recall_det_limit_type', fallback='min'
        )
        self.recall_det_limit_side_len = config.getint(
            'ocr', 'recall_det_limit_side_len', fallback=1280
        )
        self.recall_det_thresh = config.getfloat(
            'ocr', 'recall_det_thresh', fallback=0.20
        )
        self.recall_det_box_thresh = config.getfloat(
            'ocr', 'recall_det_box_thresh', fallback=0.40
        )
        self.recall_det_unclip_ratio = config.getfloat(
            'ocr', 'recall_det_unclip_ratio', fallback=2.00
        )

        # 误检治理参数（全部可配置，避免硬编码）
        # 小图严苛模式触发阈值（像素数）
        self.strict_pixels_threshold = config.getint('ocr', 'strict_pixels_threshold', fallback=20000)
        # 长度感知阈值
        self.len1_conf_thresh = config.getfloat('ocr', 'len1_conf_thresh', fallback=0.98)
        self.len2_3_conf_thresh = config.getfloat('ocr', 'len2_3_conf_thresh', fallback=0.92)
        self.len4p_conf_thresh = config.getfloat('ocr', 'len4p_conf_thresh', fallback=0.88)
        self.strict_conf_boost = config.getfloat('ocr', 'strict_conf_boost', fallback=0.03)
        # 几何过滤阈值
        self.min_box_area_ratio = config.getfloat('ocr', 'min_box_area_ratio', fallback=0.001)
        self.min_box_side_px = config.getint('ocr', 'min_box_side_px', fallback=8)
        self.min_aspect_ratio = config.getfloat('ocr', 'min_aspect_ratio', fallback=1.3)
        self.max_aspect_ratio = config.getfloat('ocr', 'max_aspect_ratio', fallback=20.0)
        # 语言比例阈值（中文占比）
        self.lang_ratio_threshold = config.getfloat('ocr', 'lang_ratio_threshold', fallback=0.5)
        # 总体一致性门槛
        self.overall_keep_min_count = config.getint('ocr', 'overall_keep_min_count', fallback=2)
        self.overall_keep_avg_conf = config.getfloat('ocr', 'overall_keep_avg_conf', fallback=0.90)
        self.overall_keep_len4p_conf = config.getfloat('ocr', 'overall_keep_len4p_conf', fallback=0.95)
        # 严苛模式下的检测后处理阈值与最小缩放边
        self.strict_limit_side_len_min = config.getint('ocr', 'strict_limit_side_len_min', fallback=256)
        self.strict_text_det_thresh = config.getfloat('ocr', 'strict_text_det_thresh', fallback=0.50)
        self.strict_text_det_box_thresh = config.getfloat('ocr', 'strict_text_det_box_thresh', fallback=0.75)
        self.strict_text_det_unclip_ratio = config.getfloat('ocr', 'strict_text_det_unclip_ratio', fallback=1.30)

        # 单字复杂度感知参数
        self.len1_conf_base = config.getfloat('ocr', 'len1_conf_base', fallback=0.92)
        self.len1_conf_high_complexity = config.getfloat('ocr', 'len1_conf_high_complexity', fallback=0.85)
        self.len1_conf_low_complexity = config.getfloat('ocr', 'len1_conf_low_complexity', fallback=0.99)
        self.edge_density_lo = config.getfloat('ocr', 'edge_density_lo', fallback=0.02)
        self.edge_density_hi = config.getfloat('ocr', 'edge_density_hi', fallback=0.08)
        self.corner_density_lo = config.getfloat('ocr', 'corner_density_lo', fallback=0.0005)
        self.corner_density_hi = config.getfloat('ocr', 'corner_density_hi', fallback=0.002)
        self.single_char_bypass_overall = config.getboolean('ocr', 'single_char_bypass_overall', fallback=True)

        # 从配置文件加载预设模式参数
        self._load_preset_params_from_config()

        # OCR实例（延迟初始化）
        self.ocr = None

        # 如果默认使用智能均衡模式，在初始化阶段不需要加载特定参数
        # 将在第一次处理图片时动态选择
        if self.smart_ocr_preset != "smart_balanced":
            # 如果不是智能均衡模式，直接加载对应的参数
            self._apply_preset_params(self.smart_ocr_preset)

        logger.info(
            f"OCR服务初始化完成 (语言: {lang}, 缓存启用: {self.ocr_cache_enabled}, 预设: {self.smart_ocr_preset})"
        )

    def _compute_roi_metrics(self, image_nd, poly):
        """计算候选框ROI的复杂度度量（边缘密度、角点密度）。

        返回:
            dict: { 'edge_density': float, 'corner_density': float }
        """
        try:
            if image_nd is None or not poly:
                return { 'edge_density': 0.0, 'corner_density': 0.0 }
            pts = poly
            if hasattr(pts, 'tolist'):
                pts = pts.tolist()
            xs = [int(p[0]) for p in pts]
            ys = [int(p[1]) for p in pts]
            minx, maxx = max(0, min(xs)), max(0, max(xs))
            miny, maxy = max(0, min(ys)), max(0, max(ys))
            h, w = image_nd.shape[:2]
            minx = max(0, min(minx, w - 1))
            maxx = max(0, min(maxx, w - 1))
            miny = max(0, min(miny, h - 1))
            maxy = max(0, min(maxy, h - 1))
            if maxx - minx < 1 or maxy - miny < 1:
                return { 'edge_density': 0.0, 'corner_density': 0.0 }
            roi = image_nd[miny:maxy, minx:maxx]
            # 转灰度
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            # 自适应阈值+Canny
            v = float(np.median(gray)) if hasattr(np, 'median') else 128.0
            lower = int(max(0, 0.66 * v))
            upper = int(min(255, 1.33 * v))
            edges = cv2.Canny(gray, lower, upper)
            edge_density = float(np.count_nonzero(edges)) / float(edges.size)
            # 角点
            max_corners = 64
            corners = cv2.goodFeaturesToTrack(gray, maxCorners=max_corners, qualityLevel=0.01, minDistance=1)
            corner_count = 0 if corners is None else len(corners)
            corner_density = float(corner_count) / float(edges.size)
            return { 'edge_density': edge_density, 'corner_density': corner_density }
        except Exception:
            return { 'edge_density': 0.0, 'corner_density': 0.0 }

    def _load_preset_params_from_config(self):
        """从配置文件加载三种模式的参数"""
        # 高速模式参数
        self.high_speed_params = {
            'text_det_thresh': config.getfloat('ocr_high_speed', 'text_det_thresh', fallback=0.5),
            'text_det_box_thresh': config.getfloat('ocr_high_speed', 'text_det_box_thresh', fallback=0.7),
            'text_det_unclip_ratio': config.getfloat('ocr_high_speed', 'text_det_unclip_ratio', fallback=1.0),
            'text_det_limit_type': config.get('ocr_high_speed', 'text_det_limit_type', fallback='max'),
            'text_det_limit_side_len': config.getint('ocr_high_speed', 'text_det_limit_side_len', fallback=960),
            'use_textline_orientation': config.getboolean('ocr_high_speed', 'use_textline_orientation', fallback=False),
            'smart_ocr_dynamic_limit_enabled': False
        }

        # 均衡模式参数
        self.balanced_params = {
            'text_det_thresh': config.getfloat('ocr_balanced', 'text_det_thresh', fallback=0.3),
            'text_det_box_thresh': config.getfloat('ocr_balanced', 'text_det_box_thresh', fallback=0.6),
            'text_det_unclip_ratio': config.getfloat('ocr_balanced', 'text_det_unclip_ratio', fallback=1.5),
            'text_det_limit_type': config.get('ocr_balanced', 'text_det_limit_type', fallback='max'),
            'text_det_limit_side_len': config.getint('ocr_balanced', 'text_det_limit_side_len', fallback=960),
            'use_textline_orientation': config.getboolean('ocr_balanced', 'use_textline_orientation', fallback=False),
            'smart_ocr_dynamic_limit_enabled': True
        }

        # 高精度模式参数
        self.high_precision_params = {
            'text_det_thresh': config.getfloat('ocr_high_precision', 'text_det_thresh', fallback=0.2),
            'text_det_box_thresh': config.getfloat('ocr_high_precision', 'text_det_box_thresh', fallback=0.4),
            'text_det_unclip_ratio': config.getfloat('ocr_high_precision', 'text_det_unclip_ratio', fallback=2.0),
            'text_det_limit_type': config.get('ocr_high_precision', 'text_det_limit_type', fallback='min'),
            'text_det_limit_side_len': config.getint('ocr_high_precision', 'text_det_limit_side_len', fallback=1280),
            'use_textline_orientation': config.getboolean('ocr_high_precision', 'use_textline_orientation', fallback=True),
            'smart_ocr_dynamic_limit_enabled': False
        }

    def _select_limit_type_by_image(self, image_nd) -> str:
        """基于图像分辨率动态选择 text_det_limit_type。

        Args:
            image_nd (numpy.ndarray): 已读取的图像矩阵

        Returns:
            str: 'max' 或 'min'。当无法读取尺寸时，返回当前生效的 limit_type。
        """
        try:
            if image_nd is None:
                return getattr(self, '_current_limit_type', self.text_det_limit_type)
            height, width = image_nd.shape[:2]
            if width >= height:
                return 'max'
            return 'min'
        except Exception:
            return getattr(self, '_current_limit_type', self.text_det_limit_type)

    def _reinit_ocr_with_limit_type(self, new_limit_type: str) -> None:
        """按需使用新的 text_det_limit_type 重建 OCR 引擎。

        仅在 limit_type 发生变化时调用。尽量复用现有参数与设备设置，
        若 PaddleOCR 版本不支持传入该参数，则回退最小参数集并继续运行。

        Args:
            new_limit_type (str): 新的 limit_type，'min' 或 'max'
        """
        try:
            # 读取与初始化一致的开关与模型名称
            use_doc_orientation_classify = config.getboolean(
                'ocr', 'use_doc_orientation_classify', fallback=False
            )
            use_doc_unwarping = config.getboolean(
                'ocr', 'use_doc_unwarping', fallback=False
            )
            # 使用当前实例的文本行方向开关（可能被预设覆盖）
            _use_textline_orientation = getattr(self, 'use_textline_orientation', False)
            text_detection_model_name = config.get(
                'ocr', 'text_detection_model_name', fallback='PP-OCRv5_server_det'
            )
            text_recognition_model_name = config.get(
                'ocr', 'text_recognition_model_name', fallback='PP-OCRv5_server_rec'
            )

            init_kwargs = dict(
                device=getattr(self, '_device_arg', 'gpu'),
                lang=self.lang,
                use_doc_orientation_classify=use_doc_orientation_classify,
                use_doc_unwarping=use_doc_unwarping,
                use_textline_orientation=_use_textline_orientation,
                text_detection_model_name=text_detection_model_name,
                text_recognition_model_name=text_recognition_model_name,
            )

            # 优先尝试传入官方新参数（包含动态的 limit_type）
            try:
                det_params_kwargs = dict(
                    text_det_thresh=self.text_det_thresh,
                    text_det_box_thresh=self.text_det_box_thresh,
                    text_det_unclip_ratio=self.text_det_unclip_ratio,
                    text_det_limit_side_len=self.text_det_limit_side_len,
                    text_rec_score_thresh=self.text_rec_score_thresh,
                    text_det_limit_type=new_limit_type,
                )
                self.ocr = PaddleOCR(**{**init_kwargs, **det_params_kwargs})
                logger.warning(
                    f"已根据图片尺寸切换 text_det_limit_type={new_limit_type} 并重建OCR"
                )
            except TypeError:
                # 回退：不传入 limit_type，仅使用最小参数集
                self.ocr = PaddleOCR(**init_kwargs)
                logger.warning(
                    "当前 PaddleOCR 版本不支持 text_det_limit_type 参数，"
                    "已使用最小参数集重建OCR。"
                )

            # 更新当前生效的 limit_type（供日志与后续判断使用）
            self.text_det_limit_type = new_limit_type
            self._current_limit_type = new_limit_type
        except Exception as e:
            logger.warning(f"重建OCR失败，继续沿用现有实例。原因: {e}")

    def _select_best_preset_for_image(self, image_nd):
        """根据图片特征选择最佳参数组合

        Args:
            image_nd: 图像矩阵

        Returns:
            str: "high_speed", "balanced", 或 "high_precision"
        """
        if image_nd is None:
            return "balanced"  # 默认均衡

        try:
            height, width = image_nd.shape[:2]
            pixels = height * width

            # 小图片用高精度模式
            if pixels < 10000 or max(height, width) < 100:
                return "high_precision"

            # 大图片用快速模式
            elif pixels > 1000000 or min(height, width) > 1000:
                return "high_speed"

            # 中等图片用均衡模式
            else:
                return "balanced"
        except Exception as e:
            logger.debug(f"动态选择模式失败，使用均衡模式: {e}")
            return "balanced"

    def _apply_preset_params(self, preset_name):
        """应用指定预设的参数

        Args:
            preset_name: 预设名称，"high_speed", "balanced", 或 "high_precision"
        """
        if preset_name == "high_speed":
            params = self.high_speed_params
        elif preset_name == "high_precision":
            params = self.high_precision_params
        else:  # balanced
            params = self.balanced_params

        # 应用参数
        self.text_det_thresh = params['text_det_thresh']
        self.text_det_box_thresh = params['text_det_box_thresh']
        self.text_det_unclip_ratio = params['text_det_unclip_ratio']
        self.text_det_limit_type = params['text_det_limit_type']
        self.text_det_limit_side_len = params['text_det_limit_side_len']
        self.use_textline_orientation = params['use_textline_orientation']
        self.smart_ocr_dynamic_limit_enabled = params['smart_ocr_dynamic_limit_enabled']

        # 仅记录当前实际生效的子模式，不覆盖全局设定 smart_ocr_preset
        self._effective_preset = preset_name

    def set_smart_ocr_preset(self, preset_name: str) -> None:
        """运行时设置智能OCR预设，并按需重建引擎。

        Args:
            preset_name (str): 'high_speed' | 'balanced' | 'high_precision' | 'smart_balanced'
        """
        try:
            name = (preset_name or '').lower().strip()

            # 如果指定了智能均衡，设置内部标记但不立即应用参数
            if name == 'smart_balanced':
                self.smart_ocr_preset = name
                # 重置日志标记，因为参数已更改
                self.__class__._common_params_logged = False
                return

            if name not in {'high_speed', 'balanced', 'high_precision'}:
                logger.warning(f"未知预设: {preset_name}")
                return

            # 应用预设参数
            self._apply_preset_params(name)

            # 重置日志标记，因为参数已更改
            self.__class__._common_params_logged = False

            # 依据当前(或新) limit_type 立即重建一次，确保立即生效
            self._reinit_ocr_with_limit_type(self.text_det_limit_type)
        except Exception as e:
            logger.warning(f"设置预设失败: {e}")


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

    def recognize_image(self, image_path: str, predict_save: bool = False, task_id: Optional[str] = None) -> Dict:
        """
        识别图片中的文字

        Args:
            image_path: 图片路径
            predict_save: 是否保存预测可视化结果
            task_id: 任务ID

        Returns:
            包含识别结果的字典
        """
        try:
            full_image_path = image_path
            if not os.path.isabs(image_path):
                full_image_path = os.path.join(settings.MEDIA_ROOT, image_path)
                logger.debug(f"将相对路径转换为绝对路径: {image_path} -> {full_image_path}")

            if not os.path.exists(full_image_path):
                logger.error(f"图片文件不存在: {full_image_path}")
                return {"error": f"图片文件不存在: {full_image_path}", "image_path": image_path}

            image_nd = self._load_image_unicode(full_image_path)
            if image_nd is None:
                logger.error(f"图像读取失败(可能为Unicode路径或文件损坏): {full_image_path}")
                return {"error": f"Image read Error: {full_image_path}", "image_path": image_path}

            # 记录图像分辨率信息
            try:
                img_height, img_width = image_nd.shape[:2]
                img_pixels = int(img_height * img_width)
            except Exception:
                img_height, img_width, img_pixels = 0, 0, 0

            # 拼接图片分辨率 (高度, 宽度)
            pic_resolution = f"{img_height} x {img_width}"  # 宽 * 高

            # 智能均衡模式：根据图像特征动态选择最佳参数组合
            actual_preset = self.smart_ocr_preset
            if self.smart_ocr_preset == "smart_balanced":
                # 动态选择最佳预设
                best_preset = self._select_best_preset_for_image(image_nd)
                # 应用该预设的参数（不会修改 smart_ocr_preset，只更新 _effective_preset）
                self._apply_preset_params(best_preset)
                # 记录实际使用的预设（用于日志显示）
                actual_preset = best_preset
            else:
                # 固定模式下，effective 即为全局设定
                self._effective_preset = self.smart_ocr_preset

            # 基于像素判断是否进入小图严苛模式
            strict_mode = False
            try:
                strict_mode = (img_pixels > 0 and img_pixels < int(self.strict_pixels_threshold))
            except Exception:
                strict_mode = False

            # 基于图像分辨率动态选择 limit_type
            current_limit_type = self._current_limit_type
            if self.smart_ocr_dynamic_limit_enabled:
                try:
                    next_limit_type = self._select_limit_type_by_image(image_nd)
                    if next_limit_type:
                        current_limit_type = next_limit_type
                        self._current_limit_type = current_limit_type
                except Exception as _dyn_err:
                    logger.debug(f"动态 limit_type 策略未生效: {_dyn_err}")

            # 从缓存池获取OCR实例，避免频繁重建
            if self.ocr_cache_enabled:
                self.ocr = self.ocr_pool.get_ocr_instance(
                    lang=self.lang,
                    limit_type=current_limit_type,
                    text_det_thresh=self.text_det_thresh,
                    text_det_box_thresh=self.text_det_box_thresh,
                    text_det_unclip_ratio=self.text_det_unclip_ratio,
                    text_det_limit_side_len=self.text_det_limit_side_len,
                    text_rec_score_thresh=self.text_rec_score_thresh,
                    use_textline_orientation=getattr(self, 'use_textline_orientation', False)
                )
                # 强制应用核心阈值到子模块，避免因参数不同频繁重建实例
                try:
                    det = getattr(self.ocr, 'text_detector', None)
                    if det and hasattr(det, 'postprocess_op'):
                        post = det.postprocess_op
                        # 根据小图严苛模式应用更严格的检测后处理阈值（仅修改当前实例持有的算子属性）
                        eff_det_thresh = float(self.strict_text_det_thresh) if strict_mode else float(self.text_det_thresh)
                        eff_box_thresh = float(self.strict_text_det_box_thresh) if strict_mode else float(self.text_det_box_thresh)
                        eff_unclip_ratio = float(self.strict_text_det_unclip_ratio) if strict_mode else float(self.text_det_unclip_ratio)
                        if hasattr(post, 'thresh'):
                            setattr(post, 'thresh', eff_det_thresh)
                        if hasattr(post, 'box_thresh'):
                            setattr(post, 'box_thresh', eff_box_thresh)
                        if hasattr(post, 'unclip_ratio'):
                            setattr(post, 'unclip_ratio', eff_unclip_ratio)
                    # 同步预处理的尺寸策略，避免为min/max重建实例
                    if det and hasattr(det, 'preprocess_op'):
                        pre = det.preprocess_op
                        if hasattr(pre, 'limit_type'):
                            setattr(pre, 'limit_type', current_limit_type)
                        if hasattr(pre, 'limit_side_len'):
                            # 严苛模式提高最小缩放边，减少纹理被放大为"字形"的假阳性
                            eff_limit_side = int(max(self.text_det_limit_side_len, self.strict_limit_side_len_min)) if strict_mode else int(self.text_det_limit_side_len)
                            setattr(pre, 'limit_side_len', eff_limit_side)
                    rec = getattr(self.ocr, 'text_recognizer', None)
                    if rec and hasattr(rec, 'postprocess_op'):
                        post = rec.postprocess_op
                        if hasattr(post, 'score_thresh'):
                            setattr(post, 'score_thresh', float(self.text_rec_score_thresh))
                except Exception as _force_err:
                    logger.debug(f"应用核心/预处理参数失败(忽略): {_force_err}")
            else:
                # 如果缓存被禁用，使用传统的重建方式
                if not hasattr(self, 'ocr') or self.ocr is None:
                    self._reinit_ocr_with_limit_type(current_limit_type)
                elif current_limit_type != getattr(self, '_last_used_limit_type', None):
                    self._reinit_ocr_with_limit_type(current_limit_type)
                    self._last_used_limit_type = current_limit_type

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
            # try:
            results = self.ocr.predict(input=image_nd)

            end_time = datetime.datetime.now()

            texts: List[str] = []
            candidate_polys: List[Any] = []  # list of polygons (Nx2) or boxes
            candidate_texts: List[str] = []
            candidate_scores: List[float] = []
            # 收集一次"实际生效的内部参数"，便于与官方demo对齐与排查
            first_raw_debug = {
                'text_det_params': None,
                'model_settings': None,
                'doc_preprocessor_res': None,
                'textline_orientation_angles': None,
            }
            try:
                if predict_save and out_dir:
                    for res in results:
                        # 静默保存，避免PaddleOCR内部打印"没有输入文件名"等提示
                        try:
                            import contextlib, io, sys
                            with contextlib.redirect_stdout(io.StringIO()):
                                with contextlib.redirect_stderr(io.StringIO()):
                                    res.save_to_img(out_dir)
                        except Exception:
                            print("save_to_img error")
                        try:
                            import contextlib, io, sys
                            with contextlib.redirect_stdout(io.StringIO()):
                                with contextlib.redirect_stderr(io.StringIO()):
                                    res.save_to_json(out_dir)
                        except Exception:
                            print("save_to_json error")

                try:
                    for item in results:
                        # PaddleOCR >=3 may return dict 或 Result 对象，且常见为嵌套 item.res
                        raw = None
                        if isinstance(item, dict):
                            raw = item.get('res') if 'res' in item else item
                        else:
                            raw = getattr(item, 'res', None)
                            if raw is None:
                                raw = item

                        # 记录一次内部参数（仅首个样本，避免重复）
                        try:
                            if first_raw_debug['text_det_params'] is None:
                                if isinstance(raw, dict):
                                    first_raw_debug['text_det_params'] = raw.get('text_det_params')
                                    first_raw_debug['model_settings'] = raw.get('model_settings')
                                    first_raw_debug['doc_preprocessor_res'] = raw.get('doc_preprocessor_res')
                                    first_raw_debug['textline_orientation_angles'] = raw.get('textline_orientation_angles')
                                else:
                                    first_raw_debug['text_det_params'] = getattr(raw, 'text_det_params', None)
                                    first_raw_debug['model_settings'] = getattr(raw, 'model_settings', None)
                                    first_raw_debug['doc_preprocessor_res'] = getattr(raw, 'doc_preprocessor_res', None)
                                    first_raw_debug['textline_orientation_angles'] = getattr(raw, 'textline_orientation_angles', None)
                        except Exception:
                            pass

                        # 优先从 raw 中读取标准化字段
                        rec_texts = []
                        rec_scores = []
                        polys = []
                        if isinstance(raw, dict):
                            rec_texts = raw.get('rec_texts') or raw.get('texts') or []
                            rec_scores = raw.get('rec_scores') or []
                            polys = raw.get('rec_polys') or raw.get('dt_polys') or raw.get('boxes') or []
                        else:
                            rec_texts = getattr(raw, 'rec_texts', []) or getattr(raw, 'texts', []) or []
                            rec_scores = getattr(raw, 'rec_scores', []) or []
                            polys = getattr(raw, 'rec_polys', None)
                            if polys is None:
                                polys = getattr(raw, 'dt_polys', None)
                            if polys is None:
                                polys = getattr(raw, 'boxes', [])

                        # 对齐长度并填充候选
                        if rec_texts and not isinstance(rec_texts, list):
                            rec_texts = [rec_texts]
                        if rec_scores and not isinstance(rec_scores, list):
                            rec_scores = [rec_scores]
                        if polys is None:
                            polys = []

                        for idx_i, t in enumerate(rec_texts):
                            if isinstance(t, str) and t.strip():
                                candidate_texts.append(t)
                                s = 1.0
                                if idx_i < len(rec_scores):
                                    try:
                                        s = float(rec_scores[idx_i])
                                    except Exception:
                                        s = 1.0
                                candidate_scores.append(s)
                        if isinstance(polys, list):
                            candidate_polys.extend(polys)
                        else:
                            try:
                                if hasattr(polys, 'tolist'):
                                    candidate_polys.extend(polys.tolist())
                            except Exception:
                                pass
                except Exception:
                    # 忽略异常并依赖下方的JSON兜底逻辑
                    pass

                # 召回优先双通道：在候选较少时追加一次高召回识别并合并候选
                try:
                    need_recall = False
                    if self.dual_channel_recall_boost_enabled:
                        # 条件：无候选或候选数低于总体门槛
                        need_recall = (not candidate_texts) or (
                                len(candidate_texts) < int(self.overall_keep_min_count)
                        )
                    if need_recall:
                        det = getattr(self.ocr, 'text_detector', None)
                        prev_vals = {}
                        try:
                            # 备份当前参数
                            if det and hasattr(det, 'postprocess_op'):
                                post = det.postprocess_op
                                prev_vals['thresh'] = getattr(post, 'thresh', None)
                                prev_vals['box_thresh'] = getattr(post, 'box_thresh', None)
                                prev_vals['unclip_ratio'] = getattr(post, 'unclip_ratio', None)
                                # 应用召回阈值
                                if hasattr(post, 'thresh'):
                                    setattr(post, 'thresh', float(self.recall_det_thresh))
                                if hasattr(post, 'box_thresh'):
                                    setattr(post, 'box_thresh', float(self.recall_det_box_thresh))
                                if hasattr(post, 'unclip_ratio'):
                                    setattr(post, 'unclip_ratio', float(self.recall_det_unclip_ratio))
                            if det and hasattr(det, 'preprocess_op'):
                                pre = det.preprocess_op
                                prev_vals['limit_type'] = getattr(pre, 'limit_type', None)
                                prev_vals['limit_side_len'] = getattr(pre, 'limit_side_len', None)
                                if hasattr(pre, 'limit_type'):
                                    setattr(pre, 'limit_type', self.recall_det_limit_type)
                                if hasattr(pre, 'limit_side_len'):
                                    setattr(pre, 'limit_side_len', int(self.recall_det_limit_side_len))
                        except Exception:
                            pass

                        try:
                            recall_results = self.ocr.predict(input=image_nd)
                            # 解析并追加候选
                            try:
                                for item in recall_results:
                                    raw = None
                                    if isinstance(item, dict):
                                        raw = item.get('res') if 'res' in item else item
                                    else:
                                        raw = getattr(item, 'res', None) or item
                                    rec_texts = []
                                    rec_scores = []
                                    polys = []
                                    if isinstance(raw, dict):
                                        rec_texts = raw.get('rec_texts') or raw.get('texts') or []
                                        rec_scores = raw.get('rec_scores') or []
                                        polys = raw.get('rec_polys') or raw.get('dt_polys') or raw.get('boxes') or []
                                    else:
                                        rec_texts = getattr(raw, 'rec_texts', []) or getattr(raw, 'texts', []) or []
                                        rec_scores = getattr(raw, 'rec_scores', []) or []
                                        polys = getattr(raw, 'rec_polys', None)
                                        if polys is None:
                                            polys = getattr(raw, 'dt_polys', None)
                                        if polys is None:
                                            polys = getattr(raw, 'boxes', [])
                                    if rec_texts and not isinstance(rec_texts, list):
                                        rec_texts = [rec_texts]
                                    if rec_scores and not isinstance(rec_scores, list):
                                        rec_scores = [rec_scores]
                                    if polys is None:
                                        polys = []
                                    # 直接追加，后续统一过滤去重
                                    for idx_i, t in enumerate(rec_texts):
                                        if isinstance(t, str) and t.strip():
                                            candidate_texts.append(t)
                                            s = 1.0
                                            if idx_i < len(rec_scores):
                                                try:
                                                    s = float(rec_scores[idx_i])
                                                except Exception:
                                                    s = 1.0
                                            candidate_scores.append(s)
                                    if isinstance(polys, list):
                                        candidate_polys.extend(polys)
                                    else:
                                        try:
                                            if hasattr(polys, 'tolist'):
                                                candidate_polys.extend(polys.tolist())
                                        except Exception:
                                            pass
                            except Exception:
                                pass
                        finally:
                            # 恢复原参数，避免影响后续图片
                            try:
                                if det and hasattr(det, 'preprocess_op'):
                                    pre = det.preprocess_op
                                    if 'limit_type' in prev_vals and prev_vals['limit_type'] is not None and hasattr(pre, 'limit_type'):
                                        setattr(pre, 'limit_type', prev_vals['limit_type'])
                                    if 'limit_side_len' in prev_vals and prev_vals['limit_side_len'] is not None and hasattr(pre, 'limit_side_len'):
                                        setattr(pre, 'limit_side_len', prev_vals['limit_side_len'])
                                if det and hasattr(det, 'postprocess_op'):
                                    post = det.postprocess_op
                                    if 'thresh' in prev_vals and prev_vals['thresh'] is not None and hasattr(post, 'thresh'):
                                        setattr(post, 'thresh', prev_vals['thresh'])
                                    if 'box_thresh' in prev_vals and prev_vals['box_thresh'] is not None and hasattr(post, 'box_thresh'):
                                        setattr(post, 'box_thresh', prev_vals['box_thresh'])
                                    if 'unclip_ratio' in prev_vals and prev_vals['unclip_ratio'] is not None and hasattr(post, 'unclip_ratio'):
                                        setattr(post, 'unclip_ratio', prev_vals['unclip_ratio'])
                            except Exception:
                                pass
                except Exception:
                    logger.debug("召回通道执行失败，已忽略并继续过滤流程")

            except Exception as persist_err:
                logger.debug(f"结果保存或解析失败: {persist_err}")

            try:
                if candidate_texts and candidate_scores and len(candidate_scores) == len(candidate_texts):
                    # 1) 几何过滤: 依据框面积占比、最短边像素与长宽比
                    geom_keep = [True] * len(candidate_texts)
                    try:
                        img_area = float(max(1, img_width * img_height))
                        for i, poly in enumerate(candidate_polys):
                            try:
                                if not poly:
                                    geom_keep[i] = False
                                    continue
                                pts = poly
                                # 支持 list[list[int]] 或 ndarray
                                if hasattr(pts, 'tolist'):
                                    pts = pts.tolist()
                                xs = [int(p[0]) for p in pts]
                                ys = [int(p[1]) for p in pts]
                                minx, maxx = min(xs), max(xs)
                                miny, maxy = min(ys), max(ys)
                                w = float(maxx - minx)
                                h = float(maxy - miny)
                                if w <= 0 or h <= 0:
                                    geom_keep[i] = False
                                    continue
                                area_ratio = (w * h) / img_area
                                side_min = min(w, h)
                                aspect = (max(w, h) / max(1.0, min(w, h)))
                                if area_ratio < float(self.min_box_area_ratio) or side_min < float(self.min_box_side_px):
                                    geom_keep[i] = False
                                    continue
                                if not (float(self.min_aspect_ratio) <= aspect <= float(self.max_aspect_ratio)):
                                    geom_keep[i] = False
                                    continue
                            except Exception:
                                geom_keep[i] = geom_keep[i] and True
                    except Exception:
                        pass

                    # 2) 长度感知阈值: 严苛模式整体抬高
                    def _len_threshold(txt_len: int) -> float:
                        if txt_len <= 1:
                            base = float(self.len1_conf_base)
                        elif txt_len <= 3:
                            base = float(self.len2_3_conf_thresh)
                        else:
                            base = float(self.len4p_conf_thresh)
                        return base + (float(self.strict_conf_boost) if strict_mode else 0.0)

                    # 3) 语言比例: 中文字符占比阈值
                    def _cn_ratio_ok(t: str) -> bool:
                        if not t:
                            return False
                        try:
                            total = len(t)
                            cn = sum(1 for ch in t if '\u4e00' <= ch <= '\u9fff')
                            ratio = (cn / max(1, total))
                            return ratio >= float(self.lang_ratio_threshold)
                        except Exception:
                            return True

                    filtered_texts = []
                    filtered_scores = []
                    filtered_polys = []
                    for idx, t in enumerate(candidate_texts):
                        # 几何先行
                        if idx < len(geom_keep) and not geom_keep[idx]:
                            continue
                        s = candidate_scores[idx] if idx < len(candidate_scores) else 0.0
                        if s is None:
                            s = 0.0
                        # 长度感知阈值
                        txt_len = len(t.strip())
                        th = _len_threshold(txt_len)
                        # 单字: 依据ROI复杂度动态调整阈值
                        if txt_len == 1:
                            metrics = self._compute_roi_metrics(image_nd, candidate_polys[idx] if idx < len(candidate_polys) else None)
                            ed, cd = float(metrics.get('edge_density', 0.0)), float(metrics.get('corner_density', 0.0))
                            # 高复杂度: 边缘或角点密度较高, 可适当放宽阈值
                            if (ed >= float(self.edge_density_hi)) or (cd >= float(self.corner_density_hi)):
                                th = min(1.0, max(th - (float(self.strict_conf_boost) + 0.03), float(self.len1_conf_high_complexity)))
                            # 低复杂度: 几乎无边缘/角点, 大幅提高阈值以压制纹理误检
                            elif (ed <= float(self.edge_density_lo)) and (cd <= float(self.corner_density_lo)):
                                th = max(th, float(self.len1_conf_low_complexity))
                        if s < th:
                            continue
                        # 语言比例
                        if not _cn_ratio_ok(t):
                            continue
                        filtered_texts.append(t)
                        filtered_scores.append(float(s))
                        if idx < len(candidate_polys):
                            filtered_polys.append(candidate_polys[idx])

                    # 4) 总体一致性门槛
                    def _passes_overall(ts: list, ss: list) -> bool:
                        if not ts:
                            return False
                        try:
                            avgc = float(sum(ss) / max(1, len(ss))) if ss else 0.0
                        except Exception:
                            avgc = 0.0
                        if len(ts) >= int(self.overall_keep_min_count) and avgc >= float(self.overall_keep_avg_conf):
                            return True
                        for i, txt in enumerate(ts):
                            if len(txt.strip()) >= 4 and (ss[i] if i < len(ss) else 0.0) >= float(self.overall_keep_len4p_conf):
                                return True
                        return False

                    passes = _passes_overall(filtered_texts, filtered_scores)
                    # 单字兜底: 当仅存在单字且其复杂度高且分高, 可选择绕过总体一致性门槛
                    if not passes and self.single_char_bypass_overall and len(filtered_texts) == 1 and len(filtered_texts[0].strip()) == 1:
                        try:
                            metrics = self._compute_roi_metrics(image_nd, filtered_polys[0] if filtered_polys else None)
                            ed, cd = float(metrics.get('edge_density', 0.0)), float(metrics.get('corner_density', 0.0))
                            if (ed >= float(self.edge_density_hi)) or (cd >= float(self.corner_density_hi)):
                                passes = filtered_scores and filtered_scores[0] >= max(float(self.len1_conf_high_complexity), 0.90)
                        except Exception:
                            pass

                    if passes:
                        candidate_texts = filtered_texts
                        candidate_scores = filtered_scores
                        candidate_polys = filtered_polys
                    else:
                        candidate_texts = []
                        candidate_scores = []
                        candidate_polys = []
            except Exception:
                # 任何过滤异常不应影响整体识别流程
                pass

            # 预处理重试标记（用于日志展示）
            preprocess_retry_used = False
            preprocess_retry_info = ""


            kept_indices = list(range(len(candidate_texts)))

            # 调试输出：仅保留必要信息（官方参数与候选列表），并支持保存到文件
            log_filter_debug = config.getboolean('ocr', 'log_filter_debug', fallback=False)
            log_filter_debug_save = config.getboolean('ocr', 'log_filter_debug_save', fallback=False)
            logs_dir = config.get('paths', 'ocr_logs_dir', fallback=str(Path(settings.BASE_DIR) / 'logs' / 'ocr'))

            if log_filter_debug:
                image_name = os.path.basename(image_path)
                header_line = f"==================== OCR filter debug | image: {image_name} ===================="
                footer_line = "--------------------------------------------------------------------------------------------------"

                # 获取识别模式中文名称 (基于实际生效的模式, 而非全局设定)
                preset_name_map = {
                    'high_speed': '快速',
                    'balanced': '均衡',
                    'high_precision': '高精度',
                    'smart_balanced': '动态均衡'
                }
                # 优先使用 _effective_preset (由当前图片特征决定)
                effective_preset_key = getattr(self, '_effective_preset', None) or self.smart_ocr_preset
                preset_zh = preset_name_map.get(effective_preset_key, '均衡')

                # 构建最终用于展示的模式名称 (智能均衡增加前缀)
                if self.smart_ocr_preset == "smart_balanced":
                    mode_display = f"动态均衡-{preset_zh}"
                else:
                    mode_display = preset_zh

                # 记录公共参数（仅在任务开始或任务ID变更时输出一次）
                if not self.__class__._common_params_logged or self.__class__._common_params_task_id != task_id:
                    # 合并当前过滤参数和内部实际参数，去除重复
                    text_detection_model_name = config.get('ocr', 'text_detection_model_name', fallback='PP-OCRv5_server_det')
                    text_recognition_model_name = config.get('ocr', 'text_recognition_model_name', fallback='PP-OCRv5_server_rec')
                    use_doc_orientation_classify = config.getboolean('ocr', 'use_doc_orientation_classify', fallback=False)
                    use_doc_unwarping = config.getboolean('ocr', 'use_doc_unwarping', fallback=False)
                    use_textline_orientation = getattr(self, 'use_textline_orientation', config.getboolean('ocr', 'use_textline_orientation', fallback=False))

                    # 整合后的参数摘要
                    common_params = (
                        f"OCR 全局参数设置(任务ID: {task_id}):\n"
                        f"- 核心阈值: text_rec_score_thresh={self.text_rec_score_thresh}\n"
                        f"- 检测参数: text_det_thresh={self.text_det_thresh}, text_det_box_thresh={self.text_det_box_thresh}, text_det_unclip_ratio={self.text_det_unclip_ratio}\n"
                        f"- 检测尺寸: text_det_limit_type={self.text_det_limit_type}, text_det_limit_side_len={self.text_det_limit_side_len}\n"
                        f"- 文档与方向: use_doc_orientation_classify={use_doc_orientation_classify}, use_doc_unwarping={use_doc_unwarping}, use_textline_orientation={use_textline_orientation}\n"
                        f"- 模型: text_detection_model_name={text_detection_model_name}, text_recognition_model_name={text_recognition_model_name}\n"
                        f"- 动态模式: smart_ocr_dynamic_limit_enabled={self.smart_ocr_dynamic_limit_enabled}\n"
                        f"- 缓存启用: ocr_cache_enabled={self.ocr_cache_enabled}\n"
                        f"- 全局识别模式: {preset_name_map.get(self.smart_ocr_preset, self.smart_ocr_preset)}\n"
                    )

                    logger.warning(common_params)

                    # 更新日志标记
                    self.__class__._common_params_logged = True
                    self.__class__._common_params_task_id = task_id

                    # 如果需要保存到文件，将公共参数写入
                    if log_filter_debug_save and task_id:
                        try:
                            os.makedirs(logs_dir, exist_ok=True)
                            file_path = os.path.join(logs_dir, f"{task_id}.log")
                            with open(file_path, 'a', encoding='utf-8') as fp:
                                fp.write(f"OCR 全局参数设置 [{time.strftime('%Y-%m-%d %H:%M:%S')}]\n")
                                fp.write(common_params)
                                fp.write("\n")
                        except Exception as perr:
                            logger.error(f"保存公共参数日志失败: {perr}")

                # 只输出图片特有信息
                try:
                    img_height, img_width = image_nd.shape[:2] if image_nd is not None else (0, 0)
                    img_pixels = img_height * img_width

                    # 图片特定信息
                    image_specific_info = (
                        f"{header_line}\n"
                        f"图片信息: {image_name} | 分辨率: {img_width}x{img_height} | 总像素: {img_pixels:,} | 识别模式: {mode_display}\n"
                    )

                    # 仅显示有差异的参数
                    internal_det_params = first_raw_debug.get('text_det_params')
                    if internal_det_params and isinstance(internal_det_params, dict):
                        # 检测与当前参数的差异
                        diff_params = []
                        if internal_det_params.get('limit_side_len') != self.text_det_limit_side_len:
                            diff_params.append(f"limit_side_len={internal_det_params.get('limit_side_len')}")
                        if internal_det_params.get('limit_type') != self.text_det_limit_type:
                            diff_params.append(f"limit_type={internal_det_params.get('limit_type')}")
                        if internal_det_params.get('thresh') != self.text_det_thresh:
                            diff_params.append(f"thresh={internal_det_params.get('thresh')}")
                        if internal_det_params.get('box_thresh') != self.text_det_box_thresh:
                            diff_params.append(f"box_thresh={internal_det_params.get('box_thresh')}")
                        if internal_det_params.get('unclip_ratio') != self.text_det_unclip_ratio:
                            diff_params.append(f"unclip_ratio={internal_det_params.get('unclip_ratio')}")

                        if diff_params:
                            image_specific_info += f"参数差异: {', '.join(diff_params)}\n"

                    # 逐项输出（仅展示前若干项，避免日志过长）
                    max_items = 50
                    lines = []
                    if preprocess_retry_used:
                        image_specific_info += f"预处理重试: {preprocess_retry_info}\n"

                    if not candidate_texts:
                        lines.append(
                            f"detector未检出文本框 (共0个)"
                        )
                    else:
                        lines.append(f"检出文本框: {len(candidate_texts)}个")
                        for i in range(min(len(candidate_texts), max_items)):
                            s = float(candidate_scores[i]) if i < len(candidate_scores) else 0.0
                            decision = "keep" if s >= self.text_rec_score_thresh else "drop"
                            lines.append(
                                f"  {i+1}. '{candidate_texts[i]}' [置信度={s:.3f}]"
                            )

                    logger.warning(
                        image_specific_info
                        + "\n".join(lines)
                        + "\n"
                        + footer_line
                    )

                    if log_filter_debug_save and task_id:
                        try:
                            os.makedirs(logs_dir, exist_ok=True)
                            file_path = os.path.join(logs_dir, f"{task_id}.log")
                            with open(file_path, 'a', encoding='utf-8') as fp:
                                fp.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {image_name} 处理\n")
                                fp.write(f"分辨率: {img_width}x{img_height} | 识别模式: {mode_display}\n")
                                if preprocess_retry_used:
                                    fp.write(f"预处理重试: {preprocess_retry_info}\n")
                                for ln in lines:
                                    fp.write(ln + "\n")
                                fp.write(footer_line + "\n\n")
                        except Exception as perr:
                            logger.error(f"保存图片日志失败: {perr}")
                except Exception as log_err:
                    logger.error(f"生成日志信息失败: {log_err}")

            # 计算参数差异摘要，用于结果输出
            param_diff_list = []
            try:
                internal_det_params = first_raw_debug.get('text_det_params')
                if internal_det_params and isinstance(internal_det_params, dict):
                    if internal_det_params.get('limit_side_len') != self.text_det_limit_side_len:
                        param_diff_list.append(
                            f"limit_side_len={internal_det_params.get('limit_side_len')}"
                        )
                    if internal_det_params.get('limit_type') != self.text_det_limit_type:
                        param_diff_list.append(
                            f"limit_type={internal_det_params.get('limit_type')}"
                        )
                    if internal_det_params.get('thresh') != self.text_det_thresh:
                        param_diff_list.append(
                            f"thresh={internal_det_params.get('thresh')}"
                        )
                    if internal_det_params.get('box_thresh') != self.text_det_box_thresh:
                        param_diff_list.append(
                            f"box_thresh={internal_det_params.get('box_thresh')}"
                        )
                    if internal_det_params.get('unclip_ratio') != self.text_det_unclip_ratio:
                        param_diff_list.append(
                            f"unclip_ratio={internal_det_params.get('unclip_ratio')}"
                        )
            except Exception:
                pass

            # 构建最终输出结果
            final_texts: List[str] = []
            final_boxes: List[Any] = []
            final_scores: List[float] = []
            for i in kept_indices:
                if 0 <= i < len(candidate_texts):
                    final_texts.append(candidate_texts[i])
                    final_scores.append(candidate_scores[i] if i < len(candidate_scores) else 0.0)
                    if i < len(candidate_polys) and candidate_polys[i] is not None:
                        final_boxes.append(candidate_polys[i])
                    else:
                        final_boxes.append([])

            time_cost = (end_time - start_time).total_seconds()
            if final_texts:
                try:
                    overall_conf = float(sum(final_scores) / max(1, len(final_scores)))
                except Exception:
                    overall_conf = 0.0
                # 生成可读的模式展示，确保与日志一致
                preset_name_map = {
                    'high_speed': '快速',
                    'balanced': '均衡',
                    'high_precision': '高精度',
                    'smart_balanced': '智能均衡'
                }
                effective_key = (self._effective_preset or self.smart_ocr_preset)
                readable_mode = preset_name_map.get(effective_key, '均衡')
                if self.smart_ocr_preset == 'smart_balanced':
                    readable_mode = f"动态均衡-{readable_mode}"
                return {
                    "image_path": image_path,
                    "texts": final_texts,
                    "boxes": final_boxes,
                    "confidence": overall_conf,
                    "time_cost": time_cost,
                    "used_preset": (self._effective_preset or self.smart_ocr_preset),
                    "mode_display": readable_mode,
                    "resolution": {"width": int(img_width), "height": int(img_height)},
                    "pixels": int(img_pixels),
                    "param_diff": ", ".join(param_diff_list) if param_diff_list else "",
                    "confidences": [float(x) for x in final_scores],
                    "pic_resolution": pic_resolution,
                }
            else:
                # 生成可读的模式展示，确保与日志一致
                preset_name_map = {
                    'high_speed': '快速',
                    'balanced': '均衡',
                    'high_precision': '高精度',
                    'smart_balanced': '智能均衡'
                }
                effective_key = (self._effective_preset or self.smart_ocr_preset)
                readable_mode = preset_name_map.get(effective_key, '均衡')
                if self.smart_ocr_preset == 'smart_balanced':
                    readable_mode = f"动态均衡-{readable_mode}"
                return {
                    "image_path": image_path,
                    "texts": [],
                    "boxes": [],
                    "confidence": 0.0,
                    "time_cost": time_cost,
                    "used_preset": (self._effective_preset or self.smart_ocr_preset),
                    "mode_display": readable_mode,
                    "resolution": {"width": int(img_width), "height": int(img_height)},
                    "pixels": int(img_pixels),
                    "param_diff": ", ".join(param_diff_list) if param_diff_list else "",
                    "confidences": [],
                    "pic_resolution": pic_resolution,
                }
        except Exception as e:
            logger.error(f"图片识别失败 {image_path}: {str(e)}")
            return {"error": f"图片识别失败: {str(e)}", "image_path": image_path, "pic_resolution": pic_resolution }

    def recognize_batch(self, image_dir: str, image_formats: List[str] = None) -> List[Dict]:
        """批量识别（兼容保留）。

        注意：旧的"单套参数/单轮流程"已被多轮识别方案取代。
        本方法仅为兼容保留，推荐改用 `recognize_rounds_batch`，
        以获得"命中即剔除、首轮命中参数回写、可视化/复制"等能力。
        """
        try:
            logger.warning(
                "recognize_batch 已兼容保留，推荐改用 recognize_rounds_batch 以启用多轮识别能力")
        except Exception:
            pass
        
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

    # ============================ 多轮识别：工具函数与实现 ============================

    @staticmethod
    def _text_is_chinese_only(text: str) -> bool:
        """仅保留包含中文且不含英文字母和数字的文本。"""
        if not text:
            return False
        has_cn = any('\u4e00' <= ch <= '\u9fff' for ch in text)
        has_ascii_alnum = any((ord(ch) < 128) and (ch.isalpha() or ch.isdigit()) for ch in text)
        return has_cn and not has_ascii_alnum

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
        """默认6轮参数（与 helper 对齐）。"""
        return [
            {
                'text_det_limit_type': 'min',
                'text_det_limit_side_len': 736,
                'text_det_thresh': 0.30,
                'text_det_box_thresh': 0.60,
                'text_det_unclip_ratio': 1.5,
                'text_rec_score_thresh': 0.9,
                'use_textline_orientation': False,
                'use_doc_unwarping': False,
            },
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
            {
                'text_det_limit_type': 'min',
                'text_det_limit_side_len': 1280,
                'text_det_thresh': 0.3,
                'text_det_box_thresh': 0.6,
                'text_det_unclip_ratio': 2.0,
                'text_rec_score_thresh': 0.6,
                'use_textline_orientation': False,
                'use_doc_unwarping': True,
            },
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
            use_textline_orientation=use_textline_orientation
        )
        self._force_apply_params_to_instance(ocr_inst, params)
        return ocr_inst

    def recognize_rounds_batch(self,
                               image_dir: str,
                               image_formats: Optional[List[str]] = None,
                               enable_draw: Optional[bool] = None,
                               enable_copy: Optional[bool] = None,
                               enable_annotate: Optional[bool] = None
                               ) -> Dict[str, Any]:
        """多轮参数识别（命中即剔除），与 helper 行为保持一致的核心流程。

        返回批次统计与每图首轮命中信息，便于上层落盘。"""
        # 固定启用多轮识别（不再从配置读取开关）

        img_exts = image_formats or ['.jpg', '.jpeg', '.png', '.bmp', '.webp']
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

        # 预分流：按 min_side 的 P95
        try:
            min_sides: List[int] = []
            name_to_path: Dict[str, str] = {}
            for p in image_paths:
                try:
                    data = np.fromfile(p, dtype=np.uint8)
                    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
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
                        data = np.fromfile(p, dtype=np.uint8)
                        img = cv2.imdecode(data, cv2.IMREAD_COLOR)
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

        cur_inputs = list(small_images) if small_images else list(image_paths)
        ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        rounds_root = os.path.join(PathUtils.get_ocr_results_dir(),
                                   f"rounds_eval_{ts}")
        try:
            os.makedirs(rounds_root, exist_ok=True)
        except Exception:
            pass
        hit_root = os.path.join(rounds_root, 'hit')
        miss_root = os.path.join(rounds_root, 'miss')
        os.makedirs(hit_root, exist_ok=True)
        os.makedirs(miss_root, exist_ok=True)

        # 通过函数参数控制：未显式传入则安全默认 False
        enable_draw = bool(enable_draw) if enable_draw is not None else False
        enable_copy = bool(enable_copy) if enable_copy is not None else False
        enable_annotate = bool(enable_annotate) if enable_annotate is not None else False
 
        # 固定使用内置6轮参数，不从配置读取
        rounds = [self._validate_round_params(x)
                  for x in self._default_round_param_sets()]
        try:
            logger.warning(
                f"多轮识别：使用内置参数集，轮数={len(rounds)}"
            )
        except Exception:
            pass
 
        total_hit = 0
        last_miss_count = 0
        first_hit_info: Dict[str, Dict[str, Any]] = {}
 
        for ridx, rp in enumerate(rounds, start=1):
            if not cur_inputs:
                logger.warning(f"多轮迭代：第{ridx}轮无输入，提前结束。")
                break
            try:
                rp = self._validate_round_params(rp)
            except Exception as ve:
                logger.error(f"多轮迭代：参数缺失或非法(第{ridx}轮)：{ve}")
                continue
            try:
                logger.warning(
                    "多轮迭代：第%s轮开始，输入=%s | 参数: limit_type=%s side_len=%s det_thresh=%.2f box_thresh=%.2f unclip=%.2f rec_score=%.2f doc_unwarp=%s textline=%s",
                    ridx, len(cur_inputs),
                    rp.get('text_det_limit_type'), rp.get('text_det_limit_side_len'),
                    float(rp.get('text_det_thresh')), float(rp.get('text_det_box_thresh')),
                    float(rp.get('text_det_unclip_ratio')), float(rp.get('text_rec_score_thresh')),
                    bool(rp.get('use_doc_unwarping', False)),
                    bool(rp.get('use_textline_orientation', False))
                )
            except Exception:
                pass
            ocr_inst = self._get_ocr_for_round(rp)
 
            vis_hit_dir = os.path.join(rounds_root, f"vis_r{ridx}", 'hit')
            vis_miss_dir = os.path.join(rounds_root, f"vis_r{ridx}", 'miss')
            if enable_draw:
                os.makedirs(vis_hit_dir, exist_ok=True)
                os.makedirs(vis_miss_dir, exist_ok=True)
 
            hit_paths: List[str] = []
            miss_paths: List[str] = []
            for p in cur_inputs:
                try:
                    data = np.fromfile(p, dtype=np.uint8)
                    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
                    if img is None:
                        miss_paths.append(p)
                        continue
                    res = ocr_inst.predict(input=img)
                    items = self._parse_predict_items(res)
                    # 中文过滤（与 helper 对齐，默认开启）
                    kept = [(poly, t, s) for (poly, t, s) in items
                            if self._text_is_chinese_only(t)]
                    ok = len(kept) > 0
 
                    if enable_draw:
                        try:
                            vis = img.copy()
                            for poly, t, s in kept:
                                pts = np.array(poly, dtype=np.int32)
                                if pts.ndim == 2 and pts.shape[0] >= 4:
                                    cv2.polylines(vis, [pts], True,
                                                  (0, 255, 0), 2)
                                    x = int(np.min(pts[:, 0])); y = int(np.min(pts[:, 1]))
                                else:
                                    x, y = 2, 20
                                if enable_annotate:
                                    label = f"{t} ({float(s):.2f})"
                                    cv2.putText(
                                        vis, label, (x, max(0, y - 5)),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                                        (0, 0, 255), 1, cv2.LINE_AA
                                    )
                                out_dir = vis_hit_dir if ok else vis_miss_dir
                                out_path = os.path.join(out_dir,
                                                        os.path.basename(p))
                                cv2.imwrite(out_path, vis)
                        except Exception:
                            pass
 
                    if ok:
                        hit_paths.append(p)
                        name = os.path.basename(p)
                        if name not in first_hit_info:
                            try:
                                h, w = img.shape[:2]
                                sr = self._compute_scaled_resolution(
                                    h, w,
                                    str(rp['text_det_limit_type']),
                                    int(rp['text_det_limit_side_len'])
                                )
                                texts_str = "|".join([str(t) for (_, t, _) in kept])
                                scores_str = "|".join([
                                    f"{float(s):.4f}" for (_, _, s) in kept
                                ])
                                first_hit_info[name] = {
                                    'round': ridx,
                                    'text_det_limit_type': rp['text_det_limit_type'],
                                    'text_det_limit_side_len': rp['text_det_limit_side_len'],
                                    'text_det_thresh': rp['text_det_thresh'],
                                    'text_det_box_thresh': rp['text_det_box_thresh'],
                                    'text_det_unclip_ratio': rp['text_det_unclip_ratio'],
                                    'text_rec_score_thresh': rp['text_rec_score_thresh'],
                                    'use_doc_unwarping': bool(rp.get('use_doc_unwarping', False)),
                                    'use_textline_orientation': bool(rp.get('use_textline_orientation', False)),
                                    'hit_texts': texts_str,
                                    'hit_scores': scores_str,
                                    'scaled_resolution': sr,
                                }
                            except Exception:
                                pass
                    else:
                        miss_paths.append(p)
                except Exception as e:
                    logger.error(f"预测失败 {p}: {e}")
                    miss_paths.append(p)
 
            # 命中即复制
            if enable_copy:
                for sp in hit_paths:
                    try:
                        shutil.copy2(sp, os.path.join(hit_root,
                                                       os.path.basename(sp)))
                    except Exception:
                        pass
            total_hit += len(hit_paths)
            last_miss_count = len(miss_paths)
            try:
                logger.warning(
                    f"多轮迭代：第{ridx}轮结束，hit={len(hit_paths)} miss={len(miss_paths)}"
                )
            except Exception:
                pass
            cur_inputs = list(miss_paths)
 
        # 最终未命中复制
        if enable_copy and cur_inputs:
            for sp in cur_inputs:
                try:
                    shutil.copy2(sp, os.path.join(miss_root,
                                                   os.path.basename(sp)))
                except Exception:
                    pass
 
        return {
            'rounds_root': rounds_root,
            'total_hit': int(total_hit),
            'final_miss': int(last_miss_count),
            'first_hit_info': first_hit_info,
        }


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
        elif os.path.isfile(args.path):
            print(f"识别单张图片: {args.path}")
            result = ocr.recognize_image(args.path)
            print(f"识别结果: {result.get('texts', [])}")
        else:
            print(f"路径不存在: {args.path}")
    else:
        print("请指定图片路径或目录，使用 --path 参数")
        print("示例: python ocr_service.py --path images/test.jpg --lang ch --gpu")