"""
OCR模块API视图
"""

import csv
import json
import logging
import os
import tarfile
import uuid
import zipfile

from django.http import HttpResponse
from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Q
from utils.orm_helper import DecimalEncoder
from .models import OCRProject, OCRGitRepository, OCRTask, OCRResult, OCRCacheHit
from .serializers import (
    OCRProjectSerializer,
    OCRGitRepositorySerializer,
    OCRTaskSerializer,
    OCRResultSerializer,
    FileUploadSerializer,
    OCRTaskCreateSerializer,
    OCRHistoryQuerySerializer,
    OCRTaskWithResultsSerializer,
    OCRProcessGitSerializer,
)
from .services.ocr_service import OCRService
from .services.gitlab import create_gitlab_service, GitLabService, GitLabConfig
from .tasks import process_ocr_task
from .services.path_utils import PathUtils
from apps.core.utils.response import api_response

# 配置日志
logger = logging.getLogger(__name__)


class OCRProjectAPIView(APIView):
    """OCR项目API"""

    permission_classes = [AllowAny]
    http_method_names = ["post"]

    def post(self, request):
        """处理项目相关操作"""
        action = request.data.get("action", "")

        if action == "list":
            projects = OCRProject.objects.all()
            serializer = OCRProjectSerializer(projects, many=True)
            return api_response(serializer.data)

        elif action == "create":
            serializer = OCRProjectSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return api_response(serializer.data)
            return api_response(status.HTTP_400_BAD_REQUEST, data=serializer.errors, msg="创建失败")

        elif action == "get":
            project_id = request.data.get("id")
            try:
                project = OCRProject.objects.get(id=project_id)
                serializer = OCRProjectSerializer(project)
                return api_response(serializer.data)
            except OCRProject.DoesNotExist:
                return api_response(status.HTTP_404_NOT_FOUND, msg="项目不存在")

        elif action == "delete":
            project_id = request.data.get("id")
            try:
                project = OCRProject.objects.get(id=project_id)
                project.delete()
                return api_response()
            except OCRProject.DoesNotExist:
                return api_response(code=status.HTTP_404_NOT_FOUND, msg="项目不存在")

        return api_response(code=status.HTTP_400_BAD_REQUEST, msg=f"不支持的操作: {action}")


class OCRGitRepositoryAPIView(APIView):
    """OCR Git仓库API"""

    permission_classes = [AllowAny]
    http_method_names = ["post"]

    def post(self, request):
        """处理Git仓库相关操作"""
        action = request.data.get("action", "")

        if action == "list":
            project_id = request.data.get("project_id")
            if project_id:
                repositories = OCRGitRepository.objects.filter(project_id=project_id)
            else:
                repositories = OCRGitRepository.objects.all()

            serializer = OCRGitRepositorySerializer(repositories, many=True)
            return api_response(data=serializer.data)

        elif action == "create":
            try:
                serializer = OCRGitRepositorySerializer(data=request.data)
                if serializer.is_valid():
                    # 获取访问令牌（如果提供）
                    token = request.data.get("token")

                    # 获取是否跳过SSL验证的标志
                    skip_ssl_verify = request.data.get("skip_ssl_verify", False)
                    if skip_ssl_verify:
                        logger.warning("⚠️ 用户请求跳过SSL验证，这可能存在安全风险")

                    # 验证Git仓库URL
                    url = serializer.validated_data.get("url")
                    try:
                        is_valid = create_gitlab_service(
                            url, token=token, skip_ssl_verify=skip_ssl_verify
                        ).validate_repository()
                        if not is_valid:
                            return api_response(
                                code=status.HTTP_400_BAD_REQUEST,
                                msg="Git仓库URL无效或无法访问"
                            )
                    except Exception as e:
                        logger.error(f"验证仓库URL失败: {str(e)}")
                        return api_response(
                            code=status.HTTP_400_BAD_REQUEST,
                            msg=f"验证仓库URL失败: {str(e)}"
                        )

                    # 保存仓库信息，但不存储令牌
                    serializer.save()

                    return api_response(data=serializer.data, msg="创建成功")
                return api_response(code=status.HTTP_400_BAD_REQUEST, data=serializer.errors, msg="创建失败")
            except Exception as e:
                logger.error(f"创建仓库异常: {str(e)}")
                return api_response(
                    code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    msg=f"创建仓库失败: {str(e)}"
                )

        elif action == "get":
            repo_id = request.data.get("id")
            try:
                repo = OCRGitRepository.objects.get(id=repo_id)
                serializer = OCRGitRepositorySerializer(repo)
                return api_response(data=serializer.data)
            except OCRGitRepository.DoesNotExist:
                return api_response(
                    code=status.HTTP_404_NOT_FOUND,
                    msg="Git仓库不存在"
                )

        elif action == "delete":
            repo_id = request.data.get("id")
            try:
                repo = OCRGitRepository.objects.get(id=repo_id)
                repo.delete()
                return api_response(msg="Git仓库删除成功")
            except OCRGitRepository.DoesNotExist:
                return api_response(
                    code=status.HTTP_404_NOT_FOUND,
                    msg="Git仓库不存在"
                )

        elif action == "get_branches":
            repo_id = request.data.get("id")
            try:
                repo = OCRGitRepository.objects.get(id=repo_id)
                # 获取是否跳过SSL验证的标志
                skip_ssl_verify = request.data.get("skip_ssl_verify", False)
                if skip_ssl_verify:
                    logger.warning("⚠️ 用户请求跳过SSL验证获取分支，这可能存在安全风险")

                branches = create_gitlab_service(
                    repo.url, token=repo.token, skip_ssl_verify=skip_ssl_verify
                ).get_repository_branches()
                return api_response(data={"branches": branches})
            except OCRGitRepository.DoesNotExist:
                return api_response(
                    code=status.HTTP_404_NOT_FOUND,
                    msg="Git仓库不存在"
                )
            except Exception as e:
                return api_response(
                    code=status.HTTP_400_BAD_REQUEST,
                    msg=f"获取分支失败: {str(e)}"
                )

        return api_response(
            code=status.HTTP_400_BAD_REQUEST,
            msg=f"不支持的操作: {action}"
        )


class OCRTaskAPIView(APIView):
    """OCR任务API"""

    permission_classes = [AllowAny]
    http_method_names = ["post"]

    def post(self, request):
        """处理任务相关操作"""
        action = request.data.get("action", "")

        if action == "list":
            tasks = OCRTask.objects.all().order_by("-created_time")
            serializer = OCRTaskSerializer(tasks, many=True)
            return api_response(data=serializer.data)

        elif action == "create":
            serializer = OCRTaskCreateSerializer(data=request.data)
            if serializer.is_valid():
                # 创建任务
                task = serializer.save()

                # 使用事务确保任务创建完成后再提交Celery任务
                from django.db import transaction
                import time
                
                def submit_celery_task():
                    time.sleep(0.1)  # 短暂延迟确保事务提交
                    logger.info(f"提交OCR任务到Celery: {task.id}")
                    process_ocr_task.delay(task.id)
                
                transaction.on_commit(submit_celery_task)

                result_serializer = OCRTaskSerializer(task)
                return api_response(data=result_serializer.data, msg="任务创建成功")
            return api_response(code=status.HTTP_400_BAD_REQUEST, data=serializer.errors, msg="任务创建失败")

        elif action == "get":
            task_id = request.data.get("id")
            try:
                task = OCRTask.objects.get(id=task_id)
                serializer = OCRTaskSerializer(task)

                # # 获取实时进度数据
                # key = f'ai_ocr_progress:{task.id}'
                # progress_data = settings.REDIS.hgetall(key)
                #
                # total_images = int(progress_data.get('total', 0))
                # matched_images = int(progress_data.get('matched', 0))
                # executed_images = int(progress_data.get('executed', 0))
                # match_rate = (matched_images / total_images * 100) if total_images > 0 else 0
                # # 前 10% 用于准备阶段，后 90% 用于处理阶段
                # font_default_progress = 10.0 # 默认进度10%
                # progress = int(progress_data.get('executed', 0)) / total_images * 100 * 0.9 + font_default_progress if total_images > 0 else font_default_progress
                # response_data = serializer.data
                # response_data.update({
                #     'status': progress_data.get('status', ''),
                #     'total_images': total_images,
                #     'matched_images': matched_images,
                #     'executed_images': executed_images,
                #     'match_rate': round(match_rate, 2),
                #     'progress': round(progress, 2),
                #     'start_time': float(progress_data.get('start_time', 0)),
                #     'end_time': float(progress_data.get('end_time', 0))
                # })
                #
                # # 汇总报告
                # report_file = task.config.get('report_file')
                # if report_file and os.path.exists(report_file):
                #     with open(report_file, 'r', encoding='utf-8') as f:
                #         report_content = f.read()
                #     response_data['report'] = {
                #         'content': report_content,
                #         'file_path': report_file
                #     }

                return api_response(data=serializer.data)
            except OCRTask.DoesNotExist:
                return api_response(
                    code=status.HTTP_404_NOT_FOUND,
                    msg="任务不存在"
                )
        # elif action == "get":
        #     task_id = request.data.get("id")
        #     try:
        #         task = OCRTask.objects.get(id=task_id)
        #         serializer = OCRTaskSerializer(task)
        #
        #         # 获取实时进度数据
        #         key = f'ai_ocr_progress:{task.id}'
        #         progress_data = settings.REDIS.hgetall(key)
        #
        #         # 字段映射与模型同步
        #         total_images = int(progress_data.get('total', 0))
        #         matched_images = int(progress_data.get('matched', 0))
        #         match_rate = (matched_images / total_images * 100) if total_images > 0 else 0
        #
        #         response_data = serializer.data
        #         response_data.update({
        #             'status': progress_data.get('status', ''),
        #             'total_images': total_images,
        #             'matched_images': matched_images,
        #             'match_rate': round(match_rate, 2),
        #             'start_time': float(progress_data.get('start_time', 0)),
        #             'end_time': float(progress_data.get('end_time', 0)),
        #             'executed_images': int(progress_data.get('executed', 0)),
        #             'success_images': int(progress_data.get('success', 0)),
        #             'fail_images': int(progress_data.get('fail', 0)),
        #             'exception_images': int(progress_data.get('exception', 0)),
        #         })
        #
        #         # 检查是否有汇总报告
        #         report_file = task.config.get('report_file')
        #         if report_file and os.path.exists(report_file):
        #             with open(report_file, 'r', encoding='utf-8') as f:
        #                 report_content = f.read()
        #             response_data['report'] = {
        #                 'content': report_content,
        #                 'file_path': report_file
        #             }
        #
        #         return Response(response_data)
        #     except OCRTask.DoesNotExist:
        #         return Response(
        #             {"detail": "任务不存在"}, status=status.HTTP_404_NOT_FOUND
        #         )

        elif action == "delete":
            task_id = request.data.get("id")
            try:
                task = OCRTask.objects.get(id=task_id)
                task.delete()
                return api_response(msg="任务删除成功")
            except OCRTask.DoesNotExist:
                return api_response(
                    code=status.HTTP_404_NOT_FOUND,
                    msg="任务不存在"
                )

        elif action == "get_details":
            task_id = request.data.get("id")
            has_math = request.data.get("has_match", None)
            keyword = request.data.get("keyword", None)
            result_type = request.data.get("result_type")
            try:
                task = OCRTask.objects.get(id=task_id)
                results = task.related_results

                if result_type:
                    results = results.filter(result_type=result_type)

                if has_math is not None:
                    results = results.filter(has_match=has_math)

                if keyword != "":
                    regex = f"/[^/]*{keyword}[^/]*$"
                    results = results.filter(image_path__iregex=regex)

                # 获取分页参数
                page = int(request.data.get("page", 1))
                page_size = int(request.data.get("page_size", 20))

                # 分页
                start = (page - 1) * page_size
                end = start + page_size

                # 获取当前页的结果
                paginated_results = results[start:end]

                # 序列化
                task_serializer = OCRTaskSerializer(task)
                results_serializer = OCRResultSerializer(paginated_results, many=True)

                return api_response(data={
                        "task": task_serializer.data,
                        "results": results_serializer.data,
                        "total": results.count(),
                        "page": page,
                        "page_size": page_size,
                        "total_pages": (results.count() + page_size - 1) // page_size,
                    })

            except OCRTask.DoesNotExist:
                return api_response(
                    code=status.HTTP_404_NOT_FOUND,
                    msg="任务不存在"
                )

        elif action == "export":
            task_id = request.data.get("id")
            export_format = request.data.get("format", "json")

            try:
                task = OCRTask.objects.get(id=task_id)
                results = OCRResult.objects.filter(task=task)
                print("results : ", results)
                if export_format == "json":
                    # 导出为JSON
                    export_data = []
                    for result in results:
                        # 确保使用相对路径
                        image_path = result.image_path
                        # 使用PathUtils规范化路径
                        image_path = PathUtils.normalize_path(image_path)

                        export_data.append(
                            {
                                "image_path": image_path,
                                "texts": result.texts,
                                "languages": result.languages,
                                "has_match": result.has_match,
                                "processing_time": result.processing_time,
                            }
                        )

                    # 创建响应
                    response = HttpResponse(
                        json.dumps(export_data, ensure_ascii=False, indent=2, cls=DecimalEncoder),
                        content_type="application/json",
                    )
                    response["Content-Disposition"] = (
                        f"attachment; filename=ocr_task_{task_id}.json"
                    )
                    return response

                elif export_format == "csv":
                    # 直接导出 helper 风格的 xlsx（替换旧逻辑，不再保留CSV旧格式）
                    xbytes, fname = _export_helper_xlsx(request, results, str(task_id))
                    response = HttpResponse(xbytes, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                    response["Content-Disposition"] = f"attachment; filename={fname}"
                    return response

                elif export_format == "txt":
                    # 导出为TXT
                    from io import StringIO

                    txt_buffer = StringIO()

                    # 写入数据
                    for result in results:
                        # 确保使用相对路径
                        image_path = result.image_path
                        # 使用PathUtils规范化路径
                        image_path = PathUtils.normalize_path(image_path)

                        txt_buffer.write(f"图片路径: {image_path}\n")
                        txt_buffer.write(f"识别文本:\n")
                        for i, text in enumerate(result.texts, 1):
                            txt_buffer.write(f"{i}. {text}\n")
                        txt_buffer.write(
                            f"语言: {', '.join(result.languages.keys())}\n"
                        )
                        txt_buffer.write(
                            f"匹配: {'是' if result.has_match else '否'}\n"
                        )
                        txt_buffer.write("-" * 50 + "\n\n")

                    # 创建响应
                    response = HttpResponse(
                        txt_buffer.getvalue(), content_type="text/plain"
                    )
                    response["Content-Disposition"] = (
                        f"attachment; filename=ocr_task_{task_id}.txt"
                    )
                    return response

                else:
                    return api_response(
                        code=status.HTTP_400_BAD_REQUEST,
                        msg=f"不支持的导出格式: {export_format}"
                    )

            except OCRTask.DoesNotExist:
                return api_response(
                    code=status.HTTP_404_NOT_FOUND,
                    msg="任务不存在"
                )

        return api_response(
            code=status.HTTP_400_BAD_REQUEST,
            msg=f"不支持的操作: {action}"
        )


class OCRResultAPIView(APIView):
    """OCR结果API"""

    permission_classes = [AllowAny]
    http_method_names = ["post"]

    def post(self, request):
        """处理结果相关操作"""
        action = request.data.get("action", "")

        if action == "list":
            task_id = request.data.get("task_id")
            if task_id:
                results = OCRResult.objects.filter(task_id=task_id)
            else:
                results = OCRResult.objects.all()

            serializer = OCRResultSerializer(results, many=True)
            return api_response(data=serializer.data)

        elif action == "get":
            result_id = request.data.get("id")
            try:
                result = OCRResult.objects.get(id=result_id)
                serializer = OCRResultSerializer(result)
                return api_response(data=serializer.data)
            except OCRResult.DoesNotExist:
                return api_response(
                    code=status.HTTP_404_NOT_FOUND,
                    msg="结果不存在"
                )

        elif action == "search":
            # 搜索结果
            task_id = request.data.get("task_id")
            query = request.data.get("query", "")
            only_matched = request.data.get("only_matched", False)

            if not task_id:
                return api_response(
                    code=status.HTTP_400_BAD_REQUEST,
                    msg="缺少task_id参数"
                )

            try:
                results = OCRResult.objects.filter(task_id=task_id)

                if only_matched:
                    results = results.filter(has_match=True)

                if query:
                    # 在文本内容中搜索
                    matching_results = []
                    for result in results:
                        for text in result.texts:
                            if query.lower() in text.lower():
                                matching_results.append(result)
                                break

                    # 转换为QuerySet
                    result_ids = [r.id for r in matching_results]
                    results = OCRResult.objects.filter(id__in=result_ids)

                # 获取分页参数
                page = int(request.data.get("page", 1))
                page_size = int(request.data.get("page_size", 20))

                # 分页
                start = (page - 1) * page_size
                end = start + page_size

                # 获取当前页的结果
                paginated_results = results[start:end]

                # 序列化
                serializer = OCRResultSerializer(paginated_results, many=True)

                return api_response(data={
                        "results": serializer.data,
                        "total": results.count(),
                        "page": page,
                        "page_size": page_size,
                        "total_pages": (results.count() + page_size - 1) // page_size,
                    })

            except Exception as e:
                return api_response(
                    code=status.HTTP_400_BAD_REQUEST,
                    msg=f"搜索失败: {str(e)}"
                )

        elif action == "update":
            # 更新结果处理是否正确，result_type
            result_ids = request.data.get("ids", {})
            # 拼接更新结构体，包括ids， result_type
            update_results = []
            for id, result_type in result_ids.items():
                try:
                    result = OCRResult.objects.get(id=id)
                    result.result_type = result_type
                    update_results.append(result)
                except OCRResult.DoesNotExist:
                    continue

            # 批量更新sql
            if update_results:
                OCRResult.objects.bulk_update(update_results, ['result_type'])
                return api_response(
                    msg="结果更新成功", data={"total": len(update_results)}
                )
            else:
                return api_response(
                    code=status.HTTP_400_BAD_REQUEST,
                    msg="没有有效的结果需要更新"
                )

        return api_response(
            code=status.HTTP_400_BAD_REQUEST,
            msg=f"不支持的操作: {action}"
        )


class OCRUploadAPIView(APIView):
    """文件上传API"""

    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    http_method_names = ["post"]

    def post(self, request):
        # 处理文件上传
        logger.info(f"收到文件上传请求，数据类型: {type(request.data)}")
        logger.info(f"请求数据键: {list(request.data.keys())}")
        
        serializer = FileUploadSerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"参数验证失败: {serializer.errors}")
            return api_response(code=status.HTTP_400_BAD_REQUEST, data=serializer.errors, msg="参数验证失败")

        uploaded_file = serializer.validated_data.get("file")
        project_id = serializer.validated_data.get("project_id")
        languages = serializer.validated_data.get("languages", ["ch"])

        try:
            # 确保项目存在
            try:
                project = OCRProject.objects.get(id=project_id)
            except OCRProject.DoesNotExist:
                return api_response(
                    code=status.HTTP_404_NOT_FOUND,
                    msg="项目不存在"
                )

            # 创建上传ID
            upload_id = f"upload_{uuid.uuid4().hex[:8]}"
            uploads_base_dir = PathUtils.get_ocr_uploads_dir()
            upload_dir = os.path.join(uploads_base_dir, upload_id)
            
            # 调试信息
            logger.info(f"上传基础目录: {uploads_base_dir}")
            logger.info(f"完整上传目录: {upload_dir}")
            
            os.makedirs(upload_dir, exist_ok=True)
            logger.info(f"目录创建成功: {upload_dir}")

            # 保存文件
            file_path = os.path.join(upload_dir, uploaded_file.name)
            with open(file_path, "wb+") as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            # 处理压缩文件
            if file_path.endswith(".zip"):
                self._extract_zip_file(file_path, upload_dir)
                os.remove(file_path)  # 删除原始ZIP文件
            elif file_path.endswith(".tar.gz") or file_path.endswith(".tgz"):
                self._extract_tar_file(file_path, upload_dir)
                os.remove(file_path)  # 删除原始TAR文件

            # 创建OCR任务
            # 保存相对于MEDIA_ROOT的相对路径，避免路径重复
            relative_upload_dir = upload_id
            task = OCRTask.objects.create(
                project=project,
                source_type="upload",
                name=f"上传识别_{uploaded_file.name}",
                status="pending",
                config={
                    "target_languages": languages,
                    "upload_id": upload_id,
                    "target_dir": relative_upload_dir,
                },
            )

            # 确保数据库事务提交后再提交Celery任务
            from django.db import transaction
            import time
            
            logger.info(f"创建OCR任务成功，任务ID: {task.id}, 类型: {type(task.id)}")
            
            # 使用事务确保任务创建完成后再提交Celery任务
            def submit_celery_task():
                # 添加短暂延迟确保数据库事务完全提交
                time.sleep(0.1)
                
                # 验证任务是否存在
                verification_task = OCRTask.objects.filter(id=task.id).first()
                if verification_task:
                    logger.info(f"任务验证通过，提交异步Celery任务: {task.id}")
                    process_ocr_task.delay(task.id)
                    logger.info(f"Celery任务已提交: {task.id}")
                else:
                    logger.error(f"任务验证失败，任务不存在: {task.id}")
                    # 记录详细调试信息
                    all_tasks = OCRTask.objects.values_list('id', 'name', 'status')[:5]
                    logger.error(f"数据库中的任务示例: {list(all_tasks)}")
            
            # 在事务提交后执行Celery任务提交
            transaction.on_commit(submit_celery_task)
            # process_ocr_task(task.id)

            serializer = OCRTaskSerializer(task)
            return api_response(
                data={"task": serializer.data},
                msg="文件上传成功，开始OCR处理"
            )

        except Exception as e:
            return api_response(
                code=status.HTTP_400_BAD_REQUEST,
                msg=f"文件上传处理失败: {str(e)}"
            )

    def _extract_zip_file(self, zip_path, extract_to):
        """解压ZIP文件"""
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_to)
        logger.info(f"解压缩ZIP文件到 {extract_to}")

    def _extract_tar_file(self, tar_path, extract_to):
        """解压TAR文件"""
        with tarfile.open(tar_path, "r:*") as tar_ref:
            tar_ref.extractall(path=extract_to)
        logger.info(f"解压缩TAR文件到 {extract_to}")


class OCRProcessAPIView(APIView):
    """OCR处理API"""

    permission_classes = [AllowAny]
    http_method_names = ["post"]

    def post(self, request):
        """处理OCR请求"""
        action = request.data.get("action", "")
        if action == "process_git":
            # 处理Git仓库源OCR
            serializer = OCRProcessGitSerializer(data=request.data)
            if serializer.is_valid():
                # 获取参数
                project_id = serializer.validated_data.get("project_id")
                repo_id = serializer.validated_data.get("repo_id")
                branch = serializer.validated_data.get("branch", "main")
                languages = serializer.validated_data.get("languages", ["ch"])
                enable_cache = serializer.validated_data.get("enable_cache", True)

                try:
                    # 获取项目和仓库
                    project = OCRProject.objects.get(id=project_id)
                    git_repo = OCRGitRepository.objects.get(id=repo_id, project=project)
                    # 创建OCR任务
                    task = OCRTask.objects.create(
                        project=project,
                        git_repository=git_repo,
                        git_branch=branch,
                        source_type="git",
                        status="pending",
                        config={
                            "branch": branch,
                            "languages": languages,
                            "target_dir": PathUtils.get_ocr_repos_dir(),
                            # 项目代码所在目录，与 target_dir 相对路径
                            "target_path": GitLabService(
                                GitLabConfig(repo_url=git_repo.url,
                                             access_token=git_repo.token,
                                             )).get_repo_name(git_repo.url),
                            "enable_cache": enable_cache,
                        },
                    )

                    # 使用事务确保任务创建完成后再提交Celery任务
                    from django.db import transaction
                    import time
                    
                    def submit_celery_task():
                        time.sleep(0.1)  # 短暂延迟确保事务提交
                        logger.info(f"提交Git OCR任务到Celery: {task.id}")
                        process_ocr_task.delay(task.id)
                    
                    transaction.on_commit(submit_celery_task)
                    
                    # 返回任务信息
                    serializer = OCRTaskSerializer(task)
                    return api_response(data=serializer.data, msg="Git仓库OCR任务创建成功")

                except OCRProject.DoesNotExist:
                    return api_response(
                        code=status.HTTP_404_NOT_FOUND,
                        msg="项目不存在"
                    )
                except OCRGitRepository.DoesNotExist:
                    return api_response(
                        code=status.HTTP_404_NOT_FOUND,
                        msg="仓库不存在"
                    )
                except Exception as e:
                    return api_response(
                        code=status.HTTP_400_BAD_REQUEST,
                        msg=f"处理失败: {str(e)}"
                    )

            return api_response(code=status.HTTP_400_BAD_REQUEST, data=serializer.errors, msg="参数验证失败")

        return api_response(
            code=status.HTTP_400_BAD_REQUEST,
            msg=f"不支持的操作: {action}"
        )


class OCRHistoryAPIView(APIView):
    """OCR历史记录API"""

    permission_classes = [AllowAny]
    http_method_names = ["post"]

    def post(self, request):
        """查询历史记录"""
        action = request.data.get("action", "list")

        if action == "download":
            return self.download_results(request)

        if action == "del":
            return self.del_result(request)
        # 默认list操作
        serializer = OCRHistoryQuerySerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(code=status.HTTP_400_BAD_REQUEST, data=serializer.errors, msg="参数验证失败")

        # 获取查询参数
        project_id = serializer.validated_data.get("project_id")
        date_from = serializer.validated_data.get("date_from")
        date_to = serializer.validated_data.get("date_to")
        page = serializer.validated_data.get("page", 1)
        page_size = serializer.validated_data.get("page_size", 20)

        # 构建查询
        query = Q()

        if project_id:
            query &= Q(project_id=project_id)

        if date_from:
            query &= Q(created_at__gte=date_from)

        if date_to:
            # 设置日期结束时间为当天23:59:59
            date_to = date_to.replace(hour=23, minute=59, second=59)
            query &= Q(created_at__lte=date_to)

        # 执行查询
        tasks = OCRTask.objects.filter(query).order_by("-created_at")

        # 计算总数
        total_count = tasks.count()

        # 分页
        start = (page - 1) * page_size
        end = start + page_size
        paginated_tasks = tasks[start:end]

        # 序列化
        task_serializer = OCRTaskWithResultsSerializer(paginated_tasks, many=True)

        return api_response(data={
                "tasks": task_serializer.data,
                "total": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size,
            })

    def download_results(self, request):
        """下载任务结果为CSV"""
        task_id = request.data.get("task_id")
        if not task_id:
            return api_response(
                code=status.HTTP_400_BAD_REQUEST,
                msg="缺少task_id参数"
            )

        try:
            # 获取任务信息
            task = OCRTask.objects.get(id=task_id)

            # 获取该任务的所有结果
            results = task.related_results

            # 直接导出 helper 风格的 xlsx（替换旧CSV导出逻辑）
            xbytes, fname = _export_helper_xlsx(request, results, str(task_id), task_name=(task.name or str(task.id)))
            response = HttpResponse(xbytes, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            response["Access-Control-Expose-Headers"] = "Content-Disposition"
            response["Content-Disposition"] = f"attachment; filename={fname}"
            return response

        except OCRTask.DoesNotExist:
            return api_response(
                code=status.HTTP_404_NOT_FOUND,
                msg="任务不存在"
            )
        except Exception as e:
            return api_response(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                msg=f"下载失败: {str(e)}"
            )

    def del_result(self, request):
        """删除历史任务及其结果"""
        task_id = request.data.get("task_id")
        if not task_id:
            return api_response(
                code=status.HTTP_400_BAD_REQUEST,
                msg="缺少task_id参数"
            )

        try:
            # 删除 task 表数据
            task = OCRTask.objects.get(id=task_id)
            task.delete()

            # 删除redis key数据
            settings.REDIS.delete(f'ai_ocr_progress:{task_id}')
            return api_response()

        except OCRTask.DoesNotExist:
            return api_response(
                code=status.HTTP_404_NOT_FOUND,
                msg="任务不存在"
            )
        except Exception as e:
            return api_response(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                msg=f"删除失败: {str(e)}"
            )


class OCRCacheStatusView(APIView):
    """OCR缓存状态查看API"""
    
    permission_classes = [AllowAny]
    http_method_names = ['post']
    
    def post(self, request):
        """获取OCR缓存池状态"""
        try:
            # 创建OCRService实例来访问缓存池
            ocr_service = OCRService()
            
            # 获取缓存统计信息
            cache_info = ocr_service.ocr_pool.get_cache_info()
            
            return api_response(data={
                "cache_info": cache_info,
                "timestamp": timezone.now()
            })
            
        except Exception as e:
            logger.error(f"获取OCR缓存状态失败: {e}")
            return api_response(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                msg=f"获取缓存状态失败: {str(e)}"
            )


class OCRCacheClearView(APIView):
    """OCR缓存清理API"""
    
    permission_classes = [AllowAny]
    http_method_names = ['post']
    
    def post(self, request):
        """清空OCR缓存池"""
        try:
            # 创建OCRService实例来访问缓存池
            ocr_service = OCRService()
            
            # 清空缓存
            ocr_service.ocr_pool.clear_cache()
            
            return api_response(data={
                "timestamp": timezone.now()
            })
            
        except Exception as e:
            logger.error(f"清理OCR缓存失败: {e}")
            return api_response(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                msg=f"清理缓存失败: {str(e)}"
            )


# 在文件内新增：按helper规范导出xlsx的工具函数
def _export_helper_xlsx(request, results, task_id: str, task_name: str = ""):
    """将 OCRResult 列表导出为 helper 风格的 xlsx（多sheet）。

    返回: (bytes_io_value, filename)
    """
    import os
    import json as _json
    import numpy as _np
    import pandas as _pd
    from io import BytesIO
    from os.path import basename as _basename

    # 读取同任务汇总 JSON 以获取 confidences
    scores_map = {}
    try:
        report_dir = PathUtils.get_ocr_reports_dir()
        report_file = os.path.join(report_dir, f"{task_id}_ocr_summary.json")
        if os.path.exists(report_file):
            with open(report_file, 'r', encoding='utf-8') as jf:
                data = _json.load(jf)
                for item in data.get('items', []):
                    name = _basename(item.get('path', '') or '')
                    confs = item.get('confidences') or []
                    if isinstance(confs, list) and confs:
                        scores_map[name] = "|".join([
                            f"{float(c):.4f}" for c in confs if c is not None
                        ])
    except Exception:
        scores_map = {}

    # 读取首轮命中参数，填充参数列
    first_hit = {}
    try:
        report_dir = PathUtils.get_ocr_reports_dir()
        param_file = os.path.join(report_dir, f"{task_id}_first_hit.json")
        if os.path.exists(param_file):
            with open(param_file, 'r', encoding='utf-8') as fp:
                first_hit = _json.load(fp)
    except Exception:
        first_hit = {}

    # 分辨率缩放计算（与helper一致）
    def _compute_scaled(w: int, h: int, limit_type: str, side_len: int) -> str:
        try:
            w = int(w); h = int(h); side = int(side_len)
            if w <= 0 or h <= 0 or side <= 0:
                return f"{w}x{h}"
            cur_max = float(max(h, w)); cur_min = float(min(h, w))
            lt = str(limit_type)
            if lt == 'max':
                if cur_max > side:
                    r = float(side) / cur_max
                    sw = int(round(w * r)); sh = int(round(h * r))
                    return f"{max(1, sw)}x{max(1, sh)}"
                return f"{w}x{h}"
            if lt == 'min':
                if cur_min < side:
                    r = float(side) / cur_min
                    sw = int(round(w * r)); sh = int(round(h * r))
                    return f"{max(1, sw)}x{max(1, sh)}"
                return f"{w}x{h}"
            # 兼容未知取值
            denom = float(min(h, w)) if lt == 'min' else float(max(h, w))
            if denom <= 0:
                return f"{w}x{h}"
            r = float(side) / denom
            sw = int(round(w * r)); sh = int(round(h * r))
            return f"{max(1, sw)}x{max(1, sh)}"
        except Exception:
            return f"{w}x{h}"

    # 主表 data
    rows = []
    img_paths = []
    for r in results:
        img_path = PathUtils.normalize_path(r.image_path)
        img_paths.append(img_path)
        img_name = _basename(img_path)
        texts_list = r.texts if isinstance(r.texts, list) else []
        fh = first_hit.get(img_name) or {}
        # 分辨率
        base_w, base_h = (None, None)
        try:
            full = img_path if os.path.isabs(img_path) else os.path.join(settings.MEDIA_ROOT, img_path)
            data = _np.fromfile(full, dtype=_np.uint8)
            import cv2 as _cv2
            img_nd = _cv2.imdecode(data, _cv2.IMREAD_COLOR)
            if img_nd is not None:
                base_h, base_w = img_nd.shape[:2]
        except Exception:
            base_w, base_h = (None, None)
        resolution_str = f"{base_w}x{base_h}" if base_w and base_h else ''
        # scaled
        scaled_str = fh.get('scaled_resolution', '')
        if not scaled_str and base_w and base_h and fh.get('text_det_limit_type') and fh.get('text_det_limit_side_len'):
            scaled_str = _compute_scaled(base_w, base_h, str(fh.get('text_det_limit_type')), int(fh.get('text_det_limit_side_len')))
        if not scaled_str:
            scaled_str = resolution_str
        # texts/scores/num_items
        hit_texts = fh.get('hit_texts', '')
        texts_str = hit_texts
        scores_str = fh.get('hit_scores', '')
        num_items_val = len(str(hit_texts).split('|')) if hit_texts else 0
        rows.append({
            'image': img_name,
            'resolution': resolution_str,
            'scaled_resolution': scaled_str,
            'num_items': num_items_val,
            'scores': scores_str,
            'use_doc_orientation_classify': 'False',
            'use_doc_unwarping': str(bool(fh.get('use_doc_unwarping', False))),
            'use_textline_orientation': str(bool(fh.get('use_textline_orientation', False))),
            'text_det_limit_type': fh.get('text_det_limit_type', ''),
            'text_det_limit_side_len': fh.get('text_det_limit_side_len', ''),
            'text_det_thresh': fh.get('text_det_thresh', ''),
            'text_det_box_thresh': fh.get('text_det_box_thresh', ''),
            'text_det_unclip_ratio': fh.get('text_det_unclip_ratio', ''),
            'text_rec_score_thresh': fh.get('text_rec_score_thresh', ''),
            'texts': texts_str,
            'hit_round': fh.get('round', ''),
        })

    df_data = _pd.DataFrame(rows)

    # 尺寸与统计
    sizes = []
    for p in img_paths:
        try:
            full = p if os.path.isabs(p) else os.path.join(settings.MEDIA_ROOT, p)
            data = _np.fromfile(full, dtype=_np.uint8)
            import cv2 as _cv2
            img = _cv2.imdecode(data, _cv2.IMREAD_COLOR)
            if img is not None:
                h, w = img.shape[:2]
                sizes.append({'image': _basename(p), 'width': int(w), 'height': int(h),
                              'min_side': int(min(w, h)), 'max_side': int(max(w, h)),
                              'area': int(w) * int(h)})
        except Exception:
            continue
    df_sizes = _pd.DataFrame(sizes)

    desc = _pd.DataFrame()
    pcts = _pd.Series(dtype=float)
    bin_min_counts = _pd.DataFrame()
    bin_max_counts = _pd.DataFrame()
    summary_rows = []
    if not df_sizes.empty:
        try:
            desc = df_sizes[['min_side', 'max_side', 'width', 'height', 'area']].describe()
            pcts = df_sizes['min_side'].quantile([0.5, 0.75, 0.9, 0.95, 0.99]).rename('quantile')
            if not df_sizes.empty:
                summary_rows = [
                    {'metric': 'total_images', 'value': int(df_sizes.shape[0])},
                    {'metric': 'unique_images', 'value': int(df_sizes['image'].nunique())},
                    {'metric': 'p50_min_side', 'value': float(pcts.loc[0.5]) if 0.5 in pcts.index else None},
                    {'metric': 'p75_min_side', 'value': float(pcts.loc[0.75]) if 0.75 in pcts.index else None},
                    {'metric': 'p90_min_side', 'value': float(pcts.loc[0.9]) if 0.9 in pcts.index else None},
                    {'metric': 'p95_min_side', 'value': float(pcts.loc[0.95]) if 0.95 in pcts.index else None},
                    {'metric': 'p99_min_side', 'value': float(pcts.loc[0.99]) if 0.99 in pcts.index else None},
                ]
            # 直方分布
            bins_min = [0, 80, 100, 120, 140, 160, 180, 200, 240, 320, 480, 720, 960, 1280, 1600, _np.inf]
            labels_min = ['0-80','80-100','100-120','120-140','140-160','160-180','180-200','200-240','240-320','320-480','480-720','720-960','960-1280','1280-1600','1600+']
            df_sizes['min_side_bin'] = _pd.cut(df_sizes['min_side'], bins=bins_min, labels=labels_min, right=False)
            bin_min_counts = df_sizes['min_side_bin'].value_counts().sort_index().rename('count').reset_index().rename(columns={'index': 'min_side_bin'})
            bins_max = [0, 160, 200, 240, 320, 480, 640, 720, 960, 1280, 1600, 1920, 2560, 3000, 4000, _np.inf]
            labels_max = ['0-160','160-200','200-240','240-320','320-480','480-640','640-720','720-960','960-1280','1280-1600','1600-1920','1920-2560','2560-3000','3000-4000','4000+']
            df_sizes['max_side_bin'] = _pd.cut(df_sizes['max_side'], bins=bins_max, labels=labels_max, right=False)
            bin_max_counts = df_sizes['max_side_bin'].value_counts().sort_index().rename('count').reset_index().rename(columns={'index': 'max_side_bin'})
        except Exception:
            pass

    # 输出xlsx到内存
    bio = BytesIO()
    try:
        with _pd.ExcelWriter(bio, engine='openpyxl') as xw:
            df_data.to_excel(xw, sheet_name='data', index=False)
            if summary_rows:
                _pd.DataFrame(summary_rows).to_excel(xw, sheet_name='summary', index=False)
            if not desc.empty:
                desc.reset_index().rename(columns={'index': 'stat'}).to_excel(xw, sheet_name='size_stats', index=False)
            if not bin_min_counts.empty:
                bin_min_counts.to_excel(xw, sheet_name='size_bins_min', index=False)
            if not bin_max_counts.empty:
                bin_max_counts.to_excel(xw, sheet_name='size_bins_max', index=False)
    except Exception:
        with _pd.ExcelWriter(bio, engine='xlsxwriter') as xw:
            df_data.to_excel(xw, sheet_name='data', index=False)
            if summary_rows:
                _pd.DataFrame(summary_rows).to_excel(xw, sheet_name='summary', index=False)
            if not desc.empty:
                desc.reset_index().rename(columns={'index': 'stat'}).to_excel(xw, sheet_name='size_stats', index=False)
            if not bin_min_counts.empty:
                bin_min_counts.to_excel(xw, sheet_name='size_bins_min', index=False)
            if not bin_max_counts.empty:
                bin_max_counts.to_excel(xw, sheet_name='size_bins_max', index=False)

    filename = f"{task_name or task_id}_helper.xlsx"
    return bio.getvalue(), filename
