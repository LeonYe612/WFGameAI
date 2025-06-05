# -*- coding: utf-8 -*-
"""
添加游戏生命周期脚本分类
"""

from django.db import migrations


def create_lifecycle_categories(apps, schema_editor):
    """创建游戏生命周期相关的脚本分类"""
    ScriptCategory = apps.get_model('scripts', 'ScriptCategory')

    # 创建启动游戏分类
    start_category, created = ScriptCategory.objects.get_or_create(
        name='启动游戏',
        defaults={
            'description': '用于启动游戏应用的脚本，执行后不会生成测试报告'
        }
    )
    if created:
        print(f"已创建分类: {start_category.name}")

    # 创建停止游戏分类
    stop_category, created = ScriptCategory.objects.get_or_create(
        name='停止游戏',
        defaults={
            'description': '用于停止游戏应用的脚本，执行后不会生成测试报告'
        }
    )
    if created:
        print(f"已创建分类: {stop_category.name}")


def reverse_create_lifecycle_categories(apps, schema_editor):
    """回滚操作：删除游戏生命周期分类"""
    ScriptCategory = apps.get_model('scripts', 'ScriptCategory')

    # 删除分类
    ScriptCategory.objects.filter(name__in=['启动游戏', '停止游戏']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('scripts', '0003_script_include_in_log'),
    ]

    operations = [
        migrations.RunPython(
            create_lifecycle_categories,
            reverse_create_lifecycle_categories
        ),
    ]
