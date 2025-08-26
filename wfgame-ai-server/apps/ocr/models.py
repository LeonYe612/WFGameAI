"""
OCR模块数据模型
"""

from email.policy import default
from django.db import models
import uuid
import datetime


def generate_task_id():
    """生成任务ID"""
    # 使用YYYY-MM-dd_HH-MM-SS格式生成任务ID，确保唯一性
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H-%M-%S")
    return f"task_{date_str}_{time_str}"


class OCRProject(models.Model):
    """OCR项目模型"""

    name = models.CharField(max_length=100, verbose_name="项目名称")
    description = models.TextField(blank=True, null=True, verbose_name="项目描述")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "OCR项目"
        verbose_name_plural = "OCR项目"
        db_table = "ocr_project"


class OCRGitRepository(models.Model):
    """OCR Git仓库模型"""

    project = models.ForeignKey(
        OCRProject,
        on_delete=models.CASCADE,
        related_name="repositories",
        verbose_name="所属项目",
    )
    url = models.CharField(max_length=255, verbose_name="仓库URL")
    branch = models.CharField(max_length=100, default="main", verbose_name="默认分支")
    token = models.CharField(max_length=255, default="", verbose_name="访问令牌")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    def __str__(self):
        return f"{self.url} ({self.branch})"

    class Meta:
        verbose_name = "OCR Git仓库"
        verbose_name_plural = "OCR Git仓库"
        db_table = "ocr_git_repository"


class OCRTask(models.Model):
    """OCR任务模型"""

    STATUS_CHOICES = (
        ("pending", "等待中"),
        ("running", "执行中"),
        ("completed", "已完成"),
        ("failed", "失败"),
    )
    SOURCE_CHOICES = (("git", "Git仓库"), ("upload", "本地上传"))

    id = models.CharField(primary_key=True, max_length=50, default=generate_task_id)
    name = models.CharField(
        max_length=255, verbose_name="任务名称", blank=True, null=True
    )
    project = models.ForeignKey(
        OCRProject,
        on_delete=models.CASCADE,
        related_name="tasks",
        verbose_name="所属项目",
    )
    source_type = models.CharField(
        max_length=10, choices=SOURCE_CHOICES, verbose_name="来源类型"
    )
    git_repository = models.ForeignKey(
        OCRGitRepository,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Git仓库",
    )
    git_branch = models.CharField(
        max_length=255, default="main", verbose_name="Git分支", blank=True, null=True
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        verbose_name="任务状态",
    )
    config = models.JSONField(verbose_name="任务配置")
    start_time = models.DateTimeField(null=True, blank=True, verbose_name="开始时间")
    end_time = models.DateTimeField(null=True, blank=True, verbose_name="结束时间")
    total_images = models.IntegerField(default=0, verbose_name="总图片数")
    matched_images = models.IntegerField(default=0, verbose_name="匹配图片数")
    match_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00, verbose_name="匹配率"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    remark = models.TextField(
        blank=True, null=True, verbose_name="备注信息"
    )

    def __str__(self):
        return self.id

    class Meta:
        verbose_name = "OCR任务"
        verbose_name_plural = "OCR任务"
        db_table = "ocr_task"


class OCRResult(models.Model):
    """OCR结果模型"""

    task = models.ForeignKey(
        OCRTask,
        on_delete=models.CASCADE,
        related_name="results",
        verbose_name="所属任务",
    )
    image_path = models.CharField(max_length=255, verbose_name="图片路径")
    texts = models.JSONField(verbose_name="识别文本")
    languages = models.JSONField(null=True, blank=True, verbose_name="识别语言")
    has_match = models.BooleanField(default=False, verbose_name="是否匹配")
    confidence = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="置信度"
    )
    processing_time = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="处理时间"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    def __str__(self):
        return f"{self.task.id}_{self.id}"

    class Meta:
        verbose_name = "OCR结果"
        verbose_name_plural = "OCR结果"
        db_table = "ocr_result"
