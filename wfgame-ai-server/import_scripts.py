#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入文件系统中的脚本到数据库并设置正确的include_in_log属性
"""

import os
import sys
import json
import django

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wfgame_ai_server_main.settings')
django.setup()

from apps.scripts.models import ScriptFile, Script, ScriptCategory

def import_scripts_from_filesystem():
    """
    从文件系统导入脚本并正确设置include_in_log属性
    """
    # 定义脚本目录
    scripts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'apps', 'scripts', 'testcase')
    print(f"正在从以下目录导入脚本: {scripts_dir}")

    # 确保目录存在
    if not os.path.exists(scripts_dir):
        print(f"❌ 脚本目录不存在: {scripts_dir}")
        return

    # 查找所有JSON脚本文件
    script_files = [f for f in os.listdir(scripts_dir) if f.endswith('.json')]
    print(f"找到 {len(script_files)} 个脚本文件")

    # 获取或创建默认类别
    default_category, _ = ScriptCategory.objects.get_or_create(name="默认")

    # 定义生命周期脚本
    lifecycle_scripts = ['start_app1.json', 'stop_app1.json']

    # 处理每个脚本文件
    for filename in script_files:
        file_path = os.path.join(scripts_dir, filename)
        file_size = os.path.getsize(file_path)

        # 判断是否为生命周期脚本
        include_in_log = filename not in lifecycle_scripts

        # 尝试从脚本文件中提取步骤数量
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                script_content = json.load(f)
                step_count = len(script_content.get('steps', []))
        except Exception as e:
            print(f"⚠️ 无法读取脚本文件 {filename}: {e}")
            step_count = 0

        # 确定脚本类型
        if 'start_app' in filename or filename == 'start_app1.json':
            category = ScriptCategory.objects.get_or_create(name="启动程序")[0]
            script_type = 'manual'
        elif 'stop_app' in filename or filename == 'stop_app1.json':
            category = ScriptCategory.objects.get_or_create(name="停止程序")[0]
            script_type = 'manual'
        elif 'login' in filename:
            category = ScriptCategory.objects.get_or_create(name="登录流程")[0]
            script_type = 'record'
        elif 'guide' in filename:
            category = ScriptCategory.objects.get_or_create(name="引导流程")[0]
            script_type = 'record'
        else:
            category = default_category
            script_type = 'manual'

        # 创建或更新ScriptFile记录
        script_file, created = ScriptFile.objects.update_or_create(
            filename=filename,
            defaults={
                'file_path': file_path,
                'file_size': file_size,
                'step_count': step_count,
                'type': script_type,
                'category': category,
                'description': f"从文件系统导入的脚本 ({script_type})",
                'include_in_log': include_in_log
            }
        )

        if created:
            print(f"✅ 已创建新脚本: {filename}, include_in_log={include_in_log}")
        else:
            print(f"✅ 已更新现有脚本: {filename}, include_in_log={include_in_log}")

    # 打印汇总信息
    print("\n=== 汇总信息 ===")
    total_scripts = ScriptFile.objects.count()
    include_log_scripts = ScriptFile.objects.filter(include_in_log=True).count()
    exclude_log_scripts = ScriptFile.objects.filter(include_in_log=False).count()

    print(f"总脚本数: {total_scripts}")
    print(f"加入日志的脚本: {include_log_scripts}")
    print(f"未加入日志的脚本: {exclude_log_scripts}")

    print("\n脚本详情:")
    for script in ScriptFile.objects.all():
        status = "未加入日志" if not script.include_in_log else "已加入日志"
        print(f"  - {script.filename} ({script.category.name}): {status}")

if __name__ == "__main__":
    import_scripts_from_filesystem()
