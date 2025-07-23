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
                use_gpu: bool = True,
                lang: str = 'ch',
                gpu_ids: List[int] = None,
                max_workers: int = None):
        """
        初始化多线程OCR处理

        Args:
            use_gpu: 是否使用GPU
            lang: 语言模型
            gpu_ids: GPU ID列表，如果提供多个ID，将在多个GPU上分配任务
            max_workers: 最大工作线程数
        """
        self.use_gpu = use_gpu
        self.lang = lang
        self.gpu_ids = gpu_ids or [0]  # 默认使用GPU 0
        self.max_workers = max_workers or OCR_MAX_WORKERS

        # 确保最大工作线程数不超过可用GPU数量(如果使用GPU)
        if self.use_gpu:
            self.max_workers = min(self.max_workers, len(self.gpu_ids))

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

        logger.info(f"初始化多线程OCR服务 (GPU: {self.use_gpu}, GPU IDs: {self.gpu_ids}, "
                   f"语言: {self.lang}, 最大线程: {self.max_workers})")

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
        if image_formats is None:
            image_formats = ['jpg', 'jpeg', 'png', 'bmp', 'tiff', 'tif', 'webp']

        # 收集所有图片路径
        image_paths = self._collect_image_paths(image_dir, image_formats)

        if not image_paths:
            logger.warning(f"在目录 {image_dir} 中未找到匹配的图片")
            return []

        self.total_images = len(image_paths)
        self.processed_images = 0
        self.error_count = 0
        self.is_running = True

        logger.info(f"在 {image_dir} 及其子目录中找到 {self.total_images} 张图片，开始多线程处理")

        # 将图片路径放入队列
        for path in image_paths:
            self.image_queue.put(path)

        all_results = []

        try:
            # 创建线程池
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 创建工作线程，每个线程使用不同的GPU ID
                futures = []
                for i in range(self.max_workers):
                    # 为每个线程分配一个GPU ID
                    gpu_id = self.gpu_ids[i % len(self.gpu_ids)]
                    futures.append(
                        executor.submit(self._worker_thread, i, gpu_id)
                    )

                # 收集结果线程
                result_collector = threading.Thread(
                    target=self._result_collector,
                    args=(all_results,)
                )
                result_collector.daemon = True
                result_collector.start()

                # 等待所有工作线程完成
                concurrent.futures.wait(futures)

                # 停止结果收集线程
                self.is_running = False
                result_collector.join(timeout=5.0)

                # 收集剩余结果
                while not self.result_queue.empty():
                    result = self.result_queue.get()
                    all_results.append(result)
                    self.result_queue.task_done()

        except Exception as e:
            logger.error(f"多线程处理异常: {str(e)}")
            self.is_running = False

        logger.info(f"多线程处理完成，共处理 {self.processed_images} 张图片，"
                   f"错误 {self.error_count} 张，成功率: {(self.processed_images - self.error_count) / self.total_images:.2%}")

        return all_results

    def _worker_thread(self, worker_id: int, gpu_id: int):
        """
        工作线程函数

        Args:
            worker_id: 工作线程ID
            gpu_id: 使用的GPU ID
        """
        logger.info(f"工作线程 {worker_id} 启动，使用 GPU {gpu_id}")

        # 为每个线程创建一个OCR实例
        ocr = OCRService(use_gpu=self.use_gpu, lang=self.lang, gpu_id=gpu_id)

        while self.is_running:
            try:
                # 非阻塞方式获取任务
                try:
                    image_path = self.image_queue.get(block=False)
                except queue.Empty:
                    # 队列为空，处理完成
                    break

                # 处理图片
                logger.debug(f"线程 {worker_id}: 处理图片 {image_path}")
                start_time = time.time()

                try:
                    result = ocr.recognize_image(image_path)
                    result['worker_id'] = worker_id
                    result['gpu_id'] = gpu_id
                    result['processing_time'] = time.time() - start_time

                    # 添加到结果队列
                    self.result_queue.put(result)

                except Exception as e:
                    logger.error(f"线程 {worker_id}: 处理图片 {image_path} 失败: {str(e)}")
                    error_result = {
                        "image_path": image_path,
                        "error": str(e),
                        "worker_id": worker_id,
                        "gpu_id": gpu_id
                    }
                    self.result_queue.put(error_result)

                    with self.lock:
                        self.error_count += 1

                finally:
                    # 更新进度
                    with self.lock:
                        self.processed_images += 1
                        progress = self.processed_images / self.total_images

                    # 通过回调报告进度
                    if self.progress_callback:
                        self.progress_callback(self.processed_images, self.total_images, self.error_count)

                    # 标记队列任务完成
                    self.image_queue.task_done()

            except Exception as e:
                logger.error(f"线程 {worker_id} 异常: {str(e)}")

        logger.info(f"工作线程 {worker_id} 结束")

    def _result_collector(self, all_results: List[Dict]):
        """
        结果收集线程

        Args:
            all_results: 用于存储所有结果的列表
        """
        logger.info("结果收集线程启动")

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

        logger.info("结果收集线程结束")

    def _collect_image_paths(self, image_dir: str, image_formats: List[str]) -> List[str]:
        """
        收集目录中的图片路径

        Args:
            image_dir: 图片目录
            image_formats: 图片格式列表

        Returns:
            List[str]: 图片路径列表
        """
        image_extensions = set()
        for ext in image_formats:
            image_extensions.add(f".{ext.lower()}")
            image_extensions.add(f".{ext.upper()}")

        image_paths = []
        for path in Path(image_dir).rglob("*"):
            if path.is_file() and path.suffix in image_extensions:
                image_paths.append(str(path))

        return image_paths