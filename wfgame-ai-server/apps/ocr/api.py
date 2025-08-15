"""
OCR模块API视图
"""

import os
import json
import uuid
import shutil
import tempfile
import logging
from pathlib import Path
from typing import Dict, List, Any
import tarfile
import zipfile

from django.http import HttpResponse
from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Q

from apis.orm_api import DecimalEncoder
from .models import OCRProject, OCRGitRepository, OCRTask, OCRResult
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
            return Response(serializer.data)

        elif action == "create":
            serializer = OCRProjectSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        elif action == "get":
            project_id = request.data.get("id")
            try:
                project = OCRProject.objects.get(id=project_id)
                serializer = OCRProjectSerializer(project)
                return Response(serializer.data)
            except OCRProject.DoesNotExist:
                return Response(
                    {"detail": "项目不存在"}, status=status.HTTP_404_NOT_FOUND
                )

        elif action == "delete":
            project_id = request.data.get("id")
            try:
                project = OCRProject.objects.get(id=project_id)
                project.delete()
                return Response({"detail": "项目删除成功"})
            except OCRProject.DoesNotExist:
                return Response(
                    {"detail": "项目不存在"}, status=status.HTTP_404_NOT_FOUND
                )

        return Response(
            {"detail": f"不支持的操作: {action}"}, status=status.HTTP_400_BAD_REQUEST
        )


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
            return Response(serializer.data)

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
                            return Response(
                                {"detail": "Git仓库URL无效或无法访问"},
                                status=status.HTTP_400_BAD_REQUEST,
                            )
                    except Exception as e:
                        logger.error(f"验证仓库URL失败: {str(e)}")
                        return Response(
                            {"detail": f"验证仓库URL失败: {str(e)}"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    # 保存仓库信息，但不存储令牌
                    serializer.save()

                    return Response(serializer.data, status=status.HTTP_201_CREATED)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.error(f"创建仓库异常: {str(e)}")
                return Response(
                    {"detail": f"创建仓库失败: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        elif action == "get":
            repo_id = request.data.get("id")
            try:
                repo = OCRGitRepository.objects.get(id=repo_id)
                serializer = OCRGitRepositorySerializer(repo)
                return Response(serializer.data)
            except OCRGitRepository.DoesNotExist:
                return Response(
                    {"detail": "Git仓库不存在"}, status=status.HTTP_404_NOT_FOUND
                )

        elif action == "delete":
            repo_id = request.data.get("id")
            try:
                repo = OCRGitRepository.objects.get(id=repo_id)
                repo.delete()
                return Response({"detail": "Git仓库删除成功"})
            except OCRGitRepository.DoesNotExist:
                return Response(
                    {"detail": "Git仓库不存在"}, status=status.HTTP_404_NOT_FOUND
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
                return Response({"branches": branches})
            except OCRGitRepository.DoesNotExist:
                return Response(
                    {"detail": "Git仓库不存在"}, status=status.HTTP_404_NOT_FOUND
                )
            except Exception as e:
                return Response(
                    {"detail": f"获取分支失败: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(
            {"detail": f"不支持的操作: {action}"}, status=status.HTTP_400_BAD_REQUEST
        )


class OCRTaskAPIView(APIView):
    """OCR任务API"""

    permission_classes = [AllowAny]
    http_method_names = ["post"]

    def post(self, request):
        """处理任务相关操作"""
        action = request.data.get("action", "")

        if action == "list":
            project_id = request.data.get("project_id")
            if project_id:
                tasks = OCRTask.objects.filter(project_id=project_id).order_by(
                    "-created_time"
                )
            else:
                tasks = OCRTask.objects.all().order_by("-created_time")

            serializer = OCRTaskSerializer(tasks, many=True)
            return Response(serializer.data)

        elif action == "create":
            serializer = OCRTaskCreateSerializer(data=request.data)
            if serializer.is_valid():
                # 创建任务
                task = serializer.save()

                # 提交Celery任务
                # process_ocr_task.delay(task.id)
                process_ocr_task(task.id)

                result_serializer = OCRTaskSerializer(task)
                return Response(result_serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        elif action == "get":
            task_id = request.data.get("id")
            try:
                task = OCRTask.objects.get(id=task_id)
                serializer = OCRTaskSerializer(task)

                # 检查是否有汇总报告
                report_file = task.config.get('report_file')
                if report_file and os.path.exists(report_file):
                    # 读取报告内容
                    with open(report_file, 'r', encoding='utf-8') as f:
                        report_content = f.read()

                    # 添加报告内容到响应
                    response_data = serializer.data
                    response_data['report'] = {
                        'content': report_content,
                        'file_path': report_file
                    }
                    return Response(response_data)

                return Response(serializer.data)
            except OCRTask.DoesNotExist:
                return Response(
                    {"detail": "任务不存在"}, status=status.HTTP_404_NOT_FOUND
                )

        elif action == "delete":
            task_id = request.data.get("id")
            try:
                task = OCRTask.objects.get(id=task_id)
                task.delete()
                return Response({"detail": "任务删除成功"})
            except OCRTask.DoesNotExist:
                return Response(
                    {"detail": "任务不存在"}, status=status.HTTP_404_NOT_FOUND
                )

        elif action == "get_details":
            task_id = request.data.get("id")
            has_math = request.data.get("has_match", None)
            keyword = request.data.get("keyword", None)
            try:
                task = OCRTask.objects.get(id=task_id)
                results = OCRResult.objects.filter(task=task)
                if has_math is True:
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

                return Response(
                    {
                        "task": task_serializer.data,
                        "results": results_serializer.data,
                        "total": results.count(),
                        "page": page,
                        "page_size": page_size,
                        "total_pages": (results.count() + page_size - 1) // page_size,
                    }
                )

            except OCRTask.DoesNotExist:
                return Response(
                    {"detail": "任务不存在"}, status=status.HTTP_404_NOT_FOUND
                )

        elif action == "export":
            task_id = request.data.get("id")
            export_format = request.data.get("format", "json")

            try:
                task = OCRTask.objects.get(id=task_id)
                results = OCRResult.objects.filter(task=task)

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
                    # 导出为CSV
                    import csv
                    from io import StringIO

                    csv_buffer = StringIO()
                    csv_writer = csv.writer(csv_buffer)

                    # 写入表头
                    csv_writer.writerow(
                        ["image_path", "text", "languages", "has_match"]
                    )

                    # 写入数据
                    for result in results:
                        # 确保使用相对路径
                        image_path = result.image_path
                        # 使用PathUtils规范化路径
                        image_path = PathUtils.normalize_path(image_path)

                        for text in result.texts:
                            languages = ",".join(result.languages.keys())
                            csv_writer.writerow(
                                [image_path, text, languages, result.has_match]
                            )

                    # 创建响应
                    response = HttpResponse(
                        csv_buffer.getvalue(), content_type="text/csv"
                    )
                    response["Content-Disposition"] = (
                        f"attachment; filename=ocr_task_{task_id}.csv"
                    )
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
                    return Response(
                        {"detail": f"不支持的导出格式: {export_format}"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            except OCRTask.DoesNotExist:
                return Response(
                    {"detail": "任务不存在"}, status=status.HTTP_404_NOT_FOUND
                )

        return Response(
            {"detail": f"不支持的操作: {action}"}, status=status.HTTP_400_BAD_REQUEST
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
            return Response(serializer.data)

        elif action == "get":
            result_id = request.data.get("id")
            try:
                result = OCRResult.objects.get(id=result_id)
                serializer = OCRResultSerializer(result)
                return Response(serializer.data)
            except OCRResult.DoesNotExist:
                return Response(
                    {"detail": "结果不存在"}, status=status.HTTP_404_NOT_FOUND
                )

        elif action == "search":
            # 搜索结果
            task_id = request.data.get("task_id")
            query = request.data.get("query", "")
            only_matched = request.data.get("only_matched", False)

            if not task_id:
                return Response(
                    {"detail": "缺少task_id参数"}, status=status.HTTP_400_BAD_REQUEST
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

                return Response(
                    {
                        "results": serializer.data,
                        "total": results.count(),
                        "page": page,
                        "page_size": page_size,
                        "total_pages": (results.count() + page_size - 1) // page_size,
                    }
                )

            except Exception as e:
                return Response(
                    {"detail": f"搜索失败: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(
            {"detail": f"不支持的操作: {action}"}, status=status.HTTP_400_BAD_REQUEST
        )


class OCRUploadAPIView(APIView):
    """文件上传API"""

    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    http_method_names = ["post"]

    def post(self, request):
        # 处理文件上传
        serializer = FileUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        uploaded_file = serializer.validated_data.get("file")
        project_id = serializer.validated_data.get("project_id")
        languages = serializer.validated_data.get("languages", ["ch"])

        try:
            # 确保项目存在
            try:
                project = OCRProject.objects.get(id=project_id)
            except OCRProject.DoesNotExist:
                return Response(
                    {"detail": "项目不存在"}, status=status.HTTP_404_NOT_FOUND
                )

            # 创建上传ID
            upload_id = f"upload_{uuid.uuid4().hex[:8]}"
            upload_dir = os.path.join(PathUtils.get_ocr_uploads_dir(), upload_id)
            os.makedirs(upload_dir, exist_ok=True)

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
            task = OCRTask.objects.create(
                project=project,
                source_type="upload",
                name=f"上传识别_{uploaded_file.name}",
                status="pending",
                config={
                    "target_languages": languages,
                    "upload_id": upload_id,
                    "target_dir": upload_dir,
                },
            )

            # 提交Celery任务
            # process_ocr_task.delay(task.id)
            process_ocr_task(task.id)

            serializer = OCRTaskSerializer(task)
            return Response(
                {"detail": "文件上传成功，开始OCR处理", "task": serializer.data},
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return Response(
                {"detail": f"文件上传处理失败: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
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

                try:
                    # 获取项目和仓库
                    project = OCRProject.objects.get(id=project_id)
                    git_repo = OCRGitRepository.objects.get(id=repo_id, project=project)
                    # 创建OCR任务
                    task = OCRTask.objects.create(
                        project=project,
                        git_repository=git_repo,
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
                                             )).get_repo_name(git_repo.url)

                        },
                    )

                    # process_git_ocr_task.delay(task.id, task_config)
                    process_ocr_task(task.id)

                    # 返回任务信息
                    serializer = OCRTaskSerializer(task)
                    return Response(serializer.data)

                except OCRProject.DoesNotExist:
                    return Response(
                        {"detail": "项目不存在"}, status=status.HTTP_404_NOT_FOUND
                    )
                except OCRGitRepository.DoesNotExist:
                    return Response(
                        {"detail": "仓库不存在"}, status=status.HTTP_404_NOT_FOUND
                    )
                except Exception as e:
                    return Response(
                        {"detail": f"处理失败: {str(e)}"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {"detail": f"不支持的操作: {action}"}, status=status.HTTP_400_BAD_REQUEST
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

        # 默认list操作
        serializer = OCRHistoryQuerySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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

        return Response(
            {
                "tasks": task_serializer.data,
                "total": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size,
            }
        )

    def download_results(self, request):
        """下载任务结果为CSV"""
        task_id = request.data.get("task_id")
        if not task_id:
            return Response(
                {"detail": "缺少task_id参数"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # 获取任务信息
            task = OCRTask.objects.get(id=task_id)

            # 获取该任务的所有结果
            results = OCRResult.objects.filter(task=task)

            # 导出为CSV
            import csv
            from io import StringIO

            csv_buffer = StringIO()
            csv_writer = csv.writer(csv_buffer)

            # 写入表头
            csv_writer.writerow(["id", "image_path", "texts"])

            # 写入数据
            for result in results:
                # 使用PathUtils规范化路径
                image_path = PathUtils.normalize_path(result.image_path)

                # 将texts列表转为字符串
                texts_str = " ".join(result.texts) if result.texts else ""

                csv_writer.writerow([result.id, image_path, texts_str])

            # 创建响应
            response = HttpResponse(csv_buffer.getvalue(), content_type="text/csv")

            # 使用任务名称作为文件名
            filename = f"{task.name if task.name else task.id}.csv"
            response["Content-Disposition"] = f"attachment; filename={filename}"

            return response

        except OCRTask.DoesNotExist:
            return Response(
                {"detail": "任务不存在"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"detail": f"下载失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
