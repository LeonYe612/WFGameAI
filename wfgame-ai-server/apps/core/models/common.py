import json
import logging
from typing import Optional

from django.db import models
from django.conf import settings
from apps.core.utils.context_vars import current_user
from apps.users.models import AuthUser


logger = logging.getLogger(__name__)

# 批量写库参数配置，提供统一入口
DEFAULT_BULK_CREATE_CONFIG = getattr(settings, "COMMON_BULK_CREATE_CONFIG", {})
DEFAULT_MAX_PACKET_BYTES = DEFAULT_BULK_CREATE_CONFIG.get(
    "max_packet_bytes",
    2 * 1024 * 1024,
)
DEFAULT_MAX_CHUNK_ROWS = DEFAULT_BULK_CREATE_CONFIG.get("max_chunk_rows", 500)


def _get_bulk_create_limits(user_batch_size: Optional[int] = None) -> tuple[int, int]:
    """获取批量写库限制配置"""
    config = getattr(settings, "COMMON_BULK_CREATE_CONFIG", {})
    max_packet_bytes = config.get("max_packet_bytes", DEFAULT_MAX_PACKET_BYTES)
    max_chunk_rows = config.get("max_chunk_rows", DEFAULT_MAX_CHUNK_ROWS)
    if user_batch_size:
        max_chunk_rows = min(max_chunk_rows, user_batch_size)
    max_packet_bytes = max(1, int(max_packet_bytes))
    max_chunk_rows = max(1, int(max_chunk_rows))
    return max_packet_bytes, max_chunk_rows


def _estimate_instance_payload(instance: models.Model) -> int:
    """估算单条记录在批量写库中的数据量"""
    total_bytes = 0
    for field in instance._meta.concrete_fields:
        value = getattr(instance, field.attname, None)
        if value is None:
            continue
        if isinstance(value, (bytes, bytearray, memoryview)):
            total_bytes += len(value)
            continue
        if isinstance(value, (list, dict)):
            total_bytes += len(json.dumps(value, ensure_ascii=False))
            continue
        total_bytes += len(str(value))
    return max(total_bytes, 1)


def _split_bulk_create_objects(
    objs: list[models.Model],
    max_packet_bytes: int,
    max_chunk_rows: int,
) -> list[list[models.Model]]:
    """根据配置切分批量写库数据"""
    chunks = []
    current_chunk: list[models.Model] = []
    current_bytes = 0
    for obj in objs:
        payload_size = _estimate_instance_payload(obj)
        limit_hit = (
            current_bytes + payload_size > max_packet_bytes
            or len(current_chunk) >= max_chunk_rows
        )
        if current_chunk and limit_hit:
            chunks.append(current_chunk)
            current_chunk = []
            current_bytes = 0
        if payload_size > max_packet_bytes:
            logger.warning(
                "单条记录估算大小超过批量阈值，可能导致数据库限制: 模型=%s, "
                "估算大小=%s",
                obj.__class__.__name__,
                payload_size,
            )
        current_chunk.append(obj)
        current_bytes += payload_size
    if current_chunk:
        chunks.append(current_chunk)
    return chunks


def get_current_user() -> Optional[AuthUser]:
    """获取当前用户对象"""
    return current_user.get() or None


def get_current_team_id() -> Optional[int]:
    """
    获取当前用户的 active_team_id.
    如果用户未登录或没有 active_team_id，则返回 None.
    """
    user: AuthUser = get_current_user()
    if not user or not user.active_team_id:
        return None
    return user.active_team_id


def get_current_user_id() -> int:
    """
    获取当前用户的 ID.
    如果用户未登录，则返回 0.
    """
    user: AuthUser = get_current_user()
    if not user or not user.id:
        return 0
    return user.id


def get_current_user_chinese_name() -> str:
    """
    获取当前用户的中文名称.
    如果用户未登录，则返回 "system".
    """
    user: AuthUser = get_current_user()
    if not user or not user.chinese_name:
        return "system"
    return user.chinese_name


def _fill_team_id(target, parent_class: str = None):
    """
    支持 dict 或 Model Instance，自动填充 team_id
    """
    if isinstance(target, dict):
        has_team_id = target.get('team_id')
    elif isinstance(target, models.Model):
        has_team_id = getattr(target, 'team_id', None)
    else:
        # 既不是 dict 也不是 Model，直接返回或抛错
        raise TypeError(f"_fill_team_id 仅支持 dict 或 Django Model 实例，当前类型: {type(target)}")

    if not has_team_id:
        team_id = get_current_team_id()
        if team_id:
            if isinstance(target, dict):
                target['team_id'] = team_id
            else:
                target.team_id = team_id
        else:
            if isinstance(target, dict):
                parent_class_name = 'dict'
            else:
                parent_class_name = parent_class or target.__class__.__bases__[0].__name__
            raise ValueError(f"{parent_class_name} 新增数据必须指定数据归属团队，请检查是否遗漏 team_id 字段")


def _fill_creator_fields(target):
    """
    支持 dict 或 Model Instance，自动填充 creator_id, creator_name
    """
    if isinstance(target, dict):
        if not target.get('creator_id'):
            target['creator_id'] = get_current_user_id()
        if not target.get('creator_name'):
            target['creator_name'] = get_current_user_chinese_name()
    elif isinstance(target, models.Model):
        if not getattr(target, 'creator_id', None):
            target.creator_id = get_current_user_id()
        if not getattr(target, 'creator_name', None):
            target.creator_name = get_current_user_chinese_name()
    else:
        raise TypeError(f"_fill_creator_fields 仅支持 dict 或 Django Model 实例，当前类型: {type(target)}")


def _fill_updater_fields(target):
    """
    支持 dict 或 Model Instance，自动填充 updater_id, updater_name
    """
    if isinstance(target, dict):
        if not target.get('updater_id'):
            target['updater_id'] = get_current_user_id()
        if not target.get('updater_name'):
            target['updater_name'] = get_current_user_chinese_name()
    elif isinstance(target, models.Model):
        target.updater_id = get_current_user_id()
        target.updater_name = get_current_user_chinese_name()
    else:
        raise TypeError(f"_fill_updater_fields 仅支持 dict 或 Django Model 实例，当前类型: {type(target)}")


class CommonFilteredManager(models.Manager):
    """通用的自定义过滤 Manager"""

    def get_queryset(self):
        """
        objects.all()方法重写：
        默认会使用全局上下文中的 user 对象进行数据权限过滤.
        如果用户未登录或用户没有 active_team_id，则返回空查询集.
        """
        user: AuthUser = get_current_user()
        if not user or not user.active_team_id:
            return super().get_queryset().none()

        return super().get_queryset().filter(team_id=user.active_team_id)

    def for_user(self, user: AuthUser):
        """
        显式为指定用户应用团队过滤.
        """
        if not user or not user.active_team_id:
            return super().get_queryset().none()

        return super().get_queryset().filter(team_id=user.active_team_id)

    def for_team(self, team_id: int):
        """
        显式指定团队ID进行过滤.
        """
        if not team_id:
            return super().get_queryset().none()

        return super().get_queryset().filter(team_id=team_id)

    def for_teams(self, team_ids: list[int]):
        """
        显式指定多个团队ID进行过滤.
        """
        if not team_ids:
            return super().get_queryset().none()

        return super().get_queryset().filter(team_id__in=team_ids)

    def all_teams(self):
        """获取所有团队的数据（跳过过滤）"""
        return super().get_queryset()

    def create(self, **kwargs):
        """
        新增记录时：
        1. 必须指定 team_id 字段才能创建数据
        2. 自动填充 creator_id, creator_name
        """
        _fill_team_id(kwargs, self.__class__.__bases__[0].__name__)
        _fill_creator_fields(kwargs)
        return super().create(**kwargs)

    def update(self, **kwargs):
        """
        记录一旦创建，数据归属的 team_id 字段不允许被修改.
        自动更新字段: updater_id, updater_name
        """
        if 'team_id' in kwargs:
            raise ValueError("不允许通过 update() 方法修改 team_id 字段")
        _fill_updater_fields(kwargs)
        return super().update(**kwargs)

    def update_or_create(self, defaults=None, **kwargs):
        """
        update_or_create 方法重写：
        1. 更新时不允许通过 defaults 修改 team_id 字段（新增允许）
        2. 新增时自动填充 team_id、creator_id、creator_name，更新时自动填充 updater_id、updater_name
        """
        if defaults is None:
            defaults = {}
        if 'team_id' in defaults:
            raise ValueError("不允许通过 update_or_create() 的 defaults 修改 team_id 字段")
        obj, created = self.get_queryset().filter(**kwargs).first(), False
        if obj is None:
            created = True
        if created:
            _fill_team_id(kwargs, self.__class__.__bases__[0].__name__)
            _fill_creator_fields(defaults)
            obj, _ = super().update_or_create(defaults=defaults, **kwargs)
            return obj, True
        else:
            _fill_updater_fields(defaults)
            obj, _ = super().update_or_create(defaults=defaults, **kwargs)
            return obj, False

    def bulk_create(self, objs, batch_size=None, ignore_conflicts=False, update_conflicts=False, update_fields=None, unique_fields=None):
        """
        批量创建时：
        1. 必须指定 team_id 字段，否则尝试自动填充
        2. 自动填充 creator_id, creator_name
        """
        objs = list(objs)
        if not objs:
            return []
        for obj in objs:
            _fill_team_id(obj)
            _fill_creator_fields(obj)
        max_packet_bytes, max_chunk_rows = _get_bulk_create_limits(batch_size)
        chunks = _split_bulk_create_objects(objs, max_packet_bytes, max_chunk_rows)
        if len(chunks) > 1:
            logger.warning(
                "批量写库触发自动切分: 模型=%s, 总记录=%s, 分批数量=%s, "
                "行数阈值=%s, 字节阈值=%s",
                objs[0].__class__.__name__,
                len(objs),
                len(chunks),
                max_chunk_rows,
                max_packet_bytes,
            )
        created_objs = []
        for chunk_index, chunk in enumerate(chunks, start=1):
            chunk_batch_size = batch_size
            if chunk_batch_size is not None:
                chunk_batch_size = min(len(chunk), chunk_batch_size)
            else:
                chunk_batch_size = len(chunk)
            logger.info(
                "执行批量写库: 模型=%s, 批次=%s/%s, 本批记录=%s, "
                "batch_size=%s",
                chunk[0].__class__.__name__,
                chunk_index,
                len(chunks),
                len(chunk),
                chunk_batch_size,
            )
            created_chunk = super().bulk_create(
                chunk,
                batch_size=chunk_batch_size,
                ignore_conflicts=ignore_conflicts,
                update_conflicts=update_conflicts,
                update_fields=update_fields,
                unique_fields=unique_fields
            )
            created_objs.extend(created_chunk)
        return created_objs

    def bulk_update(self, objs, fields, batch_size=100):
        """
        批量更新时：
        1. 不允许批量修改 team_id 字段
        2. 自动填充 updater_id, updater_name
        """
        # 确保 fields 可变，避免 Iterable 没有 append 的类型警告
        fields = list(fields)
        if 'team_id' in fields:
            raise ValueError("不允许通过 bulk_update() 方法修改 team_id 字段")
        for obj in objs:
            _fill_updater_fields(obj)
        if 'updater_id' not in fields:
            fields.append('updater_id')
        if 'updater_name' not in fields:
            fields.append('updater_name')
        return self.all_teams().bulk_update(objs, fields, batch_size=batch_size)

    def get_or_create(self, defaults=None, **kwargs):
        """
        get_or_create 方法重写：
        1. 新增时 team_id 必须有，没有则自动获取，获取不到报错
        2. 新增时自动填充 creator_id, creator_name
        """
        if defaults is None:
            defaults = {}
        obj = self.get_queryset().filter(**kwargs).first()
        if obj is not None:
            return obj, False
        _fill_team_id(kwargs, self.__class__.__bases__[0].__name__)
        _fill_creator_fields(defaults)
        return super().get_or_create(defaults=defaults, **kwargs)


class CommonFieldsMixin(models.Model):
    """支持团队所有权的抽象基类"""
    team_id = models.IntegerField(
        null=True,
        db_index=True,
        verbose_name="团队ID",
        help_text="标识数据归属的团队",
        editable=False
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="创建时间", editable=False)
    creator_id = models.IntegerField(default=0, verbose_name="创建用户ID", editable=False)
    creator_name = models.CharField(max_length=50, default="system", verbose_name="创建用户名称", editable=False)
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间", editable=False)
    updater_id = models.IntegerField(default=0, verbose_name="更新用户ID", editable=False)
    updater_name = models.CharField(max_length=50, default="system", verbose_name="更新用户名称", editable=False)
    sort_order = models.IntegerField(default=0, db_index=True, verbose_name="排序值")
    lock_version = models.IntegerField(default=0, verbose_name="乐观锁版本号")
    remark = models.TextField(blank=True, null=True, verbose_name="备注信息")

    # 使用自定义 Manager
    objects = CommonFilteredManager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """
        根据 self.pk 判断是新增还是更新
        - 新增时，自动填充 team_id, creator_id, creator_name
        - 更新时，自动填充 updater_id, updater_name
        """
        if not self.pk:
            # 新增记录
            _fill_team_id(self)
            _fill_creator_fields(self)
        else:
            # 更新记录
            if 'team_id' in kwargs:
                raise ValueError("不允许通过 save() 方法修改 team_id 字段")
            _fill_updater_fields(self)
        super().save(*args, **kwargs)
