#!/usr/bin/env python
"""
项目监控测试数据初始化脚本
创建测试项目和示例数据，解决项目监控页面无限加载问题
"""
import os
import sys
import django
from datetime import datetime, timedelta
import random

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wfgame_ai_server_main.settings')
django.setup()

from apps.project_monitor.models import ProjectMonitor, ExecutionLog, ClassStatistics

def create_test_projects():
    """创建测试项目数据"""
    print("🚀 开始创建项目监控测试数据...")

    # 测试项目配置
    test_projects = [
        {
            'name': 'WFGame AI 自动化测试',
            'yaml_path': 'testcase/wfgame_automation.json',
            'description': 'WFGame AI自动化测试项目，包含UI元素检测和交互测试',
            'status': 'active'
        },
        {
            'name': '王者荣耀自动化',
            'yaml_path': 'testcase/wangzherongyao.json',
            'description': '王者荣耀游戏自动化测试，包含登录、战斗、升级等场景',
            'status': 'active'
        },
        {
            'name': '微信小程序测试',
            'yaml_path': 'testcase/wechat_miniprogram.json',
            'description': '微信小程序功能测试项目',
            'status': 'active'
        },
        {
            'name': '淘宝购物流程',
            'yaml_path': 'testcase/taobao_shopping.json',
            'description': '淘宝APP购物流程自动化测试',
            'status': 'inactive'
        }
    ]

    created_projects = []

    for project_data in test_projects:
        # 检查项目是否已存在
        existing_project = ProjectMonitor.objects.filter(name=project_data['name']).first()
        if existing_project:
            print(f"⚠️  项目已存在: {project_data['name']}")
            created_projects.append(existing_project)
            continue

        # 创建新项目
        project = ProjectMonitor.objects.create(**project_data)
        created_projects.append(project)
        print(f"✅ 创建项目: {project.name} (ID: {project.id})")

    return created_projects

def create_test_execution_logs(projects):
    """为项目创建执行日志示例数据"""
    print("\n📊 创建执行日志数据...")

    # 常见UI元素类名
    button_classes = [
        'login_button', 'start_game', 'confirm_button', 'close_button',
        'menu_icon', 'settings_button', 'back_button', 'next_button',
        'search_button', 'submit_button', 'cancel_button', 'refresh_button',
        'play_button', 'pause_button', 'stop_button', 'share_button'
    ]

    scenarios = [
        '登录流程', '主界面导航', '设置配置', '游戏开始',
        '功能测试', '退出流程', '错误处理', '界面切换'
    ]

    devices = ['device_001', 'device_002', 'device_003', 'test_phone_1', 'test_tablet_1']

    total_logs_created = 0

    for project in projects:
        print(f"  为项目 '{project.name}' 创建执行日志...")

        # 为每个项目创建20-50条执行记录
        num_logs = random.randint(20, 50)

        for i in range(num_logs):
            # 随机生成执行时间（过去30天内）
            days_ago = random.randint(0, 30)
            hours_ago = random.randint(0, 23)
            minutes_ago = random.randint(0, 59)

            execution_time = datetime.now() - timedelta(
                days=days_ago,
                hours=hours_ago,
                minutes=minutes_ago
            )

            # 随机选择参数
            button_class = random.choice(button_classes)
            scenario = random.choice(scenarios)
            device_id = random.choice(devices)
            success = random.choice([True, True, True, False])  # 75%成功率

            # 生成检测时间 (毫秒)
            if success:
                detection_time_ms = random.randint(50, 800)  # 成功时较快
            else:
                detection_time_ms = random.randint(1000, 5000)  # 失败时较慢

            # 生成坐标
            coordinates_x = random.randint(100, 1000) if success else None
            coordinates_y = random.randint(100, 1800) if success else None

            # 创建执行日志
            ExecutionLog.objects.create(
                project=project,
                button_class=button_class,
                scenario=scenario,
                success=success,
                detection_time_ms=detection_time_ms,
                coordinates_x=coordinates_x,
                coordinates_y=coordinates_y,
                screenshot_path=f'screenshots/{device_id}_{int(execution_time.timestamp())}.jpg' if success else '',
                device_id=device_id,
                executed_at=execution_time
            )

            total_logs_created += 1

        print(f"    ✅ 创建了 {num_logs} 条执行日志")

    print(f"📊 总共创建了 {total_logs_created} 条执行日志")
    return total_logs_created

def create_test_class_statistics(projects):
    """为项目创建类统计数据"""
    print("\n📈 创建类统计数据...")

    button_classes = [
        'login_button', 'start_game', 'confirm_button', 'close_button',
        'menu_icon', 'settings_button', 'back_button', 'next_button',
        'search_button', 'submit_button', 'cancel_button', 'refresh_button'
    ]

    total_stats_created = 0

    for project in projects:
        print(f"  为项目 '{project.name}' 创建类统计...")

        for button_class in button_classes:            # 随机生成统计数据
            total_executions = random.randint(10, 100)
            total_successes = random.randint(int(total_executions * 0.6), total_executions)
            total_failures = total_executions - total_successes

            success_rate = (total_successes / total_executions) if total_executions > 0 else 0
            avg_detection_time = random.uniform(100, 600)  # 100-600毫秒

            # 创建类统计
            ClassStatistics.objects.create(
                project=project,
                button_class=button_class,
                total_executions=total_executions,
                total_successes=total_successes,
                total_failures=total_failures,
                success_rate=success_rate,
                avg_detection_time_ms=avg_detection_time
            )

            total_stats_created += 1

        print(f"    ✅ 创建了 {len(button_classes)} 条类统计")

    print(f"📈 总共创建了 {total_stats_created} 条类统计")
    return total_stats_created

def display_summary():
    """显示数据库状态摘要"""
    print("\n" + "="*60)
    print("📊 项目监控数据库状态摘要")
    print("="*60)

    # 统计项目数量
    total_projects = ProjectMonitor.objects.count()
    active_projects = ProjectMonitor.objects.filter(status='active').count()

    print(f"📁 项目总数: {total_projects}")
    print(f"🟢 活跃项目: {active_projects}")
    print(f"🔴 非活跃项目: {total_projects - active_projects}")

    # 统计执行日志
    total_logs = ExecutionLog.objects.count()
    successful_logs = ExecutionLog.objects.filter(success=True).count()

    print(f"📋 执行日志总数: {total_logs}")
    print(f"✅ 成功执行: {successful_logs}")
    print(f"❌ 失败执行: {total_logs - successful_logs}")

    # 统计类统计
    total_stats = ClassStatistics.objects.count()
    print(f"📊 类统计记录: {total_stats}")

    # 按项目显示详细信息
    print("\n📋 各项目详细信息:")
    for project in ProjectMonitor.objects.all():
        logs_count = ExecutionLog.objects.filter(project=project).count()
        stats_count = ClassStatistics.objects.filter(project=project).count()
        print(f"  • {project.name}")
        print(f"    - 状态: {project.status}")
        print(f"    - 执行日志: {logs_count} 条")
        print(f"    - 类统计: {stats_count} 条")

    print("\n✅ 项目监控数据初始化完成！")
    print("🌐 现在可以访问项目监控页面查看数据了")

def main():
    """主函数"""
    print("🎯 WFGame AI 项目监控数据初始化")
    print("=" * 50)

    try:
        # 创建测试项目
        projects = create_test_projects()

        # 创建执行日志
        create_test_execution_logs(projects)

        # 创建类统计
        create_test_class_statistics(projects)

        # 显示摘要
        display_summary()

    except Exception as e:
        print(f"❌ 初始化过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
