#!/usr/bin/env python
import os
import sys
import django

# 添加项目路径到sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wfgame_ai_server.settings')
django.setup()

from apps.scripts.models import ScriptFile, ScriptCategory

def main():
    print("=== Script Categories ===")
    categories = ScriptCategory.objects.all()
    for cat in categories:
        print(f"ID: {cat.id}, Name: {cat.name}")

    print("\n=== Script Files ===")
    scripts = ScriptFile.objects.all()
    for script in scripts:
        category_name = script.category.name if script.category else "None"
        print(f"ID: {script.id}, File: {script.file_name}, Category: {category_name}")

    print(f"\nTotal categories: {categories.count()}")
    print(f"Total scripts: {scripts.count()}")

    # 特别检查我们的测试脚本
    print("\n=== Test Scripts ===")
    start_scripts = ScriptFile.objects.filter(file_name__contains="start_app1")
    stop_scripts = ScriptFile.objects.filter(file_name__contains="stop_app1")

    for script in start_scripts:
        print(f"Start script - ID: {script.id}, File: {script.file_name}, Category: {script.category.name if script.category else 'None'}")

    for script in stop_scripts:
        print(f"Stop script - ID: {script.id}, File: {script.file_name}, Category: {script.category.name if script.category else 'None'}")

if __name__ == "__main__":
    main()
