"""
OCR模块数据模型
"""

from django.db import models
from django.db.models import Q
import datetime

from django.db.models import QuerySet

from apps.core.models.common import CommonFieldsMixin


def generate_task_id():
    """生成任务ID"""
    # 使用YYYY-MM-dd_HH-MM-SS格式生成任务ID，确保唯一性
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H-%M-%S")
    return f"task_{date_str}_{time_str}"

# deprecated 系统根据 team_id 自动管理数据隔离
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


class OCRGitRepository(CommonFieldsMixin):
    """OCR Git仓库模型"""

    project = models.ForeignKey(
        OCRProject,
        on_delete=models.CASCADE,
        related_name="repositories",
        verbose_name="所属项目",
        null=True,
    )
    url = models.CharField(max_length=255, verbose_name="仓库URL")
    branch = models.CharField(max_length=100, default="main", verbose_name="默认分支")
    token = models.CharField(max_length=255, default="", verbose_name="访问令牌")

    def __str__(self):
        return f"{self.url} ({self.branch})"

    class Meta:
        verbose_name = "OCR Git仓库"
        verbose_name_plural = "OCR Git仓库"
        db_table = "ocr_git_repository"


class OCRTask(CommonFieldsMixin):
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
    processed_images = models.IntegerField(default=0, verbose_name="已处理图片数")
    matched_images = models.IntegerField(default=0, verbose_name="匹配图片数")
    match_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00, verbose_name="匹配率"
    )

    def __str__(self):
        return self.id

    class Meta:
        verbose_name = "OCR任务"
        verbose_name_plural = "OCR任务"
        db_table = "ocr_task"

    @property
    def related_results(self) -> QuerySet:
        """获取关联的OCR结果列表"""
        query = Q(task_id=self.id)
        has_cache = OCRCacheHit.objects.filter(task_id=self.id).first()
        if has_cache:
            cached_result_ids = [int(i) for i in has_cache.result_ids.split(',')]
            query = Q(task_id=self.id) | Q(id__in=cached_result_ids)
        return OCRResult.objects.filter(query).order_by("id")


    def calculate_match_rate_by_related_results(self):
        """通过 related_results 计算匹配率"""
        related_results = self.related_results
        total = related_results.count()
        if total == 0:
            matched_images = 0
            match_rate = 0.00
        else:
            matched_images = related_results.filter(has_match=True).count()
            match_rate = round((matched_images / total) * 100, 2)
        self.processed_images = total
        self.matched_images = matched_images
        self.match_rate = match_rate
        self.save(update_fields=["processed_images", "matched_images", "match_rate"])



class OCRResult(CommonFieldsMixin):
    """OCR结果模型"""
    TYPE_CHOICES = (
        ("1", "正确"),
        ("2", "误检"),
        ("3", "漏检"),
    )

    task = models.ForeignKey(
        OCRTask,
        on_delete=models.CASCADE,
        related_name="results",
        verbose_name="所属任务",
    )
    image_hash = models.CharField(max_length=128, default="", verbose_name="图片哈希值")
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
    result_type = models.IntegerField(
        choices=TYPE_CHOICES, default=1, verbose_name="识别结果类型"
    )
    pic_resolution = models.CharField(max_length=50, blank=True, null=True, verbose_name="图片分辨率")

    def __str__(self):
        return f"{self.task.id}_{self.id}"

    class Meta:
        verbose_name = "OCR结果"
        verbose_name_plural = "OCR结果"
        db_table = "ocr_result"

class OCRCache(models.Model):
    """
    OCR图片缓存表
    记录已识别图片的哈希值及其对应的首次识别结果ID，避免重复识别相同图片
    以提升OCR功能响应速度，仅缓存首次识别成功的结果，后续相同图片均复用该结果
    """
    image_hash = models.CharField(primary_key=True, max_length=128, verbose_name="图片MD5哈希")
    result_id = models.BigIntegerField(db_index=True, verbose_name="首次识别结果ID")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "OCR图片缓存"
        verbose_name_plural = "OCR图片缓存"
        db_table = "ocr_cache"

    @staticmethod
    def hash_set():
        """获取所有已缓存的图片哈希集合"""
        return set(OCRCache.objects.values_list("image_hash", flat=True))

    @staticmethod
    def record_cache(task_id: str):
        """记录OCR任务的缓存结果"""
        results = OCRResult.objects.all_teams().filter(task_id=task_id).only("image_hash", "id")

        # 当前已保存的缓存记录(字典形式,方便后续查询)
        existing_caches = {
            cache.image_hash: cache
            for cache in OCRCache.objects.filter(
                image_hash__in=[r.image_hash for r in results]
            )
        }

        update_caches = []
        create_caches = []

        for result in results:
            if result.image_hash in existing_caches:
                # 更新已存在的缓存
                cache = existing_caches[result.image_hash]
                cache.result_id = result.id
                update_caches.append(cache)
            else:
                # 创建新的缓存记录
                create_caches.append(
                    OCRCache(image_hash=result.image_hash, result_id=result.id)
                )

        if update_caches:
            OCRCache.objects.bulk_update(update_caches, fields=["result_id"])

        if create_caches:
            OCRCache.objects.bulk_create(create_caches, ignore_conflicts=True)

class OCRCacheHit(models.Model):
    """
    OCR 缓存命中记录表
    本质上是 Task 和 Result 的多对多关系，但是为了将每次任务执行的空间复杂度降为 O(1)
    将 result_ids 的外键 concatenate 到 task_id 上，避免使用中间表带来的额外空间开销
    记录每次 OCR 任务中，哪些结果是通过缓存命中获得的
    """
    task_id = models.CharField(primary_key=True, max_length=50, verbose_name="OCR任务ID")
    result_ids = models.TextField(verbose_name="缓存命中结果ID列表，逗号分隔。例如：1,2,3")

    class Meta:
        verbose_name = "OCR缓存命中记录"
        verbose_name_plural = "OCR缓存命中记录"
        db_table = "ocr_cache_hit"

    @staticmethod
    def try_hit(image_hashes, task_id=None, batch_size=1000):
        """
        分批次查询 OCRCache，获取命中的结果ID列表。
        如果提供了 task_id，则同时创建 OCRCacheHit 记录。
        """
        hit_hashes = set()
        matched_result_ids = []

        for i in range(0, len(image_hashes), batch_size):
            batch_hashes = image_hashes[i : i + batch_size]
            cache_entries = OCRCache.objects.filter(image_hash__in=batch_hashes)
            matched_result_ids.extend(entry.result_id for entry in cache_entries)
            hit_hashes.update(entry.image_hash for entry in cache_entries)
        if task_id and matched_result_ids:
            OCRCacheHit.objects.create(
                task_id=task_id,
                result_ids=",".join(str(rid) for rid in matched_result_ids)
            )
        return hit_hashes


