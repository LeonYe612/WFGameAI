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
from .services.gitlab import (
    DownloadResult,
    GitLabConfig,
    GitLabService,
)

# 配置日志
logger = logging.getLogger(__name__)


# @shared_task
# def process_ocr_task_old(task_id):
#     """
#     处理OCR任务的异步Celery任务

#     Args:
#         task_id: OCR任务ID

#     Returns:
#         Dict: 任务处理结果
#     """
#     try:
#         # 获取任务
#         logger.info(f"开始处理OCR任务: {task_id}")

#         try:
#             task = OCRTask.objects.get(id=task_id)
#         except OCRTask.DoesNotExist:
#             logger.error(f"任务不存在: {task_id}")
#             return {"success": False, "error": "任务不存在"}

#         # 更新任务状态
#         task.status = "running"
#         task.start_time = timezone.now()
#         task.save()

#         # 获取配置
#         config = task.config
#         target_languages = config.get("target_languages", ["ch"])
#         image_formats = config.get(
#             "image_formats", ["jpg", "jpeg", "png", "bmp", "tiff", "tif", "webp"]
#         )
#         use_gpu = config.get("use_gpu", True)
#         gpu_id = config.get("gpu_id", 0)

#         # 确定GPU ID列表
#         gpu_ids = [gpu_id]

#         # 初始化多线程OCR服务
#         ocr_service = MultiThreadOCR(
#             use_gpu=use_gpu,
#             lang="ch",  # 基础语言模型
#             gpu_ids=gpu_ids,
#             max_workers=4,  # 可从配置中获取
#         )

#         # 处理不同类型的任务
#         try:
#             # 本地上传
#             if task.source_type == "upload":
#                 # 获取上传目录 (task_id的后8位作为上传ID)
#                 upload_id = f"upload_{task_id[-8:]}"
#                 upload_dir = os.path.join(
#                     settings.MEDIA_ROOT, "ocr", "uploads", upload_id
#                 )

#                 if not os.path.exists(upload_dir):
#                     raise Exception(f"上传目录不存在: {upload_dir}")

#                 # 批量识别
#                 results = ocr_service.recognize_batch(
#                     upload_dir, image_formats=image_formats
#                 )

#                 # 处理结果
#                 _process_results(task, results, target_languages)

#             # Git仓库
#             elif task.source_type == "git":
#                 if not task.git_repository:
#                     raise Exception("任务未关联Git仓库")

#                 # 获取分支
#                 branch = config.get("branch", "main")

#                 # 克隆仓库
#                 repo_path = GitService.clone_repository(
#                     task.git_repository.url, branch, task.id
#                 )

#                 # 批量识别
#                 results = ocr_service.recognize_batch(
#                     repo_path, image_formats=image_formats
#                 )

#                 # 处理结果
#                 _process_results(task, results, target_languages)

#             else:
#                 raise Exception(f"不支持的来源类型: {task.source_type}")

#             # 更新任务状态
#             task.status = "completed"
#             task.end_time = timezone.now()
#             task.save()

#             logger.info(
#                 f"任务 {task_id} 处理完成，共处理 {task.total_images} 张图片，"
#                 f"匹配 {task.matched_images} 张，匹配率: {task.match_rate:.2f}%"
#             )

#             return {
#                 "success": True,
#                 "task_id": task_id,
#                 "total_images": task.total_images,
#                 "matched_images": task.matched_images,
#                 "match_rate": task.match_rate,
#             }

#         except Exception as e:
#             logger.error(f"任务处理失败: {str(e)}")
#             logger.error(traceback.format_exc())

#             # 更新任务状态
#             task.status = "failed"
#             task.end_time = timezone.now()
#             task.save()

#             return {"success": False, "error": str(e)}

#     except Exception as e:
#         logger.error(f"处理任务异常: {str(e)}")
#         logger.error(traceback.format_exc())
#         return {"success": False, "error": str(e)}


# @shared_task
# def process_git_ocr_task(task_id, task_config=None):
#     """
#     专门处理Git仓库OCR的异步Celery任务
#     支持使用令牌进行Git仓库认证

#     Args:
#         task_id: OCR任务ID
#         task_config: 任务配置，可能包含令牌

#     Returns:
#         Dict: 任务处理结果
#     """
#     try:
#         # 获取任务
#         logger.info(f"开始处理Git OCR任务: {task_id}")

#         try:
#             task = OCRTask.objects.get(id=task_id)
#         except OCRTask.DoesNotExist:
#             logger.error(f"任务不存在: {task_id}")
#             return {"success": False, "error": "任务不存在"}

#         # 更新任务状态
#         task.status = "running"
#         task.start_time = timezone.now()
#         task.save()

#         # 获取配置
#         config = task_config or task.config
#         languages = config.get("languages", ["ch"])
#         image_formats = config.get(
#             "image_formats", ["jpg", "jpeg", "png", "bmp", "tiff", "tif", "webp"]
#         )
#         use_gpu = config.get("use_gpu", True)
#         gpu_id = config.get("gpu_id", 0)
#         token = config.get("token")  # 获取令牌
#         skip_ssl_verify = config.get("skip_ssl_verify", False)  # 获取是否跳过SSL验证

#         if skip_ssl_verify:
#             logger.warning("⚠️ 任务使用了跳过SSL验证选项，这可能存在安全风险")

#         # 分支
#         branch = config.get("branch", "main")

#         # 确定GPU ID列表
#         gpu_ids = [gpu_id]

#         # 初始化多线程OCR服务
#         ocr_service = MultiThreadOCR(
#             use_gpu=use_gpu,
#             lang="ch",  # 基础语言模型
#             gpu_ids=gpu_ids,
#             max_workers=4,  # 可从配置中获取
#         )

#         try:
#             if not task.git_repository:
#                 raise Exception("任务未关联Git仓库")

#             # 克隆仓库，使用令牌
#             logger.info(
#                 f"开始克隆仓库，使用{'令牌' if token else '无令牌'}，{'禁用' if skip_ssl_verify else '启用'}SSL验证"
#             )
#             repo_path = GitService.clone_repository(
#                 task.git_repository.url,
#                 branch,
#                 task.id,
#                 token=token,
#                 skip_ssl_verify=skip_ssl_verify,
#             )
#             logger.info(f"仓库克隆成功: {repo_path}")

#             # 批量识别
#             logger.info(f"开始OCR识别，使用GPU: {use_gpu}, GPU ID: {gpu_id}")
#             results = ocr_service.recognize_batch(
#                 repo_path, image_formats=image_formats
#             )
#             logger.info(f"识别完成，共 {len(results)} 个结果")

#             # 处理结果
#             _process_results(task, results, languages)

#             # 更新任务状态
#             task.status = "completed"
#             task.end_time = timezone.now()
#             task.save()

#             logger.info(
#                 f"任务 {task_id} 处理完成，共处理 {task.total_images} 张图片，"
#                 f"匹配 {task.matched_images} 张，匹配率: {task.match_rate:.2f}%"
#             )

#             return {
#                 "success": True,
#                 "task_id": task_id,
#                 "total_images": task.total_images,
#                 "matched_images": task.matched_images,
#                 "match_rate": task.match_rate,
#             }

#         except Exception as e:
#             logger.error(f"Git任务处理失败: {str(e)}")
#             logger.error(traceback.format_exc())

#             # 更新任务状态
#             task.status = "failed"
#             task.end_time = timezone.now()
#             task.save()

#             return {"success": False, "error": str(e)}

#     except Exception as e:
#         logger.error(f"处理Git任务异常: {str(e)}")
#         logger.error(traceback.format_exc())
#         return {"success": False, "error": str(e)}


# @shared_task
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
        logger.info(f"接收到新的 OCR 处理任务 | TaskId: {task_id}")
        task = OCRTask.objects.filter(id=task_id).first()
        if not task:
            raise Exception(f"任务不存在: {task_id}")

        # 更新任务状态
        task.status = "running"
        task.start_time = timezone.now()
        task.save()
        task_config = task.config or {}

        # 确定待检测目录
        target_dir = task_config.get("target_dir")
        check_dir = None
        if task.source_type == "upload":
            # 创建任务时已经完成上传目录，记录在 config["target_dir"] 中
            check_dir = target_dir
        elif task.source_type == "git":
            git_service = GitLabService(
                GitLabConfig(
                    repo_url=task.git_repository.url,
                    access_token=task.git_repository.token,
                )
            )
            result: DownloadResult = git_service.download_files_with_git_clone(
                repo_base_dir=target_dir,
                branch=task_config.get("branch", "master"),
            )
            if not result.success:
                raise Exception(f"Git仓库下载失败: {result.message}")
            check_dir = result.output_dir
        else:
            raise Exception(f"不支持的来源类型: {task.source_type}")

        # 确认目标目录存在
        if not check_dir or not os.path.exists(check_dir):
            raise Exception(f"OCR待检测目录不存在: {check_dir}")

        target_languages = task_config.get("target_languages", ["ch"])

        # 初始化多线程OCR服务
        ocr_service = MultiThreadOCR(
            use_gpu=task_config.get("use_gpu", True),
            lang=task_config.get("target_languages", ["ch"])[0],  # 基础语言模型
            gpu_ids=task_config.get("gpu_ids", 0),
            max_workers=4,  # 可从配置中获取
        )

        # 批量识别
        ocr_results = ocr_service.recognize_batch(
            check_dir,
            image_formats=task_config.get(
                "image_formats", ["jpg", "jpeg", "png", "bmp", "tiff", "tif", "webp"]
            ),
        )

        # 处理结果
        _process_results(task, ocr_results, target_languages)

        # 更新任务状态
        task.status = "completed"
        task.end_time = timezone.now()
        task.save()

        logger.info(
            f"任务 {task_id} 处理完成，共处理 {task.total_images} 张图片，"
            f"匹配 {task.matched_images} 张，匹配率: {task.match_rate:.2f}%"
        )

        return {
            "success": True,
            "task_id": task_id,
            "total_images": task.total_images,
            "matched_images": task.matched_images,
            "match_rate": task.match_rate,
        }

    except Exception as e:
        logger.error(f"任务处理失败: {str(e)}")
        logger.error(traceback.format_exc())

        # 更新任务状态
        task.status = "failed"
        task.end_time = timezone.now()
        task.save()

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
        if "error" in result:
            continue

        # 检查语言匹配
        texts = result.get("texts", [])
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
        processing_time = result.get("processing_time", 0)
        OCRResult.objects.create(
            task=task,
            image_path=result.get("image_path", ""),
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
