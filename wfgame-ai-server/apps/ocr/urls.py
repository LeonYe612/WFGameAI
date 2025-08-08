"""
OCR模块URL配置
"""

from django.urls import path

from . import api

urlpatterns = [
    # 项目管理API
    path("projects/", api.OCRProjectAPIView.as_view(), name="ocr_projects"),
    # Git仓库管理API
    path(
        "repositories/", api.OCRGitRepositoryAPIView.as_view(), name="ocr_repositories"
    ),
    # 任务管理API
    path("tasks/", api.OCRTaskAPIView.as_view(), name="ocr_tasks"),
    # 结果查询API
    path("results/", api.OCRResultAPIView.as_view(), name="ocr_results"),
    # 文件上传API
    path("upload/", api.OCRUploadAPIView.as_view(), name="ocr_upload"),
    # OCR处理API
    path("process/", api.OCRProcessAPIView.as_view(), name="ocr_process"),
    # 历史数据API
    path("history/", api.OCRHistoryAPIView.as_view(), name="ocr_history"),
]
