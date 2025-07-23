"""
OCR异步任务处理
基于Celery实现的异步OCR任务
"""
import os
import logging
from pathlib import Path
from django.utils import timezone
from django.conf import settings
from celery import shared_task
import traceback

from .models import OCRTask, OCRResult, OCRGitRepository
from .services.ocr_service import OCRService
from .services.multi_thread_ocr import MultiThreadOCR
from .services.git_service import GitService

# 配置日志
logger = logging.getLogger(__name__)


@shared_task
def process_ocr_task(task_id):
    """
    处理OCR任务的异步Celery任务

    Args:
        task_id: OCR任务ID

    Returns:
        Dict: 任务处理结果
    """
    try:
        # 获取任务
        logger.info(f"开始处理OCR任务: {task_id}")

        try:
            task = OCRTask.objects.get(id=task_id)
        except OCRTask.DoesNotExist:
            logger.error(f"任务不存在: {task_id}")
            return {"success": False, "error": "任务不存在"}

        # 更新任务状态
        task.status = 'running'
        task.start_time = timezone.now()
        task.save()

        # 获取配置
        config = task.config
        target_languages = config.get('target_languages', ['ch'])
        image_formats = config.get('image_formats', ['jpg', 'jpeg', 'png', 'bmp', 'tiff', 'tif', 'webp'])
        use_gpu = config.get('use_gpu', True)
        gpu_id = config.get('gpu_id', 0)

        # 确定GPU ID列表
        gpu_ids = [gpu_id]

        # 初始化多线程OCR服务
        ocr_service = MultiThreadOCR(
            use_gpu=use_gpu,
            lang='ch',  # 基础语言模型
            gpu_ids=gpu_ids,
            max_workers=4  # 可从配置中获取
        )

        # 处理不同类型的任务
        try:
            # 本地上传
            if task.source_type == 'upload':
                # 获取上传目录 (task_id的后8位作为上传ID)
                upload_id = f"upload_{task_id[-8:]}"
                upload_dir = os.path.join(settings.MEDIA_ROOT, 'ocr', 'uploads', upload_id)

                if not os.path.exists(upload_dir):
                    raise Exception(f"上传目录不存在: {upload_dir}")

                # 批量识别
                results = ocr_service.recognize_batch(upload_dir, image_formats=image_formats)

                # 处理结果
                _process_results(task, results, target_languages)

            # Git仓库
            elif task.source_type == 'git':
                if not task.git_repository:
                    raise Exception("任务未关联Git仓库")

                # 获取分支
                branch = config.get('branch', 'main')

                # 克隆仓库
                repo_path = GitService.clone_repository(task.git_repository.url, branch, task.id)

                # 批量识别
                results = ocr_service.recognize_batch(repo_path, image_formats=image_formats)

                # 处理结果
                _process_results(task, results, target_languages)

            else:
                raise Exception(f"不支持的来源类型: {task.source_type}")

            # 更新任务状态
            task.status = 'completed'
            task.end_time = timezone.now()
            task.save()

            logger.info(f"任务 {task_id} 处理完成，共处理 {task.total_images} 张图片，"
                       f"匹配 {task.matched_images} 张，匹配率: {task.match_rate:.2f}%")

            return {
                "success": True,
                "task_id": task_id,
                "total_images": task.total_images,
                "matched_images": task.matched_images,
                "match_rate": task.match_rate
            }

        except Exception as e:
            logger.error(f"任务处理失败: {str(e)}")
            logger.error(traceback.format_exc())

            # 更新任务状态
            task.status = 'failed'
            task.end_time = timezone.now()
            task.save()

            return {
                "success": False,
                "error": str(e)
            }

    except Exception as e:
        logger.error(f"处理任务异常: {str(e)}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}


def _process_results(task, results, target_languages):
    """
    处理OCR结果

    Args:
        task: OCR任务
        results: OCR识别结果
        target_languages: 目标语言列表
    """
    # 创建OCR服务用于语言检测
    ocr_service = OCRService()

    # 统计信息
    total_images = len(results)
    matched_images = 0

    for result in results:
        # 跳过错误结果
        if 'error' in result:
            continue

        # 检查语言匹配
        texts = result.get('texts', [])
        has_match = ocr_service.check_language_match(texts, target_languages)
        if has_match:
            matched_images += 1

        # 检测每个文本的语言
        languages = {}
        for text in texts:
            lang_result = ocr_service.detect_language(text)
            for lang, value in lang_result.items():
                if value:
                    languages[lang] = True

        # 保存结果到数据库
        processing_time = result.get('processing_time', 0)
        OCRResult.objects.create(
            task=task,
            image_path=result.get('image_path', ''),
            texts=texts,
            languages=languages,
            has_match=has_match,
            processing_time=processing_time,
        )

    # 更新任务统计信息
    task.total_images = total_images
    task.matched_images = matched_images
    task.match_rate = (matched_images / total_images * 100) if total_images > 0 else 0
    task.save()


@shared_task
def cleanup_old_data(days=30):
    """
    清理旧的OCR数据

    Args:
        days: 保留天数
    """
    from .management.commands.cleanup_ocr_files import Command

    try:
        logger.info(f"开始清理 {days} 天前的OCR文件和数据")
        cmd = Command()
        cmd.handle(days=days)
        logger.info("清理完成")
        return {"success": True}
    except Exception as e:
        logger.error(f"清理数据异常: {str(e)}")
        return {"success": False, "error": str(e)}