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
import datetime

from .models import OCRTask, OCRResult, OCRGitRepository
from .services.ocr_service import OCRService
from .services.multi_thread_ocr import MultiThreadOCR
from .services.gitlab import (
    DownloadResult,
    GitLabConfig,
    GitLabService,
)
from .services.path_utils import PathUtils

# 配置日志
logger = logging.getLogger(__name__)

# 定义常量 - 使用PathUtils从config.ini获取路径
REPOS_DIR = PathUtils.get_ocr_repos_dir()
UPLOADS_DIR = PathUtils.get_ocr_uploads_dir()
RESULTS_DIR = PathUtils.get_ocr_results_dir()


@shared_task
def process_ocr_task(task_id):
    """处理OCR任务"""
    logger.info(f"开始处理OCR任务: {task_id}")

    try:
        # 获取任务信息
        task = OCRTask.objects.get(id=task_id)

        # 更新任务状态
        task.status = 'processing'
        task.start_time = timezone.now()
        task.save()

        # 获取目标语言
        task_config = task.config or {}
        target_languages = task_config.get('target_languages', ['zh'])  # 默认检测中文

        # 为了方便调试，直接使用固定目录，不管任务类型
        debug_dir = PathUtils.get_debug_dir()

        # 打印完整的调试目录路径，方便排查问题
        logger.info(f"调试目录完整路径: {os.path.abspath(debug_dir)}")

        # 检查调试目录是否存在
        if os.path.exists(debug_dir):
            logger.info(f"使用调试目录: {debug_dir}")
            check_dir = debug_dir
        else:
            # 如果调试目录不存在，则使用正常流程
            logger.warning(f"调试目录不存在: {debug_dir}，使用正常流程")

            # 根据任务类型确定检查目录
            if task.source_type == 'git':
                # Git仓库
                repo = task.git_repository
                if not repo:
                    raise ValueError("任务未关联Git仓库")

                # 获取仓库目录
                repo_dir = os.path.join(REPOS_DIR, repo.local_path)
                if not os.path.exists(repo_dir):
                    # 克隆或更新仓库
                    _clone_or_update_repository(repo)

                # 获取检查目录
                target_dir = os.path.join(repo_dir, task.target_path) if task.target_path else repo_dir
                check_dir = target_dir

            elif task.source_type == 'upload':
                # 上传文件
                check_dir = os.path.join(UPLOADS_DIR, str(task.id))
                if not os.path.exists(check_dir):
                    os.makedirs(check_dir, exist_ok=True)

            else:
                raise ValueError(f"不支持的任务类型: {task.source_type}")

        # 初始化OCR服务
        ocr_service = OCRService()

        # 设置默认语言为中文
        ocr_service.lang = "ch"

        # 执行OCR识别
        logger.info(f"开始识别目录: {check_dir}")
        ocr_results = ocr_service.recognize_batch(check_dir)
        logger.info(f"识别完成，共处理 {len(ocr_results)} 张图片")

        # 处理结果
        _process_results(task, ocr_results, target_languages)

        # 生成汇总报告
        _generate_summary_report(task, ocr_results, target_languages)

        return {"status": "success", "task_id": task_id}

    except Exception as e:
        logger.error(f"任务处理失败: {str(e)}")
        # 记录详细的异常堆栈
        import traceback
        logger.error(traceback.format_exc())

        # 更新任务状态为失败
        try:
            task = OCRTask.objects.get(id=task_id)
            task.status = 'failed'
            task.end_time = timezone.now()
            task.save()
        except Exception:
            pass

        return {"status": "error", "message": str(e)}


def _generate_summary_report(task, results, target_languages):
    """生成汇总报告"""
    # 统计信息
    total_images = len(results)
    chinese_images = []

    # 筛选包含中文的图片
    for result in results:
        # 跳过处理失败的图片
        if 'error' in result:
            continue

        # 检查是否包含中文
        if OCRService.check_language_match(result.get('texts', []), 'zh'):
            # 获取文件信息
            image_path = result.get('image_path', '')

            # 使用PathUtils规范化路径
            image_path = PathUtils.normalize_path(image_path)

            file_name = os.path.basename(image_path)

            try:
                # 尝试获取文件大小
                if os.path.isabs(image_path):
                    file_size = os.path.getsize(image_path) / 1024  # KB
                else:
                    full_path = os.path.join(settings.MEDIA_ROOT, image_path)
                    file_size = os.path.getsize(full_path) / 1024  # KB
            except:
                file_size = 0

            chinese_images.append({
                'path': image_path,
                'name': file_name,
                'size': file_size,
                'time': result.get('time_cost', 0),
                'texts': result.get('texts', []),
                'chinese_text': ' '.join([text for text in result.get('texts', [])
                                        if OCRService.check_language_match([text], 'zh')])
            })

    # 计算统计信息
    chinese_count = len(chinese_images)
    chinese_rate = (chinese_count / total_images * 100) if total_images > 0 else 0

    # 生成报告内容
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report = f"""包含中文的图片检测结果
==================================================
生成时间: {now}
总处理图片数: {total_images}
包含中文图片数: {chinese_count}
中文检出率: {chinese_rate:.1f}%

包含中文的图片列表:
------------------------------"""

    # 添加每张图片的详细信息
    for i, img in enumerate(chinese_images, 1):
        report += f"""
{i}. 图片信息:
   文件路径: {img['path']}
   文件名: {img['name']}
   文件大小: {img['size']:.2f} KB
   处理时间: {img['time']:.2f}秒
   识别的中文: {img['chinese_text']}
   完整文本: {' '.join(img['texts'])}"""

    # 添加说明信息
    report += """

1、识别结束后的结果按照以上格式汇总输出。
2、不再单张图片单个文件输出。"""

    # 保存报告
    report_dir = PathUtils.get_ocr_reports_dir()
    os.makedirs(report_dir, exist_ok=True)
    report_file = os.path.join(report_dir, f"{task.id}_summary.txt")

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    # 更新任务信息
    task.config['report_file'] = report_file
    task.save()

    logger.info(f"汇总报告已生成: {report_file}")

    # 打印简要统计信息到日志
    logger.info(f"OCR识别统计: 总图片数={total_images}, 包含中文图片数={chinese_count}, 检出率={chinese_rate:.1f}%")


def _process_results(task, results, target_languages):
    """处理OCR识别结果"""
    anomaly_images = []
    matched_images = 0
    total_images = len(results)

    for result in results:
        # 跳过处理失败的图片
        if 'error' in result:
            continue

        # 检查是否包含目标语言文本
        has_match = False
        for lang in target_languages:
            if OCRService.check_language_match(result.get('texts', []), lang):
                has_match = True
                break

        # 获取图片路径，转换为相对路径
        image_path = result.get('image_path', '')
        # 使用PathUtils规范化路径
        image_path = PathUtils.normalize_path(image_path)

        # 保存结果到数据库
        OCRResult.objects.create(
            task=task,
            image_path=image_path,
            texts=result.get('texts', []),
            languages={lang: True for lang in target_languages if OCRService.check_language_match(result.get('texts', []), lang)},
            has_match=has_match,
            confidence=result.get('confidence', 0.95),
            processing_time=result.get('time_cost', 0)
        )

        if has_match:
            matched_images += 1
            # 记录异常图片路径
            anomaly_images.append(image_path)

    # 更新任务状态
    task.status = 'completed'
    task.end_time = timezone.now()
    task.total_images = total_images
    task.matched_images = matched_images
    task.match_rate = (matched_images / total_images * 100) if total_images > 0 else 0
    task.save()

    # 汇总报告异常图片数量
    if matched_images > 0:
        logger.info(f"检测到异常图片: {matched_images}/{total_images} ({(matched_images/total_images*100):.2f}%)")


def _clone_or_update_repository(repo):
    """克隆或更新Git仓库"""
    from .services.gitlab import GitLabService

    logger.info(f"克隆或更新仓库: {repo.url}")

    # 创建GitLab服务
    git_service = GitLabService(repo.url, repo.token)

    # 获取仓库本地路径
    repo_dir = os.path.join(REPOS_DIR, repo.local_path or git_service.get_repo_name())

    # 检查仓库是否已存在
    if os.path.exists(repo_dir):
        # 更新仓库
        logger.info(f"更新仓库: {repo_dir}")
        try:
            git_service.pull_repository(repo_dir, repo.branch)
            logger.info(f"仓库更新成功: {repo_dir}")
            return repo_dir
        except Exception as e:
            logger.error(f"仓库更新失败: {str(e)}")
            # 如果更新失败，尝试重新克隆
            import shutil
            shutil.rmtree(repo_dir, ignore_errors=True)

    # 克隆仓库
    logger.info(f"克隆仓库: {repo.url} -> {repo_dir}")
    try:
        git_service.clone_repository(repo_dir, repo.branch)
        logger.info(f"仓库克隆成功: {repo_dir}")

        # 更新仓库本地路径
        if not repo.local_path:
            repo.local_path = git_service.get_repo_name()
            repo.save()

        return repo_dir
    except Exception as e:
        logger.error(f"仓库克隆失败: {str(e)}")
        raise


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
