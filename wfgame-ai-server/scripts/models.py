#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================
Description:
脚本管理应用的数据模型
Author: WFGame AI Team
CreateDate: 2024-05-15
Version: 1.0
===============================
"""

import os
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class ScriptCategory(models.Model):
    """
    脚本分类模型
    
    用于对测试脚本进行分类管理，如登录流程、战斗流程、UI测试等
    """
    name = models.CharField(_('分类名称'), max_length=100)
    description = models.TextField(_('分类描述'), blank=True)
    parent = models.ForeignKey('self', verbose_name=_('父分类'), 
                              on_delete=models.CASCADE, 
                              null=True, blank=True, 
                              related_name='children')
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)

    class Meta:
        verbose_name = _('脚本分类')
        verbose_name_plural = _('脚本分类')
        ordering = ['name']

    def __str__(self):
        return self.name


class Script(models.Model):
    """
    测试脚本模型
    
    存储测试脚本的基本信息和内容
    """
    TYPE_CHOICES = (
        ('record', _('录制')),
        ('manual', _('手动')),
        ('generated', _('自动生成')),
    )
    
    name = models.CharField(_('脚本名称'), max_length=255)
    type = models.CharField(_('脚本类型'), max_length=20, choices=TYPE_CHOICES, default='manual')
    category = models.ForeignKey(ScriptCategory, 
                                verbose_name=_('所属分类'), 
                                on_delete=models.SET_NULL, 
                                null=True, 
                                related_name='scripts')
    content = models.TextField(_('脚本内容'))
    description = models.TextField(_('脚本描述'), blank=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, 
                             verbose_name=_('创建者'), 
                             on_delete=models.SET_NULL, 
                             null=True, 
                             related_name='created_scripts')
    is_active = models.BooleanField(_('是否启用'), default=True)
    execution_count = models.IntegerField(_('执行次数'), default=0)
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)

    class Meta:
        verbose_name = _('测试脚本')
        verbose_name_plural = _('测试脚本')
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['type']),
        ]

    def __str__(self):
        return self.name


class ScriptExecution(models.Model):
    """
    脚本执行记录模型
    
    记录每次脚本执行的状态和结果
    """
    STATUS_CHOICES = (
        ('pending', _('等待中')),
        ('running', _('执行中')),
        ('completed', _('已完成')),
        ('failed', _('失败')),
        ('cancelled', _('已取消')),
    )
    
    script = models.ForeignKey(Script, 
                              verbose_name=_('脚本'), 
                              on_delete=models.CASCADE, 
                              related_name='executions')
    status = models.CharField(_('执行状态'), max_length=20, choices=STATUS_CHOICES, default='pending')
    start_time = models.DateTimeField(_('开始时间'), null=True, blank=True)
    end_time = models.DateTimeField(_('结束时间'), null=True, blank=True)
    execution_time = models.FloatField(_('执行时长(秒)'), null=True, blank=True)
    result = models.TextField(_('执行结果'), blank=True)
    error_message = models.TextField(_('错误信息'), blank=True)
    executed_by = models.ForeignKey(settings.AUTH_USER_MODEL, 
                                  verbose_name=_('执行人'), 
                                  on_delete=models.SET_NULL, 
                                  null=True, 
                                  related_name='executed_scripts')
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)

    class Meta:
        verbose_name = _('脚本执行记录')
        verbose_name_plural = _('脚本执行记录')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.script.name} - {self.get_status_display()} - {self.created_at}"


class ScriptVersion(models.Model):
    """脚本版本历史"""
    script = models.ForeignKey(Script, 
                              verbose_name=_('脚本'), 
                              on_delete=models.CASCADE, 
                              related_name='versions')
    version = models.CharField(_('版本'), max_length=50)
    content = models.JSONField(_('脚本内容'), default=dict)
    comment = models.TextField(_('版本说明'), blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, 
                                  verbose_name=_('创建者'), 
                                  on_delete=models.SET_NULL, 
                                  null=True, blank=True)
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)

    class Meta:
        verbose_name = _('脚本版本')
        verbose_name_plural = _('脚本版本')
        ordering = ['-created_at']
        unique_together = [['script', 'version']]

    def __str__(self):
        return f"{self.script.name} v{self.version}" 