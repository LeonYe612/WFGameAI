from django.db import models
from django.utils.translation import gettext_lazy as _

class AIModel(models.Model):
    """AI模型"""
    TYPE_OCR = 'ocr'
    TYPE_YOLO = 'yolo'
    
    TYPE_CHOICES = (
        (TYPE_OCR, 'OCR'),
        (TYPE_YOLO, 'YOLO'),
    )

    name = models.CharField(_('模型名称'), max_length=255)
    type = models.CharField(_('模型类型'), max_length=20, choices=TYPE_CHOICES, default=TYPE_OCR)
    version = models.CharField(_('版本号'), max_length=50)
    path = models.CharField(_('模型路径'), max_length=255, unique=True)
    description = models.TextField(_('模型描述'), blank=True, null=True)
    enable = models.BooleanField(_('是否启用'), default=True)
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)

    class Meta:
        db_table = 'ai_model'
        verbose_name = _('AI模型')
        verbose_name_plural = _('AI模型')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} v{self.version} ({self.get_type_display()})"

    def __str__(self):
        return f"{self.name} (v{self.version})"