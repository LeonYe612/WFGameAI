#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设置生命周期脚本的include_in_log属性
"""

import os
import sys
import django

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wfgame_ai_server_main.settings')
django.setup()

from apps.scripts.models import ScriptFile, Script

def setup_lifecycle_scripts():
    """设置生命周期脚本不加入日志"""

    lifecycle_scripts = ['start_app1.json', 'stop_app1.json']

    print("Setting up lifecycle scripts...")

    # 更新ScriptFile记录
    for script_name in lifecycle_scripts:
        # 查找完全匹配的文件名
        script_files = ScriptFile.objects.filter(filename=script_name)
        if script_files.exists():
            for script_file in script_files:
                script_file.include_in_log = False
                script_file.save()
                print(f"✓ Updated ScriptFile: {script_file.filename} -> include_in_log = False")
        else:
            print(f"⚠ ScriptFile not found: {script_name}")

    # 更新Script记录
    for script_name in lifecycle_scripts:
        script_base_name = script_name.replace('.json', '')
        scripts = Script.objects.filter(name__icontains=script_base_name)
        if scripts.exists():
            for script in scripts:
                script.include_in_log = False
                script.save()
                print(f"✓ Updated Script: {script.name} -> include_in_log = False")
        else:
            print(f"⚠ Script not found containing: {script_base_name}")

    # 确保其他脚本都设置为加入日志
    print("\nEnsuring other scripts are included in log...")

    # 更新其他ScriptFile记录
    other_script_files = ScriptFile.objects.exclude(filename__in=lifecycle_scripts)
    updated_count = 0
    for script_file in other_script_files:
        if not script_file.include_in_log:
            script_file.include_in_log = True
            script_file.save()
            updated_count += 1

    if updated_count > 0:
        print(f"✓ Updated {updated_count} other ScriptFile records to include_in_log = True")

    # 更新其他Script记录
    other_scripts = Script.objects.exclude(name__in=[name.replace('.json', '') for name in lifecycle_scripts])
    updated_count = 0
    for script in other_scripts:
        if not script.include_in_log:
            script.include_in_log = True
            script.save()
            updated_count += 1

    if updated_count > 0:
        print(f"✓ Updated {updated_count} other Script records to include_in_log = True")

    print("\n=== Summary ===")
    print("ScriptFile records:")
    for script_file in ScriptFile.objects.all():
        status = "未加入日志" if not script_file.include_in_log else "已加入日志"
        print(f"  {script_file.filename}: {status}")

    print("\nScript records:")
    for script in Script.objects.all():
        status = "未加入日志" if not script.include_in_log else "已加入日志"
        print(f"  {script.name}: {status}")

if __name__ == "__main__":
    setup_lifecycle_scripts()
