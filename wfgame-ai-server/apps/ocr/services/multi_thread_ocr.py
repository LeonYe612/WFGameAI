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

        # 使用缓存池机制，避免为每个线程创建独立的OCR实例
        # 工作线程将从共享的OCR实例池中获取实例，大大提高效率
        self.worker_ocrs: List[Optional[OCRService]] = []
        
        logger.info("使用OCR实例池模式初始化工作线程")
        for i in range(self.max_workers):
            try:
                # 创建OCRService实例，但不立即初始化PaddleOCR
                # 实际的PaddleOCR实例将在处理时从缓存池获取
                ocr_service = OCRService(lang=self.lang)
                
                # 若任务配置指定了预设，则应用到服务配置中
                try:
                    preset_name = ''
                    if isinstance(self.task.config, dict):
                        preset_name = self.task.config.get('smart_ocr_preset', '')
                    if preset_name:
                        # 应用预设到OCRService的参数配置中
                        self._apply_preset_to_ocr_service(ocr_service, preset_name)
                except Exception as _preset_err:
                    logger.warning(f"应用智能OCR预设失败: {_preset_err}")
                
                self.worker_ocrs.append(ocr_service)
                logger.debug(f"初始化工作线程 {i} 的OCR服务成功")
                
            except Exception as init_err:
                logger.error(f"初始化OCR服务失败(线程索引 {i}): {init_err}")
                self.worker_ocrs.append(None)
        
        # 预热缓存：如果配置启用，预先创建常用的OCR实例
        if config.getboolean('ocr', 'ocr_warm_cache_on_startup', fallback=False):
            self._warm_ocr_cache()

    def _apply_preset_to_ocr_service(self, ocr_service: OCRService, preset_name: str) -> None:
        """
        应用OCR预设到OCRService实例
        
        Args:
            ocr_service: OCRService实例
            preset_name: 预设名称 (high_speed/balanced/high_precision)
        """
        preset = preset_name.lower()
        
        if preset == 'high_speed':
            # 高速模式：降低精度换速度
            ocr_service.text_det_limit_type = 'max'
            ocr_service.text_det_limit_side_len = 960
            ocr_service.text_det_thresh = 0.5
            ocr_service.text_det_box_thresh = 0.7
            ocr_service.text_det_unclip_ratio = 1.0
            ocr_service.smart_ocr_dynamic_limit_enabled = False
            logger.info(f"应用高速模式预设到OCR服务")
            
        elif preset == 'high_precision':
            # 高精度模式：提升精度
            ocr_service.text_det_limit_type = 'min'
            ocr_service.text_det_limit_side_len = 1280
            ocr_service.text_det_thresh = 0.2
            ocr_service.text_det_box_thresh = 0.4
            ocr_service.text_det_unclip_ratio = 2.0
            ocr_service.smart_ocr_dynamic_limit_enabled = False
            logger.info(f"应用高精度模式预设到OCR服务")
            
        else:
            # balanced 或其他：均衡模式
            ocr_service.text_det_limit_side_len = 960
            ocr_service.text_det_thresh = 0.3
            ocr_service.text_det_box_thresh = 0.6
            ocr_service.text_det_unclip_ratio = 1.5
            ocr_service.smart_ocr_dynamic_limit_enabled = True
            logger.info(f"应用均衡模式预设到OCR服务")
    
    def _warm_ocr_cache(self) -> None:
        """
        智能预热OCR缓存池，预先创建最常用的OCR实例
        
        预热策略：
        1. 如果禁用动态切换，只预热默认配置（1个实例=2次模型创建）
        2. 如果启用动态切换，预热max和min两种配置（2个实例=4次模型创建）
        """
        try:
            logger.info("开始智能预热OCR缓存池")
            
            # 从第一个有效的OCR服务获取实例池
            valid_ocr_service = None
            for ocr_service in self.worker_ocrs:
                if ocr_service is not None:
                    valid_ocr_service = ocr_service
                    break
            
            if valid_ocr_service is None:
                logger.warning("没有找到有效的OCR服务，跳过缓存预热")
                return
            
            # 基础配置参数
            base_config = {
                'lang': self.lang,
                'text_det_thresh': valid_ocr_service.text_det_thresh,
                'text_det_box_thresh': valid_ocr_service.text_det_box_thresh,
                'text_det_unclip_ratio': valid_ocr_service.text_det_unclip_ratio,
                'text_det_limit_side_len': valid_ocr_service.text_det_limit_side_len,
            }
            
            # 根据是否启用动态切换决定预热策略
            if valid_ocr_service.smart_ocr_dynamic_limit_enabled:
                # 启用动态切换：预热max和min两种配置
                configs_to_warm = [
                    {**base_config, 'limit_type': 'max'},  # 宽图优化
                    {**base_config, 'limit_type': 'min'},  # 高图优化
                ]
                logger.info("动态切换已启用，预热max和min两种配置")
            else:
                # 禁用动态切换：只预热默认配置
                configs_to_warm = [
                    {**base_config, 'limit_type': valid_ocr_service.text_det_limit_type}
                ]
                logger.info(f"动态切换已禁用，只预热默认配置: {valid_ocr_service.text_det_limit_type}")
            
            # 执行预热
            warmed_count = 0
            for config in configs_to_warm:
                try:
                    valid_ocr_service.ocr_pool.get_ocr_instance(**config)
                    warmed_count += 1
                    logger.info(f"✅ 预热OCR实例成功: {config['limit_type']} (第{warmed_count}个)")
                except Exception as e:
                    logger.warning(f"❌ 预热OCR实例失败: {config['limit_type']}, 错误: {e}")
            
            # 获取缓存统计信息
            cache_info = valid_ocr_service.ocr_pool.get_cache_info()
            logger.info(f"🎯 OCR缓存池预热完成: 预热{warmed_count}个实例, 预计创建{warmed_count*2}个模型, 缓存统计: {cache_info}")
            
        except Exception as e:
            logger.error(f"OCR缓存池预热失败: {e}")

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
        seconds = total_time % 60  # 保留小数

        logger.warning(
            f"{'单' if self.max_workers == 1 else '多'}线程处理完成，共处理 {self.processed_images} 张图片，错误 "
            f"{self.error_count} 张，成功率: "
            f"{(self.processed_images - self.error_count) / self.total_images:.2%}"
        )
        logger.warning(
            f"总处理时间: {hours}小时 {minutes}分钟 {seconds:.2f}秒，平均速度: "
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
        result = None
        update_func = None
        counter_attr = None

        try:
            full_path = self._get_full_image_path(relative_path)

            if not os.path.exists(full_path):
                logger.error(f"图片文件不存在: {full_path}")
                result = {
                    "image_path": relative_path,
                    "error": f"图片文件不存在: {full_path}",
                    "worker_id": worker_id,
                    "has_match": False,
                    "languages": {},
                }
                update_func = self.update_progress_fail
                counter_attr = "error_count"
            else:
                #  调用OCR识别
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
                    update_func = self.update_progress_fail
                    counter_attr = "error_count"
                else:
                    languages = {lang: True for lang in (self.match_languages or ['ch'])
                                 if OCRService.check_language_match(texts, lang)}
                    result['languages'] = languages
                    result['has_match'] = bool(languages)
                    result['confidence'] = result.get('confidence', 0.95)
                    result['processing_time'] = result.get('time_cost', 0)
                    update_func = lambda: self.update_progress_success(result['has_match'])
                    counter_attr = "processed_images"

        except Exception as e:
            logger.error(f"处理图片失败 {relative_path}: {e}")
            result = {
                "image_path": relative_path,
                "error": str(e),
                "worker_id": worker_id,
                "has_match": False,
                "languages": {},
            }
            update_func = self.update_progress_fail
            counter_attr = "error_count"

        # 统一处理队列和进度
        try:
            # 线程安全地更新已处理图片计数
            with self.lock:
                self.processed_images += 1

            self.result_queue.put(result)
            if counter_attr:
                with self.lock:
                    setattr(self, counter_attr, getattr(self, counter_attr) + 1)
            if update_func:
                update_func()
        except Exception as e:
            logger.error(f"result_queue.put失败: {e}")

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

                # 只调用一次图片处理逻辑
                self._process_single_image(ocr, relative_path, worker_id)
                processed_count += 1

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
                processing_time=result.get('processing_time', 0),
                pic_resolution=result.get('pic_resolution', '')
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