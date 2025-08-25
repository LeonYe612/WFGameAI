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

# 设置 PaddleOCR 相关日志级别，减少不必要的输出
logging.getLogger('PaddleOCR').setLevel(logging.ERROR)
logging.getLogger('paddle').setLevel(logging.ERROR)
logging.getLogger('paddleocr').setLevel(logging.ERROR)
logging.getLogger('PaddleOCR').setLevel(logging.ERROR)
# 设置更严格的日志级别
logging.getLogger('glog').setLevel(logging.ERROR)
logging.getLogger('PIL').setLevel(logging.ERROR)
logging.getLogger('cv2').setLevel(logging.ERROR)

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

        try:
            # 设置环境变量来减少 PaddleOCR 的输出
            os.environ['PADDLEOCR_SHOW_LOG'] = 'False'
            os.environ['PADDLE_LOG_LEVEL'] = 'ERROR'
            os.environ['FLAGS_allocator_strategy'] = 'auto_growth'
            os.environ['FLAGS_eager_delete_tensor_gb'] = '0.0'
            # 关闭 PaddleOCR 的文件保存提示
            os.environ['PADDLEOCR_SAVE_LOG'] = 'False'
            os.environ['PADDLEOCR_VERBOSE'] = 'False'
            # 设置更严格的日志级别
            os.environ['GLOG_v'] = '0'
            os.environ['GLOG_logtostderr'] = '0'
            # 关闭 Paddle 的详细输出
            os.environ['FLAGS_logtostderr'] = '0'
            os.environ['FLAGS_log_dir'] = '/dev/null'
            os.environ['FLAGS_log_prefix'] = '0'
            # 关闭模型下载提示
            os.environ['PADDLE_DISABLE_LOGGER'] = '1'
            os.environ['PADDLE_DISABLE_PROFILING'] = '1'
            
            # 初始化 PaddleOCR
            self.ocr = PaddleOCR(
                use_doc_orientation_classify=False, # 是否加载并使用文档方向分类功能。
                use_doc_unwarping=True, # 是否加载并使用文本图像矫正功能。
                use_textline_orientation=True, # 是否加载并使用文本行方向功能。
                device=device_arg, # 指定使用设备，可选值为 'cpu' 或 'gpu'。
                # text_detection_model_name="PP-OCRv5_mobile_det", # 指定文本检测模型名称。
                # text_recognition_model_name="PP-OCRv5_mobile_rec", # 指定文本识别模型名称。
                # text_detection_model_name="PP-OCRv5_server_det", # 指定文本检测模型名称。
                # text_recognition_model_name="PP-OCRv5_server_rec", # 指定文本识别模型名称。
                lang=self.lang, # 指定语言，可选值为 'ch' 或 'en'。
                enable_mkldnn=True
            )
        except Exception as init_err:
            logger.error(f"PaddleOCR模型初始化失败: {init_err}")
            raise
        print(f"PaddleOCR模型初始化完成，device={device_arg}")



    def initialize(self):
        return self.ocr is not None

    def _collect_texts_from_json(self, data: Any) -> List[str]:

        texts: List[str] = []

        def _walk(node: Any):
            if isinstance(node, dict):
                for key, value in node.items():
                    key_lower = str(key).lower()
                    # 支持多种常见字段，以及 PaddleOCR 保存结果中的 rec_texts
                    if key_lower in {"text", "transcription", "label", "text_content", "rec_texts"}:
                        if isinstance(value, str) and value:
                            texts.append(value)
                        elif isinstance(value, list):
                            for v in value:
                                if isinstance(v, str) and v:
                                    texts.append(v)
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
            # Additional raw outputs to enable filtering
            candidate_polys: List[Any] = []  # list of polygons (Nx2) or boxes
            candidate_texts: List[str] = []
            candidate_scores: List[float] = []
            try:
                if predict_save and out_dir:
                    for res in results:
                        try:
                            # res.print()  # 注释掉调试输出，避免打印大量原始结果
                            pass
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

                # Extract raw fields directly from results, if available
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
                    # ignore failures and rely on JSON fallback below
                    pass

                # If predict_save enabled, extract texts from JSON files as fallback
                if predict_save and out_dir and not candidate_texts:
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

                # As a final fallback (no JSON or no save), attempt to use item.rec_texts
                if not candidate_texts and not texts:
                    try:
                        for item in results:
                            if isinstance(item, dict):
                                rec_texts = item.get('rec_texts')
                                if rec_texts:
                                    candidate_texts.extend([t for t in rec_texts if isinstance(t, str)])
                            else:
                                if hasattr(item, 'rec_texts'):
                                    candidate_texts.extend([t for t in getattr(item, 'rec_texts') if isinstance(t, str)])
                    except Exception:
                        pass
            except Exception as persist_err:
                logger.debug(f"结果保存或解析失败: {persist_err}")

            # Merge sources into a single list before filtering
            if texts and not candidate_texts:
                candidate_texts = texts[:]  # use JSON texts if no direct outputs
                candidate_scores = [1.0 for _ in candidate_texts]
                candidate_polys = []

            # ---------- Non-text filtering (configurable) ----------
            # Purpose: reduce false positives on pure images/icons
            enable_filter = config.getboolean('ocr', 'enable_non_text_filter', fallback=True)
            min_rec_score = config.getfloat('ocr', 'min_rec_score', fallback=0.90)
            min_text_len = config.getint('ocr', 'min_text_length', fallback=2)
            min_zh_ratio = config.getfloat('ocr', 'min_chinese_ratio', fallback=0.40)
            min_edge_density = config.getfloat('ocr', 'min_edge_density', fallback=0.01)
            min_box_area_ratio = config.getfloat('ocr', 'min_box_area_ratio', fallback=0.00005)
            max_box_area_ratio = config.getfloat('ocr', 'max_box_area_ratio', fallback=0.50)
            nms_iou_thr = config.getfloat('ocr', 'nms_iou_threshold', fallback=0.30)
            # New fine-grained gates
            allow_single_char = config.getboolean('ocr', 'allow_single_char', fallback=False)
            single_char_min_score = config.getfloat('ocr', 'single_char_min_score', fallback=max(0.95, min_rec_score))
            single_char_min_edge_density = config.getfloat('ocr', 'single_char_min_edge_density', fallback=0.05)
            single_char_min_box_area_ratio = config.getfloat('ocr', 'single_char_min_box_area_ratio', fallback=max(min_box_area_ratio, 0.0001))
            min_box_edge_density = config.getfloat('ocr', 'min_box_edge_density', fallback=0.02)
            min_box_width_px = config.getint('ocr', 'min_box_width_px', fallback=12)
            min_box_height_px = config.getint('ocr', 'min_box_height_px', fallback=12)
            min_box_aspect_ratio = config.getfloat('ocr', 'min_box_aspect_ratio', fallback=0.20)
            max_box_aspect_ratio = config.getfloat('ocr', 'max_box_aspect_ratio', fallback=6.0)
            border_edge_margin_px = config.getint('ocr', 'border_edge_margin_px', fallback=3)
            max_border_edge_ratio = config.getfloat('ocr', 'max_border_edge_ratio', fallback=0.65)
            log_filter_debug = config.getboolean('ocr', 'log_filter_debug', fallback=False)
            log_filter_debug_max_items = config.getint('ocr', 'log_filter_debug_max_items', fallback=5)
            center_edge_margin_ratio = config.getfloat('ocr', 'center_edge_margin_ratio', fallback=0.2)
            min_center_edge_density = config.getfloat('ocr', 'min_center_edge_density', fallback=0.01)
            single_char_min_center_edge_density = config.getfloat('ocr', 'single_char_min_center_edge_density', fallback=0.03)
            filter_empty_fallback = config.getboolean('ocr', 'filter_empty_fallback', fallback=False)
            allow_large_text_box = config.getboolean('ocr', 'allow_large_text_box', fallback=True)
            large_box_area_ratio = config.getfloat('ocr', 'large_box_area_ratio', fallback=0.90)
            large_box_min_center_edge_density = config.getfloat('ocr', 'large_box_min_center_edge_density', fallback=0.03)
            large_box_min_interior_border_ratio = config.getfloat('ocr', 'large_box_min_interior_border_ratio', fallback=0.60)

            img_h, img_w = image_nd.shape[:2]
            total_pixels = max(1, img_h * img_w)
            # Edge density: fast heuristic to detect pure graphics/backgrounds
            try:
                gray = cv2.cvtColor(image_nd, cv2.COLOR_BGR2GRAY)
                edges = cv2.Canny(gray, 100, 200)
                edge_density = float((edges > 0).sum()) / float(total_pixels)
            except Exception:
                edge_density = 0.0

            kept_indices: List[int] = []
            if enable_filter:
                # Early gate: if image has extremely low edge density, treat as non-text image
                # 放宽：若没有任何候选文本，则不因边缘密度直接判空，避免整体误杀
                if edge_density < min_edge_density and candidate_texts:
                    candidate_texts = []
                    candidate_scores = []
                    candidate_polys = []
                else:
                    # Build rectangles from polygons for area & IoU
                    rects: List[List[float]] = []
                    for poly in candidate_polys:
                        try:
                            # poly: list of [x, y] points
                            xs = [p[0] for p in poly]
                            ys = [p[1] for p in poly]
                            x1, y1 = max(0.0, float(min(xs))), max(0.0, float(min(ys)))
                            x2, y2 = min(float(img_w), float(max(xs))), min(float(img_h), float(max(ys)))
                            rects.append([x1, y1, x2, y2])
                        except Exception:
                            rects.append([0.0, 0.0, 0.0, 0.0])
                    if not rects and candidate_texts:
                        # If polygons missing, approximate with a single full image rect to allow length/score filters
                        rects = [[0.0, 0.0, float(img_w), float(img_h)] for _ in candidate_texts]
                    
                    # Per-candidate filters: score, length, chinese ratio, area ratio
                    prelim_idx: List[int] = []
                    debug_logs: List[str] = []
                    for i in range(len(candidate_texts)):
                        t = candidate_texts[i]
                        s = candidate_scores[i] if i < len(candidate_scores) else 0.0
                        r = rects[i] if i < len(rects) else [0.0, 0.0, 0.0, 0.0]
                        decision = "keep"
                        reason = []
                        # score filter
                        if s < min_rec_score:
                            decision = "drop"; reason.append(f"score({s:.3f})<min_rec_score({min_rec_score})")
                        # length filter
                        if decision == "keep" and len(t.strip()) < min_text_len:
                            decision = "drop"; reason.append(f"len({len(t.strip())})<min_text_length({min_text_len})")
                        # chinese ratio filter
                        if decision == "keep":
                            zh_count = 0
                            for ch in t:
                                oc = ord(ch)
                                if (0x4E00 <= oc <= 0x9FFF) or (0x3400 <= oc <= 0x4DBF) or (0x3000 <= oc <= 0x303F):
                                    zh_count += 1
                            if len(t.strip()) == 0:
                                decision = "drop"; reason.append("empty")
                            else:
                                zh_ratio = (zh_count / max(1, len(t)))
                                if zh_ratio < min_zh_ratio:
                                    decision = "drop"; reason.append(f"zh({zh_ratio:.3f})<min_chinese_ratio({min_zh_ratio})")
                        # geometry-based gates (if rects available)
                        roi_edge_density = None
                        center_edge_density = None
                        if decision == "keep" and rects:
                            bw = max(0.0, r[2] - r[0]); bh = max(0.0, r[3] - r[1])
                            if bw < 1.0 or bh < 1.0:
                                decision = "drop"; reason.append(f"bbox({bw:.1f}x{bh:.1f})<1px")
                            if decision == "keep":
                                area_ratio = (bw * bh) / float(total_pixels)
                                if area_ratio < min_box_area_ratio or area_ratio > max_box_area_ratio:
                                    # 对大文本框放宽面积上限
                                    if not (allow_large_text_box and area_ratio >= large_box_area_ratio):
                                        decision = "drop"; reason.append(f"area({area_ratio:.6f}) not in[min_box_area_ratio({min_box_area_ratio}),max_box_area_ratio({max_box_area_ratio})]")
                                    else:
                                        reason.append(f"area({area_ratio:.6f})>=large_box_area_ratio({large_box_area_ratio}), 放宽面积限制")
                            if decision == "keep":
                                if bw < float(min_box_width_px) or bh < float(min_box_height_px):
                                    decision = "drop"; reason.append(f"size({bw:.1f}x{bh:.1f})<min_box_width_px({min_box_width_px})xmin_box_height_px({min_box_height_px})")
                            if decision == "keep":
                                aspect = bw / max(1e-6, bh)
                                if aspect < min_box_aspect_ratio or aspect > max_box_aspect_ratio:
                                    decision = "drop"; reason.append(f"aspect({aspect:.3f}) not in[min_box_aspect_ratio({min_box_aspect_ratio}),max_box_aspect_ratio({max_box_aspect_ratio})]")
                            if decision == "keep":
                                try:
                                    x1 = int(max(0, min(img_w - 1, r[0]))); y1 = int(max(0, min(img_h - 1, r[1])))
                                    x2 = int(max(0, min(img_w, r[2])));   y2 = int(max(0, min(img_h, r[3])))
                                    if x2 > x1 and y2 > y1:
                                        roi = image_nd[y1:y2, x1:x2]
                                        roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                                        roi_edges = cv2.Canny(roi_gray, 100, 200)
                                        roi_edge_density = float((roi_edges > 0).sum()) / float(max(1, roi_edges.size))
                                        # 面积占比用于后续放宽判断
                                        area_ratio_cache = (bw * bh) / float(total_pixels)
                                        if roi_edge_density < min_box_edge_density:
                                            # 对大文本框允许更低密度阈值
                                            if not (allow_large_text_box and area_ratio_cache >= large_box_area_ratio and roi_edge_density >= (min_box_edge_density * 0.5)):
                                                decision = "drop"; reason.append(f"roi_edge({roi_edge_density:.6f})<min_box_edge_density({min_box_edge_density})")
                                            else:
                                                reason.append(f"roi_edge({roi_edge_density:.6f})<min_box_edge_density({min_box_edge_density}), 但大框放宽到{min_box_edge_density*0.5:.6f}")
                                        # center / border 计算
                                        h, w = roi_edges.shape[:2]
                                        m_h = max(1, int(h * center_edge_margin_ratio))
                                        m_w = max(1, int(w * center_edge_margin_ratio))
                                        cy1, cy2 = m_h, max(m_h + 1, h - m_h)
                                        cx1, cx2 = m_w, max(m_w + 1, w - m_w)
                                        center = roi_edges[cy1:cy2, cx1:cx2] if cy2 > cy1 and cx2 > cx1 else roi_edges
                                        center_edge_density = float((center > 0).sum()) / float(max(1, center.size))
                                        if center_edge_density < min_center_edge_density:
                                            # 大文本框对 center 边缘密度单独放宽
                                            if not (allow_large_text_box and area_ratio_cache >= large_box_area_ratio and center_edge_density >= large_box_min_center_edge_density):
                                                decision = "drop"; reason.append(f"center_edge({center_edge_density:.6f})<min_center_edge_density({min_center_edge_density})")
                                            else:
                                                reason.append(f"center_edge({center_edge_density:.6f})<min_center_edge_density({min_center_edge_density}), 但大框放宽到{large_box_min_center_edge_density:.6f}")
                                        # 边框占比
                                        top = roi_edges[0:m_h, :]; bottom = roi_edges[max(0, h - m_h):h, :]
                                        left = roi_edges[:, 0:m_w]; right = roi_edges[:, max(0, w - m_w):w]
                                        border_on = float((top > 0).sum() + (bottom > 0).sum() + (left > 0).sum() + (right > 0).sum())
                                        total_on = float((roi_edges > 0).sum() + 1e-6)
                                        border_ratio = border_on / total_on
                                        if border_ratio > max_border_edge_ratio:
                                            # 大文本框：内部也应有充足边缘，若中心边缘密度足够，且边框占比不过度高，则可放宽
                                            if not (allow_large_text_box and area_ratio_cache >= large_box_area_ratio and center_edge_density is not None and center_edge_density >= large_box_min_center_edge_density and border_ratio <= max(0.95, large_box_min_interior_border_ratio)):
                                                decision = "drop"; reason.append(f"border({border_ratio:.3f})>max_border_edge_ratio({max_border_edge_ratio})")
                                            else:
                                                reason.append(f"border({border_ratio:.3f})>max_border_edge_ratio({max_border_edge_ratio}), 但大框放宽到{max(0.95, large_box_min_interior_border_ratio):.3f}")
                                except Exception:
                                    pass
                        # single-character hardening
                        if decision == "keep" and len(t.strip()) == 1 and not allow_single_char:
                            if s < single_char_min_score:
                                decision = "drop"; reason.append(f"score({s:.3f})<single_char_min_score({single_char_min_score})")
                            if roi_edge_density is not None and roi_edge_density < single_char_min_edge_density:
                                decision = "drop"; reason.append(f"roi_edge({roi_edge_density:.6f})<single_char_min_edge_density({single_char_min_edge_density})")
                            if rects:
                                bw = max(0.0, r[2] - r[0]); bh = max(0.0, r[3] - r[1])
                                area_ratio = (bw * bh) / float(total_pixels)
                                if area_ratio < single_char_min_box_area_ratio or area_ratio > max_box_area_ratio:
                                    decision = "drop"; reason.append(f"area({area_ratio:.6f}) not in[single_char_min_box_area_ratio({single_char_min_box_area_ratio}),max_box_area_ratio({max_box_area_ratio})]")
                            if center_edge_density is not None and center_edge_density < single_char_min_center_edge_density:
                                decision = "drop"; reason.append(f"center_edge({center_edge_density:.6f})<single_char_min_center_edge_density({single_char_min_center_edge_density})")
                        if decision == "keep":
                            prelim_idx.append(i)
                        if log_filter_debug and i < log_filter_debug_max_items:
                            debug_logs.append(f"idx={i}, txt='{t}', score={s:.3f}, decision={decision}, reason={','.join(reason)}")
                    if log_filter_debug and debug_logs:
                        # 显示当前使用的过滤参数
                        param_summary = f"""当前过滤参数:
- 基础过滤: enable_non_text_filter={enable_filter}, min_rec_score={min_rec_score}, min_text_length={min_text_len}, min_chinese_ratio={min_zh_ratio}
- 边缘密度: min_edge_density={min_edge_density}, min_box_edge_density={min_box_edge_density}, min_center_edge_density={min_center_edge_density}
- 面积限制: min_box_area_ratio={min_box_area_ratio}, max_box_area_ratio={max_box_area_ratio}
- 尺寸限制: min_box_width_px={min_box_width_px}, min_box_height_px={min_box_height_px}
- 长宽比: min_box_aspect_ratio={min_box_aspect_ratio}, max_box_aspect_ratio={max_box_aspect_ratio}
- 边框检测: border_edge_margin_px={border_edge_margin_px}, max_border_edge_ratio={max_border_edge_ratio}
- 大框放宽: allow_large_text_box={allow_large_text_box}, large_box_area_ratio={large_box_area_ratio}, large_box_min_center_edge_density={large_box_min_center_edge_density}
- 单字强化: allow_single_char={allow_single_char}, single_char_min_score={single_char_min_score}, single_char_min_edge_density={single_char_min_edge_density}, single_char_min_center_edge_density={single_char_min_center_edge_density}
- 空结果回退: filter_empty_fallback={filter_empty_fallback}
--------------------------------------------------------------------------------------------------"""
                        logger.warning("OCR filter debug: \n" + param_summary + "\n" + "\n".join(debug_logs))

                    # NMS to remove overlapped boxes, keep higher score（若无框信息则跳过NMS）
                    used = [False] * len(candidate_texts)
                    if prelim_idx and rects:
                        # sort prelim indices by score desc
                        prelim_idx.sort(key=lambda idx: candidate_scores[idx] if idx < len(candidate_scores) else 0.0, reverse=True)
                        def _iou(a, b):
                            ax1, ay1, ax2, ay2 = a
                            bx1, by1, bx2, by2 = b
                            inter_x1 = max(ax1, bx1)
                            inter_y1 = max(ay1, by1)
                            inter_x2 = min(ax2, bx2)
                            inter_y2 = min(ay2, by2)
                            iw = max(0.0, inter_x2 - inter_x1)
                            ih = max(0.0, inter_y2 - inter_y1)
                            inter = iw * ih
                            area_a = max(0.0, (ax2 - ax1)) * max(0.0, (ay2 - ay1))
                            area_b = max(0.0, (bx2 - bx1)) * max(0.0, (by2 - by1))
                            union = area_a + area_b - inter if (area_a + area_b - inter) > 0 else 1.0
                            return inter / union
                        for idx_main in prelim_idx:
                            if used[idx_main]:
                                continue
                            kept_indices.append(idx_main)
                            used[idx_main] = True
                            r_main = rects[idx_main]
                            for idx_other in prelim_idx:
                                if used[idx_other]:
                                    continue
                                r_other = rects[idx_other]
                                try:
                                    if _iou(r_main, r_other) >= nms_iou_thr:
                                        used[idx_other] = True
                                except Exception:
                                    continue
                    else:
                        # 没有框信息时，按置信度序保留所有通过预筛的候选
                        prelim_idx.sort(key=lambda idx: candidate_scores[idx] if idx < len(candidate_scores) else 0.0, reverse=True)
                        kept_indices.extend(prelim_idx)
            else:
                # Filtering disabled: keep all candidates
                kept_indices = list(range(len(candidate_texts)))

            # 如果启用过滤但最终没有任何保留，且已有候选文本，为避免误杀，退回保留全部候选
            if enable_filter and not kept_indices and candidate_texts and filter_empty_fallback:
                kept_indices = list(range(len(candidate_texts)))

            # Build final outputs
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

            # If all filtered out, return empty texts
            time_cost = (end_time - start_time).total_seconds()
            if final_texts:
                # Overall confidence: mean of kept scores
                try:
                    overall_conf = float(sum(final_scores) / max(1, len(final_scores)))
                except Exception:
                    overall_conf = 0.0
                return {
                    "image_path": image_path,
                    "texts": final_texts,
                    "boxes": final_boxes,
                    "confidence": overall_conf,
                    "time_cost": time_cost
                }
            else:
                # No reliable text after filtering
                return {
                    "image_path": image_path,
                    "texts": [],
                    "boxes": [],
                    "confidence": 0.0,
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