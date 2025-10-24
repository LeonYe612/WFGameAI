"""
设备管理应用的数据模型
"""

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class DeviceType(models.Model):
    """设备类型"""
    name = models.CharField(_('类型名称'), max_length=100)
    description = models.TextField(_('类型描述'), blank=True)
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)

    class Meta:
        db_table = 'ai_devicetype'
        verbose_name = _('设备类型')
        verbose_name_plural = _('设备类型')
        ordering = ['name']

    def __str__(self):
        return self.name


class Device(models.Model):
    """设备"""
    ONLINE = 'online'
    OFFLINE = 'offline'
    UNAUTHORIZED = 'unauthorized'

    STATUS_CHOICES = (
        (ONLINE, _('在线')),
        (OFFLINE, _('离线')),
        (UNAUTHORIZED, _('未授权')),
    )

    name = models.CharField(_('设备名称'), max_length=255)
    device_id = models.CharField(_('设备ID'), max_length=255, unique=True)
    brand = models.CharField(_('品牌'), max_length=100, blank=True)
    model = models.CharField(_('型号'), max_length=100, blank=True)
    android_version = models.CharField(_('系统版本'), max_length=50, blank=True)
    type = models.ForeignKey(DeviceType,
                            verbose_name=_('设备类型'),
                            on_delete=models.SET_NULL,
                            null=True,
                            related_name='devices')
    status = models.CharField(_('状态'), max_length=20, choices=STATUS_CHOICES, default='offline')
    ip_address = models.CharField(_('IP地址'), max_length=50, blank=True)
    width = models.IntegerField(_('屏幕宽度'), default=0)
    height = models.IntegerField(_('屏幕高度'), default=0)
    last_online = models.DateTimeField(_('最后在线时间'), null=True, blank=True)
    description = models.TextField(_('设备描述'), blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL,
                             verbose_name=_('所有者'),
                             on_delete=models.SET_NULL,
                             null=True, blank=True,
                             related_name='owned_devices')
    current_user = models.ForeignKey(settings.AUTH_USER_MODEL,
                                    verbose_name=_('当前使用者'),
                                    on_delete=models.SET_NULL,
                                    null=True, blank=True,
                                    related_name='using_devices')
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)

    class Meta:
        db_table = 'ai_device'
        verbose_name = _('设备')
        verbose_name_plural = _('设备')
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['device_id']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.name} ({self.device_id})"


class DeviceLog(models.Model):
    """设备日志"""
    LOG_LEVEL_CHOICES = (
        ('info', _('信息')),
        ('warning', _('警告')),
        ('error', _('错误')),
        ('critical', _('严重')),
    )

    device = models.ForeignKey(Device,
                              verbose_name=_('设备'),
                              on_delete=models.CASCADE,
                              related_name='logs')
    level = models.CharField(_('日志级别'), max_length=20, choices=LOG_LEVEL_CHOICES, default='info')
    message = models.TextField(_('日志内容'))
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)

    class Meta:
        db_table = 'ai_devicelog'
        verbose_name = _('设备日志')
        verbose_name_plural = _('设备日志')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.device.name} - {self.get_level_display()} - {self.created_at}"