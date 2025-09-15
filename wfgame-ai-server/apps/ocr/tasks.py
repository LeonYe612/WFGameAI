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
import time

from regex import F
from sympy import false

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


# 通用工具函数：语言命中与文本过滤（避免任何硬编码语言码）
def _is_language_hit(texts, target_languages):
    """判断识别结果是否命中任一目标语言。

    Args:
        texts (list[str]): 文本识别得到的文本列表，允许为空列表或None。
        target_languages (list[str] | None): 目标语言代码列表，例如 ['ch','en']。
            若为None或空列表，则默认使用 ['ch']。

    Returns:
        bool: 当且仅当 `texts` 中包含任一 `target_languages` 对应语言的文本时
        返回 True，否则返回 False。

    Raises:
        无显式抛出。内部异常会被吞并以保证稳健性。

    Example:
        >>> _is_language_hit(['你好','hello'], ['en'])
        True
        >>> _is_language_hit(['你好'], ['en'])
        False

    Notes:
        - 为保证健壮性，单项语言匹配异常不会影响整体判断，会被忽略继续。
        - 该函数不做语言码合法性校验，默认交由 `OCRService.check_language_match` 处理。
    """
    safe_langs = target_languages or ['ch']
    for lang in safe_langs:
        try:
            if OCRService.check_language_match(texts or [], lang):
                return True
        except Exception:
            # 单项语言匹配异常不影响整体判断
            continue
    return False


def _filter_texts_by_languages(texts, target_languages):
    """按目标语言过滤文本并返回命中项。

    Args:
        texts (list[str]): 文本识别得到的文本列表，允许为空列表或None。
        target_languages (list[str] | None): 目标语言代码列表，例如 ['ch','en']。
            若为None或空列表，则默认使用 ['ch']。

    Returns:
        list[str]: 所有被任一目标语言规则命中的文本项，按原顺序返回。

    Raises:
        无显式抛出。内部异常会被吞并以保证稳健性。

    Example:
        >>> _filter_texts_by_languages(['你好','hello'], ['en'])
        ['hello']

    Notes:
        - 使用 `OCRService.check_language_match` 对单条文本进行判定。
        - 单条判定异常不会中断流程，仅跳过该条。
    """
    safe_langs = target_languages or ['ch']
    filtered = []
    for text in texts or []:
        try:
            if any(OCRService.check_language_match([text], lang) for lang in safe_langs):
                filtered.append(text)
        except Exception:
            continue
    return filtered


@shared_task(queue="ai_queue")
def process_ocr_task(task_id):
    """调度并处理指定 OCR 任务。

    Args:
        task_id (int|str): `OCRTask` 主键ID。

    Returns:
        dict: 执行结果字典，包含 `status` 与可选的 `task_id`/`message` 等。

    Raises:
        异常会被捕获记录到日志，并回写任务状态为 failed，不向外抛出。

    Example:
        由 Celery Worker 异步调用：
        >>> process_ocr_task.delay(123)

    Notes:
        - 批量写库逻辑在 `MultiThreadOCR` 内部完成。
        - 目标语言从 `task.config['target_languages']` 动态获取，未设置默认 ['ch']。
        - 命中规则统一在 `_is_language_hit` / `_filter_texts_by_languages` 中处理。
    """
    logger.info(f"开始处理OCR任务: {task_id}")

    try:
        # step1. 获取任务信息
        task = OCRTask.objects.get(id=task_id)

        # 更新任务状态
        task.status = 'running'
        task.start_time = timezone.now()
        task.save()

        # 获取目标语言
        task_config = task.config or {}
        target_languages = task_config.get('target_languages', ['ch'])  # 默认检测中文（官方语言码）


        # 从命令行指定的配置文件读取OCR多线程配置
        config = settings.CFG._config
        ocr_max_workers = config.getint('ocr', 'ocr_max_workers', fallback=4)

        logger.warning(f"从配置文件读取OCR配置: max_workers={ocr_max_workers}, 配置文件: {settings.CFG._config_path}")

        # 为了方便调试，直接使用固定目录，不管任务类型
        debug_dir = PathUtils.get_debug_dir()
        debug_status = True

        # 打印完整的调试目录路径，方便排查问题
        logger.info(f"调试目录完整路径: {os.path.abspath(debug_dir)}")

        # step2. 获取待检测目录路径
        # 获取待检测目录路径 & 待检测文件相对路径
        target_dir = task_config.get("target_dir")
        target_path = task_config.get("target_path")
        check_dir = ""

        # 检查调试目录是否存在 且 开启调试（快速使用指定目录图片排查识别逻辑时使用）
        if os.path.exists(debug_dir) and debug_status:
            logger.info(f"使用调试目录: {debug_dir}")
            check_dir = debug_dir
        else:
            # 如果调试目录不存在，则使用正常流程
            logger.warning(f"调试目录:[ {debug_dir} ] 不存在或未开启调试模式，使用正常流程")

            # 根据任务类型确定检查目录
            if task.source_type == 'upload':
                check_dir = target_dir
            elif task.source_type == 'git':
                check_dir = os.path.join(target_dir, target_path)
                git_service = GitLabService(
                    GitLabConfig(
                        repo_url=task.git_repository.url,
                        access_token=task.git_repository.token,
                    )
                )
                result: DownloadResult = git_service.download_files_with_git_clone(
                    repo_base_dir=check_dir,
                    branch=task_config.get("branch", "main"),
                )
                if not result.success:
                    logger.error(f"Git仓库下载失败: {result.message}")
                    task.status = 'failed'
                    task.end_time = timezone.now()
                    task.remark = f"Git仓库下载失败: {result.message}"
                    task.save()
                    return {"status": "error", "message": f"Git仓库下载失败: {result.message}"}
            else:
                logger.error(f"不支持的任务类型: {task.source_type}")
                task.status = 'failed'
                task.end_time = timezone.now()
                task.remark = f"不支持的任务类型: {task.source_type}"
                task.save()
                return {"status": "error", "message": f"不支持的任务类型: {task.source_type}"}

        # 检查目标目录
        if not check_dir or not os.path.exists(check_dir):
            logger.error(f"OCR待检测目录不存在: {check_dir}")
            task.status = 'failed'
            task.end_time = timezone.now()
            task.remark = f"OCR待检测目录不存在: {check_dir}"
            task.save()
            return {"status": "error", "message": f"OCR待检测目录不存在: {check_dir}"}

        # step4. 执行主逻辑
        # 初始化多线程OCR服务
        logger.warning(f"初始化多线程OCR服务 ( 最大工作线程: {ocr_max_workers})")
        multi_thread_ocr = MultiThreadOCR(
            task,
            lang="ch",  # 默认使用中文模型
            max_workers=ocr_max_workers,  # 使用配置的工作线程数
            match_languages=target_languages  # 将命中判定语言动态传入，避免硬编码
        )

        # OCR多线程识别（所有批量写库逻辑已在 MultiThreadOCR 内部完成）
        logger.warning(f"开始多线程识别目录: {check_dir}")
        start_time = time.time()
        ocr_results = multi_thread_ocr.recognize_batch(check_dir)
        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.warning(f"多线程识别完成，共处理 {len(ocr_results)} 张图片，耗时 {elapsed_time:.2f} 秒")

        if not ocr_results:
            logger.error("OCR识别结果为空，请检查目录是否包含图片或OCR引擎是否正常工作")
            task.status = 'failed'
            task.end_time = timezone.now()
            task.remark = f"OCR识别结果为空，请检查目录是否包含图片或OCR引擎是否正常工作"
            task.save()
            return {"status": "failed", "task_id": task_id, "msg": "OCR识别结果为空，请检查目录是否包含图片或OCR引擎是否正常工作"}

        # 检查结果格式
        if len(ocr_results) > 0:
            sample_result = ocr_results[0]
            logger.warning(f"结果样例: {sample_result}")

        # 生成汇总报告（如有需要）
        logger.warning("开始生成汇总报告")
        _generate_summary_report(task, ocr_results, target_languages)
        logger.warning("汇总报告生成完成")

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
            task.remark = f"任务处理失败: {str(e)}"
            task.save()
        except Exception:
            pass

        return {"status": "error", "message": str(e)}


def _generate_summary_report(task, results, target_languages):
    """生成OCR汇总报告（按动态目标语言命中）。

    Args:
        task (OCRTask): 当前任务实例。
        results (list[dict]): 识别结果列表，元素包含 `image_path`、`texts` 等字段。
        target_languages (list[str] | None): 目标语言代码列表；None/空默认 ['ch']。

    Returns:
        None: 结果直接写入报告文件，并更新 `task.config['report_file']`。

    Raises:
        无显式抛出。内部异常已做保护性处理并记录日志。

    Example:
        >>> _generate_summary_report(task, results, ['ch','en'])

    Notes:
        - 命中判定遵循“任意目标语言命中即视为命中”。
        - 路径统一经 `PathUtils.normalize_path` 规范化。
        - 将在 `MEDIA_ROOT/ocr/reports/` 目录生成两个文件:
          1) `{task.id}_ocr_summary.json` 本次任务的结构化汇总
          2) `ocr_summary.json` 指向最近一次生成的覆盖式汇总
    """
    # 统计信息
    total_images = len(results)
    matched_images = []

    # 筛选包含目标语言的图片（命中规则：包含任一目标语言文字即为命中）
    for result in results:
        # 跳过处理失败的图片
        if 'error' in result:
            continue

        texts = result.get('texts', [])
        if not _is_language_hit(texts, target_languages):
            continue

        # 获取文件信息
        image_path = result.get('image_path', '')
        image_path = PathUtils.normalize_path(image_path)
        file_name = os.path.basename(image_path)

        try:
            # 尝试获取文件大小（相对路径拼接 MEDIA_ROOT）
            if os.path.isabs(image_path):
                file_size = os.path.getsize(image_path) / 1024  # KB
            else:
                full_path = os.path.join(settings.MEDIA_ROOT, image_path)
                file_size = os.path.getsize(full_path) / 1024  # KB
        except Exception:
            file_size = 0

        matched_texts = _filter_texts_by_languages(texts, target_languages)

        matched_images.append({
            'path': image_path,
            'name': file_name,
            'size': file_size,
            'time': result.get('time_cost', 0),
            'texts': texts,
            'matched_texts': ' '.join(matched_texts),
        })

    # 计算统计信息
    matched_count = len(matched_images)
    matched_rate = (matched_count / total_images * 100) if total_images > 0 else 0

    # 生成报告内容（动态目标语言）
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    langs_str = ','.join(target_languages or ['ch'])
    report = f"""包含目标语言的图片检测结果
==================================================
生成时间: {now}
目标语言: {langs_str}
总处理图片数: {total_images}
命中图片数: {matched_count}
命中率: {matched_rate:.1f}%

命中的图片列表:
------------------------------"""

    # 添加每张图片的详细信息
    for i, img in enumerate(matched_images, 1):
        report += f"""
{i}. 图片信息:
   文件路径: {img['path']}
   文件名: {img['name']}
   文件大小: {img['size']:.2f} KB
   处理时间: {img['time']:.2f}秒
   命中文本: {img['matched_texts']}
   完整文本: {' '.join(img['texts'])}"""

    # 添加说明信息
    report += """

1、识别结束后的结果按照以上格式汇总输出。
2、不再单张图片单个文件输出。"""

    # 保存报告
    report_dir = PathUtils.get_ocr_reports_dir()
    os.makedirs(report_dir, exist_ok=True)

    # 同步输出结构化 JSON 汇总，便于前端或其他工具使用
    try:
        import json
        json_items = []
        for img in matched_images:
            json_items.append({
                'path': img['path'],
                'name': img['name'],
                'matched_texts': img['matched_texts'],
                # 新增字段, 从结果回填: 分辨率、像素、参数差异、置信度、模式
                'resolution': None,
                'pixels': None,
                'param_diff': None,
                'confidences': None,
                'mode_display': None,
            })
        # 若原始 results 中包含 used_preset/mode_display, 则进行对齐合并
        try:
            # 建立 path -> extras 的映射
            extras = {}
            for r in results:
                if 'error' in r:
                    continue
                p = PathUtils.normalize_path(r.get('image_path', ''))
                extras[p] = {
                    'mode_display': r.get('mode_display'),
                    'resolution': r.get('resolution'),
                    'pixels': r.get('pixels'),
                    'param_diff': r.get('param_diff'),
                    'confidences': r.get('confidences'),
                }
            # 回填
            for item in json_items:
                ext = extras.get(item['path']) or {}
                if ext.get('mode_display') is not None:
                    item['mode_display'] = ext.get('mode_display')
                if ext.get('resolution') is not None:
                    item['resolution'] = ext.get('resolution')
                if ext.get('pixels') is not None:
                    item['pixels'] = ext.get('pixels')
                if ext.get('param_diff') is not None:
                    item['param_diff'] = ext.get('param_diff')
                if ext.get('confidences') is not None:
                    item['confidences'] = ext.get('confidences')
        except Exception:
            pass

        summary_json = {
            'task_id': task.id,
            'generated_at': now,
            'target_languages': target_languages or ['ch'],
            'total_images': total_images,
            'matched_count': matched_count,
            'matched_rate': round(matched_rate, 2),
            'items': json_items,
        }
        json_dir = report_dir
        json_file = os.path.join(json_dir, f"{task.id}_ocr_summary.json")
        with open(json_file, 'w', encoding='utf-8') as jf:
            json.dump(summary_json, jf, ensure_ascii=False, indent=2)
        # 生成覆盖式别名文件, 方便用户直接查找最近一次的汇总
        alias_file = os.path.join(json_dir, "ocr_summary.json")
        with open(alias_file, 'w', encoding='utf-8') as af:
            json.dump(summary_json, af, ensure_ascii=False, indent=2)
        # 使用 warning 级别便于在控制台看到完整路径
        logger.warning(f"OCR JSON汇总已生成: {json_file}")
        logger.warning(f"OCR 最近一次汇总(覆盖): {alias_file}")
    except Exception as je:
        logger.error(f"生成OCR JSON汇总失败: {je}")

    # 仅生成JSON, 不再生成txt; 保持任务其他信息不变

    logger.info(
        f"OCR识别统计: 总图片数={total_images}, 命中图片数={matched_count}, 命中率={matched_rate:.1f}%"
    )


def _process_results(task, results, target_languages):
    """
    处理OCR识别结果（通用动态语言命中）。

    Args:
        task (OCRTask): 当前任务实例。
        results (list[dict]): 识别结果列表，元素包含 `image_path`、`texts` 等字段。
        target_languages (list[str] | None): 目标语言代码列表；None/空默认 ['ch']。

    Returns:
        dict: 包含以下键：
            - processed_results (list[dict]): 附带 `languages`/`has_match` 的结果列表
            - matched_images (list[dict]): 命中图片的精简信息
            - matched_count (int): 命中数量
            - matched_rate (float): 命中率（0~100）

    Raises:
        无显式抛出。内部异常会在必要处被保护性捕获并记录。

    Example:
        >>> data = _process_results(task, results, ['ch','en'])
        >>> data['matched_count']

    Notes:
        - 命中规则：只要包含任一目标语言文本即命中。
        - 避免硬编码语言；按输入动态决定。
        - 严格控制缩进与循环层级，保证可维护性与可读性。
    """
    logger.warning(f"开始处理OCR结果，共 {len(results)} 个结果")

    processed_results = []
    matched_images = []

    safe_langs = target_languages or ['ch']

    for result in results:
        if 'error' in result:
            continue

        texts = result.get('texts', [])
        languages = {}
        for lang in safe_langs:
            try:
                if OCRService.check_language_match(texts, lang):
                    languages[lang] = True
            except Exception:
                continue
        has_match = bool(languages)

        enriched = {
            **result,
            'languages': languages,
            'has_match': has_match,
        }
        processed_results.append(enriched)

        if has_match:
            image_path = PathUtils.normalize_path(result.get('image_path', ''))
            file_name = os.path.basename(image_path)
            try:
                if os.path.isabs(image_path):
                    file_size = os.path.getsize(image_path) / 1024  # KB
                else:
                    full_path = os.path.join(settings.MEDIA_ROOT, image_path)
                    file_size = os.path.getsize(full_path) / 1024  # KB
            except Exception:
                file_size = 0

            matched_texts = _filter_texts_by_languages(texts, safe_langs)

            matched_images.append({
                'path': image_path,
                'name': file_name,
                'size': file_size,
                'time': result.get('time_cost', 0),
                'texts': texts,
                'matched_texts': ' '.join(matched_texts),
            })

    total_images = len(results)
    matched_count = len(matched_images)
    matched_rate = (matched_count / total_images * 100) if total_images > 0 else 0

    logger.info(
        f"OCR识别统计: 总图片数={total_images}, 命中图片数={matched_count}, 命中率={matched_rate:.1f}%"
    )

    # 可按需返回结构化结果，当前不影响既有调用方
    return {
        'processed_results': processed_results,
        'matched_images': matched_images,
        'matched_count': matched_count,
        'matched_rate': matched_rate,
    }

    