#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务管理应用的数据模型
"""

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class TaskGroup(models.Model):
    """任务组"""
    name = models.CharField(_('组名'), max_length=100)
    description = models.TextField(_('描述'), blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                verbose_name=_('创建者'),
                                on_delete=models.SET_NULL,
                                null=True)
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)

    class Meta:
        db_table = 'ai_task_group'
        verbose_name = _('任务组')
        verbose_name_plural = _('任务组')
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class Task(models.Model):
    """测试任务"""
    STATUS_CHOICES = (
        ('pending', _('等待中')),
        ('running', _('执行中')),
        ('completed', _('已完成')),
        ('failed', _('失败')),
        ('cancelled', _('已取消')),
    )

    PRIORITY_CHOICES = (
        (0, _('低')),
        (1, _('中')),
        (2, _('高')),
    )

    name = models.CharField(_('任务名称'), max_length=255)
    group = models.ForeignKey(TaskGroup,
                           verbose_name=_('任务组'),
                           on_delete=models.SET_NULL,
                           null=True,
                           blank=True,
                           related_name='tasks')
    status = models.CharField(_('状态'), max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.IntegerField(_('优先级'), choices=PRIORITY_CHOICES, default=1)
    scripts = models.ManyToManyField('scripts.Script',
                                   verbose_name=_('关联脚本'),
                                   through='TaskScript')
    devices = models.ManyToManyField('devices.Device',
                                   verbose_name=_('目标设备'),
                                   through='TaskDevice')
    description = models.TextField(_('任务描述'), blank=True)
    schedule_time = models.DateTimeField(_('计划执行时间'), null=True, blank=True)
    start_time = models.DateTimeField(_('开始时间'), null=True, blank=True)
    end_time = models.DateTimeField(_('结束时间'), null=True, blank=True)
    execution_time = models.FloatField(_('执行时长(秒)'), null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                verbose_name=_('创建者'),
                                on_delete=models.SET_NULL,
                                null=True,
                                related_name='created_tasks')
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)

    class Meta:
        db_table = 'ai_task'
        verbose_name = _('测试任务')
        verbose_name_plural = _('测试任务')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"


class TaskScript(models.Model):
    """任务-脚本关联"""
    task = models.ForeignKey(Task,
                          verbose_name=_('任务'),
                          on_delete=models.CASCADE)
    script = models.ForeignKey('scripts.Script',
                            verbose_name=_('脚本'),
                            on_delete=models.CASCADE)
    order = models.IntegerField(_('执行顺序'), default=0)
    timeout = models.IntegerField(_('超时时间(秒)'), default=3600)
    retry_count = models.IntegerField(_('重试次数'), default=0)
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)

    class Meta:
        db_table = 'ai_task_script'
        verbose_name = _('任务脚本')
        verbose_name_plural = _('任务脚本')
        ordering = ['order']
        unique_together = ('task', 'script', 'order')

    def __str__(self):
        return f"{self.task.name} - {self.script.name} ({self.order})"


class TaskDevice(models.Model):
    """任务-设备关联"""
    STATUS_CHOICES = (
        ('pending', _('等待中')),
        ('running', _('执行中')),
        ('completed', _('已完成')),
        ('failed', _('失败')),
        ('cancelled', _('已取消')),
    )

    task = models.ForeignKey(Task,
                          verbose_name=_('任务'),
                          on_delete=models.CASCADE)
    device = models.ForeignKey('devices.Device',
                            verbose_name=_('设备'),
                            on_delete=models.CASCADE)
    status = models.CharField(_('状态'), max_length=20, choices=STATUS_CHOICES, default='pending')
    start_time = models.DateTimeField(_('开始时间'), null=True, blank=True)
    end_time = models.DateTimeField(_('结束时间'), null=True, blank=True)
    execution_time = models.FloatField(_('执行时长(秒)'), null=True, blank=True)
    error_message = models.TextField(_('错误信息'), blank=True)
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)

    class Meta:
        db_table = 'ai_task_device'
        verbose_name = _('任务设备')
        verbose_name_plural = _('任务设备')
        ordering = ['created_at']

    def __str__(self):
        return f"{self.task.name} - {self.device.name} ({self.get_status_display()})"
