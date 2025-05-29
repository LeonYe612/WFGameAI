#!/usr/bin/env python
"""
设置脚本的include_in_log属性
- start_app1.json 和 stop_app1.json 设置为 False（不加入日志）
- 其他脚本设置为 True（加入日志）
"""
import os
import sys
import django

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wfgame_ai_server_main.settings')
django.setup()

from apps.scripts.models import Script

def setup_include_in_log():
    """设置脚本的include_in_log属性"""

    print("🔧 设置脚本的include_in_log属性...")

    # 不加入日志的脚本（生命周期管理脚本）
    exclude_scripts = ['start_app1.json', 'stop_app1.json']

    # 更新所有脚本
    all_scripts = Script.objects.all()
    updated_count = 0

    for script in all_scripts:
        filename = script.filename if hasattr(script, 'filename') else script.name

        # 判断是否应该加入日志
        should_include = filename not in exclude_scripts

        # 更新include_in_log字段
        if script.include_in_log != should_include:
            script.include_in_log = should_include
            script.save()
            updated_count += 1

            status = "已加入日志" if should_include else "未加入日志"
            print(f"✅ 更新脚本: {filename} -> {status}")
        else:
            status = "已加入日志" if should_include else "未加入日志"
            print(f"✓ 脚本已正确设置: {filename} -> {status}")

    print(f"\n📊 操作完成:")
    print(f"   总脚本数: {all_scripts.count()}")
    print(f"   更新数量: {updated_count}")

    # 显示当前状态
    include_count = Script.objects.filter(include_in_log=True).count()
    exclude_count = Script.objects.filter(include_in_log=False).count()

    print(f"\n📈 当前状态:")
    print(f"   已加入日志: {include_count} 个脚本")
    print(f"   未加入日志: {exclude_count} 个脚本")

    # 显示未加入日志的脚本
    excluded_scripts = Script.objects.filter(include_in_log=False)
    if excluded_scripts.exists():
        print(f"\n🚫 未加入日志的脚本:")
        for script in excluded_scripts:
            filename = script.filename if hasattr(script, 'filename') else script.name
            print(f"   - {filename}")

if __name__ == "__main__":
    setup_include_in_log()
