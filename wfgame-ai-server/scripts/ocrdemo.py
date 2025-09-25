# -*- coding: utf-8 -*-
# @File    : ocrdemo.py
import os
import json
import glob
import re
from typing import List, Dict, Any

import cv2
from paddleocr import PaddleOCR


class SmartPaddleOCR:
    """
    精简版智能OCR。

    仅保留三种预设（高速、均衡、高精度）的参数值；
    仅根据图片宽高（长、短边）动态调整 text_det_limit_type 为 'min' 或 'max'；
    其它复杂预检、特征计算、结果解析与可视化全部移除，保证代码整洁、可快速验证。
    """

    def __init__(self):
        """
        初始化：仅构建预设参数，并根据默认预设初始化一次 OCR。
        """
        # 三种预设，完整保留其参数值
        self.config_presets: Dict[str, Dict[str, Any]] = {
            'high_speed': {
                'text_det_limit_type': 'max',
                'text_det_limit_side_len': 960,
                'text_det_thresh': 0.5,
                'text_det_box_thresh': 0.7,
                'text_det_unclip_ratio': 1.0,
                'use_textline_orientation': False
            },
            'balanced': {
                'text_det_limit_type': 'max',
                'text_det_limit_side_len': 960,
                'text_det_thresh': 0.3,
                'text_det_box_thresh': 0.6,
                'text_det_unclip_ratio': 1.5,
                'use_textline_orientation': False
            },
            'high_precision': {
                'text_det_limit_type': 'min',
                'text_det_limit_side_len': 1280,
                'text_det_thresh': 0.2,
                'text_det_box_thresh': 0.4,
                'text_det_unclip_ratio': 2.0,
                'use_textline_orientation': True
            }
        }

        # 默认配置：以均衡预设为基准，并补齐模型/阈值/开关字段
        self.default_config: Dict[str, Any] = self.config_presets['balanced'].copy()
        self.default_config.update({
            'text_detection_model_name': 'PP-OCRv5_server_det',
            'text_recognition_model_name': 'PP-OCRv5_server_rec',
            'text_rec_score_thresh': 0.0,
            'use_doc_orientation_classify': False,
            'use_doc_unwarping': False,
        })

        # 当前生效配置（默认使用均衡预设的值）
        self.current_config: Dict[str, Any] = self.default_config.copy()

        # OCR 引擎实例
        self.ocr = None
        self._init_ocr(self.current_config)

        # 本次批处理的聚合结果
        self._session_results: List[Dict[str, Any]] = []

    def _diff_config(self, used_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算与默认配置的差异，仅返回不同的键值。
        """
        diff: Dict[str, Any] = {}
        for k, v in used_config.items():
            if k not in self.default_config or self.default_config[k] != v:
                diff[k] = v
        return diff

    def _init_ocr(self, config: Dict[str, Any]) -> None:
        """
        按给定配置初始化 OCR 引擎。
        """
        # 记录当前配置
        self.current_config = config.copy()

        # 统一补齐摘要中需要用到的关键字段（便于打印/写入）
        if 'text_detection_model_name' not in self.current_config:
            self.current_config['text_detection_model_name'] = 'PP-OCRv5_server_det'
        if 'text_recognition_model_name' not in self.current_config:
            self.current_config['text_recognition_model_name'] = 'PP-OCRv5_server_rec'
        if 'text_rec_score_thresh' not in self.current_config:
            self.current_config['text_rec_score_thresh'] = 0.0
        if 'use_doc_orientation_classify' not in self.current_config:
            self.current_config['use_doc_orientation_classify'] = False
        if 'use_doc_unwarping' not in self.current_config:
            self.current_config['use_doc_unwarping'] = False

        # 用官方参数名初始化，避免使用任何已废弃或不被支持的参数
        self.ocr = PaddleOCR(
            text_detection_model_name=self.current_config['text_detection_model_name'],
            text_recognition_model_name=self.current_config['text_recognition_model_name'],
            text_det_limit_type=self.current_config.get('text_det_limit_type', 'max'),
            text_det_limit_side_len=self.current_config.get('text_det_limit_side_len', 960),
            text_det_thresh=self.current_config.get('text_det_thresh', 0.3),
            text_det_box_thresh=self.current_config.get('text_det_box_thresh', 0.6),
            text_det_unclip_ratio=self.current_config.get('text_det_unclip_ratio', 1.5),
            text_rec_score_thresh=self.current_config.get('text_rec_score_thresh', 0.0),
            use_textline_orientation=self.current_config.get('use_textline_orientation', False),
            use_doc_orientation_classify=self.current_config.get('use_doc_orientation_classify', False),
            use_doc_unwarping=self.current_config.get('use_doc_unwarping', False),
            lang='ch'
        )

    def _select_limit_type_by_image(self, image_path: str) -> str:
        """
        基于图片宽高动态决定 text_det_limit_type：
        - 宽 >= 高 时使用 'max'（限制长边）
        - 否则使用 'min'（限制短边）

        说明：这是最直观、最稳定的规则，避免复杂阈值与特征导致的不确定性。
        """
        img = cv2.imread(image_path)
        if img is None:
            # 读取失败时，保持默认（与均衡预设一致）
            return self.config_presets['balanced']['text_det_limit_type']
        h, w = img.shape[:2]
        return 'max' if w >= h else 'min'

    def _to_builtin(self, obj):
        """
        将对象递归转换为可 JSON 序列化的原生类型（用于保存原始结果）。
        """
        try:
            import numpy as _np
        except Exception:
            _np = None

        if obj is None or isinstance(obj, (str, int, float, bool)):
            return obj
        if _np is not None and isinstance(obj, (_np.floating, _np.integer)):
            return obj.item()
        if _np is not None and isinstance(obj, _np.ndarray):
            return obj.tolist()
        if isinstance(obj, dict) or hasattr(obj, 'items'):
            try:
                items_iter = obj.items()
            except Exception:
                try:
                    obj = dict(obj)
                    items_iter = obj.items()
                except Exception:
                    return str(obj)
            return {str(self._to_builtin(k)): self._to_builtin(v) for k, v in items_iter}
        if isinstance(obj, (list, tuple, set)):
            return [self._to_builtin(x) for x in obj]
        return str(obj)

    def _count_candidates(self, result: Any) -> int:
        """
        估算候选文本数量：
        - dict: 优先 rec_texts，其次 rec_boxes/dt_polys
        - list: 遍历每个元素，优先取 item.res(dict) 后再统计 rec_texts/boxes
        - 其它情况返回 0
        """
        try:
            # 直接是字典
            if isinstance(result, dict):
                texts = result.get('rec_texts') or result.get('texts')
                if isinstance(texts, (list, tuple)):
                    return len(texts)
                boxes = result.get('rec_boxes') or result.get('dt_polys') or result.get('boxes')
                if isinstance(boxes, (list, tuple)):
                    return len(boxes)
                return 0

            # 列表/元组：遍历每项（可能是 Result 对象或 dict）
            if isinstance(result, (list, tuple)) and len(result) > 0:
                total = 0
                for item in result:
                    try:
                        raw = None
                        if isinstance(item, dict):
                            raw = item.get('res') if 'res' in item else item
                        else:
                            raw = getattr(item, 'res', None) or item
                        if isinstance(raw, dict):
                            texts = raw.get('rec_texts') or raw.get('texts')
                            boxes = raw.get('rec_boxes') or raw.get('dt_polys') or raw.get('boxes')
                            if isinstance(texts, (list, tuple)) and texts:
                                total += len(texts)
                            elif isinstance(boxes, (list, tuple)) and boxes:
                                total += len(boxes)
                    except Exception:
                        continue
                return total
            return 0
        except Exception:
            return 0

    def _build_param_summary(self, predict_save: bool, candidates: int) -> str:
        """
        构造参数摘要（格式参考 ocr_service 513-522）。
        """
        c = self.current_config
        score_thresh = c.get('text_rec_score_thresh')
        det_thresh = c.get('text_det_thresh')
        det_box_thresh = c.get('text_det_box_thresh')
        det_unclip_ratio = c.get('text_det_unclip_ratio')
        det_limit_type = c.get('text_det_limit_type')
        det_limit_side_len = c.get('text_det_limit_side_len')
        use_doc_orientation_classify = c.get('use_doc_orientation_classify')
        use_doc_unwarping = c.get('use_doc_unwarping')
        use_textline_orientation = c.get('use_textline_orientation')
        text_detection_model_name = c.get('text_detection_model_name')
        text_recognition_model_name = c.get('text_recognition_model_name')

        param_summary = (
            "当前过滤参数:\n"
            f"- 核心阈值: text_rec_score_thresh={score_thresh}\n"
            f"- 检测参数: text_det_thresh={det_thresh}, text_det_box_thresh={det_box_thresh}, text_det_unclip_ratio={det_unclip_ratio}\n"
            f"- 检测尺寸: text_det_limit_type={det_limit_type}, text_det_limit_side_len={det_limit_side_len}\n"
            f"- 文档与方向: use_doc_orientation_classify={use_doc_orientation_classify}, use_doc_unwarping={use_doc_unwarping}, use_textline_orientation={use_textline_orientation}\n"
            f"- 模型: text_detection_model_name={text_detection_model_name}, text_recognition_model_name={text_recognition_model_name}\n"
            f"- 输出: predict_save={predict_save}, candidates={candidates}\n"
        )
        return param_summary

    def _extract_texts_scores(self, result: Any) -> List[Dict[str, Any]]:
        """
        提取识别文本与置信度，并过滤出中文（汉字）。
        返回 [{"text": 汉字字符串, "score": 置信度}, ...]
        兼容 dict 或 list[Result|dict]（优先 item.res）。
        """
        pairs: List[Dict[str, Any]] = []
        try:
            def _collect_from_raw(raw: Any) -> None:
                try:
                    if not isinstance(raw, dict):
                        return
                    texts = raw.get('rec_texts') or raw.get('texts') or []
                    scores = raw.get('rec_scores') or []
                    if isinstance(texts, (list, tuple)) and isinstance(scores, (list, tuple)):
                        for t, s in zip(texts, scores):
                            if t is None:
                                continue
                            zh = ''.join(re.findall(r"[\u4e00-\u9fff]+", str(t)))
                            if zh:
                                pairs.append({"text": zh, "score": float(s) if s is not None else 0.0})
                    elif isinstance(texts, (list, tuple)) and texts:
                        # 没有分数时给0.0
                        for t in texts:
                            if t is None:
                                continue
                            zh = ''.join(re.findall(r"[\u4e00-\u9fff]+", str(t)))
                            if zh:
                                pairs.append({"text": zh, "score": 0.0})
                except Exception:
                    return

            # 直接字典
            if isinstance(result, dict):
                _collect_from_raw(result)
                return pairs

            # 列表/元组：遍历
            if isinstance(result, (list, tuple)) and len(result) > 0:
                for item in result:
                    try:
                        raw = None
                        if isinstance(item, dict):
                            raw = item.get('res') if 'res' in item else item
                        else:
                            raw = getattr(item, 'res', None) or item
                        _collect_from_raw(raw)
                    except Exception:
                        continue
        except Exception:
            return pairs
        return pairs

    def _print_recognized_texts(self, result: Any) -> None:
        """
        打印识别到的汉字与其阈值（置信度）。
        """
        pairs = self._extract_texts_scores(result)
        if not pairs:
            print("识别文本: 无中文结果")
            return
        print("识别文本:")
        for p in pairs:
            print(f"- 文本: {p['text']} | 置信度: {p['score']:.4f}")

    def predict(self, image_path: str, save_output: bool = True,
                output_dir: str = "output") -> Any:
        """
        执行识别：仅根据图片宽高调整 text_det_limit_type，然后调用 predict。
        结果聚合到单个汇总文件中。
        """
        # 1) 基于图片宽高选择 'min' 或 'max'
        limit_type = self._select_limit_type_by_image(image_path)

        # 2) 若与当前配置不同，则基于当前预设（均衡）生成新配置并重建 OCR
        if limit_type != self.current_config.get('text_det_limit_type'):
            new_cfg = self.default_config.copy()
            new_cfg['text_det_limit_type'] = limit_type
            self._init_ocr(new_cfg)

        # 3) 调用 predict
        try:
            result = self.ocr.predict(image_path)
        except TypeError as e:
            # 避免传参问题导致的报错影响验证
            raise RuntimeError(f"OCR 调用失败: {e}")

        # 3.1) 统计候选数量并打印参数摘要
        candidates = self._count_candidates(result)
        summary_text = self._build_param_summary(save_output, candidates)
        print(summary_text)

        # 3.2) 提取识别到的中文与阈值，并打印
        pairs = self._extract_texts_scores(result)
        if not pairs:
            print("识别文本: 无中文结果")
        else:
            print("识别文本:")
            for p in pairs:
                print(f"- 文本: {p['text']} | 置信度: {p['score']:.4f}")

        # 3.3) 记录分辨率
        img = cv2.imread(image_path)
        if img is not None:
            h, w = img.shape[:2]
        else:
            h, w = 0, 0

        # 3.4) 聚合本图结果（仅保存与默认不同的配置）
        entry = {
            "separator": "==============================",
            "image_name": os.path.basename(image_path),
            "resolution": {"width": w, "height": h, "pixels": w * h},
            "diff_config": self._diff_config(self.current_config),
            "recognized_texts": pairs
        }
        self._session_results.append(entry)

        # 单图不再落地文件，由process_directory结束时统一写入
        return result

    def _write_summary(self, output_dir: str) -> None:
        """
        写入单个汇总文件：包含默认配置与每张图片的差异配置、分辨率、识别文本。
        """
        os.makedirs(output_dir, exist_ok=True)
        summary_path = os.path.join(output_dir, "ocr_summary.json")
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump({
                "default_config": self._to_builtin(self.default_config),
                "images": self._to_builtin(self._session_results)
            }, f, ensure_ascii=False, indent=2)
        print(f"汇总结果已保存到: {summary_path}\n合计图片数: {len(self._session_results)}")

    def process_directory(self, directory_path: str,
                          save_output: bool = True,
                          output_dir: str = "output") -> None:
        """
        扫描目录下的图片并逐一执行识别。
        仅支持常见图片后缀，大小写不敏感。
        """
        image_extensions = ['*.png', '*.jpg', '*.jpeg', '*.bmp', '*.tiff', '*.tif']
        image_paths_all: List[str] = []

        for ext in image_extensions:
            image_paths_all.extend(glob.glob(os.path.join(directory_path, ext)))
            image_paths_all.extend(glob.glob(os.path.join(directory_path, ext.upper())))

        # 去重：Windows大小写不敏感，upper/lower 两次glob会重复，这里用规范化绝对路径去重并保持顺序
        unique_paths: List[str] = []
        seen = set()
        for p in image_paths_all:
            try:
                key = os.path.normcase(os.path.abspath(p))
            except Exception:
                key = p
            if key not in seen:
                seen.add(key)
                unique_paths.append(p)

        # 重置本次批处理聚合
        self._session_results = []

        print(f"找到 {len(unique_paths)} 张图片")
        for i, image_path in enumerate(unique_paths, start=1):
            print(f"\n处理图片 [{i}/{len(unique_paths)}]: {os.path.basename(image_path)}")
            try:
                self.predict(image_path, save_output=False, output_dir=output_dir)
            except Exception as e:
                print(f"处理图片 {image_path} 时出错: {e}")
        
        # 批处理结束，统一写入汇总文件
        self._write_summary(output_dir)
        print(f"\n所有图片处理完成! 汇总结果保存在 '{output_dir}' 目录中")


if __name__ == "__main__":
    # 创建精简智能OCR实例
    smart_ocr = SmartPaddleOCR()

    # 指定测试图像目录（相对路径，避免绝对路径）
    test_image_dir = "wfgame-ai-server/media/ocr/repositories/ocr_hit/"

    # 处理目录中的所有图片（仅保存原始结果JSON，便于快速验证）
    smart_ocr.process_directory(test_image_dir, save_output=True)