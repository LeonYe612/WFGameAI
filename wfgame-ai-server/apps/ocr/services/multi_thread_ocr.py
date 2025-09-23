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
                
               
                self.worker_ocrs.append(ocr_service)
                logger.debug(f"初始化工作线程 {i} 的OCR服务成功")
                
            except Exception as init_err:
                logger.error(f"初始化OCR服务失败(线程索引 {i}): {init_err}")
                self.worker_ocrs.append(None)
        
        # 预热缓存：如果配置启用，预先创建常用的OCR实例
        if config.getboolean('ocr', 'ocr_warm_cache_on_startup', fallback=False):
            self._warm_ocr_cache()


    def _warm_ocr_cache(self) -> None:
        """
        智能预热OCR缓存池，预先创建最常用的OCR实例
        
        预热策略：
        1. 如果禁用动态切换，只预热默认配置（1个实例=2次模型创建）
        2. 如果启用动态切换，预热max和min两种配置（2个实例=4次模型创建）
        """
        try:
            # 动态获取轮数，避免误导
            try:
                tmp_service = OCRService(lang=self.lang)
                round_num = len(tmp_service._default_round_param_sets())
            except Exception:
                round_num = 0
            logger.info(f"开始预热OCR缓存池(基于内置{round_num}轮参数)")
            
            # 从第一个有效的OCR服务获取实例池
            valid_ocr_service = None
            for ocr_service in self.worker_ocrs:
                if ocr_service is not None:
                    valid_ocr_service = ocr_service
                    break
            
            if valid_ocr_service is None:
                logger.warning("没有找到有效的OCR服务，跳过缓存预热")
                return
            
            # 使用服务内置的参数集进行预热（仅按需创建实例，不涉及文本阈值属性）
            try:
                param_sets = valid_ocr_service._default_round_param_sets()
            except Exception:
                param_sets = []
            configs_to_warm = []
            for rp in param_sets:
                try:
                    configs_to_warm.append({
                        'lang': self.lang,
                        'limit_type': str(rp.get('text_det_limit_type', 'max')),
                        'text_det_thresh': float(rp.get('text_det_thresh', 0.3)),
                        'text_det_box_thresh': float(rp.get('text_det_box_thresh', 0.6)),
                        'text_det_unclip_ratio': float(rp.get('text_det_unclip_ratio', 1.5)),
                        'text_det_limit_side_len': int(rp.get('text_det_limit_side_len', 960)),
                        'use_textline_orientation': bool(rp.get('use_textline_orientation', False)),
                    })
                except Exception:
                    continue
            
            # 执行预热
            warmed_count = 0
            for config in configs_to_warm:
                try:
                    valid_ocr_service.ocr_pool.get_ocr_instance(**config)
                    warmed_count += 1
                    logger.info(f"预热OCR实例成功: {config['limit_type']} side={config['text_det_limit_side_len']} (第{warmed_count}个)")
                except Exception as e:
                    logger.warning(f"预热OCR实例失败: {config.get('limit_type')}, 错误: {e}")
            
            # 获取缓存统计信息
            cache_info = valid_ocr_service.ocr_pool.get_cache_info()
            logger.info(f"OCR缓存池预热完成: 预热{warmed_count}个实例, 缓存统计: {cache_info}")
            
        except Exception as e:
            logger.error(f"OCR缓存池预热失败: {e}")


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
                pic_resolution=result.get('pic_resolution', ''),
                team_id=self.task.team_id
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