#!/usr/bin/env python3
"""
添加应用生命周期脚本类别到数据库
"""
import os
import sys
import django

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wfgame_ai_server_main.settings')
django.setup()

from apps.scripts.models import ScriptCategory

def add_app_lifecycle_categories():
    """添加应用生命周期管理的脚本类别"""

    # 定义新的脚本类别
    categories = [
        {
            'name': '启动程序',
            'description': '用于启动应用程序的脚本，包含应用包名和活动名称配置'
        },
        {
            'name': '停止程序',
            'description': '用于停止应用程序的脚本，通过包名强制停止应用'
        }
    ]

    created_count = 0

    for cat_data in categories:
        category, created = ScriptCategory.objects.get_or_create(
            name=cat_data['name'],
            defaults={'description': cat_data['description']}
        )

        if created:
            print(f"✅ 已创建脚本类别: {category.name}")
            created_count += 1
        else:
            print(f"ℹ️  脚本类别已存在: {category.name}")

    print(f"\n📊 共创建了 {created_count} 个新的脚本类别")

    # 显示所有类别
    print("\n📋 当前所有脚本类别:")
    for cat in ScriptCategory.objects.all():
        print(f"  - {cat.name}: {cat.description}")

if __name__ == '__main__':
    try:
        add_app_lifecycle_categories()
        print("\n✅ 脚本类别添加完成!")
    except Exception as e:
        print(f"❌ 添加脚本类别时出错: {str(e)}")
        import traceback
        traceback.print_exc()
