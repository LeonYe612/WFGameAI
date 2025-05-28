#!/usr/bin/env python
import os
import sys
import django

# 设置Django环境
sys.path.append('c:\\Users\\Administrator\\PycharmProjects\\WFGameAI\\wfgame-ai-server')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wfgame_ai_server.settings')
django.setup()

from apps.scripts.models import ScriptFile, ScriptCategory

def create_error_test_record():
    """创建错误处理测试脚本记录"""

    try:
        # 获取启动程序类别
        startup_category = ScriptCategory.objects.get(name='启动程序')

        # 创建测试脚本记录
        test_script = ScriptFile.objects.create(
            name='malformed_lifecycle_test.json',
            path='apps/scripts/testcase/malformed_lifecycle_test.json',
            category=startup_category,
            description='错误处理测试 - 缺少参数的生命周期脚本'
        )

        print(f"创建错误测试脚本记录成功:")
        print(f"  ID: {test_script.id}")
        print(f"  名称: {test_script.name}")
        print(f"  分类: {test_script.category.name}")
        print(f"  路径: {test_script.path}")

        return test_script.id

    except Exception as e:
        print(f"创建错误测试脚本记录失败: {e}")
        return None

if __name__ == "__main__":
    script_id = create_error_test_record()
    if script_id:
        print(f"\n测试脚本ID: {script_id}")
        print("可以使用这个ID进行错误处理测试")
