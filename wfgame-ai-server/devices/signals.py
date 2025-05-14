"""
设备管理应用的信号处理器
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Device, DeviceLog


@receiver(post_save, sender=Device)
def log_device_status_change(sender, instance, created, **kwargs):
    """
    记录设备状态变化
    
    当设备状态变化时，自动创建日志记录
    """
    if created:
        # 新设备创建
        DeviceLog.objects.create(
            device=instance,
            level='info',
            message=f"设备 '{instance.name}' 已添加到系统，初始状态为 {instance.get_status_display()}"
        )
    else:
        # 检查设备状态是否有变化
        if hasattr(instance, '_original_status') and instance._original_status != instance.status:
            DeviceLog.objects.create(
                device=instance,
                level='info',
                message=f"设备状态从 '{instance.get_status_display()}' 变更为 '{instance.get_status_display()}'"
            )
            
            # 如果设备状态变为在线，更新最后在线时间
            if instance.status == 'online':
                instance.last_online = timezone.now()
                # 避免无限递归，使用update而不是save
                Device.objects.filter(pk=instance.pk).update(last_online=instance.last_online)


@receiver(pre_save, sender=Device)
def store_original_status(sender, instance, **kwargs):
    """
    存储设备的原始状态
    
    用于后续比较状态变化
    """
    if instance.pk:
        try:
            instance._original_status = Device.objects.get(pk=instance.pk).status
        except Device.DoesNotExist:
            pass 