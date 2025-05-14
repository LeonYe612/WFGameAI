"""
脚本管理应用的数据模型
"""

import os
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class ScriptCategory(models.Model):
    """脚本分类"""
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
    """测试脚本"""
    STATUS_CHOICES = (
        ('draft', _('草稿')),
        ('active', _('激活')),
        ('deprecated', _('废弃')),
    )
    
    name = models.CharField(_('脚本名称'), max_length=255)
    description = models.TextField(_('脚本描述'), blank=True)
    content = models.JSONField(_('脚本内容'), default=dict)
    category = models.ForeignKey(ScriptCategory, 
                                verbose_name=_('分类'), 
                                on_delete=models.SET_NULL, 
                                null=True, blank=True, 
                                related_name='scripts')
    status = models.CharField(_('状态'), max_length=20, choices=STATUS_CHOICES, default='draft')
    version = models.CharField(_('版本'), max_length=50, default='1.0.0')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, 
                              verbose_name=_('作者'), 
                              on_delete=models.SET_NULL, 
                              null=True, blank=True, 
                              related_name='scripts')
    is_template = models.BooleanField(_('是否为模板'), default=False)
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)

    class Meta:
        verbose_name = _('测试脚本')
        verbose_name_plural = _('测试脚本')
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['status']),
            models.Index(fields=['category']),
            models.Index(fields=['is_template']),
        ]

    def __str__(self):
        return f"{self.name} (v{self.version})"


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