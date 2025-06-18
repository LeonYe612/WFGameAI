#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WFGameAI统一报告系统 - 使用示例
演示如何使用新的统一报告管理系统
"""

import sys
from pathlib import Path

# 添加项目路径
base_dir = Path(__file__).resolve().parent
sys.path.append(str(base_dir))

def demonstrate_unified_report_system():
    """演示统一报告系统的主要功能"""
    print("🎯 WFGameAI统一报告系统使用示例")
    print("=" * 50)

    try:
        # 1. 导入和初始化
        print("\n1️⃣ 初始化统一报告系统...")
        from apps.reports.report_manager import ReportManager
        from apps.reports.report_generator import ReportGenerator
        from apps.reports.report_config import get_report_config

        # 获取配置
        config = get_report_config()
        print(f"✅ 配置加载成功 - 保留天数: {config.report_retention_days}")

        # 初始化管理器
        manager = ReportManager()
        generator = ReportGenerator(manager)
        print(f"✅ 报告管理器初始化成功")
        print(f"   报告根目录: {manager.reports_root}")

        # 2. 创建设备报告
        print("\n2️⃣ 创建设备报告...")
        device_name = "示例设备_iPhone13"
        device_dir = manager.create_device_report_dir(device_name)
        print(f"✅ 设备报告目录创建成功: {device_dir.name}")

        # 3. 生成报告URL
        print("\n3️⃣ 生成报告访问URL...")
        urls = manager.generate_report_urls(device_dir)
        for url_type, url in urls.items():
            print(f"   {url_type}: {url}")

        # 4. 获取报告列表
        print("\n4️⃣ 获取现有报告列表...")
        device_reports = manager.get_device_reports()
        summary_reports = manager.get_summary_reports()
        print(f"✅ 设备报告数量: {len(device_reports)}")
        print(f"✅ 汇总报告数量: {len(summary_reports)}")

        # 显示最近的几个设备报告
        if device_reports:
            print("\n   最近的设备报告:")
            for report in device_reports[:3]:  # 显示前3个
                print(f"     - {report['name']} ({report['created_str']})")

        # 5. 获取统计信息
        print("\n5️⃣ 获取系统统计信息...")
        stats = manager.get_report_stats()
        print(f"✅ 统计信息:")
        print(f"   设备报告数: {stats['device_reports_count']}")
        print(f"   汇总报告数: {stats['summary_reports_count']}")
        print(f"   总占用空间: {stats['total_size_bytes'] / 1024 / 1024:.2f} MB")
        print(f"   最后更新: {stats['last_updated']}")

        # 6. 模拟脚本配置
        print("\n6️⃣ 模拟报告生成...")
        sample_scripts = [
            {
                "path": "sample_game_script.air",
                "loop_count": 1,
                "max_duration": 300,
                "description": "游戏自动化脚本"
            },
            {
                "path": "sample_test_script.air",
                "loop_count": 2,
                "max_duration": 600,
                "description": "功能测试脚本"
            }
        ]

        # 生成设备报告（模拟）
        print("   正在生成设备报告...")
        # 注意：这里不实际生成HTML，只演示流程
        print(f"   ✅ 设备报告生成完成（模拟）")

        # 生成汇总报告
        print("   正在生成汇总报告...")
        summary_report = generator.generate_summary_report([device_dir], sample_scripts)
        if summary_report:
            print(f"   ✅ 汇总报告生成成功: {summary_report.name}")

        # 7. 清理功能演示
        print("\n7️⃣ 报告清理功能演示...")
        print("   注意: 这里只演示，不实际清理")
        # cleanup_stats = manager.cleanup_old_reports(days=30)
        print("   ✅ 清理功能可用（未执行）")

        print("\n🎉 统一报告系统演示完成！")
        print("\n📚 主要功能:")
        print("   ✅ 统一的报告目录管理")
        print("   ✅ 自动URL生成")
        print("   ✅ 报告列表和统计")
        print("   ✅ HTML报告生成")
        print("   ✅ 并发安全操作")
        print("   ✅ 配置化管理")
        print("   ✅ 错误处理和重试")

        return True

    except Exception as e:
        print(f"\n❌ 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    demonstrate_unified_report_system()
