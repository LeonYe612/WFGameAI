#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试报告管理应用的数据模型
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models.common import CommonFieldsMixin


class Report(CommonFieldsMixin):
    """测试报告"""
    STATUS_CHOICES = (
        ('generating', _('生成中')),
        ('completed', _('已完成')),
        ('failed', _('生成失败')),
    )

    name = models.CharField(_('报告名称'), max_length=255)
    task = models.ForeignKey('tasks.Task',
                          verbose_name=_('关联任务'),
                          on_delete=models.SET_NULL,
                          null=True,
                          related_name='reports')
    status = models.CharField(_('状态'), max_length=20, choices=STATUS_CHOICES, default='generating')
    report_path = models.CharField(_('报告路径'), max_length=500)
    summary_path = models.CharField(_('汇总报告路径'), max_length=500, blank=True)
    start_time = models.DateTimeField(_('开始时间'))
    end_time = models.DateTimeField(_('结束时间'))
    duration = models.FloatField(_('持续时间(秒)'))
    total_cases = models.IntegerField(_('用例总数'), default=0)
    passed_cases = models.IntegerField(_('通过用例数'), default=0)
    failed_cases = models.IntegerField(_('失败用例数'), default=0)
    error_cases = models.IntegerField(_('错误用例数'), default=0)
    skipped_cases = models.IntegerField(_('跳过用例数'), default=0)
    success_rate = models.FloatField(_('成功率'), default=0)

    class Meta:
        db_table = 'report_report'
        verbose_name = _('测试报告')
        verbose_name_plural = _('测试报告')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['success_rate']),
        ]

    def __str__(self):
        return self.name


class ReportDetail(CommonFieldsMixin):
    """报告详情"""
    report = models.ForeignKey(Report,
                            verbose_name=_('报告'),
                            on_delete=models.CASCADE,
                            related_name='details')
    device = models.ForeignKey('devices.Device',
                            verbose_name=_('设备'),
                            on_delete=models.SET_NULL,
                            null=True)
    script = models.ForeignKey('scripts.Script',
                            verbose_name=_('脚本'),
                            on_delete=models.SET_NULL,
                            null=True)
    result = models.CharField(_('执行结果'), max_length=50)
    start_time = models.DateTimeField(_('开始时间'))
    end_time = models.DateTimeField(_('结束时间'))
    duration = models.FloatField(_('持续时间(秒)'))
    error_message = models.TextField(_('错误信息'), blank=True)
    screenshot_path = models.CharField(_('截图路径'), max_length=500, blank=True)
    log_path = models.CharField(_('日志路径'), max_length=500, blank=True)

    class Meta:
        db_table = 'report_detail'
        verbose_name = _('报告详情')
        verbose_name_plural = _('报告详情')
        ordering = ['start_time']

    def __str__(self):
        return f"{self.report.name} - {self.device.name if self.device else 'Unknown Device'} - {self.script.name if self.script else 'Unknown Script'}"
