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

        # 检测GPU显存大小，为高端显卡提供更多线程支持
        gpu_memory = self._detect_gpu_memory()
        logger.warning(f"GPU显存大小: {gpu_memory}MB")

        # 根据GPU显存调整每个GPU可用的线程数
        if self.use_gpu:
            threads_per_gpu = 1  # 默认值

            if gpu_memory >= 20000:  # 20GB及以上显存(RTX 4090等)
                threads_per_gpu = 16
                logger.warning(f"检测到高端显卡(显存 {gpu_memory}MB)，每GPU分配16个线程")
            elif gpu_memory >= 16000:  # 16GB及以上显存
                threads_per_gpu = 8
                logger.warning(f"检测到高性能显卡(显存 {gpu_memory}MB)，每GPU分配8个线程")
            elif gpu_memory >= 8000:  # 8GB及以上显存
                threads_per_gpu = 4
                logger.warning(f"检测到中端显卡(显存 {gpu_memory}MB)，每GPU分配4个线程")
            else:
                logger.warning(f"检测到入门级显卡(显存 {gpu_memory}MB)，每GPU分配1个线程")

            # 计算总线程数 = GPU数量 × 每GPU线程数，但不超过用户设置的max_workers
            total_gpu_threads = len(self.gpu_ids) * threads_per_gpu
            self.max_workers = min(self.max_workers, total_gpu_threads)

            logger.warning(f"GPU模式: 使用 {len(self.gpu_ids)} 个GPU，每个GPU {threads_per_gpu} 个线程，总计 {self.max_workers} 个线程")
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

        logger.info(f"初始化多线程OCR服务 (GPU: {self.use_gpu}, GPU IDs: {self.gpu_ids}, "
                   f"语言: {self.lang}, 最大线程: {self.max_workers})")
        logger.info(f"配置文件中设置的最大工作线程数: {OCR_MAX_WORKERS}")
        logger.info(f"实际使用的工作线程数: {self.max_workers}")

    def _detect_gpu_memory(self) -> int:
        """
        检测GPU显存大小(MB)

        Returns:
            int: 显存大小(MB)
        """
        try:
            import torch

            # 检查是否有NVIDIA GPU可用
            if torch.cuda.is_available():
                # 默认使用第一个NVIDIA GPU
                # 设置环境变量，确保使用此GPU
                import os
                os.environ["CUDA_VISIBLE_DEVICES"] = "0"
                gpu_properties = torch.cuda.get_device_properties(0)
                total_memory = gpu_properties.total_memory / (1024 * 1024)  # 转换为MB

                logger.warning(f"使用NVIDIA GPU: {gpu_properties.name}，显存: {total_memory:.0f}MB")

                return int(total_memory)
            else:
                logger.warning("未检测到NVIDIA GPU")
                return False
        except Exception as e:
            logger.warning(f"设置NVIDIA GPU失败: {str(e)}")
            return False

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

        # 如果图片数量过多，考虑是否需要限制处理数量
        if len(image_paths) > 10000:
            logger.warning(f"图片数量过多({len(image_paths)}张)，处理时间可能较长")

        self.total_images = len(image_paths)
        self.processed_images = 0
        self.error_count = 0
        self.is_running = True

        logger.warning(f"在 {image_dir} 及其子目录中找到 {self.total_images} 张图片，收集耗时 {path_collect_time:.2f} 秒")
        logger.warning(f"使用 {self.max_workers} 个工作线程进行处理")

        # 估计处理时间
        est_time_per_image = 0.5  # 假设每张图片处理时间0.5秒
        est_total_time = (self.total_images / self.max_workers) * est_time_per_image if self.max_workers > 0 else 0
        est_hours = int(est_total_time / 3600)
        est_minutes = int((est_total_time % 3600) / 60)
        est_seconds = int(est_total_time % 60)
        logger.warning(f"预计处理时间: {est_hours}小时 {est_minutes}分钟 {est_seconds}秒")

        # 将图片路径放入队列
        for path in image_paths:
            self.image_queue.put(path)

        all_results = []

        # 定期报告进度的线程
        progress_reporting_active = True

        def progress_reporter():
            last_processed = 0
            last_time = time.time()

            while progress_reporting_active and self.is_running:
                time.sleep(30)  # 每30秒报告一次

                current_time = time.time()
                current_processed = self.processed_images

                if current_processed > last_processed:
                    # 计算处理速度
                    time_diff = current_time - last_time
                    images_diff = current_processed - last_processed
                    speed = images_diff / time_diff if time_diff > 0 else 0

                    # 计算剩余时间
                    remaining_images = self.total_images - current_processed
                    est_remaining_time = remaining_images / speed if speed > 0 else 0
                    est_hours = int(est_remaining_time / 3600)
                    est_minutes = int((est_remaining_time % 3600) / 60)
                    est_seconds = int(est_remaining_time % 60)

                    # 计算总进度
                    progress = (current_processed / self.total_images) * 100 if self.total_images > 0 else 0

                    logger.warning(f"进度: {current_processed}/{self.total_images} ({progress:.2f}%), "
                                  f"速度: {speed:.2f} 张/秒, "
                                  f"剩余时间: {est_hours}小时 {est_minutes}分钟 {est_seconds}秒")

                    last_processed = current_processed
                    last_time = current_time

        # 启动进度报告线程
        progress_thread = threading.Thread(target=progress_reporter)
        progress_thread.daemon = True
        progress_thread.start()

        try:
            # 创建线程池
            logger.warning(f"创建线程池，最大工作线程数: {self.max_workers}")
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 创建工作线程，每个线程使用不同的GPU ID
                futures = []
                for i in range(self.max_workers):
                    # 为每个线程分配一个GPU ID
                    gpu_id = self.gpu_ids[i % len(self.gpu_ids)]
                    logger.warning(f"创建工作线程 {i}，使用 GPU {gpu_id}")
                    futures.append(
                        executor.submit(self._worker_thread, i, gpu_id)
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
                self.is_running = False
                logger.warning("等待结果收集线程结束")
                result_collector.join(timeout=5.0)

                # 停止进度报告线程
                progress_reporting_active = False
                progress_thread.join(timeout=1.0)

                # 收集剩余结果
                remaining_results = 0
                while not self.result_queue.empty():
                    result = self.result_queue.get()
                    all_results.append(result)
                    self.result_queue.task_done()
                    remaining_results += 1

                if remaining_results > 0:
                    logger.warning(f"收集了 {remaining_results} 个剩余结果")

        except Exception as e:
            logger.error(f"多线程处理异常: {str(e)}")
            logger.error(traceback.format_exc())
            self.is_running = False
            progress_reporting_active = False

        # 计算总处理时间和速度
        total_time = time.time() - batch_start_time
        avg_speed = self.processed_images / total_time if total_time > 0 else 0
        hours = int(total_time / 3600)
        minutes = int((total_time % 3600) / 60)
        seconds = int(total_time % 60)

        logger.warning(f"多线程处理完成，共处理 {self.processed_images} 张图片，"
                     f"错误 {self.error_count} 张，成功率: {(self.processed_images - self.error_count) / self.total_images:.2%}")
        logger.warning(f"总处理时间: {hours}小时 {minutes}分钟 {seconds}秒，平均速度: {avg_speed:.2f} 张/秒")

        return all_results

    def _worker_thread(self, worker_id: int, gpu_id: int):
        """
        工作线程函数

        Args:
            worker_id: 工作线程ID
            gpu_id: 使用的GPU ID
        """
        logger.warning(f"工作线程 {worker_id} 启动，使用 GPU {gpu_id}")

        # 为每个线程创建一个OCR实例
        ocr = OCRService(use_gpu=self.use_gpu, lang=self.lang, gpu_id=gpu_id)

        # 统计信息
        processed_count = 0
        start_time = time.time()
        last_log_time = start_time

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
                img_start_time = time.time()

                try:
                    # 确保路径正确
                    from django.conf import settings
                    if not os.path.isabs(image_path):
                        # 如果是相对路径，检查文件是否存在
                        full_path = os.path.join(settings.MEDIA_ROOT, image_path)
                        if not os.path.exists(full_path):
                            logger.error(f"线程 {worker_id}: 图片文件不存在: {full_path}")
                            error_result = {
                                "image_path": image_path,
                                "error": f"图片文件不存在: {full_path}",
                                "worker_id": worker_id,
                                "gpu_id": gpu_id
                            }
                            self.result_queue.put(error_result)
                            with self.lock:
                                self.error_count += 1
                            continue

                    # 使用OCRService处理图片
                    result = ocr.recognize_image(image_path)
                    result['worker_id'] = worker_id
                    result['gpu_id'] = gpu_id
                    result['processing_time'] = time.time() - img_start_time

                    # 添加到结果队列
                    self.result_queue.put(result)

                    # 更新处理计数
                    processed_count += 1

                    # 每100张图片或每30秒输出一次进度
                    current_time = time.time()
                    if processed_count % 100 == 0 or (current_time - last_log_time) > 30:
                        elapsed = current_time - start_time
                        speed = processed_count / elapsed if elapsed > 0 else 0
                        logger.warning(f"线程 {worker_id}: 已处理 {processed_count} 张图片，速度 {speed:.2f} 张/秒")
                        last_log_time = current_time

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

        # 线程结束，输出统计信息
        total_time = time.time() - start_time
        avg_speed = processed_count / total_time if total_time > 0 else 0
        logger.warning(f"工作线程 {worker_id} 结束，共处理 {processed_count} 张图片，平均速度 {avg_speed:.2f} 张/秒")

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