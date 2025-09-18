from typing import Optional

from django.db import models
from apps.core.utils.context_vars import current_user
from apps.users.models import AuthUser

def get_current_team_id() -> Optional[int]:
    """获取当前用户的激活团队ID"""
    user: AuthUser = current_user.get()
    if user and user.active_team_id:
        return user.active_team_id
    return None

class TeamFilteredManager(models.Manager):
    """支持团队过滤的自定义 Manager"""

    def get_queryset(self):
        """
        objects.all()方法重写：
        默认会使用全局上下文中的 user 对象进行数据权限过滤.
        如果用户未登录或用户没有 active_team_id，则返回空查询集.
        """
        user: AuthUser = current_user.get()
        if not user or not user.active_team_id:
            return super().get_queryset().none()

        return super().get_queryset().filter(team_id=user.active_team_id)

    def for_user(self, user:AuthUser):
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
        校验必须指定 team_id 才能创建数据.
        """
        if not kwargs.get('team_id'):
            team_id = get_current_team_id()
            if team_id:
                kwargs['team_id'] = team_id
            else:
                parent_class = self.__class__.__bases__[0].__name__
                raise ValueError(f"{parent_class} 新增数据必须指定数据归属团队，请检查是否遗漏 team_id 字段")
        return super().create(**kwargs)

    def update(self, **kwargs):
        """
        校验不能通过 update() 方法修改 team_id 字段.
        """
        if 'team_id' in kwargs:
            raise ValueError("不允许通过 update() 方法修改 team_id 字段")
        return super().update(**kwargs)

    def update_or_create(
        self,
        defaults = ...,
        create_defaults = ...,
        **kwargs,
    ):
        """
        校验必须指定 team_id 才能创建数据，且不能更新 team_id 字段.
        """
        if 'team_id' in kwargs:
            raise ValueError("不允许通过 update_or_create() 方法修改 team_id 字段")
        if not defaults:
            defaults = {}
        if not defaults.get('team_id'):
            team_id = get_current_team_id()
            if team_id:
                defaults['team_id'] = team_id
            else:
                parent_class = self.__class__.__bases__[0].__name__
                raise ValueError(f"{parent_class} 新增数据必须指定数据归属团队，请检查是否遗漏 team_id 字段")
        return super().update_or_create(
            defaults=defaults,
            create_defaults=create_defaults,
            **kwargs,
        )


class TeamOwnedMixin(models.Model):
    """支持团队所有权的抽象基类"""
    team_id = models.IntegerField(
        null=True,
        db_index=True,
        verbose_name="团队ID",
        help_text="标识数据归属的团队",
    )

    # 使用自定义 Manager
    objects = TeamFilteredManager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """保存时验证数据必须有团队归属"""
        if not self.team_id:
            team_id = get_current_team_id()
            if team_id:
                self.team_id = team_id
            else:
                parent_class = self.__class__.__bases__[0].__name__
                raise ValueError(f"{parent_class} 新增数据必须指定数据归属团队，请检查是否遗漏 team_id 字段")
        super().save(*args, **kwargs)
