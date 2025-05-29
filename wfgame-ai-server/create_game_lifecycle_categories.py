#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建生命周期分类：启动游戏和停止游戏
"""

import os
import sys
import django

# 添加项目路径到sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wfgame_ai_server_main.settings')
django.setup()

from apps.scripts.models import ScriptCategory

def create_lifecycle_categories():
    """创建生命周期管理分类"""

    categories = [
        {
            'name': '启动游戏',
            'description': '用于启动游戏应用的脚本分类'
        },
        {
            'name': '停止游戏',
            'description': '用于停止游戏应用的脚本分类'
        }
    ]

    created_count = 0

    for cat_info in categories:
        category, created = ScriptCategory.objects.get_or_create(
            name=cat_info['name'],
            defaults={'description': cat_info['description']}
        )

        if created:
            print(f"✅ 创建分类: {category.name}")
            created_count += 1
        else:
            print(f"⚠️  分类已存在: {category.name}")

    print(f"\n📊 操作完成，新创建 {created_count} 个分类")

    # 显示所有分类
    print("\n当前所有分类:")
    for category in ScriptCategory.objects.all().order_by('id'):
        print(f"  ID: {category.id}, 名称: {category.name}")

if __name__ == "__main__":
    create_lifecycle_categories()
