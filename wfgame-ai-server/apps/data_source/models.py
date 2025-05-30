#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据源管理应用的数据模型
"""

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class DataSource(models.Model):
    """数据源"""
    TYPE_CHOICES = (
        ('excel', _('Excel文件')),
        ('database', _('数据库')),
        ('api', _('API接口')),
        ('json', _('JSON文件')),
    )

    name = models.CharField(_('数据源名称'), max_length=100)
    type = models.CharField(_('数据源类型'), max_length=20, choices=TYPE_CHOICES)
    config = models.JSONField(_('配置信息'), default=dict)
    description = models.TextField(_('描述'), blank=True)
    is_active = models.BooleanField(_('是否启用'), default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                verbose_name=_('创建者'),
                                on_delete=models.SET_NULL,
                                null=True)
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)

    class Meta:
        db_table = 'ai_data_source'
        verbose_name = _('数据源')
        verbose_name_plural = _('数据源')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"


class TestData(models.Model):
    """测试数据"""
    data_source = models.ForeignKey(DataSource,
                                 verbose_name=_('数据源'),
                                 on_delete=models.CASCADE,
                                 related_name='test_data')
    name = models.CharField(_('数据名称'), max_length=255)
    data = models.JSONField(_('数据内容'))
    tags = models.JSONField(_('标签'), default=list)
    is_active = models.BooleanField(_('是否启用'), default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                verbose_name=_('创建者'),
                                on_delete=models.SET_NULL,
                                null=True)
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)

    class Meta:
        db_table = 'ai_test_data'
        verbose_name = _('测试数据')
        verbose_name_plural = _('测试数据')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return self.name


class DataUsageLog(models.Model):
    """数据使用日志"""
    test_data = models.ForeignKey(TestData,
                               verbose_name=_('测试数据'),
                               on_delete=models.CASCADE,
                               related_name='usage_logs')
    script = models.ForeignKey('scripts.Script',
                            verbose_name=_('使用脚本'),
                            on_delete=models.SET_NULL,
                            null=True)
    task = models.ForeignKey('tasks.Task',
                          verbose_name=_('所属任务'),
                          on_delete=models.SET_NULL,
                          null=True)
    used_at = models.DateTimeField(_('使用时间'), auto_now_add=True)
    result = models.CharField(_('使用结果'), max_length=50)
    error_message = models.TextField(_('错误信息'), blank=True)

    class Meta:
        db_table = 'ai_data_usage_log'
        verbose_name = _('数据使用日志')
        verbose_name_plural = _('数据使用日志')
        ordering = ['-used_at']

    def __str__(self):
        return f"{self.test_data.name} - {self.script.name if self.script else 'Unknown Script'} ({self.used_at})"
