from celery import shared_task
from .services import send_message, SSEEvent
from apps.ocr.models import OCRTask
from apps.ocr.serializers import OCRTaskSerializer
from django.core.cache import cache
import time
import logging

logger = logging.getLogger(__name__)


def notify_ocr_task_progress(update_vals: dict, debounce: bool = False, delay: int = 2):
    """
    发送 OCR任务 进度通知

    :param update_vals: 更新值字典，包含进度等信息
    :param debounce: 是否启用防抖
    :param delay: 防抖延迟时间（秒）
    """
    if debounce:
        return notify_ocr_task_progress_debounced(update_vals, delay=delay)
    else:
        return notify_ocr_task_progress_immediately(update_vals)


@shared_task()
def notify_ocr_task_progress_immediately(update_vals: dict):
    """
    发送 OCR任务 进度通知
    :param update_vals: 更新值字典，包含进度等信息
    """
    task_id = update_vals.pop('id', None)
    if not task_id:
        logger.warning("OCR task progress notification called without task_id")
        return

    try:
        # 更新数据库
        task = OCRTask.objects.all_teams().filter(id=task_id).first()
        if not task:
            logger.warning(f"OCR task with id {task_id} not found")
            return

        for key, value in update_vals.items():
            if hasattr(task, key):
                setattr(task, key, value)
        task.save()

        # 发送通知
        send_message(OCRTaskSerializer(task).data, SSEEvent.OCR_TASK_UPDATE.value)
        
    except Exception as exc:
        logger.error(f"Error in OCR task progress notification: {exc}")


def notify_ocr_task_progress_debounced(update_vals: dict, delay: int = 3):
    """
    防抖版本的 OCR 任务进度通知 - 在投递前进行防抖
    
    :param update_vals: 更新值字典
    :param delay: 防抖延迟时间（秒）
    :return: 任务结果或 None(如果被防抖跳过)
    """
    task_id = update_vals.get('id')
    if not task_id:
        logger.warning("OCR task debounced notification called without task_id")
        return

    cache_key = f"ocr_task_debounce_{task_id}"
    current_time = time.time()
    
    # 检查上次调用时间
    last_call_time = cache.get(cache_key)
    
    if last_call_time:
        time_since_last_call = current_time - last_call_time
        if time_since_last_call < delay:
            # 在防抖时间内，跳过这次调用
            logger.debug(f"OCR task {task_id} notification debounced")
            return None
    
    # 更新最后调用时间
    cache.set(cache_key, current_time, timeout=delay * 2)
    
    # 投递任务
    return notify_ocr_task_progress_immediately(update_vals.copy())

