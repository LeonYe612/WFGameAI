#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Device Screen Analyzer - 实时设备屏幕元素识别工具

该工具结合了设备连接、截图捕获和YOLO模型推理，使用best.pt模型
对连接设备的屏幕进行实时UI元素识别和分析。

主要功能：
1. 自动检测和连接ADB设备
2. 实时截图捕获
3. 使用best.pt YOLO模型进行UI元素识别
4. 可视化识别结果
5. 支持多设备同时分析
6. 导出分析结果和统计数据

使用示例：
    python device_screen_analyzer.py --model best.pt --device auto
    python device_screen_analyzer.py --continuous --interval 2 --save-results
    python device_screen_analyzer.py --list-devices
"""

import os
import sys
import cv2
import numpy as np
import time
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import traceback
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

# 添加项目路径
project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 导入项目模块
try:
    from ultralytics import YOLO
    from adbutils import adb
    from airtest.core.api import connect_device, snapshot
    from airtest.core.android.android import Android
except ImportError as e:
    print(f"导入依赖模块失败: {e}")
    print("请确保已安装 ultralytics, adbutils, airtest 等依赖")
    sys.exit(1)

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('device_screen_analyzer.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class DetectionResult:
    """检测结果数据类"""
    class_name: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    center: Tuple[int, int]          # center_x, center_y

@dataclass
class AnalysisSession:
    """分析会话数据类"""
    device_id: str
    start_time: datetime
    total_screenshots: int = 0
    total_detections: int = 0
    detection_history: List[Dict] = None

    def __post_init__(self):
        if self.detection_history is None:
            self.detection_history = []

class DeviceScreenAnalyzer:
    """设备屏幕分析器"""

    def __init__(self, model_path: str = None, confidence_threshold: float = 0.6):
        """
        初始化屏幕分析器

        Args:
            model_path: YOLO模型路径，默认使用best.pt
            confidence_threshold: 检测置信度阈值
        """
        self.model_path = model_path or self._find_best_model()
        self.confidence_threshold = confidence_threshold
        self.model = None

        self.connected_devices = {}
        self.analysis_sessions = {}
        # 使用绝对路径，将结果保存在脚本目录下的 screen_analysis_results 目录中
        script_dir = Path(__file__).parent
        self.results_dir = script_dir / "screen_analysis_results"
        self.is_running = False

        # 创建结果目录
        self.results_dir.mkdir(exist_ok=True)

        # 加载模型
        self._load_model()

    def _find_best_model(self) -> str:
        """查找best.pt模型文件"""
        # 可能的模型路径
        potential_paths = [
            "datasets/train/weights/best.pt",
            "apps/scripts/datasets/train/weights/best.pt",
            "wfgame-ai-server/apps/scripts/datasets/train/weights/best.pt",
            str(project_root / "wfgame-ai-server/apps/scripts/datasets/train/weights/best.pt"),
            "best.pt",
            "models/best.pt"
        ]

        for path in potential_paths:
            full_path = Path(path)
            if full_path.exists():
                logger.info(f"找到模型文件: {full_path}")
                return str(full_path.absolute())

        # 如果没找到，使用默认路径
        default_path = project_root / "apps/scripts/datasets/train/weights/best.pt"
        logger.warning(f"未找到best.pt模型，将尝试使用: {default_path}")
        return str(default_path)

    def _load_model(self):
        """加载YOLO模型"""
        try:
            if not Path(self.model_path).exists():
                raise FileNotFoundError(f"模型文件不存在: {self.model_path}")

            logger.info(f"加载YOLO模型: {self.model_path}")
            self.model = YOLO(self.model_path)

            # 获取模型类别信息
            if hasattr(self.model, 'names'):
                logger.info(f"模型类别: {self.model.names}")
            else:
                logger.warning("无法获取模型类别信息")

            logger.info("YOLO模型加载成功")

        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            raise

    def list_devices(self) -> List[str]:
        """列出所有连接的设备"""
        try:
            devices = []
            # 使用adbutils获取设备列表
            adb_devices = adb.device_list()

            for device in adb_devices:
                device_id = device.serial
                # 检查设备状态
                try:
                    status = device.get_state()
                    if status == "device":
                        devices.append(device_id)
                        logger.info(f"发现设备: {device_id}")
                    else:
                        logger.warning(f"设备 {device_id} 状态异常: {status}")
                except Exception as e:
                    logger.warning(f"检查设备 {device_id} 状态失败: {e}")

            return devices

        except Exception as e:
            logger.error(f"获取设备列表失败: {e}")
            return []

    def connect_device(self, device_id: str) -> bool:
        """连接指定设备"""
        try:
            if device_id in self.connected_devices:
                logger.info(f"设备 {device_id} 已连接")
                return True

            # 使用airtest连接设备
            device_uri = f"android:///{device_id}"
            device = connect_device(device_uri)

            if device:
                self.connected_devices[device_id] = device
                logger.info(f"成功连接设备: {device_id}")

                # 创建分析会话
                self.analysis_sessions[device_id] = AnalysisSession(
                    device_id=device_id,
                    start_time=datetime.now()
                )

                return True
            else:
                logger.error(f"连接设备失败: {device_id}")
                return False

        except Exception as e:
            logger.error(f"连接设备 {device_id} 异常: {e}")
            return False

    def capture_screenshot(self, device_id: str) -> Optional[np.ndarray]:
        """捕获设备截图"""
        try:
            if device_id not in self.connected_devices:
                logger.error(f"设备 {device_id} 未连接")
                return None

            device = self.connected_devices[device_id]

            # 使用airtest获取截图
            screenshot = device.snapshot()

            if screenshot is not None:
                # 转换为OpenCV格式
                frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

                # 更新会话统计
                if device_id in self.analysis_sessions:
                    self.analysis_sessions[device_id].total_screenshots += 1

                return frame
            else:
                logger.warning(f"设备 {device_id} 截图失败")
                return None

        except Exception as e:
            logger.error(f"捕获设备 {device_id} 截图失败: {e}")
            return None

    def analyze_screenshot(self, frame: np.ndarray, device_id: str = None) -> List[DetectionResult]:
        """分析截图并返回检测结果"""
        try:
            if self.model is None:
                logger.error("YOLO模型未加载")
                return []

            # 调整图像尺寸用于推理
            inference_frame = cv2.resize(frame, (640, 640))

            # 进行推理
            results = self.model.predict(
                source=inference_frame,
                conf=self.confidence_threshold,
                verbose=False
            )

            if not results or len(results) == 0:
                return []

            # 解析检测结果
            detections = []
            result = results[0]

            if hasattr(result, 'boxes') and result.boxes is not None:
                boxes = result.boxes
                orig_h, orig_w = frame.shape[:2]
                scale_x, scale_y = orig_w / 640, orig_h / 640

                for i, box in enumerate(boxes):
                    # 获取类别信息
                    cls_id = int(box.cls.item())
                    class_name = "unknown"
                    if hasattr(self.model, 'names') and cls_id in self.model.names:
                        class_name = self.model.names[cls_id]

                    # 获取置信度
                    confidence = float(box.conf.item())

                    # 获取边界框（转换回原始图像尺寸）
                    xyxy = box.xyxy[0].tolist()
                    x1 = int(xyxy[0] * scale_x)
                    y1 = int(xyxy[1] * scale_y)
                    x2 = int(xyxy[2] * scale_x)
                    y2 = int(xyxy[3] * scale_y)

                    # 计算中心点
                    center_x = int((x1 + x2) / 2)
                    center_y = int((y1 + y2) / 2)

                    detection = DetectionResult(
                        class_name=class_name,
                        confidence=confidence,
                        bbox=(x1, y1, x2, y2),
                        center=(center_x, center_y)
                    )

                    detections.append(detection)

                # 更新会话统计
                if device_id and device_id in self.analysis_sessions:
                    self.analysis_sessions[device_id].total_detections += len(detections)

            return detections

        except Exception as e:
            logger.error(f"分析截图失败: {e}")
            return []

    def visualize_results(self, frame: np.ndarray, detections: List[DetectionResult]) -> np.ndarray:
        """在图像上可视化检测结果"""
        result_frame = frame.copy()

        for detection in detections:
            x1, y1, x2, y2 = detection.bbox

            # 绘制边界框
            cv2.rectangle(result_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # 绘制类别和置信度
            label = f"{detection.class_name}: {detection.confidence:.2f}"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]

            # 绘制标签背景
            cv2.rectangle(
                result_frame,
                (x1, y1 - label_size[1] - 10),
                (x1 + label_size[0], y1),
                (0, 255, 0),
                -1
            )

            # 绘制标签文字
            cv2.putText(
                result_frame,
                label,
                (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 0),
                2
            )

            # 绘制中心点
            cv2.circle(result_frame, detection.center, 3, (0, 0, 255), -1)

        return result_frame

    def analyze_single_screenshot(self, device_id: str, save_result: bool = True) -> Dict[str, Any]:
        """分析单次截图"""
        try:
            # 捕获截图
            frame = self.capture_screenshot(device_id)
            if frame is None:
                return {"success": False, "error": "截图捕获失败"}

            # 分析截图
            detections = self.analyze_screenshot(frame, device_id)

            # 准备结果数据
            result_data = {
                "success": True,
                "device_id": device_id,
                "timestamp": datetime.now().isoformat(),
                "screenshot_shape": frame.shape,
                "total_detections": len(detections),
                "detections": []
            }

            # 添加检测详情
            for detection in detections:
                detection_data = {
                    "class_name": detection.class_name,
                    "confidence": detection.confidence,
                    "bbox": detection.bbox,
                    "center": detection.center
                }
                result_data["detections"].append(detection_data)

            # 保存结果
            if save_result:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                # 可视化并保存图像
                result_frame = self.visualize_results(frame, detections)
                image_path = self.results_dir / f"{device_id}_{timestamp}_result.jpg"
                cv2.imwrite(str(image_path), result_frame)

                # 保存原始截图
                original_path = self.results_dir / f"{device_id}_{timestamp}_original.jpg"
                cv2.imwrite(str(original_path), frame)

                # 保存JSON数据
                json_path = self.results_dir / f"{device_id}_{timestamp}_data.json"
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(result_data, f, ensure_ascii=False, indent=2)

                result_data["saved_files"] = {
                    "result_image": str(image_path),
                    "original_image": str(original_path),
                    "json_data": str(json_path)
                }

            logger.info(f"设备 {device_id} 分析完成，检测到 {len(detections)} 个元素")
            return result_data

        except Exception as e:
            logger.error(f"分析设备 {device_id} 截图失败: {e}")
            return {"success": False, "error": str(e)}

    def start_continuous_analysis(self, device_ids: List[str], interval: float = 2.0, max_iterations: int = None):
        """开始连续分析"""
        self.is_running = True
        logger.info(f"开始连续分析，设备: {device_ids}, 间隔: {interval}秒")

        iteration = 0
        try:
            while self.is_running:
                if max_iterations and iteration >= max_iterations:
                    break

                # 并行分析所有设备
                with ThreadPoolExecutor(max_workers=len(device_ids)) as executor:
                    futures = []
                    for device_id in device_ids:
                        future = executor.submit(self.analyze_single_screenshot, device_id, True)
                        futures.append((device_id, future))

                    # 收集结果
                    for device_id, future in futures:
                        try:
                            result = future.result(timeout=30)
                            if result["success"]:
                                detections_count = result["total_detections"]
                                logger.info(f"设备 {device_id}: 检测到 {detections_count} 个元素")
                            else:
                                logger.warning(f"设备 {device_id} 分析失败: {result.get('error', 'Unknown error')}")
                        except Exception as e:
                            logger.error(f"设备 {device_id} 分析异常: {e}")

                iteration += 1
                if self.is_running:
                    time.sleep(interval)

        except KeyboardInterrupt:
            logger.info("接收到停止信号，正在停止分析...")
        finally:
            self.is_running = False
            self._generate_analysis_report()

    def stop_analysis(self):
        """停止分析"""
        self.is_running = False
        logger.info("分析已停止")

    def _generate_analysis_report(self):
        """生成分析报告"""
        try:
            report_data = {
                "analysis_summary": {
                    "total_devices": len(self.analysis_sessions),
                    "analysis_end_time": datetime.now().isoformat(),
                    "results_directory": str(self.results_dir)
                },
                "device_sessions": {}
            }

            for device_id, session in self.analysis_sessions.items():
                session_data = {
                    "device_id": session.device_id,
                    "start_time": session.start_time.isoformat(),
                    "total_screenshots": session.total_screenshots,
                    "total_detections": session.total_detections,
                    "average_detections_per_screenshot": (
                        session.total_detections / session.total_screenshots
                        if session.total_screenshots > 0 else 0
                    )
                }
                report_data["device_sessions"][device_id] = session_data

            # 保存报告
            report_path = self.results_dir / f"analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)

            logger.info(f"分析报告已保存: {report_path}")

        except Exception as e:
            logger.error(f"生成分析报告失败: {e}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Device Screen Analyzer - 实时设备屏幕元素识别工具",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # 基本参数
    parser.add_argument('--model', type=str, help='YOLO模型路径（默认使用best.pt）')
    parser.add_argument('--confidence', type=float, default=0.6, help='检测置信度阈值')
    parser.add_argument('--device', type=str, help='指定设备ID（auto表示自动选择）')

    # 操作模式
    parser.add_argument('--list-devices', action='store_true', help='列出所有连接的设备')
    parser.add_argument('--single-shot', action='store_true', help='执行单次截图分析')
    parser.add_argument('--continuous', action='store_true', help='连续监控模式')

    # 连续模式参数
    parser.add_argument('--interval', type=float, default=2.0, help='连续模式的截图间隔（秒）')
    parser.add_argument('--max-iterations', type=int, help='最大分析次数（仅连续模式）')

    # 输出选项
    parser.add_argument('--save-results', action='store_true', default=True, help='保存分析结果')
    parser.add_argument('--output-dir', type=str, help='结果输出目录')

    args = parser.parse_args()

    try:
        # 创建分析器实例
        analyzer = DeviceScreenAnalyzer(
            model_path=args.model,
            confidence_threshold=args.confidence
        )

        # 设置输出目录
        if args.output_dir:
            analyzer.results_dir = Path(args.output_dir)
            analyzer.results_dir.mkdir(exist_ok=True)

        # 列出设备
        if args.list_devices:
            devices = analyzer.list_devices()
            if devices:
                print("连接的设备:")
                for i, device_id in enumerate(devices, 1):
                    print(f"  {i}. {device_id}")
            else:
                print("未发现连接的设备")
            return

        # 获取目标设备列表
        target_devices = []
        if args.device == "auto" or args.device is None:
            # 自动获取所有设备
            all_devices = analyzer.list_devices()
            if not all_devices:
                logger.error("未发现可用设备")
                return
            target_devices = all_devices
        else:
            # 使用指定设备
            target_devices = [args.device]

        # 连接设备
        connected_devices = []
        for device_id in target_devices:
            if analyzer.connect_device(device_id):
                connected_devices.append(device_id)

        if not connected_devices:
            logger.error("无法连接任何设备")
            return

        logger.info(f"已连接设备: {connected_devices}")

        # 执行分析
        if args.single_shot:
            # 单次分析
            for device_id in connected_devices:
                result = analyzer.analyze_single_screenshot(device_id, args.save_results)
                if result["success"]:
                    print(f"设备 {device_id} 分析完成:")
                    print(f"  检测到 {result['total_detections']} 个元素")
                    if args.save_results and "saved_files" in result:
                        print(f"  结果已保存至: {result['saved_files']['result_image']}")
                else:
                    print(f"设备 {device_id} 分析失败: {result.get('error', 'Unknown error')}")

        elif args.continuous:
            # 连续监控
            analyzer.start_continuous_analysis(
                device_ids=connected_devices,
                interval=args.interval,
                max_iterations=args.max_iterations
            )

        else:
            # 默认执行单次分析
            for device_id in connected_devices:
                analyzer.analyze_single_screenshot(device_id, args.save_results)

    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.error(f"程序执行失败: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
