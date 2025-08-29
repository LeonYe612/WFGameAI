"""
OCR模块序列化器
"""

from rest_framework import serializers
from django.utils import timezone
from .models import OCRProject, OCRGitRepository, OCRTask, OCRResult


class OCRProjectSerializer(serializers.ModelSerializer):
    """OCR项目序列化器"""

    class Meta:
        model = OCRProject
        fields = ["id", "name", "description", "created_at", "updated_at"]


class OCRGitRepositorySerializer(serializers.ModelSerializer):
    """OCR Git仓库序列化器"""

    class Meta:
        model = OCRGitRepository
        fields = ["id", "project", "url", "branch", "token", "created_at"]


class OCRTaskSerializer(serializers.ModelSerializer):
    """OCR任务序列化器"""

    project_name = serializers.ReadOnlyField(source="project.name")
    git_repository_url = serializers.ReadOnlyField(
        source="git_repository.url", default=""
    )
    duration = serializers.SerializerMethodField()

    class Meta:
        model = OCRTask
        fields = [
            "id",
            "project",
            "project_name",
            "source_type",
            "git_repository",
            "git_repository_url",
            "status",
            "config",
            "start_time",
            "end_time",
            "total_images",
            "matched_images",
            "match_rate",
            "created_at",
            "duration",
            "remark",
        ]
        # name 字段已从数据库模型中移除

    def get_duration(self, obj):
        """计算任务执行时长"""
        if obj.start_time and obj.end_time:
            duration = obj.end_time - obj.start_time
            return str(duration).split(".")[0]  # 格式化为 HH:MM:SS
        return "00:00:00"


class OCRResultSerializer(serializers.ModelSerializer):
    """OCR结果序列化器"""

    task_id = serializers.ReadOnlyField(source="task.id")

    class Meta:
        model = OCRResult
        fields = [
            "id",
            "task",
            "task_id",
            "image_path",
            "texts",
            "languages",
            "has_match",
            "confidence",
            "processing_time",
            "created_at",
            "result_type"
        ]


class OCRProcessGitSerializer(serializers.Serializer):
    """Git仓库处理序列化器"""

    project_id = serializers.IntegerField(required=True)
    repo_id = serializers.IntegerField(required=True)
    branch = serializers.CharField(required=False, default="main")
    languages = serializers.ListField(
        child=serializers.CharField(), required=False, default=["ch"]
    )
    token = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, data):
        """验证处理参数"""
        if not data.get("project_id"):
            raise serializers.ValidationError("项目ID为必填项")
        if not data.get("repo_id"):
            raise serializers.ValidationError("仓库ID为必填项")
        return data


class TaskCreationSerializer(serializers.Serializer):
    """任务创建序列化器"""

    project_id = serializers.IntegerField(required=True)
    source_type = serializers.ChoiceField(choices=["git", "upload"], required=True)
    git_repository_id = serializers.IntegerField(required=False, allow_null=True)
    branch = serializers.CharField(required=False, allow_blank=True, default="main")
    image_formats = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=["jpg", "jpeg", "png", "bmp", "tiff", "tif", "webp"],
    )
    target_languages = serializers.ListField(
        child=serializers.CharField(), required=False, default=["ch"]
    )

    def validate(self, data):
        """验证任务创建参数"""
        if data["source_type"] == "git" and not data.get("git_repository_id"):
            raise serializers.ValidationError("Git仓库ID为必填项")
        return data


class FileUploadSerializer(serializers.Serializer):
    """文件上传序列化器"""

    file = serializers.FileField(required=True)
    project_id = serializers.IntegerField(required=True)
    languages = serializers.ListField(
        child=serializers.CharField(), required=False, default=["ch"]
    )

    def validate_file(self, value):
        """验证上传文件"""
        # 文件大小限制 (100MB)
        if value.size > 100 * 1024 * 1024:
            raise serializers.ValidationError("文件大小不能超过100MB")

        # 验证文件扩展名
        allowed_extensions = [
            ".jpg",
            ".jpeg",
            ".png",
            ".bmp",
            ".tiff",
            ".tif",
            ".webp",
            ".zip",
            ".tar.gz",
            ".tgz",
        ]
        ext = value.name.lower()
        if not any(ext.endswith(allowed_ext) for allowed_ext in allowed_extensions):
            raise serializers.ValidationError(
                f"不支持的文件类型，允许的格式: {', '.join(allowed_extensions)}"
            )

        return value


class OCRTaskCreateSerializer(serializers.ModelSerializer):
    """OCR任务创建序列化器"""

    class Meta:
        model = OCRTask
        fields = ["id", "project", "git_repository", "source_type", "status", "config"]
        read_only_fields = ["id", "status"]

    def create(self, validated_data):
        """创建任务"""
        # 设置任务状态为待处理
        validated_data["status"] = "pending"

        # 不再需要处理 name 字段，因为它已从模型中移除
        return super().create(validated_data)


class OCRHistoryQuerySerializer(serializers.Serializer):
    """OCR历史查询序列化器"""

    project_id = serializers.IntegerField(required=False, allow_null=True)
    date_from = serializers.DateTimeField(required=False, allow_null=True)
    date_to = serializers.DateTimeField(required=False, allow_null=True)
    page = serializers.IntegerField(required=False, default=1)
    page_size = serializers.IntegerField(required=False, default=20)


class OCRTaskWithResultsSerializer(serializers.ModelSerializer):
    """带有结果统计的OCR任务序列化器"""

    project_name = serializers.ReadOnlyField(source="project.name")
    git_repository_url = serializers.ReadOnlyField(
        source="git_repository.url", default=""
    )
    duration = serializers.SerializerMethodField()
    results_count = serializers.SerializerMethodField()

    class Meta:
        model = OCRTask
        fields = [
            "id",
            "project",
            "project_name",
            "source_type",
            "git_repository",
            "git_branch",
            "git_repository_url",
            "status",
            "config",
            "start_time",
            "end_time",
            "total_images",
            "matched_images",
            "match_rate",
            "created_at",
            "duration",
            "results_count",
            "remark",
        ]
        # 排除 name 字段，直到数据库迁移完成
        # fields 中已经不包含 name，这里明确排除以确保安全

    def get_duration(self, obj):
        """计算任务执行时长"""
        if obj.start_time and obj.end_time:
            duration = obj.end_time - obj.start_time
            return str(duration).split(".")[0]  # 格式化为 HH:MM:SS
        return "00:00:00"

    def get_results_count(self, obj):
        """获取结果数量"""
        return OCRResult.objects.filter(task=obj).count()


class OCRPerformanceSerializer(serializers.Serializer):
    """OCR性能统计序列化器"""

    gpu_usage = serializers.FloatField()
    cpu_usage = serializers.FloatField()
    memory_usage = serializers.FloatField()
    active_tasks = serializers.IntegerField()
    pending_tasks = serializers.IntegerField()
    completed_tasks = serializers.IntegerField()
    failed_tasks = serializers.IntegerField()
    average_processing_time = serializers.FloatField()
