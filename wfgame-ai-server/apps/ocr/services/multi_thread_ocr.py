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
from ..models import OCRResult

# 配置日志
logger = logging.getLogger(__name__)

# 读取配置
# config = configparser.ConfigParser()
# config.read(settings.BASE_DIR.parent / 'config.ini', encoding='utf-8')
config = settings.CFG._config

# OCR并发相关配置
OCR_MAX_WORKERS = config.getint('ocr', 'ocr_max_workers', fallback=4)


class MultiThreadOCR:
    """多线程OCR处理类"""

    def __init__(self,
                 task,
                 lang: str = 'ch',
                 max_workers: int = None,
                 predict_save: bool = False, # 是否保存预测可视化图片/JSON 结果
                 match_languages: Optional[List[str]] = None
                 ):
        """
        初始化多线程OCR处理

        Args:
            lang (str): OCR识别模型语言（用于 PaddleOCR 初始化，例如 'ch'）。
            max_workers (int): 最大工作线程数。
            predict_save (bool): 是否保存预测可视化图片/JSON 结果。
            match_languages (list[str] | None): 动态命中判定所用语言码列表，
                若为 None 或空，则默认 ['ch']。命中逻辑与 OCR 识别语言解耦。
        """
        self.task = task
        # 初始化 Redis 助手
        self.redis_helper = settings.REDIS
        self.lang = lang
        self.match_languages = match_languages or ['ch']
        self.max_workers = max_workers or OCR_MAX_WORKERS
        self.predict_save = predict_save  # 是否保存预测可视化/JSON 结果
        # 安全初始化任务ID：若未通过构造传入，则尝试从 task.id 获取
        try:
            if not hasattr(self, 'task_id') or self.task_id is None:
                self.task_id = str(getattr(task, 'id', '')) if getattr(task, 'id', None) is not None else None
        except Exception:
            self.task_id = None

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
                # 若任务配置指定了预设，则运行时应用预设（前端可传入 high_speed/balanced/high_precision）
                try:
                    preset_name = ''
                    if isinstance(self.task.config, dict):
                        preset_name = self.task.config.get('smart_ocr_preset', '')
                    if preset_name:
                        ocr_inst.set_smart_ocr_preset(preset_name)
                except Exception as _preset_err:
                    logger.warning(f"应用智能OCR预设失败: {_preset_err}")
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

    def _collect_image_paths(self, image_dir: str, image_formats: List[str]) -> List[str]:
        """
        收集目录中的图片路径，统一返回相对路径

        Args:
            image_dir: 图片目录
            image_formats: 图片格式列表

        Returns:
            List[str]: 相对于MEDIA_ROOT的图片路径列表
        """
        image_extensions = set()
        for ext in image_formats:
            image_extensions.add(f".{ext.lower()}")
            image_extensions.add(f".{ext.upper()}")

        image_paths = []
        media_root = settings.MEDIA_ROOT

        # 确保media_root以/结尾
        if not media_root.endswith(os.sep):
            media_root += os.sep

        logger.info(f"媒体根目录: {media_root}")
        logger.info(f"搜索目录: {image_dir}")

        for path in Path(image_dir).rglob("*"):
            if path.is_file() and path.suffix in image_extensions:
                absolute_path = str(path.resolve())

                # 统一转换为相对路径
                if absolute_path.startswith(media_root):
                    relative_path = os.path.relpath(absolute_path, media_root)
                    relative_path = relative_path.replace('\\', '/')  # 统一使用正斜杠
                    image_paths.append(relative_path)
                    logger.debug(f"添加图片: {relative_path}")
                else:
                    logger.warning(f"跳过不在媒体目录下的图片: {absolute_path}")

        logger.info(f"收集到 {len(image_paths)} 张图片")
        return image_paths

    def _get_full_image_path(self, relative_path: str) -> str:
        """
        根据相对路径获取完整的绝对路径

        Args:
            relative_path: 相对于MEDIA_ROOT的路径

        Returns:
            str: 完整的绝对路径
        """
        return os.path.join(settings.MEDIA_ROOT, relative_path)

    def recognize_batch(self, image_dir: str, image_formats: List[str] = None) -> List[Dict]:
        """
        多线程批量识别图片

        Args:
            image_dir: 图片目录
            image_formats: 图片格式列表

        Returns:
            List[Dict]: 识别结果列表
        """
        all_results = []
        batch_start_time = time.time()

        if image_formats is None:
            image_formats = ['jpg', 'jpeg', 'png', 'bmp', 'tiff', 'tif', 'webp']

        # 收集所有图片路径
        logger.warning(f"开始收集图片路径: {image_dir}")
        path_collect_start = time.time()
        image_paths = self._collect_image_paths(image_dir, image_formats)
        path_collect_time = time.time() - path_collect_start

        self.total_images = len(image_paths)
        self.processed_images = 0
        self.error_count = 0
        self.is_running = True

        # 初始化redis
        self.init_progress(self.total_images)

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

        # 启动结果收集线程
        collector_thread = threading.Thread(target=self._result_collector, args=(all_results,))
        collector_thread.start()

        # 单线程模式特殊处理
        if self.max_workers == 1:
            logger.warning("使用单线程模式处理图片，避免并发问题")
            self._process_single_thread()
        else:
            # 多线程模式处理
            self._process_multi_thread()

        # 等待所有图片处理完
        self.is_running = False
        self.result_queue.join()
        collector_thread.join()

        # 完成任务
        self.finish_progress('completed')

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

    def _process_single_thread(self):
        """单线程处理逻辑（统一复用 _process_single_image）
        
        说明:
            早前实现中部分图片未经过 `_process_single_image`，
            导致 `languages/has_match` 未设置且未更新进度统计。
            此处统一改为所有图片均走 `_process_single_image`，
            确保命中判定与 Redis 进度计数一致。
        """
        try:
            ocr = self.worker_ocrs[0]
            if ocr is None:
                logger.error("OCR实例初始化失败，无法处理图片")
                return

            while not self.image_queue.empty():
                try:
                    relative_path = self.image_queue.get(block=False)
                    # 统一使用单张图片处理函数，内部负责设置 has_match/languages
                    self._process_single_image(ocr, relative_path, 0)
                except queue.Empty:
                    break
                except Exception as e:
                    self.update_progress_exception()
                    logger.error(f"单线程处理异常: {e}")
                    logger.error(traceback.format_exc())
                    break
        except Exception as e:
            self.update_progress_exception()
            logger.error(f"单线程处理逻辑失败: {e}")
            logger.error(traceback.format_exc())

    def _process_multi_thread(self):
        """多线程处理逻辑"""
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
            logger.warning(f"创建线程池，最大工作线程数: {self.max_workers}")
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = []
                for i in range(self.max_workers):
                    logger.warning(f"创建工作线程 {i}")
                    futures.append(executor.submit(self._worker_thread, i))

                # 等待所有工作线程完成
                logger.warning("等待所有工作线程完成")
                self.update_status('running')
                concurrent.futures.wait(futures)
                logger.warning("所有工作线程已完成")

        except Exception as e:
            self.update_progress_exception()
            logger.error(f"多线程处理异常: {str(e)}")
            logger.error(traceback.format_exc())
        finally:
            progress_reporting_active = False

    def _process_single_image(self, ocr: OCRService, relative_path: str, worker_id: int):
        logger.debug(f"处理图片: {relative_path}")
        img_start_time = time.time()

        try:
            full_path = self._get_full_image_path(relative_path)

            if not os.path.exists(full_path):
                logger.error(f"图片文件不存在: {full_path}")
                error_result = {
                    "image_path": relative_path,
                    "error": f"图片文件不存在: {full_path}",
                    "worker_id": worker_id,
                    "has_match": False,
                    "languages": {},
                }
                try:
                    self.result_queue.put(error_result)
                    self.update_progress_fail()
                    with self.lock:
                        self.error_count += 1
                except Exception as e:
                    logger.error(f"result_queue.put失败: {e}")
                return

            result = ocr.recognize_image(full_path, predict_save=self.predict_save)
            result['worker_id'] = worker_id
            result['image_path'] = relative_path
            result['time_cost'] = time.time() - img_start_time

            texts = result.get('texts', [])
            error = result.get('error', None)

            if error or not texts:
                result['has_match'] = False
                result['languages'] = {}
                result['confidence'] = 0.0
                result['processing_time'] = 0
                try:
                    self.result_queue.put(result)
                    with self.lock:
                        self.processed_images += 1
                    self.update_progress_fail()
                except Exception as e:
                    logger.error(f"result_queue.put失败: {e}")
                return
            else:
                languages = {lang: True for lang in (self.match_languages or ['ch'])
                             if OCRService.check_language_match(texts, lang)}
                result['languages'] = languages
                result['has_match'] = bool(languages)
                result['confidence'] = result.get('confidence', 0.95)
                result['processing_time'] = result.get('time_cost', 0)
                try:
                    self.result_queue.put(result)
                    with self.lock:
                        self.processed_images += 1
                    self.update_progress_success(result['has_match'])
                except Exception as e:
                    logger.error(f"result_queue.put失败: {e}")
                return

        except Exception as e:
            logger.error(f"处理图片失败 {relative_path}: {e}")
            error_result = {
                "image_path": relative_path,
                "error": str(e),
                "worker_id": worker_id,
                "has_match": False,
                "languages": {},
            }
            try:
                self.result_queue.put(error_result)
                with self.lock:
                    self.error_count += 1
                self.update_progress_exception()
            except Exception as e:
                logger.error(f"result_queue.put失败: {e}")
            return

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

        while self.is_running:
            try:
                try:
                    relative_path = self.image_queue.get(block=False)  # 队列中存储的是相对路径
                except queue.Empty:
                    break

                self._process_single_image(ocr, relative_path, worker_id)
                processed_count += 1
                logger.debug(f"线程 {worker_id}: 处理图片 {relative_path}")
                img_start_time = time.time()

                try:
                    from django.conf import settings
                    if not os.path.isabs(relative_path):
                        full_path = os.path.join(settings.MEDIA_ROOT, relative_path)
                        if not os.path.exists(full_path):
                            logger.error(
                                f"线程 {worker_id}: 图片文件不存在: {full_path}"
                            )
                            error_result = {
                                "image_path": relative_path,
                                "error": f"图片文件不存在: {full_path}",
                                "worker_id": worker_id
                            }
                            self.result_queue.put(error_result)
                            with self.lock:
                                self.error_count += 1
                            continue

                    # 识别
                    result = ocr.recognize_image(relative_path, predict_save=self.predict_save, task_id=self.task_id)
                    result['worker_id'] = worker_id
                    # 统一字段命名，与OCRService保持一致
                    result['time_cost'] = time.time() - img_start_time

                    self.result_queue.put(result)

                    processed_count += 1
                    # todo 更新redis 对应任务处理图片数量
                    with self.lock:
                        self.processed_images += 1

                except Exception as e:
                    logger.error(
                        f"线程 {worker_id}: 处理失败 {relative_path}: {e}"
                    )
                    error_result = {
                        "image_path": relative_path,
                        "error": str(e),
                        "worker_id": worker_id
                    }
                    self.result_queue.put(error_result)
                    with self.lock:
                        self.error_count += 1

            except Exception as e:
                self.update_progress_exception()
                logger.error(f"线程 {worker_id}: 未知异常: {e}")
                logger.error(traceback.format_exc())
                break

        logger.debug(f"线程 {worker_id} 完成，处理 {processed_count} 张图片")

    def _result_collector(self, all_results: List[Dict]):
        """结果收集线程"""
        logger.warning("结果收集线程启动")
        buffer = []
        # todo 改成百分比存图，但是可能会导致一次插入数据过多（多任务执行会涉及到表锁）
        batch_size = settings.CFG.getint('ocr', 'ocr_batch_size', fallback=10)
        flush_interval = settings.CFG.getint('ocr', 'ocr_flush_interval', fallback=3)
        last_flush = time.time()

        while self.is_running or not self.result_queue.empty():
            try:
                try:
                    result = self.result_queue.get(timeout=3.0)
                except queue.Empty:
                    continue
                buffer.append(result)
                # 处理结果
                all_results.append(result)
                # 如果设置了结果回调，则调用
                if self.result_callback:
                    self.result_callback(result)

                # 满足批量或定时条件就写库
                if len(buffer) >= batch_size or (time.time() - last_flush) > flush_interval:
                    if buffer:
                        self.bulk_insert_to_db(buffer)
                        buffer.clear()
                        last_flush = time.time()
                # 标记结果处理完成
                self.result_queue.task_done()
            except Exception as e:
                logger.error(f"结果收集线程异常: {str(e)}")

        # 处理剩余未写入的数据
        if buffer:
            self.bulk_insert_to_db(buffer)
        logger.warning("结果收集线程结束")

    def bulk_insert_to_db(self, results):
        """
        批量插入OCR识别结果到数据库
        Args:
            results: List[Dict]，每个dict为一张图片的识别结果
        """
        objs = []
        for result in results:
            obj = OCRResult(
                task=self.task,
                image_path=result.get('image_path', '').replace('\\', '/'),
                texts=result.get('texts', []),
                languages=result.get('languages', {}),
                has_match=result.get('has_match', False),
                confidence=result.get('confidence', 0.0),
                processing_time=result.get('processing_time', 0)
            )
            objs.append(obj)
        if objs:
            OCRResult.objects.bulk_create(objs)
            logger.warning(f"批量插入 {len(objs)} 条OCR结果到数据库")
        # todo 如果考虑继续读 task 数据，需要在此处更新 self.task 实例相关统计字段

    def init_progress(self, total_images: int):
        """初始化任务进度"""
        key = f'ai_ocr_progress:{self.task.id}'
        progress_data = {
            'task_id': str(self.task.id), # 任务ID
            'total': total_images, # 总图片数
            'executed': 0, # 已处理图片数
            'matched': 0, # 目标语言匹配图片数
            'success': 0, # 识别到文本内容图片数
            'fail': 0, # 未识别到文本内容图片数
            'exception': 0, # 处理异常图片数
            'match_rate': 0.0, # 匹配率（后续只在finish_progress中更新）
            'status': 'pending', # 任务状态
            'worker_nums': self.max_workers, # ，工作线程数
            'start_time': time.time() # 任务开始时间
        }
        return self.redis_helper.hmset(key, progress_data)

    def update_progress_success(self, result=False):
        """更新成功计数（原子操作）"""
        key = f'ai_ocr_progress:{self.task.id}'
        pipe = self.redis_helper.pipeline()
        pipe.hincrby(key, 'executed', 1)
        pipe.hincrby(key, 'success', 1)
        # 只要有匹配，matched 计数+1
        if result:
            pipe.hincrby(key, 'matched', 1)
        return pipe.execute()

    def update_progress_fail(self):
        """更新失败计数（原子操作）"""
        key = f'ai_ocr_progress:{self.task.id}'
        pipe = self.redis_helper.pipeline()
        pipe.hincrby(key, 'executed', 1)
        pipe.hincrby(key, 'fail', 1)
        return pipe.execute()

    def update_progress_exception(self):
        """更新异常计数（原子操作）"""
        key = f'ai_ocr_progress:{self.task.id}'
        pipe = self.redis_helper.pipeline()
        pipe.hincrby(key, 'executed', 1)
        pipe.hincrby(key, 'exception', 1)
        return pipe.execute()

    def finish_progress(self, status='completed'):
        """完成任务 & task统计结果更新（只查Redis，不回表）"""
        key = f'ai_ocr_progress:{self.task.id}'
        progress_data = self.redis_helper.hgetall(key)

        total_images = int(progress_data.get('total', 0))
        executed_images = int(progress_data.get('executed', 0))
        success_images = int(progress_data.get('success', 0))
        fail_images = int(progress_data.get('fail', 0))
        exception_images = int(progress_data.get('exception', 0))
        matched_images = int(progress_data.get('matched', 0))
        match_rate = (matched_images / total_images * 100) if total_images > 0 else 0

        # 更新 Redis 进度状态
        self.redis_helper.hmset(key, {
            'status': status,
            'end_time': time.time(),
            'match_rate': round(match_rate, 2)
        })

        # 更新数据库任务状态
        self.task.status = status
        self.task.end_time = timezone.now()
        self.task.total_images = total_images
        self.task.processed_images = executed_images
        self.task.success_images = success_images
        self.task.fail_images = fail_images
        self.task.exception_images = exception_images
        self.task.matched_images = matched_images
        self.task.match_rate = round(match_rate, 2)
        self.task.save()

        logger.warning(
            f"任务 {self.task.id} 完成统计: "
            f"总计 {total_images} 张, 执行 {executed_images} 张, "
            f"成功 {success_images} 张, 失败 {fail_images} 张, "
            f"异常 {exception_images} 张, 匹配 {matched_images} 张, "
            f"匹配率 {match_rate:.2f}%"
        )

        return {
            'total_images': total_images,
            'executed_images': executed_images,
            'success_images': success_images,
            'fail_images': fail_images,
            'exception_images': exception_images,
            'matched_images': matched_images,
            'match_rate': round(match_rate, 2),
            'status': status
        }

    def update_status(self, status: str):
        """更新任务状态"""
        key = f'ai_ocr_progress:{self.task.id}'
        self.redis_helper.hset(key, 'status', status)
        self.task.status = status
        self.task.save()
        logger.warning(f"任务 {self.task.id} 状态更新为: {status}")
        return status

    def get_progress(self):
        """获取当前进度信息（带计算字段）"""
        key = f'ai_ocr_progress:{self.task.id}'
        progress_data = self.redis_helper.hgetall(key)
        total_images = int(progress_data.get('total', 0))
        executed_images = int(progress_data.get('executed', 0))
        matched_images = int(progress_data.get('matched', 0))
        match_rate = (matched_images / total_images * 100) if total_images > 0 else 0

        # 返回带计算字段的进度信息
        return {
            'total_images': total_images,
            'executed_images': executed_images,
            'matched_images': matched_images,
            'match_rate': round(match_rate, 2),
            'success_images': int(progress_data.get('success', 0)),
            'fail_images': int(progress_data.get('fail', 0)),
            'exception_images': int(progress_data.get('exception', 0)),
            'status': progress_data.get('status', ''),
            'start_time': float(progress_data.get('start_time', 0)),
            'end_time': float(progress_data.get('end_time', 0)),
        }