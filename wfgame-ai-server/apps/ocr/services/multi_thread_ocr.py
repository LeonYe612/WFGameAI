"""
多线程OCR服务
提供高效的并发OCR处理能力
"""
import os
import time
import threading
import queue
import logging
import configparser
from typing import List, Dict, Optional, Union
from pathlib import Path
from django.conf import settings
from django.utils import timezone
import concurrent.futures
import traceback

from .ocr_service import OCRService

# 配置日志
logger = logging.getLogger(__name__)

# 读取配置
config = configparser.ConfigParser()
config.read(settings.BASE_DIR.parent / 'config.ini', encoding='utf-8')

# OCR并发相关配置
OCR_MAX_WORKERS = config.getint('ocr', 'ocr_max_workers', fallback=4)


class MultiThreadOCR:
    """多线程OCR处理类"""

    def __init__(self,
                lang: str = 'ch',
                max_workers: int = None,
                predict_save: bool = False # 是否保存预测可视化图片/JSON 结果
                ):
        """
        初始化多线程OCR处理

        Args:
            lang: 语言模型
            max_workers: 最大工作线程数
        """
        self.lang = lang
        self.max_workers = max_workers or OCR_MAX_WORKERS
        self.predict_save = predict_save  # 是否保存预测可视化/JSON 结果

        # 确保最小值为1，避免无效值
        if self.max_workers <= 0:
            self.max_workers = 1
            logger.warning("工作线程数设置为无效值，已自动调整为1")

        # 单线程模式特殊处理
        if self.max_workers == 1:
            logger.warning("检测到单线程模式配置(ocr_max_workers=1)，将禁用GPU多线程优化")
            num_gpus = 0
            gpu_memory = 0
        else:
            # GPU 优先策略：若检测到可用 GPU，则按显存规模分配每个 GPU 的线程数，
            # 总线程数 = GPU 数量 × 每GPU线程数；否则按 CPU 模式使用 max_workers。
            num_gpus = 0
            try:
                import torch
                if torch.cuda.is_available():
                    num_gpus = torch.cuda.device_count()
            except Exception:
                num_gpus = 0

            # 检测 GPU0 显存规模（用于估算线程密度）。如无 GPU，返回 0。
            gpu_memory = self._detect_gpu_memory()
            logger.warning(f"GPU显存大小(设备0): {gpu_memory}MB")

        if num_gpus > 0 and self.max_workers > 1:
            threads_per_gpu = 1
            if gpu_memory >= 20000:
                threads_per_gpu = 16
                logger.warning(
                    f"检测到高端显卡(显存 {gpu_memory}MB)，每GPU分配16个线程"
                )
            elif gpu_memory >= 16000:
                threads_per_gpu = 8
                logger.warning(
                    f"检测到高性能显卡(显存 {gpu_memory}MB)，每GPU分配8个线程"
                )
            elif gpu_memory >= 8000:
                threads_per_gpu = 4
                logger.warning(
                    f"检测到中端显卡(显存 {gpu_memory}MB)，每GPU分配4个线程"
                )
            else:
                logger.warning(
                    f"检测到入门级显卡(显存 {gpu_memory}MB)，每GPU分配1个线程"
                )

            total_gpu_threads = num_gpus * threads_per_gpu
            self.max_workers = min(self.max_workers, total_gpu_threads)
            logger.warning(
                f"GPU优先模式: 检测到 {num_gpus} 个GPU，每个GPU {threads_per_gpu} 个线程，"
                f"总计使用 {self.max_workers} 个线程"
            )
        else:
            if self.max_workers == 1:
                logger.warning(f"单线程模式: 使用 1 个工作线程")
            else:
                logger.warning(f"CPU模式: 使用 {self.max_workers} 个线程")

        # 状态追踪
        self.total_images = 0
        self.processed_images = 0
        self.error_count = 0
        self.is_running = False
        self.progress_callback = None
        self.result_callback = None

        # 线程安全的队列和锁
        self.image_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.lock = threading.Lock()

        logger.info(
            f"初始化多线程OCR服务 (语言: {self.lang}, 最大线程: {self.max_workers})"
        )
        logger.info(f"配置文件中设置的最大工作线程数: {OCR_MAX_WORKERS}")
        logger.info(f"实际使用的工作线程数: {self.max_workers}")

        # 顺序初始化与工作线程数一致数量的OCR实例，避免并发初始化导致底层库竞态
        self.worker_ocrs: List[Optional[OCRService]] = []
        for i in range(self.max_workers):
            try:
                # OCRService 内部已按配置优先GPU，否则回退CPU
                ocr_inst = OCRService(lang=self.lang)
                self.worker_ocrs.append(ocr_inst)
            except Exception as init_err:
                logger.error(f"初始化OCR实例失败(线程索引 {i}): {init_err}")
                self.worker_ocrs.append(None)
            # 小延时，避免底层库加载竞态
            time.sleep(0.1)

    def _detect_gpu_memory(self) -> int:
        """
        检测GPU显存大小(MB)。

        返回:
            int: 显存大小(MB)。无GPU或检测失败时返回0。
        """
        try:
            import torch
            # 仅做快速可用性检测，不做复杂的 CUDA 加载
            if torch.cuda.is_available():
                gpu_properties = torch.cuda.get_device_properties(0)
                total_memory = gpu_properties.total_memory / (1024 * 1024)
                logger.warning(
                    f"使用NVIDIA GPU: {gpu_properties.name}，显存: {total_memory:.0f}MB"
                )
                return int(total_memory)
            logger.warning("未检测到NVIDIA GPU")
            return 0
        except Exception as e:
            logger.warning(f"检测GPU显存失败: {str(e)}")
            return 0

    def set_callbacks(self, progress_callback=None, result_callback=None):
        """
        设置回调函数

        Args:
            progress_callback: 进度回调，接收参数(processed, total, error_count)
            result_callback: 结果回调，接收参数(result)
        """
        self.progress_callback = progress_callback
        self.result_callback = result_callback

    def recognize_batch(self, image_dir: str, image_formats: List[str] = None) -> List[Dict]:
        """
        多线程批量识别图片

        Args:
            image_dir: 图片目录
            image_formats: 图片格式列表

        Returns:
            List[Dict]: 识别结果列表
        """
        batch_start_time = time.time()

        if image_formats is None:
            image_formats = ['jpg', 'jpeg', 'png', 'bmp', 'tiff', 'tif', 'webp']

        # 收集所有图片路径
        logger.warning(f"开始收集图片路径: {image_dir}")
        path_collect_start = time.time()
        image_paths = self._collect_image_paths(image_dir, image_formats)
        path_collect_time = time.time() - path_collect_start

        if not image_paths:
            logger.warning(f"在目录 {image_dir} 中未找到匹配的图片")
            return []

        # 如果至少有一个OCR实例不可用，给出告警但继续执行（对应线程将跳过）
        if all(inst is None for inst in self.worker_ocrs):
            logger.error("所有OCR实例初始化均失败，无法开始识别")
            return []

        # 如果图片数量过多，提示处理时间可能较长
        if len(image_paths) > 10000:
            logger.warning(f"图片数量过多({len(image_paths)}张)，处理时间可能较长")

        self.total_images = len(image_paths)
        self.processed_images = 0
        self.error_count = 0
        self.is_running = True

        logger.warning(
            f"在 {image_dir} 及其子目录中找到 {self.total_images} 张图片，"
            f"收集耗时 {path_collect_time:.2f} 秒"
        )
        logger.warning(f"使用 {self.max_workers} 个工作线程进行处理")

        # 粗略估计处理时间（仅用于日志友好提示）
        est_time_per_image = 0.5
        est_total_time = (
            (self.total_images / self.max_workers) * est_time_per_image
            if self.max_workers > 0 else 0
        )
        est_hours = int(est_total_time / 3600)
        est_minutes = int((est_total_time % 3600) / 60)
        est_seconds = int(est_total_time % 60)
        logger.warning(
            f"预计处理时间: {est_hours}小时 {est_minutes}分钟 {est_seconds}秒"
        )

        # 将图片路径放入队列
        for path in image_paths:
            self.image_queue.put(path)

        all_results = []

        # 单线程模式特殊处理
        if self.max_workers == 1:
            logger.warning("使用单线程模式处理图片，避免并发问题")
            try:
                # 直接使用第一个OCR实例
                ocr = self.worker_ocrs[0]
                if ocr is None:
                    logger.error("OCR实例初始化失败，无法处理图片")
                    return []

                # 直接处理所有图片
                while not self.image_queue.empty():
                    try:
                        image_path = self.image_queue.get(block=False)
                        logger.debug(f"单线程处理图片: {image_path}")
                        img_start_time = time.time()

                        try:
                            if not os.path.isabs(image_path):
                                full_path = os.path.join(settings.MEDIA_ROOT, image_path)
                                if not os.path.exists(full_path):
                                    logger.error(f"图片文件不存在: {full_path}")
                                    error_result = {
                                        "image_path": image_path,
                                        "error": f"图片文件不存在: {full_path}",
                                        "worker_id": 0
                                    }
                                    all_results.append(error_result)
                                    self.error_count += 1
                                    continue

                            # 识别
                            result = ocr.recognize_image(image_path, predict_save=self.predict_save)
                            result['worker_id'] = 0
                            # 统一字段命名，与OCRService保持一致
                            result['time_cost'] = time.time() - img_start_time

                            all_results.append(result)
                            self.processed_images += 1

                            # 如果设置了结果回调，则调用
                            if self.result_callback:
                                self.result_callback(result)

                        except Exception as e:
                            logger.error(f"单线程处理失败 {image_path}: {e}")
                            error_result = {
                                "image_path": image_path,
                                "error": str(e),
                                "worker_id": 0
                            }
                            all_results.append(error_result)
                            self.error_count += 1

                    except queue.Empty:
                        break
                    except Exception as e:
                        logger.error(f"单线程处理异常: {e}")
                        logger.error(traceback.format_exc())
                        break

            except Exception as e:
                logger.error(f"单线程处理异常: {str(e)}")
                logger.error(traceback.format_exc())

        else:
            # 多线程模式处理
            # 定期报告进度的线程
            progress_reporting_active = True

            def progress_reporter():
                last_processed = 0
                last_time = time.time()

                while progress_reporting_active and self.is_running:
                    time.sleep(30)
                    current_time = time.time()
                    current_processed = self.processed_images
                    if current_processed > last_processed:
                        time_diff = current_time - last_time
                        images_diff = current_processed - last_processed
                        speed = images_diff / time_diff if time_diff > 0 else 0
                        remaining_images = self.total_images - current_processed
                        est_remaining_time = (
                            remaining_images / speed if speed > 0 else 0
                        )
                        est_h = int(est_remaining_time / 3600)
                        est_m = int((est_remaining_time % 3600) / 60)
                        est_s = int(est_remaining_time % 60)
                        progress = (
                            (current_processed / self.total_images) * 100
                            if self.total_images > 0 else 0
                        )
                        logger.warning(
                            f"进度: {current_processed}/{self.total_images} "
                            f"({progress:.2f}%), 速度: {speed:.2f} 张/秒, 剩余时间: "
                            f"{est_h}小时 {est_m}分钟 {est_s}秒"
                        )
                        last_processed = current_processed
                        last_time = current_time

            # 启动进度报告线程
            progress_thread = threading.Thread(target=progress_reporter)
            progress_thread.daemon = True
            progress_thread.start()

            try:
                # 创建线程池
                logger.warning(
                    f"创建线程池，最大工作线程数: {self.max_workers}"
                )
                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=self.max_workers
                ) as executor:
                    futures = []
                    for i in range(self.max_workers):
                        logger.warning(f"创建工作线程 {i}")
                        futures.append(
                            executor.submit(self._worker_thread, i)
                        )

                    # 收集结果线程
                    logger.warning("启动结果收集线程")
                    result_collector = threading.Thread(
                        target=self._result_collector,
                        args=(all_results,)
                    )
                    result_collector.daemon = True
                    result_collector.start()

                    # 等待所有工作线程完成
                    logger.warning("等待所有工作线程完成")
                    concurrent.futures.wait(futures)
                    logger.warning("所有工作线程已完成")

                    # 停止结果收集线程
                    progress_reporting_active = False
                    logger.warning("等待结果收集线程结束")
                    result_collector.join()
                    logger.warning("结果收集线程结束")
            except Exception as e:
                logger.error(f"多线程处理异常: {str(e)}")
                logger.error(traceback.format_exc())
                self.is_running = False
                progress_reporting_active = False

        # 统计信息
        total_time = time.time() - batch_start_time
        avg_speed = self.processed_images / total_time if total_time > 0 else 0
        hours = int(total_time / 3600)
        minutes = int((total_time % 3600) / 60)
        seconds = int(total_time % 60)

        logger.warning(
            f"{'单' if self.max_workers == 1 else '多'}线程处理完成，共处理 {self.processed_images} 张图片，错误 "
            f"{self.error_count} 张，成功率: "
            f"{(self.processed_images - self.error_count) / self.total_images:.2%}"
        )
        logger.warning(
            f"总处理时间: {hours}小时 {minutes}分钟 {seconds}秒，平均速度: "
            f"{avg_speed:.2f} 张/秒"
        )

        return all_results

    def _worker_thread(self, worker_id: int):
        """
        工作线程函数

        Args:
            worker_id: 工作线程ID
        """
        logger.warning(f"工作线程 {worker_id} 启动")

        # 复用对应索引的OCR实例
        ocr = self.worker_ocrs[worker_id] if worker_id < len(self.worker_ocrs) else None
        if ocr is None:
            logger.error(f"线程 {worker_id}: OCR实例未初始化，跳过该线程任务")
            return

        processed_count = 0
        start_time = time.time()
        last_log_time = start_time

        while self.is_running:
            try:
                try:
                    image_path = self.image_queue.get(block=False)
                except queue.Empty:
                    break

                logger.debug(f"线程 {worker_id}: 处理图片 {image_path}")
                img_start_time = time.time()

                try:
                    from django.conf import settings
                    if not os.path.isabs(image_path):
                        full_path = os.path.join(settings.MEDIA_ROOT, image_path)
                        if not os.path.exists(full_path):
                            logger.error(
                                f"线程 {worker_id}: 图片文件不存在: {full_path}"
                            )
                            error_result = {
                                "image_path": image_path,
                                "error": f"图片文件不存在: {full_path}",
                                "worker_id": worker_id
                            }
                            self.result_queue.put(error_result)
                            with self.lock:
                                self.error_count += 1
                            continue

                    # 识别
                    result = ocr.recognize_image(image_path, predict_save=self.predict_save)
                    result['worker_id'] = worker_id
                    # 统一字段命名，与OCRService保持一致
                    result['time_cost'] = time.time() - img_start_time

                    self.result_queue.put(result)

                    processed_count += 1
                    with self.lock:
                        self.processed_images += 1

                except Exception as e:
                    logger.error(
                        f"线程 {worker_id}: 处理失败 {image_path}: {e}"
                    )
                    error_result = {
                        "image_path": image_path,
                        "error": str(e),
                        "worker_id": worker_id
                    }
                    self.result_queue.put(error_result)
                    with self.lock:
                        self.error_count += 1

            except Exception as e:
                logger.error(f"线程 {worker_id}: 未知异常: {e}")
                logger.error(traceback.format_exc())
                break

        logger.debug(f"线程 {worker_id} 完成，处理 {processed_count} 张图片")

    def _result_collector(self, all_results: List[Dict]):
        """
        结果收集线程

        Args:
            all_results: 用于存储所有结果的列表
        """
        logger.warning("结果收集线程启动")

        while self.is_running or not self.result_queue.empty():
            try:
                # 获取结果，设置超时以便及时退出
                try:
                    result = self.result_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                # 处理结果
                all_results.append(result)

                # 如果设置了结果回调，则调用
                if self.result_callback:
                    self.result_callback(result)

                # 标记结果处理完成
                self.result_queue.task_done()

            except Exception as e:
                logger.error(f"结果收集线程异常: {str(e)}")

        logger.warning("结果收集线程结束")

    def _collect_image_paths(self, image_dir: str, image_formats: List[str]) -> List[str]:
        """
        收集目录中的图片路径

        Args:
            image_dir: 图片目录
            image_formats: 图片格式列表

        Returns:
            List[str]: 图片路径列表
        """
        from django.conf import settings

        image_extensions = set()
        for ext in image_formats:
            image_extensions.add(f".{ext.lower()}")
            image_extensions.add(f".{ext.upper()}")

        image_paths = []
        media_root = settings.MEDIA_ROOT

        for path in Path(image_dir).rglob("*"):
            if path.is_file() and path.suffix in image_extensions:
                # 将绝对路径转换为相对于媒体根目录的路径
                try:
                    if str(path).startswith(media_root):
                        # 如果路径在媒体目录下，转换为相对路径
                        rel_path = os.path.relpath(str(path), media_root)
                        # 确保路径使用正斜杠，符合Web URL格式
                        rel_path = rel_path.replace('\\', '/')
                        image_paths.append(rel_path)
                        logger.debug(f"图片路径转换: {str(path)} -> {rel_path}")
                    else:
                        # 如果不在媒体目录下，记录警告但仍使用绝对路径
                        logger.warning(f"图片路径不在媒体目录下: {str(path)}")
                        image_paths.append(str(path))
                except Exception as e:
                    logger.error(f"路径转换失败: {str(path)}, 错误: {str(e)}")
                    image_paths.append(str(path))

        logger.info(f"收集到 {len(image_paths)} 张图片，媒体根目录: {media_root}")
        return image_paths