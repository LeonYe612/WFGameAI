"""
项目监控系统的Django数据模型
严格遵循编码标准：MySQL数据库、ai_前缀表名
"""
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class ProjectMonitor(models.Model):
    """AI项目监控表 - 遵循ai_前缀命名规范"""
    STATUS_CHOICES = (
        ('active', _('活跃')),
        ('inactive', _('非活跃')),
    )

    name = models.CharField(_('项目名称'), max_length=100, unique=True)
    yaml_path = models.CharField(_('YAML配置路径'), max_length=255)
    description = models.TextField(_('项目描述'), blank=True)
    status = models.CharField(_('状态'), max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)

    class Meta:
        db_table = 'ai_projects'
        verbose_name = _('AI项目监控')
        verbose_name_plural = _('AI项目监控')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return self.name


class ExecutionLog(models.Model):
    """AI执行记录表 - 遵循ai_前缀命名规范"""
    project = models.ForeignKey(
        ProjectMonitor,
        verbose_name=_('项目'),
        on_delete=models.CASCADE,
        related_name='execution_logs'
    )
    button_class = models.CharField(_('按钮类名'), max_length=50)
    scenario = models.CharField(_('场景'), max_length=100, blank=True)
    success = models.BooleanField(_('执行成功'))
    detection_time_ms = models.IntegerField(_('检测时间(毫秒)'), null=True, blank=True)
    coordinates_x = models.FloatField(_('X坐标'), null=True, blank=True)
    coordinates_y = models.FloatField(_('Y坐标'), null=True, blank=True)
    screenshot_path = models.CharField(_('截图路径'), max_length=255, blank=True)
    device_id = models.CharField(_('设备ID'), max_length=50, blank=True)
    executed_at = models.DateTimeField(_('执行时间'), auto_now_add=True)

    class Meta:
        db_table = 'ai_execution_logs'
        verbose_name = _('AI执行记录')
        verbose_name_plural = _('AI执行记录')
        ordering = ['-executed_at']
        indexes = [
            models.Index(fields=['project', 'button_class']),
            models.Index(fields=['executed_at']),
            models.Index(fields=['success']),
            models.Index(fields=['button_class', 'success']),
        ]

    def __str__(self):
        return f"{self.project.name}.{self.button_class} - {'成功' if self.success else '失败'}"


class ClassStatistics(models.Model):
    """AI类统计表 - 遵循ai_前缀命名规范"""
    project = models.ForeignKey(
        ProjectMonitor,
        verbose_name=_('项目'),
        on_delete=models.CASCADE,
        related_name='class_statistics'
    )
    button_class = models.CharField(_('按钮类名'), max_length=50)
    total_executions = models.IntegerField(_('总执行次数'), default=0)
    total_successes = models.IntegerField(_('总成功次数'), default=0)
    total_failures = models.IntegerField(_('总失败次数'), default=0)
    avg_detection_time_ms = models.FloatField(_('平均检测时间(毫秒)'), null=True, blank=True)
    success_rate = models.FloatField(_('成功率'), default=0.0)
    last_executed_at = models.DateTimeField(_('最后执行时间'), null=True, blank=True)
    last_updated = models.DateTimeField(_('最后更新时间'), auto_now=True)

    class Meta:
        db_table = 'ai_class_statistics'
        verbose_name = _('AI类统计')
        verbose_name_plural = _('AI类统计')
        ordering = ['-last_updated']
        unique_together = [['project', 'button_class']]
        indexes = [
            models.Index(fields=['project', 'button_class']),
            models.Index(fields=['success_rate']),
            models.Index(fields=['last_executed_at']),
        ]

    def __str__(self):
        return f"{self.project.name}.{self.button_class} - {self.success_rate:.2%}"

    @property
    def performance_level(self):
        """性能等级评估"""
        if self.success_rate >= 0.95:
            return 'excellent'
        elif self.success_rate >= 0.85:
            return 'good'
        elif self.success_rate >= 0.70:
            return 'poor'
        else:
            return 'critical'
