"""
为现有的启动和停止脚本创建数据库记录并分配正确的分类
"""
import os
import sys
import django

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wfgame_ai_server_main.settings')
django.setup()

from apps.scripts.models import ScriptFile, ScriptCategory

def create_lifecycle_script_records():
    """为生命周期管理脚本创建数据库记录"""

    # 获取分类
    try:
        start_category = ScriptCategory.objects.get(name='启动程序')
        stop_category = ScriptCategory.objects.get(name='停止程序')
    except ScriptCategory.DoesNotExist as e:
        print(f"❌ 分类不存在: {e}")
        return

    # 定义脚本信息
    scripts = [
        {
            'filename': 'start_app1.json',
            'category': start_category,
            'description': '启动卡牌2app',
            'author': 'WFGameAI'
        },
        {
            'filename': 'stop_app1.json',
            'category': stop_category,
            'description': '停止卡牌2app',
            'author': 'WFGameAI'
        }
    ]

    # 获取testcase目录路径
    base_dir = os.path.dirname(os.path.abspath(__file__))
    testcase_dir = os.path.join(base_dir, "apps", "scripts", "testcase")

    created_count = 0
    updated_count = 0

    for script_info in scripts:
        filename = script_info['filename']
        file_path = os.path.join(testcase_dir, filename)

        # 检查文件是否存在
        if not os.path.exists(file_path):
            print(f"⚠️  文件不存在: {file_path}")
            continue

        # 获取文件大小
        file_size = os.path.getsize(file_path)

        # 计算相对路径
        relative_path = os.path.join("apps", "scripts", "testcase", filename)

        # 检查是否已存在记录
        existing_script = ScriptFile.objects.filter(filename=filename).first()

        if existing_script:
            # 更新现有记录
            existing_script.category = script_info['category']
            existing_script.description = script_info['description']
            existing_script.file_path = relative_path
            existing_script.file_size = file_size
            existing_script.save()
            updated_count += 1
            print(f"✅ 更新脚本记录: {filename} -> {script_info['category'].name}")
        else:
            # 创建新记录
            ScriptFile.objects.create(
                filename=filename,
                file_path=relative_path,
                file_size=file_size,
                category=script_info['category'],
                description=script_info['description'],
                type='manual',
                status='active'
            )
            created_count += 1
            print(f"✅ 创建脚本记录: {filename} -> {script_info['category'].name}")

    print(f"\n📊 操作完成:")
    print(f"   新创建: {created_count} 条记录")
    print(f"   更新: {updated_count} 条记录")


if __name__ == "__main__":
    create_lifecycle_script_records()
