"""
脚本管理应用的信号处理器
"""

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
import json
import semver

from .models import Script, ScriptVersion


@receiver(pre_save, sender=Script)
def validate_script_content(sender, instance, **kwargs):
    """保存脚本前验证脚本内容的有效性"""
    # 如果脚本内容不是有效的JSON格式，将引发异常
    if isinstance(instance.content, str):
        instance.content = json.loads(instance.content)


@receiver(post_save, sender=Script)
def create_script_version(sender, instance, created, **kwargs):
    """当脚本保存时，自动创建新的版本记录"""
    if not created:
        # 检查最新版本与当前版本的内容是否相同
        latest_version = instance.versions.order_by('-created_at').first()
        
        # 如果没有版本历史或内容有变化，则创建新版本
        if not latest_version or latest_version.content != instance.content:
            # 如果存在版本，生成新版本号
            if latest_version:
                try:
                    # 尝试使用语义化版本
                    current_version = latest_version.version
                    # 增加小版本号
                    new_version = semver.bump_minor(current_version)
                except ValueError:
                    # 如果不是语义化版本，简单地添加版本后缀
                    new_version = f"{instance.version}.{instance.versions.count() + 1}"
            else:
                new_version = instance.version
                
            # 创建新版本记录
            ScriptVersion.objects.create(
                script=instance,
                version=new_version,
                content=instance.content,
                comment=f"更新于 {instance.updated_at.strftime('%Y-%m-%d %H:%M:%S')}",
                created_by=instance.author
            )
            
            # 更新脚本的当前版本号
            if instance.version != new_version:
                instance.version = new_version
                # 避免无限递归，使用update而不是save
                Script.objects.filter(pk=instance.pk).update(version=new_version) 