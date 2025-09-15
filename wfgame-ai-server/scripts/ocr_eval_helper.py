# -*- coding: utf-8 -*-
"""PaddleOCR 可视化与简易评测脚本

功能：
- 批量扫描默认目录图片，调用 PaddleOCR 进行预测，保存带框与文字的可视化图片；
- 输出每张图片的统计信息（检测条目数、平均置信度）为 CSV；
- 若同名标签 JSON（或 txt）存在，执行简单对比，统计近似 Precision/Recall（IOU>0.5 近似）、输出全局汇总；
- 使用仓库内的默认参数，便于与现有服务保持一致；

使用：
  conda activate py39_yolov10
  python wfgame-ai-server/scripts/ocr_eval_helper.py

输出目录：wfgame-ai-server/media/ocr/repositories/ocr_eval

说明：
- 不依赖 PaddleOCR 官方训练/eval 框架文件结构，在当前项目中即可运行；
- 简易评测仅供快速筛查，严格评测请结合官方 eval 工具与标注格式执行。

PaddleOCR 处理流水与参数映射（PP-OCRv5）：
1) 设备与语言环境（全局）
   - device: GPU/CPU（本项目强制 'gpu'）
   - lang: 语言字典（本项目 'ch'）
2) 文档方向分类（可选，默认关闭）
   - 开关: use_doc_orientation_classify
   - 作用: 判断整图是否需要旋转校正
3) 文本检测（Text Detection）
   3.1 预处理（缩放/归一化）
       - text_det_limit_type: 'min'/'max' 缩放规则
           - 'max': 仅当长边>side_len 时等比缩小至长边=side_len；否则不缩放
           - 'min': 仅当短边<side_len 时等比放大至短边=side_len；否则不缩放
       - text_det_limit_side_len: 目标边长度
   3.2 推理
       - text_detection_model_name: 检测模型名（PP-OCRv5_server_det）
   3.3 后处理（DB 后处理）
       - text_det_thresh: 二值化阈值
       - text_det_box_thresh: 框置信度阈值
       - text_det_unclip_ratio: 扩框比（膨胀，利于包住整行）
   输出: 候选文字多边形框
4) 文本行方向分类（可选，默认关闭）
   - 开关: use_textline_orientation
   - 若开启: 对候选小图做旋转方向判断
5) 文本识别（Text Recognition）
   5.1 预处理（缩放到识别输入尺寸）
   5.2 推理
       - text_recognition_model_name: 识别模型名（PP-OCRv5_server_rec）
   5.3 后处理
       - text_rec_score_thresh: 识别分数阈值（低于阈值丢弃）
   输出: 文本内容与置信度
6) 文档去畸变（可选，默认关闭）
   - 开关: use_doc_unwarping
"""

import os
import json
import csv
import logging
import sys
import shutil
import argparse
from typing import Any, Dict, List, Tuple
from typing import Optional
from datetime import datetime
# 独立运行：不从外部配置文件读取参数
from typing import cast
import pandas as pd

import numpy as np
import cv2
import math

# 尝试导入PIL用于中文文本绘制
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except Exception:  # noqa: BLE001
    PIL_AVAILABLE = False

# 参数应用助手
def log_pipeline_overview(tag: str, params: Dict[str, float]) -> None:
    """按 PaddleOCR 处理流程顺序输出关键参数，便于非专业人士理解。
    仅当 DEBUG_EVAL=1 时生效。
    """
    if not DEBUG_EVAL:
        return
    lines = [
        f"[PIPELINE] route={tag}",
        "1) 设备/语言: device=gpu, lang=ch",
        "2) 文档方向分类: use_doc_orientation_classify=False",
        "3) 文本检测:",
        f"   - 预处理缩放: text_det_limit_type={params.get('det_limit_type')} "
        f"limit_side_len={params.get('det_limit_side_len')}",
        f"   - 后处理阈值: text_det_thresh={params.get('det_thresh'):.2f} "
        f"box_thresh={params.get('box_thresh'):.2f} unclip={params.get('unclip_ratio'):.2f}",
        f"4) 文本行方向分类: use_textline_orientation={params.get('use_textline_orientation', False)}",
        "5) 文本识别:",
        f"   - 后处理阈值: text_rec_score_thresh={params.get('rec_score_thresh'):.2f}",
        "6) 文档去畸变: use_doc_unwarping=False",
    ]
    for ln in lines:
        LOGGER.info(ln)

def apply_params_to_ocr(ocr: "PaddleOCR", det_limit_type: Optional[str], det_limit_side_len: Optional[int],
                        det_thresh: float, box_thresh: float, unclip_ratio: float,
                        rec_score_thresh: float) -> None:
    try:
        # 不再改动预处理缩放相关参数（limit_type/limit_side_len），统一交由框架默认值处理
        det = getattr(ocr, 'text_detector', None)
        # 检测 postprocess
        if det and hasattr(det, 'postprocess_op'):
            post = det.postprocess_op
            if hasattr(post, 'thresh'):
                setattr(post, 'thresh', float(det_thresh))
            if hasattr(post, 'box_thresh'):
                setattr(post, 'box_thresh', float(box_thresh))
            if hasattr(post, 'unclip_ratio'):
                setattr(post, 'unclip_ratio', float(unclip_ratio))
        # 识别 postprocess
        rec = getattr(ocr, 'text_recognizer', None)
        if rec and hasattr(rec, 'postprocess_op'):
            post = rec.postprocess_op
            if hasattr(post, 'score_thresh'):
                setattr(post, 'score_thresh', float(rec_score_thresh))
    except Exception as e:  # noqa: BLE001
        LOGGER.warning("应用参数失败: %s", e)


def choose_dynamic_params(height: int, width: int) -> Dict[str, float]:

    h, w = int(height), int(width)
    min_side = min(h, w)
    max_side = max(h, w)
    #
    aspect = (max_side / max(1, min_side)) if min_side > 0 else 1.0
    pixels = h * w

    if (min_side <= 120) or (pixels <= 150 * 150):
        limit_type = 'max'
        side_len = compute_adaptive_side_len(h, w, 'small_icon', limit_type)
        return {
            'det_limit_type': limit_type,
            'det_limit_side_len': side_len,
            'det_thresh': 0.17,
            'box_thresh': 0.40,
            'unclip_ratio': 3.30,
            'rec_score_thresh': 0.30,
            'use_textline_orientation': False,
            'tag': 'small_icon',
        }

    if (aspect >= 1.8) and (min_side >= 700):
        limit_type = 'min'
        side_len = compute_adaptive_side_len(h, w, 'vertical_sparse', limit_type)
        return {
            'det_limit_type': limit_type,
            'det_limit_side_len': side_len,
            'det_thresh': 0.28,
            'box_thresh': 0.58,
            'unclip_ratio': 1.6,
            'rec_score_thresh': 0.60,
            'use_textline_orientation': False,
            'tag': 'vertical_sparse',
        }

    if (aspect >= 1.8) or (max_side >= 1400):
        limit_type = 'min'
        side_len = compute_adaptive_side_len(h, w, 'high_recall', limit_type)
        return {
            'det_limit_type': limit_type,
            'det_limit_side_len': side_len,
            'det_thresh': 0.20,
            'box_thresh': 0.45,
            'unclip_ratio': 2.2,
            'rec_score_thresh': 0.45,
            'use_textline_orientation': False,
            'tag': 'high_recall',
        }

    if (min_side <= 160) or (pixels <= 256 * 256):
        limit_type = 'max'
        side_len = compute_adaptive_side_len(h, w, 'anti_fp', limit_type)
        return {
            'det_limit_type': limit_type,
            'det_limit_side_len': side_len,
            'det_thresh': 0.35,
            'box_thresh': 0.65,
            'unclip_ratio': 1.3,
            'rec_score_thresh': 0.65,
            'use_textline_orientation': False,
            'tag': 'anti_fp',
        }

    limit_type = 'max'
    side_len = compute_adaptive_side_len(h, w, 'balanced', limit_type)
    return {
        'det_limit_type': limit_type,
        'det_limit_side_len': side_len,
        'det_thresh': 0.25,
        'box_thresh': 0.50,
        'unclip_ratio': 1.8,
        'rec_score_thresh': 0.52,
        'use_textline_orientation': False,
        'tag': 'balanced',
    }

# GPU 环境
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
os.environ["FLAGS_use_gpu"] = "true"
os.environ["FLAGS_fraction_of_gpu_memory_to_use"] = "0.8"
os.environ["OPENCV_DNN_OPENCL_ALLOW_ALL_DEVICES"] = "0"
os.environ["MKL_SERVICE_FORCE_INTEL"] = "0"
os.environ["OCR_EVAL_DEBUG"] = "1"
os.environ["OCR_EVAL_PLATFORM_COMPAT"] = "1" # 1 关闭平台对齐；0 开启平台对齐
os.environ["OCR_EVAL_BASELINE_ONLY"] = "0" # 1 仅使用基线；0 使用动态参数
os.environ["OCR_EVAL_DRAW"] = "0" # 1 开启可视化绘制与保存；0 关闭
os.environ["OCR_EVAL_MARK"] = "0" # 1 开启对csv中result、actual_result字段标注；0 关闭
os.environ["OCR_EVAL_SUMMARY"] = "1" # 1 开启统计；0 关闭
os.environ["OCR_EVAL_COPY"] = "1" # 1 开启复制结果图片；0 关闭
os.environ["OCR_EVAL_ROUNDS"] = "1" # 1 开启多轮参数迭代；0 关闭
os.environ["OCR_EVAL_WRITE_RESULTS"] = "0" # 1 开启写入结果；0 关闭

try:
    from paddleocr import PaddleOCR
except Exception as _e:
    raise RuntimeError("未找到 paddleocr 库，请先在 py39_yolov10 环境中安装依赖。") from _e


LOGGER = logging.getLogger("ocr_eval_helper")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
DEBUG_EVAL = os.environ.get("OCR_EVAL_DEBUG", "0") == "1"
DEBUG_OVERRIDE_SCALE = os.environ.get("OCR_EVAL_OVERRIDE_SCALE", "0") == "1"
PLATFORM_COMPAT = os.environ.get("OCR_EVAL_PLATFORM_COMPAT", "0") == "1"
COMPAT_FILTER_REC = os.environ.get("OCR_EVAL_COMPAT_FILTER_REC", "0") == "1"
# 中文过滤开关（默认开启）：仅保留中文文本
CH_ONLY = os.environ.get("OCR_EVAL_CH_ONLY", "1") == "1"
# 严格中文过滤（默认关闭）：启用后按最小长度过滤，抑制单字/偏旁部首等
STRICT_CH_ONLY = os.environ.get("OCR_EVAL_STRICT_CH_ONLY", "0") == "1"
try:
    CH_MIN_LEN = int(os.environ.get("OCR_EVAL_CH_MIN_LEN", "2"))
except Exception:
    CH_MIN_LEN = 2
BASELINE_ONLY = os.environ.get("OCR_EVAL_BASELINE_ONLY", "0") == "1"
STRICT_PARITY = os.environ.get("OCR_EVAL_STRICT_PARITY", "0") == "1"
# 可视化绘制开关（默认关闭）：1开启可视化绘制与保存，0关闭
DRAW_ENABLED = os.environ.get("OCR_EVAL_DRAW", "0") == "1"

# 严格对齐：禁用一切脚本侧额外过滤，确保仅用初始化参数
if STRICT_PARITY:
    CH_ONLY = False
    COMPAT_FILTER_REC = False

# 记录各 OCR 实例的初始化参数，便于CSV输出真实配置
OCR_INIT_PARAMS_BY_ID: Dict[int, Dict[str, Any]] = {}


def repo_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))


def ensure_dir(p: str) -> None:
    if not os.path.exists(p):
        os.makedirs(p, exist_ok=True)


def clear_dir(p: str) -> None:
    """清空目录（若存在），随后重建。"""
    try:
        if os.path.exists(p):
            shutil.rmtree(p, ignore_errors=True)
        os.makedirs(p, exist_ok=True)
        LOGGER.info("已清空输出目录: %s", os.path.abspath(p))
    except Exception as e:  # noqa: BLE001
        LOGGER.error("清空输出目录失败: %s - %s", p, e)
        raise


def read_img(path: str) -> np.ndarray:
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    # 优先常规读取
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        # 回退：支持中文路径/特殊字符路径
        try:
            data = np.fromfile(path, dtype=np.uint8)
            img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        except Exception:
            img = None
    if img is None:
        raise ValueError(f"无法读取图片: {path}")
    return img


def find_chinese_font_path_from_system() -> str:
    """在系统字体目录中查找常见中文字体，避免依赖项目内字体。"""
    candidates_win = [
        'msyh.ttc', 'msyh.ttf', 'msyhl.ttc', 'msyhbd.ttc',  # 微软雅黑
        'SimHei.ttf', 'simhei.ttf',  # 黑体
        'simsun.ttc', 'SimSun.ttf',  # 宋体
        'STSONG.TTF', 'STHEITI.TTF', 'STZHONGS.TTF',
    ]
    candidates_mac = [
        'PingFang.ttc', 'Heiti.ttc', 'Songti.ttc', 'STHeiti Medium.ttc',
        'Hiragino Sans GB.ttc',
    ]
    candidates_linux_keywords = [
        'NotoSansCJK', 'NotoSansSC', 'SourceHanSansSC', 'WenQuanYi', 'DroidSansFallback',
    ]

    # Windows
    win_fonts_dir = None
    if os.name == 'nt':
        windir = os.environ.get('WINDIR') or os.environ.get('windir')
        if windir:
            win_fonts_dir = os.path.join(windir, 'Fonts')
        if win_fonts_dir and os.path.isdir(win_fonts_dir):
            for name in candidates_win:
                p = os.path.join(win_fonts_dir, name)
                if os.path.exists(p):
                    return p

    # macOS
    if sys.platform == 'darwin':
        mac_dirs = [
            '/System/Library/Fonts', '/Library/Fonts', os.path.expanduser('~/Library/Fonts')
        ]
        for d in mac_dirs:
            if os.path.isdir(d):
                for name in candidates_mac:
                    p = os.path.join(d, name)
                    if os.path.exists(p):
                        return p
                # 关键词匹配
                for root_dir, _dirs, files in os.walk(d):
                    for f in files:
                        if any(k in f for k in candidates_linux_keywords):
                            p = os.path.join(root_dir, f)
                            return p

    # Linux
    linux_dirs = [
        '/usr/share/fonts', '/usr/local/share/fonts', os.path.expanduser('~/.fonts')
    ]
    for d in linux_dirs:
        if os.path.isdir(d):
            # 优先关键词
            for root_dir, _dirs, files in os.walk(d):
                for f in files:
                    lower = f.lower()
                    if lower.endswith(('.ttf', '.ttc', '.otf')) and any(k.lower() in lower for k in candidates_linux_keywords):
                        return os.path.join(root_dir, f)
            # 否则返回第一种可用字体
            for root_dir, _dirs, files in os.walk(d):
                for f in files:
                    if f.lower().endswith(('.ttf', '.ttc', '.otf')):
                        return os.path.join(root_dir, f)

    return ""


def text_is_chinese_only(text: str) -> bool:
    """仅保留包含中文且不含英文字母和数字的文本。"""
    if not text:
        return False
    has_cn = any('\u4e00' <= ch <= '\u9fff' for ch in text)
    has_ascii_alnum = any((ord(ch) < 128) and (ch.isalpha() or ch.isdigit()) for ch in text)
    return has_cn and not has_ascii_alnum


def filter_chinese_items(items: List[Tuple[np.ndarray, str, float]]) -> List[Tuple[np.ndarray, str, float]]:
    """过滤，仅保留中文文本项。"""
    return [(p, t, s) for (p, t, s) in items if text_is_chinese_only(t)]


def filter_chinese_items_configurable(items: List[Tuple[np.ndarray, str, float]]) -> List[Tuple[np.ndarray, str, float]]:
    """根据开关执行中文过滤：
    - CH_ONLY=True 时：保留 text_is_chinese_only(text) 的项
    - STRICT_CH_ONLY=True 时：再按 CH_MIN_LEN 进行长度过滤
    """
    if not CH_ONLY:
        return list(items)
    kept = [(p, t, s) for (p, t, s) in items if text_is_chinese_only(t)]
    if STRICT_CH_ONLY:
        kept = [(p, t, s) for (p, t, s) in kept if len(t or "") >= max(1, int(CH_MIN_LEN))]
    return kept


def _poly_area(poly: np.ndarray) -> float:
    try:
        x = poly[:, 0]; y = poly[:, 1]
        return float(0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))
    except Exception:
        return 0.0


def _shape_wh(poly: np.ndarray) -> Tuple[float, float]:
    xs = poly[:, 0]; ys = poly[:, 1]
    return float(np.max(xs) - np.min(xs)), float(np.max(ys) - np.min(ys))


def _mean_intensity(img: np.ndarray, poly: np.ndarray) -> float:
    try:
        mask = np.zeros(img.shape[:2], dtype=np.uint8)
        cv2.fillPoly(mask, [poly.astype(np.int32)], 255)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        vals = gray[mask == 255]
        if vals.size == 0:
            return 0.0
        return float(np.mean(vals))
    except Exception:
        return 0.0




def parse_predict(res: Any) -> List[Tuple[np.ndarray, str, float]]:
    items: List[Tuple[np.ndarray, str, float]] = []
    if res is None:
        return items
    if isinstance(res, list) and res:
        first = res[0]
        if isinstance(first, dict):
            raw = first
            texts = raw.get('rec_texts') or raw.get('texts') or []
            scores = raw.get('rec_scores') or []
            polys = raw.get('rec_polys') or raw.get('dt_polys') or raw.get('boxes') or []
            if texts and not isinstance(texts, list):
                texts = [texts]
            if scores and not isinstance(scores, list):
                scores = [scores]
            if polys is None:
                polys = []
            n = max(len(texts), len(scores), len(polys))
            for i in range(n):
                t = texts[i] if i < len(texts) else ""
                s = float(scores[i]) if i < len(scores) else 0.0
                p = polys[i] if i < len(polys) else np.array([[0,0],[1,0],[1,1],[0,1]])
                items.append((np.array(p, dtype=np.float32), str(t), float(s)))
            return items
        if isinstance(first, list):
            for itm in first:
                if isinstance(itm, list) and len(itm) >= 2 and isinstance(itm[0], (list, np.ndarray)) and isinstance(itm[1], (list, tuple)):
                    poly = np.array(itm[0], dtype=np.float32)
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
        polys = raw.get('rec_polys') or raw.get('dt_polys') or raw.get('boxes') or []
        if texts and not isinstance(texts, list):
            texts = [texts]
        if scores and not isinstance(scores, list):
            scores = [scores]
        if polys is None:
            polys = []
        n = max(len(texts), len(scores), len(polys))
        for i in range(n):
            t = texts[i] if i < len(texts) else ""
            s = float(scores[i]) if i < len(scores) else 0.0
            p = polys[i] if i < len(polys) else np.array([[0,0],[1,0],[1,1],[0,1]])
            items.append((np.array(p, dtype=np.float32), str(t), float(s)))
    return items


def draw_result(img: np.ndarray, items: List[Tuple[np.ndarray, str, float]],
                font_path: str, enabled: bool = False) -> np.ndarray:
    """绘制检测框与中文文本（可控开关）。

    当 enabled 为 False 时，直接返回原图，不做任何绘制。
    当 enabled 为 True 时，绘制多边形框与文本。
    优先使用PIL中文字体；若不可用则退回OpenCV（可能出现乱码）。
    """
    if not enabled:
        return img
    vis = img.copy()
    # 绘制框
    for poly, _, _ in items:
        pts = np.array(poly, dtype=np.int32)
        if pts.ndim == 2 and pts.shape[0] >= 4:
            cv2.polylines(vis, [pts], True, (0, 255, 0), 2)

    # 绘制文字
    if PIL_AVAILABLE and font_path:
        try:
            pil_img = Image.fromarray(cv2.cvtColor(vis, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(pil_img)
            try:
                font = ImageFont.truetype(font_path, 18)
            except Exception:
                font = ImageFont.load_default()
            for poly, text, score in items:
                pts = np.array(poly, dtype=np.int32)
                if pts.ndim == 2 and pts.shape[0] >= 4:
                    x, y = int(np.min(pts[:, 0])), int(np.min(pts[:, 1]))
                else:
                    x, y = 2, 20
                label = f"{text} ({score:.2f})"
                draw.text((x, max(0, y - 20)), label, fill=(255, 0, 0), font=font)
            vis = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
            return vis
        except Exception:
            # 退回OpenCV
            pass

    # OpenCV 英文绘制（中文可能乱码）
    font = cv2.FONT_HERSHEY_SIMPLEX
    for poly, text, score in items:
        pts = np.array(poly, dtype=np.int32)
        if pts.ndim == 2 and pts.shape[0] >= 4:
            x, y = int(np.min(pts[:, 0])), int(np.min(pts[:, 1]))
        else:
            x, y = 2, 20
        label = f"{text} ({score:.2f})"
        cv2.putText(vis, label, (x, max(0, y - 5)), font, 0.5, (0, 0, 255), 1,
                    cv2.LINE_AA)
    return vis


def iou_poly(a: np.ndarray, b: np.ndarray) -> float:
    try:
        import shapely.geometry as geom
        import shapely.ops as ops
    except Exception:
        # 简易矩形 IOU 近似
        def to_rect(p):
            xs = [float(x[0]) for x in p]
            ys = [float(x[1]) for x in p]
            return min(xs), min(ys), max(xs), max(ys)
        ax1, ay1, ax2, ay2 = to_rect(a); bx1, by1, bx2, by2 = to_rect(b)
        inter_x1, inter_y1 = max(ax1, bx1), max(ay1, by1)
        inter_x2, inter_y2 = min(ax2, bx2), min(ay2, by2)
        iw, ih = max(0.0, inter_x2 - inter_x1), max(0.0, inter_y2 - inter_y1)
        inter = iw * ih
        area_a = max(0.0, (ax2-ax1) * (ay2-ay1))
        area_b = max(0.0, (bx2-bx1) * (by2-by1))
        union = area_a + area_b - inter
        return float(inter / union) if union > 0 else 0.0
    # 精确多边形 IOU（若安装了 shapely）
    pa = geom.Polygon(a); pb = geom.Polygon(b)
    if not pa.is_valid or not pb.is_valid:
        return 0.0
    inter = pa.intersection(pb).area
    union = pa.union(pb).area
    return float(inter / union) if union > 0 else 0.0


def compute_scaled_resolution(h: int, w: int, limit_type: str, side_len: int) -> Tuple[int, int]:
    """根据 limit_type 与 side_len 估算等比缩放后的分辨率，仅用于 CSV 展示。
    规则：
    - limit_type='max': 若长边大于 side_len 则等比缩小至长边=side_len；否则保持原尺寸
    - limit_type='min': 若短边小于 side_len 则等比放大至短边=side_len；否则保持原尺寸
    - 其他值：退回旧逻辑
    """
    try:
        h = int(h); w = int(w); side = int(side_len)
        if h <= 0 or w <= 0 or side <= 0:
            return (w, h)
        lt = str(limit_type)
        cur_max = float(max(h, w))
        cur_min = float(min(h, w))

        if lt == 'max':
            if cur_max > side:
                r = float(side) / cur_max
                sw = int(round(w * r)); sh = int(round(h * r))
                return (max(1, sw), max(1, sh))
            return (w, h)

        if lt == 'min':
            if cur_min < side:
                r = float(side) / cur_min
                sw = int(round(w * r)); sh = int(round(h * r))
                return (max(1, sw), max(1, sh))
            return (w, h)

        # 兼容未知取值：保持旧逻辑
        denom = float(min(h, w)) if lt == 'min' else float(max(h, w))
        if denom <= 0:
            return (w, h)
        r = float(side) / denom
        sw = int(round(w * r)); sh = int(round(h * r))
        return (max(1, sw), max(1, sh))
    except Exception:
        return (w, h)




def _route_ratio_bounds(route_tag: str) -> Tuple[float, float]:
    def _f(name: str, dv: float) -> float:
        try:
            return float(os.environ.get(name, str(dv)))
        except Exception:
            return dv
    r_min = _f('SCALE_RATIO_MIN', 0.8)
    r_max = _f('SCALE_RATIO_MAX', 3.0)
    if route_tag == 'small_icon':
        return (r_min, _f('SCALE_RATIO_SMALL_ICON_MAX', 4.0))
    if route_tag == 'high_recall' or route_tag.startswith('high_recall'):
        return (r_min, _f('SCALE_RATIO_HIGH_RECALL_MAX', 2.5))
    if route_tag == 'vertical_sparse':
        return (r_min, _f('SCALE_RATIO_VERTICAL_MAX', 1.6))
    if route_tag == 'anti_fp':
        return (r_min, _f('SCALE_RATIO_ANTIFP_MAX', 1.3))
    return (r_min, _f('SCALE_RATIO_BALANCED_MAX', 1.3))


def _clamp_side_len_by_ratio(h: int, w: int, limit_type: str, route_tag: str, side_len: int) -> int:
    """将 side_len 转换为相对 denom 的比例后进行夹取，避免放大/缩小过度。"""
    h = int(max(1, h)); w = int(max(1, w))
    denom = float(min(h, w) if limit_type == 'min' else max(h, w))
    if denom <= 0:
        return int(side_len)
    cur_ratio = float(max(1, int(side_len))) / denom
    r_min, r_max = _route_ratio_bounds(route_tag)
    clamped_ratio = max(r_min, min(r_max, cur_ratio))
    return int(round(denom * clamped_ratio))




# ===== 标注与统计（基于目录的 CSV 后处理） =====

# 固定目录与映射（保持与 mark.py 第6-11行一致）
_MARK_BASE_DIR = r'C:\Users\Administrator\PycharmProjects\WFGameAI\output\1141'
_MARK_SUB_DIRS = {
    '正确': 'actual_correct_132',
    # '漏检': 'missed_detection_33',
    # '误检': 'false_detection_54'
}


def _detect_encoding(file_path: str, sample_size: int = 65536) -> Optional[str]:
    """尝试检测文件编码（可选依赖 chardet）。失败返回 None。"""
    try:
        import chardet
    except Exception:
        chardet = None
    if chardet is None:
        return None
    try:
        with open(file_path, 'rb') as f:
            raw = f.read(sample_size)
        result = chardet.detect(raw)
        enc = result.get('encoding') if isinstance(result, dict) else None
        if isinstance(enc, str):
            return enc.lower()
    except Exception:
        return None
    return None


def _read_csv_robust(file_path: str, encoding: str = 'auto') -> pd.DataFrame:
    """鲁棒读取 CSV：优先使用指定/探测编码，失败时多编码回退。"""
    tried: set[str] = set()
    if isinstance(encoding, str) and encoding.lower() != 'auto':
        tried.add(encoding.lower())
        return pd.read_csv(file_path, encoding=encoding)

    detected = _detect_encoding(file_path)
    fallback_encodings = [
        'utf-8', 'utf-8-sig', 'gb18030', 'gbk', 'cp936', 'big5', 'latin1'
    ]
    if detected and detected not in tried:
        try:
            tried.add(detected)
            return pd.read_csv(file_path, encoding=detected)
        except Exception:
            pass
    last_err: Optional[Exception] = None
    for enc in fallback_encodings:
        if enc in tried:
            continue
        try:
            return pd.read_csv(file_path, encoding=enc)
        except Exception as e:
            last_err = e
            continue
    if last_err is not None:
        raise last_err
    raise RuntimeError('无法读取 CSV：未知错误')


def _parse_labels_mapping(mapping_str: Optional[str]) -> Optional[Dict[str, str]]:
    """解析 label=dirname, ... 映射字符串。"""
    if not mapping_str:
        return None
    mapping: Dict[str, str] = {}
    parts = [p.strip() for p in mapping_str.split(',') if p.strip()]
    for part in parts:
        if '=' not in part:
            raise ValueError(f"labels 项格式错误: '{part}'，应为 label=dirname")
        label, dirname = [x.strip() for x in part.split('=', 1)]
        if not label or not dirname:
            raise ValueError(f"labels 项缺少 label 或 dirname: '{part}'")
        mapping[label] = dirname
    return mapping


def _collect_image_names(dir_path: str) -> set[str]:
    """收集目录下图片名（去扩展名，小写）。"""
    names: set[str] = set()
    try:
        for n in os.listdir(dir_path):
            p = os.path.join(dir_path, n)
            if not os.path.isfile(p):
                continue
            root, _ = os.path.splitext(n)
            if root:
                names.add(root.lower())
    except FileNotFoundError:
        LOGGER.warning("目录未找到: %s", os.path.abspath(dir_path))
    except Exception as e:
        LOGGER.warning("扫描目录失败: %s - %s", os.path.abspath(dir_path), e)
    return names


def _build_label_dirs(base_dir: str, labels_map: Optional[Dict[str, str]]) -> Dict[str, str]:
    """构建标签到子目录名的映射；若未提供映射，则自动以子目录名为标签名。"""
    if labels_map:
        return dict(labels_map)
    label_dirs: Dict[str, str] = {}
    for entry in os.listdir(base_dir):
        full = os.path.join(base_dir, entry)
        if os.path.isdir(full):
            label_dirs[entry] = entry
    if not label_dirs:
        raise RuntimeError(f"未在基准目录发现任何子目录: {base_dir}")
    return label_dirs


def post_mark_csv(csv_path: str,
                  base_dir: str,
                  labels_map_str: Optional[str] = None,
                  image_col: Optional[str] = None,
                  read_encoding: str = 'auto',
                  write_encoding: str = 'utf-8-sig') -> Dict[str, int]:
    """根据基准目录子目录为 CSV 标注 result 列，并返回标签统计。"""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(csv_path)
    if not os.path.isdir(base_dir):
        raise NotADirectoryError(base_dir)

    labels_map = _parse_labels_mapping(labels_map_str)
    label_dirs = _build_label_dirs(base_dir, labels_map)
    image_sets: Dict[str, set[str]] = {}
    for label, subdir in label_dirs.items():
        dir_path = os.path.join(base_dir, subdir)
        image_sets[label] = _collect_image_names(dir_path)

    df = _read_csv_robust(csv_path, encoding=read_encoding)
    if df.shape[1] < 1:
        raise ValueError("CSV 至少需要一列（图片名列）")
    img_col = image_col if image_col else df.columns[0]
    if img_col not in df.columns:
        raise KeyError(f"图片名列不存在: {img_col}")

    df['__normalized_name__'] = df[img_col].apply(
        lambda x: os.path.splitext(str(x))[0].lower()
    )
    if 'result' not in df.columns:
        df['result'] = ''

    for idx, name in enumerate(df['__normalized_name__'].tolist()):
        matched = ''
        for label, img_set in image_sets.items():
            if name in img_set:
                matched = label
                break
        df.at[idx, 'result'] = matched

    df.drop(columns=['__normalized_name__'], inplace=True)
    df.to_csv(csv_path, index=False, encoding=write_encoding)

    # 统计 result 列（供需要时使用）
    stats: Dict[str, int] = {}
    for v in df['result'].tolist():
        stats[v] = stats.get(v, 0) + 1
    return stats


def add_actual_result_and_summarize(csv_path: str,
                                     write_encoding: str = 'utf-8-sig') \
        -> Dict[str, int]:
    """在 CSV 中新增 actual_result 字段，并按规则标注与汇总统计。

    规则：
    - 若 result 为空 且 texts 非空 -> actual_result='误检'
    - 若 result 非空 且 texts 为空 -> actual_result='漏检'
    - 若 result 与 texts 均非空 -> actual_result='正确'
    - 若 result 与 texts 均为空 -> actual_result=''（不计入三类）

    返回：{'正确': x, '误检': y, '漏检': z}
    """
    df = _read_csv_robust(csv_path, encoding='auto')

    # 兼容缺失列
    if 'result' not in df.columns:
        df['result'] = ''
    if 'texts' not in df.columns:
        df['texts'] = ''

    def _is_empty_str(v: Any) -> bool:
        try:
            s = str(v).strip()
            return s == '' or s.lower() == 'nan'
        except Exception:
            return True

    actual_vals: List[str] = []
    for _, row in df.iterrows():
        r = row.get('result', '')
        t = row.get('texts', '')
        r_empty = _is_empty_str(r)
        t_empty = _is_empty_str(t)
        if r_empty and not t_empty:
            actual_vals.append('误检')
        elif (not r_empty) and t_empty:
            actual_vals.append('漏检')
        elif (not r_empty) and (not t_empty):
            actual_vals.append('正确')
        else:
            actual_vals.append('')

    df['actual_result'] = actual_vals
    df.to_csv(csv_path, index=False, encoding=write_encoding)

    stats: Dict[str, int] = {'正确': 0, '误检': 0, '漏检': 0}
    for v in actual_vals:
        if v in stats:
            stats[v] += 1
        else:
            stats[v] = stats.get(v, 0) + 1
    return stats


def copy_images_from_df(df: pd.DataFrame,
                        image_name_to_path: Dict[str, str],
                        out_root: str) -> None:
    """基于内存DataFrame复制图片。

    优先按 actual_result 分类（当且仅当标注已开启且存在该列）；否则按命中：
    - texts 非空 或 hit 为真 -> 归入 hit
    - 否则 -> miss
    """
    if df is None or df.empty:
        LOGGER.warning("复制图片跳过：主数据为空")
        return

    img_col = 'image' if 'image' in df.columns else df.columns[0]
    valid_exts = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}

    mark_enabled = os.environ.get("OCR_EVAL_MARK", "0") == "1"
    use_actual = mark_enabled and ('actual_result' in df.columns)

    if use_actual:
        subdirs = ['correct', 'false_detection', 'missed_detection', 'missed_false']
        for sd in subdirs:
            ensure_dir(os.path.join(out_root, sd))
        copied = 0
        for _, row in df.iterrows():
            img_name = str(row.get(img_col, '')).strip()
            if not img_name or os.path.splitext(str(img_name))[-1].lower() not in valid_exts:
                continue
            result = str(row.get('actual_result', '')).strip()
            src = image_name_to_path.get(img_name) or image_name_to_path.get(os.path.basename(img_name))
            if not src or not os.path.exists(src):
                LOGGER.warning("未找到原始图片路径: %s", img_name)
                continue
            targets: List[str] = []
            if result == '正确':
                targets = ['correct']
            elif result == '误检':
                targets = ['false_detection', 'missed_false']
            elif result == '漏检':
                targets = ['missed_detection', 'missed_false']
            else:
                continue
            for t in targets:
                dst = os.path.join(out_root, t, os.path.basename(img_name))
                try:
                    shutil.copy2(src, dst)
                    copied += 1
                except Exception as e:
                    LOGGER.error("复制失败: %s -> %s - %s", src, dst, e)
        LOGGER.info("复制完成：%d 个文件 -> %s", copied, os.path.abspath(out_root))
        return

    # fallback: 按命中复制到 hit/miss
    ensure_dir(os.path.join(out_root, 'hit'))
    ensure_dir(os.path.join(out_root, 'miss'))

    def _true_like(v: Any) -> bool:
        s = str(v).strip().lower()
        return s in ('true', '1', 'yes', 'y', 't')

    def _has_text(v: Any) -> bool:
        s = str(v).strip().lower()
        return s != '' and s != 'nan'

    copied = 0
    for _, row in df.iterrows():
        img_name = str(row.get(img_col, '')).strip()
        if not img_name or os.path.splitext(str(img_name))[-1].lower() not in valid_exts:
            continue
        hit_raw = row.get('hit', '')
        is_hit = _true_like(hit_raw) or _has_text(row.get('texts', ''))
        src = image_name_to_path.get(img_name) or image_name_to_path.get(os.path.basename(img_name))
        if not src or not os.path.exists(src):
            LOGGER.warning("未找到原始图片路径: %s", img_name)
            continue
        tdir = 'hit' if is_hit else 'miss'
        dst = os.path.join(out_root, tdir, os.path.basename(img_name))
        try:
            shutil.copy2(src, dst)
            copied += 1
        except Exception as e:
            LOGGER.error("复制失败: %s -> %s - %s", src, dst, e)
    LOGGER.info("复制完成：%d 个文件 -> %s", copied, os.path.abspath(out_root))


def main() -> None:
    # 使用环境变量控制：OCR_EVAL_MARK=1 开启标注；OCR_EVAL_SUMMARY=1 开启统计
    mark_enable = os.environ.get("OCR_EVAL_MARK", "0") == "1"
    summary_enable = os.environ.get("OCR_EVAL_SUMMARY", "0") == "1"

    root = repo_root()

    # 目标扫描目录（无需传参）
    scan_dirs = [
        # os.path.join(root, 'wfgame-ai-server', 'media', 'ocr', 'repositories', 'ocr_param'), # 1
        # os.path.join(root, 'wfgame-ai-server', 'media', 'ocr', 'repositories', 'ocr_test'),  # 27张
        # os.path.join(root, 'wfgame-ai-server', 'media', 'ocr', 'repositories', 'ocr_mix'), # 233 +5+38=276张 error
        os.path.join(root, 'wfgame-ai-server', 'media', 'ocr', 'repositories', 'ocr_hit'), # 1141
    ]

# 初始化 OCR（与项目当前参数理念保持一致，后续如需调参可修改此处）
    # 独立运行常量：内置模型名，避免外部依赖
    det_model_name = 'PP-OCRv5_server_det'
    rec_model_name = 'PP-OCRv5_server_rec'

    base_init_kwargs = dict(
        device='gpu', 
        lang='ch', 
        ocr_version='PP-OCRv5',
        text_detection_model_name=det_model_name,
        text_recognition_model_name=rec_model_name,
        use_doc_orientation_classify=False,
        use_textline_orientation=False,
        
        # 版本1:放宽阈值策略，从第一轮开始放宽误检率，从而快速收敛正确率和漏检率。正确100张,误检54张,漏检33张
        # use_doc_unwarping=False,
        # text_det_limit_type='min', 
        # text_det_limit_side_len=720,
        # text_det_thresh=0.3,
        # text_det_box_thresh=0.5,
        # text_det_unclip_ratio=3.3,
        # text_rec_score_thresh=0.5,
        
        # 版本1.1（对误54+漏33=87）结果：正确=25 误检=32 漏检=8
        # use_doc_unwarping=False,
        # text_det_limit_type='max', 
        # text_det_limit_side_len=960,
        # text_det_thresh=0.3,
        # text_det_box_thresh=0.5,
        # text_det_unclip_ratio=3.3,
        # text_rec_score_thresh=0.1,
        
        # 版本1.2（对误32+漏8=40）结果：正确=7 误检=21 漏检=1
        # use_doc_unwarping=False,
        # text_det_limit_type='min', 
        # text_det_limit_side_len=960,
        # text_det_thresh=0.4,
        # text_det_box_thresh=0.6,
        # text_det_unclip_ratio=2,
        # text_rec_score_thresh=0.15,
        
        
        # 第一轮检测：提高阈值，从第一轮开始收紧误检率。预计正确率会缓慢上升，漏检率会缓慢下降。
        # 输入：ocr_hit
        # 目的：通用标准参数，用于快速收敛正确率和误检率。
        # 正确=61/133 误检=4 漏检=72
        # 输出：ocr_eval_copy_eval_summary_20250911_174311
        # use_doc_unwarping=False,
        # text_det_limit_type='min', 
        # text_det_limit_side_len=720,
        # text_det_thresh=0.3,
        # text_det_box_thresh=0.5,
        # text_det_unclip_ratio=3.3,
        # text_rec_score_thresh=0.8,
        
        #第二轮检测：
        # 输出：ocr_eval_copy_eval_summary_20250911_174311/missed_false
        # 设计目的：解决正方形、长方形图片，文字方正，占比较高的标准图片漏检问题。
        # 正确=36/132 误检=0 漏检=35
        # 输出：ocr_eval_copy_eval_summary_20250911_180257
        # use_doc_unwarping=False,
        # text_det_limit_type='max', 
        # text_det_limit_side_len=960,
        # text_det_thresh=0.3,
        # text_det_box_thresh=0.6,
        # text_det_unclip_ratio=2,
        # text_rec_score_thresh=0.6,
        
        #第三轮检测：
        # 输入：ocr_eval_copy_eval_summary_20250911_180257/missed_false
        # 设计目的：解决宽高比例超过2:1的图片（长条图）的扭曲，文字严重倾斜，占比较高的标准图片漏检问题。
        # 正确=33/132 误检=0 漏检=2
        # 输出：ocr_eval_copy_eval_summary_20250911_185727/missed_false
        # use_doc_unwarping=True,
        # text_det_limit_type='min', 
        # text_det_limit_side_len=1280,
        # text_det_thresh=0.3,
        # text_det_box_thresh=0.6,
        # text_det_unclip_ratio=2,
        # text_rec_score_thresh=0.16,
        
        # 第四轮检测：
        # 设计目的：解决宽高比超过1:2的图片（高条图）的扭曲，文字贴近4边（易被裁掉），文字严重倾斜，文字极小，非常模糊的图片漏检问题。
        # 解决文字极小，非常模糊的图片漏检问题。
        # 正确=2/2 误检=0 漏检=0
        # use_doc_unwarping=False,
        # text_det_limit_type='min', 
        # text_det_limit_side_len=1280,
        # text_det_thresh=0.25,
        # text_det_box_thresh=0.45,
        # text_det_unclip_ratio=2,
        # text_rec_score_thresh=0.2,
        
        #第五轮检测：
        # 解决文字极小，非常模糊的图片漏检问题。
        
        # 正确=/132 误检= 漏检=
        
        #第六轮检测：
        # 设计目的：解决特殊艺术字：背景噪音极大、笔迹潦草、狂草、大篆、象形文字、书法字、私人印章等图片漏检问题。
        # 正确=/132 误检= 漏检=

        
    )

    ocr = PaddleOCR(**base_init_kwargs)
    OCR_INIT_PARAMS_BY_ID[id(ocr)] = dict(base_init_kwargs)
    # 动态分流实例池（避免同一实例内参数变更不生效的情况）
    ocr_pool: Dict[str, PaddleOCR] = {'balanced': ocr}
    printed_routes: Dict[str, bool] = {}

    def get_ocr_for_params(params: Dict[str, float]) -> "PaddleOCR":
        tag = params.get('tag', 'balanced')
        if tag in ocr_pool:
            if DEBUG_EVAL and not printed_routes.get(tag):
                log_pipeline_overview(tag, params)
                printed_routes[tag] = True
            return ocr_pool[tag]
        # 基础构造参数
        kwargs = make_init_from_active(base_init_kwargs, params)
        inst = PaddleOCR(**kwargs)
        OCR_INIT_PARAMS_BY_ID[id(inst)] = dict(kwargs)
        # 再次强制应用关键阈值，确保生效
        det_args = _resolve_effective_thresholds(params, kwargs, base_init_kwargs)
        apply_params_to_ocr(
            inst,
            det_args[0], det_args[1], det_args[2], det_args[3], det_args[4],
            det_args[5]
        )
        ocr_pool[tag] = inst
        if DEBUG_EVAL and not printed_routes.get(tag):
            log_pipeline_overview(tag, params)
            printed_routes[tag] = True
        return inst

    # 清空项目根 output 目录，并准备子目录 output/ocr_eval
    project_output = os.path.join(root, 'output')
    
    out_dir = os.path.join(project_output, 'ocr_eval')
    clear_dir(out_dir)
    ensure_dir(out_dir)

    LOGGER.info("输出目录: %s", os.path.abspath(out_dir))

    # 扫描图片
    exts = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
    images: List[str] = []
    for d in scan_dirs:
        if not os.path.exists(d):
            continue
        for n in sorted(os.listdir(d)):
            p = os.path.join(d, n)
            if os.path.isfile(p) and os.path.splitext(n)[1].lower() in exts:
                images.append(p)
    LOGGER.info("扫描目录: %s", "; ".join([os.path.abspath(x) for x in scan_dirs]))
    LOGGER.info("发现图片数量: %d", len(images))
    if not images:
        LOGGER.error("未检测到待处理图片。请将图片放入上述目录后重试。")
        return

    

    # 系统中文字体路径
    font_path = find_chinese_font_path_from_system()
    if not font_path and PIL_AVAILABLE:
        LOGGER.warning("未找到系统中文字体，可能导致图片中文标注显示异常。")

    # 统一命名前缀
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    base_name = f'eval_summary_{ts}'

    # 预先声明尺寸采集列表与数据行，供后续预分流/统计/Excel导出
    image_sizes_rows: List[Dict[str, Any]] = []
    data_rows: List[Dict[str, Any]] = []

    saved_count = 0
    for idx, img_path in enumerate(images, start=1):
        LOGGER.info("[%d/%d] 处理: %s", idx, len(images), os.path.abspath(img_path))
        try:
            img = read_img(img_path)
        except Exception as e:
            LOGGER.error("读取失败: %s - %s", img_path, e)
            continue

        # 分辨率
        h, w = (img.shape[0], img.shape[1]) if img is not None else (0, 0)
        resolution_str = f"{w}x{h}"
        # 记录尺寸行数据（供后续统计）
        try:
            image_sizes_rows.append({
                'image': os.path.basename(img_path),
                'width': int(w),
                'height': int(h),
                'min_side': int(min(w, h)),
                'max_side': int(max(w, h)),
                'area': int(w) * int(h),
            })
        except Exception:
            pass

        # 禁用基线识别：不进行OCR预测，仅记录基本信息，texts/scores占位为空
        scaled_resolution_str = resolution_str
        try:
            data_rows.append({
                'image': os.path.basename(img_path),
                'resolution': resolution_str,
                'scaled_resolution': scaled_resolution_str,
                'num_items': 0,
                'scores': '',
                'route': 'rounds_pending',
                'use_doc_orientation_classify': 'False',
                'use_doc_unwarping': 'False',
                'use_textline_orientation': 'False',
                'det_limit_type': '',
                'det_limit_side_len': '',
                'det_thresh': '',
                'box_thresh': '',
                'unclip_ratio': '',
                'rec_score_thresh': '',
                'texts': '',
            })
        except Exception as e:
            LOGGER.error("处理失败(保存/占位): %s - %s", img_path, e)
            continue

    LOGGER.info("成功保存可视化: %d/%d 张", saved_count, len(images))
    LOGGER.info("可视化目录: %s", os.path.abspath(out_dir))

    # 构建主数据DataFrame，供后续多轮写回与最终导出使用
    try:
        df_main = pd.DataFrame(data_rows)
    except Exception:
        df_main = pd.DataFrame()

    # 尺寸分布统计与Excel导出（与CSV同名）
    try:
        th_small_rec: Optional[int] = None
        small_images: List[str] = []
        rest_images: List[str] = []
        # 将主数据构造成 DataFrame（已在上方构建，此处不再重建）
        if 'image' in df_main.columns:
            pass
        if image_sizes_rows:
            df_sizes = pd.DataFrame(image_sizes_rows)
            # 统计分布：描述性统计与分位数
            desc = df_sizes[['min_side', 'max_side', 'width', 'height', 'area']].describe()
            pcts = df_sizes['min_side'].quantile([0.5, 0.75, 0.9, 0.95, 0.99]).rename('quantile')
            th_small_rec = int(max(1, int(round(float(pcts.loc[0.95]) / 10.0) * 10))) if 0.95 in pcts.index else int(max(1, int(round(float(pcts.iloc[-1]) / 10.0) * 10)))
            # 分箱：按短边与长边分组
            bins_min = [0, 80, 100, 120, 140, 160, 180, 200, 240, 320, 480, 720, 960, 1280, 1600, np.inf]
            labels_min = [
                '0-80','80-100','100-120','120-140','140-160','160-180','180-200',
                '200-240','240-320','320-480','480-720','720-960','960-1280','1280-1600','1600+'
            ]
            df_sizes['min_side_bin'] = pd.cut(df_sizes['min_side'], bins=bins_min, labels=labels_min, right=False)
            bin_min_counts = df_sizes['min_side_bin'].value_counts().sort_index().rename('count').reset_index().rename(columns={'index': 'min_side_bin'})
            # max_side 分箱
            bins_max = [0, 160, 200, 240, 320, 480, 640, 720, 960, 1280, 1600, 1920, 2560, 3000, 4000, np.inf]
            labels_max = [
                '0-160','160-200','200-240','240-320','320-480','480-640','640-720','720-960',
                '960-1280','1280-1600','1600-1920','1920-2560','2560-3000','3000-4000','4000+'
            ]
            df_sizes['max_side_bin'] = pd.cut(df_sizes['max_side'], bins=bins_max, labels=labels_max, right=False)
            bin_max_counts = df_sizes['max_side_bin'].value_counts().sort_index().rename('count').reset_index().rename(columns={'index': 'max_side_bin'})
        else:
            LOGGER.info("未采集到尺寸数据，跳过尺寸分布导出与预分流。")
    except Exception as e:
        LOGGER.error("尺寸分布统计失败: %s", e)

    # 可选：目录标注 + 统计（使用固定目录与映射）
    if mark_enable and os.environ.get("OCR_EVAL_WRITE_RESULTS", "0") == "1":
        labels_map_str = ",".join([f"{k}={v}" for k, v in _MARK_SUB_DIRS.items()])
        if not os.path.isdir(_MARK_BASE_DIR):
            LOGGER.error("标注跳过：基准目录不存在: %s", _MARK_BASE_DIR)
            stats = {}
        else:
            try:
                stats = post_mark_csv(
                    csv_path=csv_path,
                    base_dir=_MARK_BASE_DIR,
                    labels_map_str=labels_map_str,
                    image_col='image',
                    read_encoding='auto',
                    write_encoding='utf-8-sig',
                )
            except Exception as e:
                LOGGER.error("标注失败: %s", e)
                stats = {}
 
         # 新增 actual_result 并打印统计
        try:
             actual_stats = add_actual_result_and_summarize(
                 csv_path=csv_path,
                 write_encoding='utf-8-sig'
             )
        except Exception as e:
             LOGGER.error("生成 actual_result 失败: %s", e)
             actual_stats = {}

        if summary_enable:
            # 旧 result 统计（保留输出，便于对比）
            total_rows = 0
            try:
                df_tmp = _read_csv_robust(csv_path, encoding='auto')
                total_rows = int(df_tmp.shape[0])
            except Exception:
                pass
            correct = int(stats.get('正确', 0))
            false_det = int(stats.get('误检', 0))
            missed = int(stats.get('漏检', 0))
            matched = sum(v for k, v in stats.items() if k)
            unmatched = max(0, total_rows - matched) if total_rows else 0

            def _p(n: int) -> str:
                if total_rows <= 0:
                    return "0.00%"
                return f"{(n / float(total_rows)) * 100.0:.2f}%"

            LOGGER.error(
                "预期-标注统计(result): 总计=%d 正确=%d(%s) 误检=%d(%s) 漏检=%d(%s) 未匹配=%d(%s)",
                total_rows, correct, _p(correct), false_det, _p(false_det),
                missed, _p(missed), unmatched, _p(unmatched)
            )

            # actual_result 统计输出
            ar_correct = int(actual_stats.get('正确', 0))
            ar_false = int(actual_stats.get('误检', 0))
            ar_missed = int(actual_stats.get('漏检', 0))
            LOGGER.error(
                "实际-标注统计(actual_result): 正确=%d 误检=%d 漏检=%d",
                ar_correct, ar_false, ar_missed
            )

    # 复制图片延后到多轮规范化之后执行（若未启用多轮则在最终导出前执行）
    _pending_copy = os.environ.get("OCR_EVAL_COPY", "0") == "1"

    # 多轮参数迭代（命中/未命中分拣）
    if os.environ.get("OCR_EVAL_ROUNDS", "0") == "1":
        try:
            # 初始输入集：若预分流存在，第一轮来自 small_images，否则使用 images
            if 'small_images' in locals() and small_images:
                cur_inputs = list(small_images)
                LOGGER.error("多轮迭代：启用预分流，第一轮输入=小图 %d 张", len(cur_inputs))
            else:
                cur_inputs = list(images)
                LOGGER.error("多轮迭代：未启用预分流，第一轮输入=%d 张", len(cur_inputs))
            if not cur_inputs:
                LOGGER.error("多轮迭代：未发现初始图片，已跳过。")
                return

            rounds = _round_param_sets()

            # 本次运行唯一根目录
            rounds_root = os.path.join(project_output, f"rounds_{base_name}")
            ensure_dir(rounds_root)
            # 合并输出目录，仅保留两个
            hit_root = os.path.join(rounds_root, 'hit')
            miss_root = os.path.join(rounds_root, 'miss')
            ensure_dir(hit_root)
            ensure_dir(miss_root)

            # 以参数签名缓存 OCR 实例，避免重复构建
            ocr_by_sig: Dict[str, "PaddleOCR"] = {}
            # 记录首次命中轮次与参数
            first_hit_info: Dict[str, Dict[str, Any]] = {}
            total_hit = 0
            last_miss_count = 0

            for ridx, params in enumerate(rounds, start=1):
                if not cur_inputs:
                    LOGGER.error("多轮迭代：第%d轮无输入，提前结束。", ridx)
                    break

                LOGGER.error("多轮迭代：第%d轮开始，输入张数=%d", ridx, len(cur_inputs))

                # 合成 OCR 初始化参数（含去畸变覆盖）
                init_kwargs_round = _apply_doc_unwarp_flag(base_init_kwargs, params.get('use_doc_unwarping', False))
                kwargs_for_sig = make_init_from_active(init_kwargs_round, params)
                sig = json.dumps(kwargs_for_sig, sort_keys=True)
                if sig in ocr_by_sig:
                    ocr_used = ocr_by_sig[sig]
                    try:
                        det_args = _resolve_effective_thresholds(params, kwargs_for_sig, base_init_kwargs)
                        apply_params_to_ocr(
                            ocr_used,
                            det_args[0], det_args[1], det_args[2], det_args[3], det_args[4], det_args[5]
                        )
                    except Exception as ap_err:
                        LOGGER.warning("多轮迭代：应用参数失败，使用默认值继续 - %s", ap_err)
                else:
                    ocr_used = PaddleOCR(**kwargs_for_sig)
                    # 强制应用关键阈值（带回退，避免 None）
                    try:
                        det_args = _resolve_effective_thresholds(params, kwargs_for_sig, base_init_kwargs)
                        apply_params_to_ocr(
                            ocr_used,
                            det_args[0], det_args[1], det_args[2], det_args[3], det_args[4], det_args[5]
                        )
                    except Exception as ap_err:
                        LOGGER.warning("多轮迭代：应用参数失败，使用默认值继续 - %s", ap_err)
                    ocr_by_sig[sig] = ocr_used

                # 执行本轮预测并分拣
                hit_paths: List[str] = []
                miss_paths: List[str] = []

                for p in cur_inputs:
                    try:
                        img = read_img(p)
                        res = ocr_used.predict([img])
                        items = parse_predict(res)
                        items_kept = filter_chinese_items_configurable(items) if CH_ONLY else items
                        ok = len(items_kept) > 0
                        (hit_paths if ok else miss_paths).append(p)
                        # 若命中且首次命中，记录命中时scores/texts与scaled_resolution
                        if ok:
                            name = os.path.basename(p)
                            if name not in first_hit_info:
                                try:
                                    det_args_tmp = _resolve_effective_thresholds(params, kwargs_for_sig, base_init_kwargs)
                                    lt_tmp, side_tmp = det_args_tmp[0], int(det_args_tmp[1])
                                    h_tmp, w_tmp = (img.shape[0], img.shape[1]) if img is not None else (0, 0)
                                    sw, sh = compute_scaled_resolution(h_tmp, w_tmp, str(lt_tmp), int(side_tmp))
                                    texts_str = "|".join([str(t) for (_, t, _) in items_kept])
                                    scores_str = "|".join([f"{float(s):.4f}" for (_, _, s) in items_kept])
                                    first_hit_info[name] = {
                                        'round': ridx,
                                        'det_limit_type': det_args_tmp[0],
                                        'det_limit_side_len': det_args_tmp[1],
                                        'det_thresh': det_args_tmp[2],
                                        'box_thresh': det_args_tmp[3],
                                        'unclip_ratio': det_args_tmp[4],
                                        'rec_score_thresh': det_args_tmp[5],
                                        'use_doc_unwarping': bool(params.get('use_doc_unwarping', False)),
                                        'hit_texts': texts_str,
                                        'hit_scores': scores_str,
                                        'scaled_resolution': f"{sw}x{sh}",
                                    }
                                except Exception:
                                    pass
                    except Exception as e:
                        LOGGER.error("多轮迭代：预测失败 %s - %s", p, e)
                        miss_paths.append(p)

                # 合并复制到 hit/miss 根目录
                def _copy_many(paths: List[str], dst_dir: str) -> int:
                    n = 0
                    for sp in paths:
                        try:
                            shutil.copy2(sp, os.path.join(dst_dir, os.path.basename(sp)))
                            n += 1
                        except Exception as ce:
                            LOGGER.error("复制失败: %s -> %s - %s", sp, dst_dir, ce)
                    return n

                nh = _copy_many(hit_paths, hit_root)
                # miss 不在每轮落盘，循环结束后一次性写入最终 miss
                total_hit += nh
                last_miss_count = len(miss_paths)
                LOGGER.error("多轮迭代：第%d轮结束，hit=%d miss=%d 输出目录=%s", ridx, nh, len(miss_paths), rounds_root)

                # 下一轮输入：第1轮后合并 rest_images；之后沿用 miss
                if ridx == 1 and 'rest_images' in locals() and rest_images:
                    cur_inputs = list(set(miss_paths) | set(rest_images))
                else:
                    cur_inputs = list(miss_paths)

            # 所有轮次完成后打印汇总
            LOGGER.error("多轮迭代：全部完成，总命中=%d 最终未命中=%d 输出根目录=%s", total_hit, last_miss_count, rounds_root)

            # 将命中轮次与命中参数写回主DataFrame
            try:
                if 'hit_round' not in df_main.columns:
                    df_main['hit_round'] = ''
                img_col = 'image' if 'image' in df_main.columns else df_main.columns[0]
                for i, row in df_main.iterrows():
                    name = str(row.get(img_col, '')).strip()
                    info = first_hit_info.get(os.path.basename(name))
                    if not info:
                        continue
                    if 'hit_scores' in info and info['hit_scores']:
                        df_main.at[i, 'scores'] = str(info['hit_scores'])
                    if 'hit_texts' in info and info['hit_texts']:
                        df_main.at[i, 'texts'] = str(info['hit_texts'])
                    if 'scaled_resolution' in info and info['scaled_resolution']:
                        df_main.at[i, 'scaled_resolution'] = str(info['scaled_resolution'])
                    df_main.at[i, 'hit_round'] = int(info['round'])
                    df_main.at[i, 'det_limit_type'] = str(info['det_limit_type'])
                    df_main.at[i, 'det_limit_side_len'] = int(info['det_limit_side_len'])
                    df_main.at[i, 'det_thresh'] = float(info['det_thresh'])
                    df_main.at[i, 'box_thresh'] = float(info['box_thresh'])
                    df_main.at[i, 'unclip_ratio'] = float(info['unclip_ratio'])
                    df_main.at[i, 'rec_score_thresh'] = float(info['rec_score_thresh'])
                    df_main.at[i, 'use_doc_unwarping'] = str(bool(info['use_doc_unwarping']))
            except Exception as e:
                LOGGER.error("写回命中轮次与参数失败: %s", e)

            # 最终未命中图片复制到 miss_root
            try:
                final_miss_paths: List[str] = list(cur_inputs)
                def _copy_many(paths: List[str], dst_dir: str) -> int:
                    n = 0
                    for sp in paths:
                        try:
                            shutil.copy2(sp, os.path.join(dst_dir, os.path.basename(sp)))
                            n += 1
                        except Exception as ce:
                            LOGGER.error("复制失败: %s -> %s - %s", sp, dst_dir, ce)
                    return n
                copied_miss = _copy_many(final_miss_paths, miss_root)
                LOGGER.info("最终未命中已复制: %d -> %s", copied_miss, miss_root)
            except Exception as e:
                LOGGER.error("复制最终未命中失败: %s", e)
        except Exception as e:
            LOGGER.error("多轮迭代流程失败: %s", e)

    # 最终导出Excel（使用更新后的 df_main），覆盖早期版本
    try:
        # 尺寸统计（若未构建则基于 image_sizes_rows 现算）
        if 'df_main' not in locals() or df_main is None:
            df_main = pd.DataFrame(data_rows) if 'data_rows' in locals() else pd.DataFrame()
        if 'image_sizes_rows' in locals() and image_sizes_rows:
            df_sizes = pd.DataFrame(image_sizes_rows)
            desc = df_sizes[['min_side', 'max_side', 'width', 'height', 'area']].describe()
            pcts = df_sizes['min_side'].quantile([0.5, 0.75, 0.9, 0.95, 0.99]).rename('quantile')
            bins_min = [0, 80, 100, 120, 140, 160, 180, 200, 240, 320, 480, 720, 960, 1280, 1600, np.inf]
            labels_min = [
                '0-80','80-100','100-120','120-140','140-160','160-180','180-200',
                '200-240','240-320','320-480','480-720','720-960','960-1280','1280-1600','1600+'
            ]
            df_sizes['min_side_bin'] = pd.cut(df_sizes['min_side'], bins=bins_min, labels=labels_min, right=False)
            bin_min_counts = df_sizes['min_side_bin'].value_counts().sort_index().rename('count').reset_index().rename(columns={'index': 'min_side_bin'})
            bins_max = [0, 160, 200, 240, 320, 480, 640, 720, 960, 1280, 1600, 1920, 2560, 3000, 4000, np.inf]
            labels_max = [
                '0-160','160-200','200-240','240-320','320-480','480-640','640-720','720-960',
                '960-1280','1280-1600','1600-1920','1920-2560','2560-3000','3000-4000','4000+'
            ]
            df_sizes['max_side_bin'] = pd.cut(df_sizes['max_side'], bins=bins_max, labels=labels_max, right=False)
            bin_max_counts = df_sizes['max_side_bin'].value_counts().sort_index().rename('count').reset_index().rename(columns={'index': 'max_side_bin'})
        else:
            df_sizes = pd.DataFrame()
            desc = pd.DataFrame()
            pcts = pd.Series(dtype=float)
            bin_min_counts = pd.DataFrame()
            bin_max_counts = pd.DataFrame()

        xlsx_path = os.path.join(project_output, f"{base_name}.xlsx")
        try:
            with pd.ExcelWriter(xlsx_path, engine='openpyxl') as xw:
                df_main.to_excel(xw, sheet_name='data', index=False)
                if not df_sizes.empty:
                    summary_rows = [
                        {'metric': 'total_images', 'value': int(df_sizes.shape[0])},
                        {'metric': 'unique_images', 'value': int(df_sizes['image'].nunique())},
                        {'metric': 'p50_min_side', 'value': float(pcts.loc[0.5]) if 0.5 in pcts.index else None},
                        {'metric': 'p75_min_side', 'value': float(pcts.loc[0.75]) if 0.75 in pcts.index else None},
                        {'metric': 'p90_min_side', 'value': float(pcts.loc[0.9]) if 0.9 in pcts.index else None},
                        {'metric': 'p95_min_side', 'value': float(pcts.loc[0.95]) if 0.95 in pcts.index else None},
                        {'metric': 'p99_min_side', 'value': float(pcts.loc[0.99]) if 0.99 in pcts.index else None},
                    ]
                    pd.DataFrame(summary_rows).to_excel(xw, sheet_name='summary', index=False)
                    if not desc.empty:
                        desc.reset_index().rename(columns={'index': 'stat'}).to_excel(xw, sheet_name='size_stats', index=False)
                    if not bin_min_counts.empty:
                        bin_min_counts.to_excel(xw, sheet_name='size_bins_min', index=False)
                    if not bin_max_counts.empty:
                        bin_max_counts.to_excel(xw, sheet_name='size_bins_max', index=False)
        except Exception:
            with pd.ExcelWriter(xlsx_path, engine='xlsxwriter') as xw:
                df_main.to_excel(xw, sheet_name='data', index=False)
                if not df_sizes.empty:
                    summary_rows = [
                        {'metric': 'total_images', 'value': int(df_sizes.shape[0])},
                        {'metric': 'unique_images', 'value': int(df_sizes['image'].nunique())},
                        {'metric': 'p50_min_side', 'value': float(pcts.loc[0.5]) if 0.5 in pcts.index else None},
                        {'metric': 'p75_min_side', 'value': float(pcts.loc[0.75]) if 0.75 in pcts.index else None},
                        {'metric': 'p90_min_side', 'value': float(pcts.loc[0.9]) if 0.9 in pcts.index else None},
                        {'metric': 'p95_min_side', 'value': float(pcts.loc[0.95]) if 0.95 in pcts.index else None},
                        {'metric': 'p99_min_side', 'value': float(pcts.loc[0.99]) if 0.99 in pcts.index else None},
                    ]
                    pd.DataFrame(summary_rows).to_excel(xw, sheet_name='summary', index=False)
                    if not desc.empty:
                        desc.reset_index().rename(columns={'index': 'stat'}).to_excel(xw, sheet_name='size_stats', index=False)
                    if not bin_min_counts.empty:
                        bin_min_counts.to_excel(xw, sheet_name='size_bins_min', index=False)
                    if not bin_max_counts.empty:
                        bin_max_counts.to_excel(xw, sheet_name='size_bins_max', index=False)
        LOGGER.info("最终Excel已导出: %s", os.path.abspath(xlsx_path))
    except Exception as e:
        LOGGER.error("最终Excel导出失败: %s", e)


def make_active_from_init(init_kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """从初始化参数中抽取 active 参数字典（仅与流水相关的字段）。"""
    return {
        'det_limit_type': init_kwargs.get('text_det_limit_type'),
        'det_limit_side_len': init_kwargs.get('text_det_limit_side_len'),
        'det_thresh': init_kwargs.get('text_det_thresh'),
        'box_thresh': init_kwargs.get('text_det_box_thresh'),
        'unclip_ratio': init_kwargs.get('text_det_unclip_ratio'),
        'rec_score_thresh': init_kwargs.get('text_rec_score_thresh'),
        'use_textline_orientation': init_kwargs.get('use_textline_orientation', False),
        'tag': 'from_init',
    }

def make_init_from_active(base_init: Dict[str, Any], active: Dict[str, Any]) -> Dict[str, Any]:
    """基于 base_init 覆盖构造新的实例化参数字典。"""
    merged = dict(base_init)
    merged.update({
        'text_det_limit_type': active.get('det_limit_type'),
        'text_det_limit_side_len': active.get('det_limit_side_len'),
        'text_det_thresh': active.get('det_thresh'),
        'text_det_box_thresh': active.get('box_thresh'),
        'text_det_unclip_ratio': active.get('unclip_ratio'),
        'text_rec_score_thresh': active.get('rec_score_thresh'),
        'use_textline_orientation': active.get('use_textline_orientation', False),
    })
    return merged


def _list_images_in_dirs(dirs: List[str]) -> List[str]:
    """扫描多个目录下的图片文件路径列表。"""
    exts = {'.jpg', '.png'}
    out: List[str] = []
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for n in sorted(os.listdir(d)):
            p = os.path.join(d, n)
            if os.path.isfile(p) and os.path.splitext(n)[1].lower() in exts:
                out.append(p)
    return out


def _round_param_sets() -> List[Dict[str, Any]]:
    """返回4套按顺序执行的参数(仅与流水相关字段)。"""
    '''
    1. 先集中处理小图，因为小图非常容易误检，所以需要先集中处理
    2. 再处理方正规整图，因为方正规整图的误检率较低，所以可以放到最后处理
    3. 最后处理长条扭曲图，因为长条扭曲图的误检率较高，所以需要放到最后处理
    4. 最后处理高条/边缘贴近图，因为高条/边缘贴近图的误检率较高，所以需要放到最后处理
    '''
    return [
        # 第一轮：收紧误检率（min/720，较高rec阈值）
        {
            'det_limit_type': 'min',
            'det_limit_side_len': 680,
            'det_thresh': 0.3,
            'box_thresh': 0.6,
            'unclip_ratio': 1.5,
            'rec_score_thresh': 0.8,
            'use_textline_orientation': False,
            'use_doc_unwarping': False,
        },
        # 第二轮：方正规整图，极多小图非常容易误检，可考虑放到最后处理（max/960，中等阈值）
        {
            'det_limit_type': 'max',
            'det_limit_side_len': 960,
            'det_thresh': 0.3,
            'box_thresh': 0.6,
            'unclip_ratio': 2.0,
            'rec_score_thresh': 0.8,
            'use_textline_orientation': False,
            'use_doc_unwarping': False,
        },
        # 第三轮：长条扭曲（min/1280，开启去畸变，低rec阈值）
        {
            'det_limit_type': 'min',
            'det_limit_side_len': 1280,
            'det_thresh': 0.3,
            'box_thresh': 0.6,
            'unclip_ratio': 2.0,
            'rec_score_thresh': 0.6,
            'use_textline_orientation': False,
            'use_doc_unwarping': True,
        },
        # 第四轮：高条/边缘贴近（min/1280，适度放宽det阈值）
        {
            'det_limit_type': 'min',
            'det_limit_side_len': 1280,
            'det_thresh': 0.25,
            'box_thresh': 0.45,
            'unclip_ratio': 2.0,
            'rec_score_thresh': 0.8,
            'use_textline_orientation': False,
            'use_doc_unwarping': False,
        },
    ]


def _apply_doc_unwarp_flag(base_init: Dict[str, Any], use_doc_unwarping: bool) -> Dict[str, Any]:
    """在初始化参数上覆盖 use_doc_unwarping。"""
    merged = dict(base_init)
    merged['use_doc_unwarping'] = bool(use_doc_unwarping)
    return merged


def _resolve_effective_thresholds(params: Dict[str, Any],
                                  kwargs_for_sig: Dict[str, Any],
                                  base_init: Dict[str, Any]) -> Tuple[str, int, float, float, float, float]:
    """解析并回退阈值参数，返回六元组供 apply_params_to_ocr 使用。"""
    det_limit_type_val = (
        params.get('det_limit_type')
        or kwargs_for_sig.get('text_det_limit_type')
        or base_init.get('text_det_limit_type')
        or 'min'
    )
    det_limit_side_len_val = (
        params.get('det_limit_side_len')
        or kwargs_for_sig.get('text_det_limit_side_len')
        or base_init.get('text_det_limit_side_len')
        or 0
    )
    det_thresh_val = float(
        params.get('det_thresh')
        or kwargs_for_sig.get('text_det_thresh')
        or base_init.get('text_det_thresh')
        or 0.3
    )
    box_thresh_val = float(
        params.get('box_thresh')
        or kwargs_for_sig.get('text_det_box_thresh')
        or base_init.get('text_det_box_thresh')
        or 0.5
    )
    unclip_ratio_val = float(
        params.get('unclip_ratio')
        or kwargs_for_sig.get('text_det_unclip_ratio')
        or base_init.get('text_det_unclip_ratio')
        or 2.0
    )
    rec_score_thresh_val = float(
        params.get('rec_score_thresh')
        or kwargs_for_sig.get('text_rec_score_thresh')
        or base_init.get('text_rec_score_thresh')
        or 0.0
    )
    return (
        str(det_limit_type_val), int(det_limit_side_len_val), det_thresh_val,
        box_thresh_val, unclip_ratio_val, rec_score_thresh_val
    )


if __name__ == '__main__':
    main() 