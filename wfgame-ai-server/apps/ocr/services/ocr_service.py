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
    """基于 PP-OCRv5 的 OCR 服务（使用 PaddleOCR.predict 工作流）。

    说明:      
        处理顺序:
        1) 预处理阶段（由初始化开关控制是否启用）
           - 文档方向分类: use_doc_orientation_classify
           - 文档扭曲矫正: use_doc_unwarping
           - 文本行方向分类: use_textline_orientation
           - 检测前的缩放: 仅强制设置 limit_side_len（不写 limit_type，避免版本不兼容）
        2) 文本检测阶段（DB后处理阈值在此生效）
           - text_det_thresh、text_det_box_thresh、text_det_unclip_ratio
        3) 文本识别与结果过滤阶段
           - 识别后处理内部阈值: postprocess_op.score_thresh（若版本支持）
           - 结果层兜底过滤: text_rec_score_thresh（保证最高优先级）
    """

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
            
            # 为了保证相同输入在相同参数/模型下的结果尽可能一致，开启确定性设置
            # 1) cuDNN 确定性卷积（可能牺牲少量性能换取一致性）
            os.environ['FLAGS_cudnn_deterministic'] = '1'
            os.environ['FLAGS_cudnn_exhaustive_search'] = '0'
            # 2) 固定随机种子（Python/NumPy/Paddle）
            try:
                import random as _py_random
                _seed_val = 1234
                _py_random.seed(_seed_val)
                np.random.seed(_seed_val)
                try:
                    import paddle as _paddle
                    if hasattr(_paddle, 'seed'):
                        _paddle.seed(_seed_val)
                except Exception:
                    pass
                logger.warning("已启用确定性设置: FLAGS_cudnn_deterministic=1, 随机种子=1234")
            except Exception:
                pass

            # 核心OCR阈值与边长限制从配置读取（优先新参数名，旧名作为回退）
            # 检测后处理阈值
            text_det_thresh = config.getfloat(
                'ocr', 'text_det_thresh',
                fallback=config.getfloat('ocr', 'det_db_thresh', fallback=0.30)
            )
            text_det_box_thresh = config.getfloat(
                'ocr', 'text_det_box_thresh',
                fallback=config.getfloat('ocr', 'det_db_box_thresh', fallback=0.60)
            )
            text_det_unclip_ratio = config.getfloat(
                'ocr', 'text_det_unclip_ratio',
                fallback=config.getfloat('ocr', 'det_db_unclip_ratio', fallback=1.50)
            )
            # 检测预处理边长限制
            text_det_limit_type = config.get(
                'ocr', 'text_det_limit_type',
                fallback=config.get('ocr', 'det_limit_type', fallback='max')
            )

            text_det_limit_side_len = config.getint(
                'ocr', 'text_det_limit_side_len',
                fallback=config.getint('ocr', 'det_limit_side_len', fallback=736)
            )
            # 识别过滤阈值（优先官方字段名）
            try:
                text_rec_score_thresh = config.getfloat('ocr', 'text_rec_score_thresh')
            except Exception:
                text_rec_score_thresh = config.getfloat('ocr', 'rec_score_thresh', fallback=0.00)

            # 保存为实例属性（使用官方参数名），供后续强制写入与结果层过滤使用
            self.text_det_thresh = text_det_thresh
            self.text_det_box_thresh = text_det_box_thresh
            self.text_det_unclip_ratio = text_det_unclip_ratio
            self.text_det_limit_type = text_det_limit_type
            self.text_det_limit_side_len = text_det_limit_side_len
            self.text_rec_score_thresh = text_rec_score_thresh

            logger.warning(
                "应用OCR核心阈值参数: "
                f"text_det_thresh={text_det_thresh}, "
                f"text_det_box_thresh={text_det_box_thresh}, "
                f"text_det_unclip_ratio={text_det_unclip_ratio}, "
                f"text_det_limit_type={text_det_limit_type}, "
                f"text_det_limit_side_len={text_det_limit_side_len}, "
                f"text_rec_score_thresh={text_rec_score_thresh}"
            )

            # 初始化 PaddleOCR
            # 说明：以下三个开关用于控制“预测前的预处理阶段”是否启用
            # - use_doc_orientation_classify: 文档方向分类
            # - use_doc_unwarping: 文档扭曲矫正
            # - use_textline_orientation: 文本行方向分类
            # 它们在 self.ocr.predict() 调用之前由内部管线执行
            use_doc_orientation_classify = config.getboolean(
                'ocr', 'use_doc_orientation_classify', fallback=False
            )
            use_doc_unwarping = config.getboolean(
                'ocr', 'use_doc_unwarping', fallback=False
            )
            use_textline_orientation = config.getboolean(
                'ocr', 'use_textline_orientation', fallback=False
            )
            text_detection_model_name = config.get(
                'ocr', 'text_detection_model_name', fallback='PP-OCRv5_server_det'
            )
            text_recognition_model_name = config.get(
                'ocr', 'text_recognition_model_name', fallback='PP-OCRv5_server_rec'
            )

            logger.warning(
                "OCR初始化配置: "
                f"use_doc_orientation_classify={use_doc_orientation_classify}, "
                f"use_doc_unwarping={use_doc_unwarping}, "
                f"use_textline_orientation={use_textline_orientation}, "
                f"text_detection_model_name={text_detection_model_name}, "
                f"text_recognition_model_name={text_recognition_model_name}"
            )

            init_kwargs = dict(
                device=device_arg,
                lang=self.lang,
                use_doc_orientation_classify=use_doc_orientation_classify,
                use_doc_unwarping=use_doc_unwarping,
                use_textline_orientation=use_textline_orientation,
                text_detection_model_name=text_detection_model_name,
                text_recognition_model_name=text_recognition_model_name,
            )

            # 严格仅传入官方支持且稳定的参数，避免启动报错
            # 优先尝试传入官方新参数；若当前安装版本不支持则回退最小参数集
            try:
                det_params_kwargs = dict(
                    text_det_thresh=text_det_thresh,
                    text_det_box_thresh=text_det_box_thresh,
                    text_det_unclip_ratio=text_det_unclip_ratio,
                    text_det_limit_side_len=text_det_limit_side_len,
                    text_rec_score_thresh=text_rec_score_thresh,
                )
                self.ocr = PaddleOCR(**{**init_kwargs, **det_params_kwargs})
                logger.warning(
                    "PaddleOCR初始化已接收核心参数(text_det_*, text_rec_score_thresh)"
                )
            except TypeError:
                # 回退：使用最小参数集初始化，后续强制写入子模块
                self.ocr = PaddleOCR(**init_kwargs)

        
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

    def recognize_image(self, image_path: str, predict_save: bool = False, task_id: Optional[str] = None) -> Dict:

        if not self.initialize():
            return {"error": "OCR引擎初始化失败"}

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

            # 调用 self.ocr.predict() 进入官方流水线，顺序如下：
            # 1) （可选）预处理: 方向/扭曲/文本行方向 + 检测缩放(limit_side_len)
            # 2) 文本检测: DB 后处理阈值(thresh/box_thresh/unclip_ratio)
            # 3) 文本识别: 识别 + （可选）内部 score_thresh 过滤
            # 4) 结果层兜底过滤: 再次按 text_rec_score_thresh 过滤，保证最高优先级
            #    注: 为兼容不同版本，内部与结果层双保险，不改变检测/识别主流程
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

            except Exception as persist_err:
                logger.debug(f"结果保存或解析失败: {persist_err}")

            try:
                if candidate_texts and candidate_scores and len(candidate_scores) == len(candidate_texts):
                    filtered_texts = []
                    filtered_scores = []
                    filtered_polys = []
                    for idx, t in enumerate(candidate_texts):
                        s = candidate_scores[idx] if idx < len(candidate_scores) else 1.0
                        if s is None:
                            s = 0.0
                        if s >= getattr(self, 'text_rec_score_thresh', 0.0):
                            filtered_texts.append(t)
                            filtered_scores.append(s)
                            if idx < len(candidate_polys):
                                filtered_polys.append(candidate_polys[idx])
                    candidate_texts = filtered_texts
                    candidate_scores = filtered_scores
                    candidate_polys = filtered_polys
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
                # 读取现有官方参数，分组输出
                score_thresh = float(getattr(self, 'text_rec_score_thresh', 0.0))
                det_thresh = float(getattr(self, 'text_det_thresh', config.getfloat('ocr', 'text_det_thresh', fallback=0.30)))
                det_box_thresh = float(getattr(self, 'text_det_box_thresh', config.getfloat('ocr', 'text_det_box_thresh', fallback=0.60)))
                det_unclip_ratio = float(getattr(self, 'text_det_unclip_ratio', config.getfloat('ocr', 'text_det_unclip_ratio', fallback=1.50)))
                det_limit_type = getattr(self, 'text_det_limit_type', config.get('ocr', 'text_det_limit_type', fallback='short'))
                det_limit_side_len = int(getattr(self, 'text_det_limit_side_len', config.getint('ocr', 'text_det_limit_side_len', fallback=736)))
                use_doc_orientation_classify = config.getboolean('ocr', 'use_doc_orientation_classify', fallback=False)
                use_doc_unwarping = config.getboolean('ocr', 'use_doc_unwarping', fallback=False)
                use_textline_orientation = config.getboolean('ocr', 'use_textline_orientation', fallback=False)
                text_detection_model_name = config.get('ocr', 'text_detection_model_name', fallback='PP-OCRv5_server_det')
                text_recognition_model_name = config.get('ocr', 'text_recognition_model_name', fallback='PP-OCRv5_server_rec')

                # 参数摘要（分组格式）
                param_summary = (
                    "当前过滤参数:\n"
                    f"- 核心阈值: text_rec_score_thresh={score_thresh}\n"
                    f"- 检测参数: text_det_thresh={det_thresh}, text_det_box_thresh={det_box_thresh}, text_det_unclip_ratio={det_unclip_ratio}\n"
                    f"- 检测尺寸: text_det_limit_type={det_limit_type}, text_det_limit_side_len={det_limit_side_len}\n"
                    f"- 文档与方向: use_doc_orientation_classify={use_doc_orientation_classify}, use_doc_unwarping={use_doc_unwarping}, use_textline_orientation={use_textline_orientation}\n"
                    f"- 模型: text_detection_model_name={text_detection_model_name}, text_recognition_model_name={text_recognition_model_name}\n"
                    f"- 输出: predict_save={predict_save}, candidates={len(candidate_texts)}\n"
                )
                # 追加内部实际参数摘要，便于对齐官方demo
                try:
                    internal_det = first_raw_debug.get('text_det_params') if isinstance(first_raw_debug, dict) else None
                    internal_ms = first_raw_debug.get('model_settings') if isinstance(first_raw_debug, dict) else None
                    internal_doc = first_raw_debug.get('doc_preprocessor_res') if isinstance(first_raw_debug, dict) else None
                    internal_angles = first_raw_debug.get('textline_orientation_angles') if isinstance(first_raw_debug, dict) else None
                    internal_summary = (
                        "内部实际参数(来自PaddleOCR返回):\n"
                        f"- text_det_params={internal_det}\n"
                        f"- model_settings={internal_ms}\n"
                        # f"- doc_preprocessor_res={internal_doc}\n"
                        f"- textline_orientation_angles={internal_angles}\n"
                    )
                except Exception:
                    internal_summary = "内部实际参数(来自PaddleOCR返回): <unavailable>\n"
                # 添加图片分辨率信息
                try:
                    img_height, img_width = image_nd.shape[:2] if image_nd is not None else (0, 0)
                    img_pixels = img_height * img_width
                    resolution_summary = f"图片分辨率: {img_width}x{img_height} (总像素: {img_pixels:,})\n"
                except Exception:
                    resolution_summary = "图片分辨率: <unavailable>\n"
                # 逐项输出（仅展示前若干项，避免日志过长）
                max_items = 50
                lines = []
                if not candidate_texts:
                    lines.append(
                        f"detector produced 0 boxes under: text_det_limit_type={det_limit_type}, text_det_limit_side_len={det_limit_side_len}, text_det_thresh={det_thresh}, text_det_box_thresh={det_box_thresh}, text_det_unclip_ratio={det_unclip_ratio}"
                    )
                else:
                    for i in range(min(len(candidate_texts), max_items)):
                        s = float(candidate_scores[i]) if i < len(candidate_scores) else 0.0
                        decision = "keep" if s >= score_thresh else "drop"
                        comparator = ">=" if decision == "keep" else "<"
                        reason = f"score({s:.3f}){comparator}text_rec_score_thresh({score_thresh})"
                        lines.append(
                            f"idx={i}, txt='{candidate_texts[i]}', score={s:.3f}, decision={decision}, reason={reason}"
                        )
                logger.warning(
                    header_line
                    + (f"\n[preprocess_retry]=True method={preprocess_retry_info}\n" if preprocess_retry_used else "\n")
                    + param_summary
                    + resolution_summary
                    + internal_summary
                    + "\n".join(lines)
                    + "\n"
                    + footer_line
                )
                if log_filter_debug_save and task_id:
                    try:
                        os.makedirs(logs_dir, exist_ok=True)
                        file_path = os.path.join(logs_dir, f"{task_id}.log")
                        with open(file_path, 'a', encoding='utf-8') as fp:
                            fp.write(header_line + "\n")
                            fp.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] image_name={image_name} image_path={image_path}\n")
                            fp.write((f"[preprocess_retry]=True method={preprocess_retry_info}\n" if preprocess_retry_used else ""))
                            fp.write(param_summary)
                            fp.write(resolution_summary)
                            fp.write(internal_summary)
                            for ln in lines:
                                fp.write(ln + "\n")
                            fp.write(footer_line + "\n\n")
                    except Exception as perr:
                        logger.error(f"保存调试日志失败: {perr}")

            
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
                return {
                    "image_path": image_path,
                    "texts": final_texts,
                    "boxes": final_boxes,
                    "confidence": overall_conf,
                    "time_cost": time_cost
                }
            else:
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