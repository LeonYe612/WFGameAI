#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================
Description:
用于生成测试报告结构的辅助脚本，可以快速创建测试报告样例来验证目录结构正确性
Author: WFGame AI Team
CreateDate: 2025-05-29
===============================
"""

import os
import sys
import json
import shutil
from datetime import datetime


def generate_test_device_report():
    """生成测试设备报告样例"""
    print("=== 生成测试设备报告 ===")

    # 项目根目录
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # 统一报告目录
    staticfiles_reports_dir = os.path.join(base_dir, "staticfiles", "reports")
    device_reports_dir = os.path.join(staticfiles_reports_dir, "ui_run", "WFGameAI.air", "log")

    # 确保目录存在
    os.makedirs(device_reports_dir, exist_ok=True)

    # 创建设备报告目录
    device_name = f"Test_Device_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    device_report_dir = os.path.join(device_reports_dir, device_name)
    os.makedirs(device_report_dir, exist_ok=True)

    # 创建log子目录
    log_dir = os.path.join(device_report_dir, "log")
    os.makedirs(log_dir, exist_ok=True)

    # 创建示例截图
    for i in range(3):
        # 创建空白的jpg文件
        timestamp = int(datetime.now().timestamp() * 1000) + i
        img_file = os.path.join(device_report_dir, f"{timestamp}.jpg")
        with open(img_file, "w") as f:
            f.write(f"Placeholder for image {i+1}")

        # 创建缩略图
        thumb_file = os.path.join(device_report_dir, f"{timestamp}_small.jpg")
        with open(thumb_file, "w") as f:
            f.write(f"Placeholder for thumbnail {i+1}")

    # 创建log.txt文件
    log_file = os.path.join(device_report_dir, "log.txt")
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(json.dumps({
            "tag": "function",
            "depth": 1,
            "time": datetime.now().timestamp(),
            "data": {
                "name": "test_operation",
                "call_args": {"param1": "value1"},
                "start_time": datetime.now().timestamp() - 0.1,
                "ret": True,
                "end_time": datetime.now().timestamp()
            }
        }, ensure_ascii=False) + "\n")

    # 创建HTML报告
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Device Report - {device_name}</title>
        <meta charset="utf-8">
    </head>
    <body>
        <h1>Test Device Report</h1>
        <p>Generated at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        <p>This is a test report to validate directory structure.</p>
    </body>
    </html>
    """
    html_file = os.path.join(device_report_dir, "log.html")
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"[OK] 设备报告已生成: {device_report_dir}")
    print(f"  - 报告HTML: {html_file}")
    print(f"  - 日志文件: {log_file}")
    print(f"  - 截图数量: 3")

    return device_report_dir


def generate_test_summary_report(device_reports=None):
    """生成测试汇总报告样例"""
    print("\n=== 生成测试汇总报告 ===")

    # 项目根目录
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # 统一报告目录
    staticfiles_reports_dir = os.path.join(base_dir, "staticfiles", "reports")
    summary_reports_dir = os.path.join(staticfiles_reports_dir, "summary_reports")

    # 确保目录存在
    os.makedirs(summary_reports_dir, exist_ok=True)

    # 生成时间戳
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

    # 创建汇总报告数据
    summary_data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "devices": [],
        "total": len(device_reports) if device_reports else 0,
        "success": len(device_reports) if device_reports else 0,
        "passed": 0
    }

    # 添加设备数据
    if device_reports:
        for i, device_report_dir in enumerate(device_reports):
            device_name = os.path.basename(device_report_dir)
            passed = (i % 2 == 0)  # 一半通过，一半失败

            summary_data["devices"].append({
                "name": device_name,
                "report": f"../ui_run/WFGameAI.air/log/{device_name}/log.html",
                "success": True,
                "passed": passed,
                "status": "通过" if passed else "失败"
            })

            if passed:
                summary_data["passed"] += 1

    # 计算成功率和通过率
    if summary_data["total"] > 0:
        summary_data["success_rate"] = f"{summary_data['success']}/{summary_data['total']}"
        summary_data["pass_rate"] = f"{summary_data['passed']}/{summary_data['total']}"
        summary_data["success_percent"] = f"{(summary_data['success'] / summary_data['total'] * 100):.1f}%"
        summary_data["pass_percent"] = f"{(summary_data['passed'] / summary_data['total'] * 100):.1f}%"
    else:
        summary_data["success_rate"] = "0/0"
        summary_data["pass_rate"] = "0/0"
        summary_data["success_percent"] = "0%"
        summary_data["pass_percent"] = "0%"

    # 创建HTML内容
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Summary Report - {timestamp}</title>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1 {{ color: #333; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            .pass {{ color: green; }}
            .fail {{ color: red; }}
        </style>
    </head>
    <body>
        <h1>测试汇总报告</h1>
        <p>生成时间: {summary_data["timestamp"]}</p>

        <h2>测试结果统计</h2>
        <p>总设备数: {summary_data["total"]}</p>
        <p>报告生成成功: {summary_data["success"]} ({summary_data["success_percent"]})</p>
        <p>测试通过: {summary_data["passed"]} ({summary_data["pass_percent"]})</p>

        <h2>设备详情</h2>
        <table>
            <tr>
                <th>设备</th>
                <th>状态</th>
                <th>报告链接</th>
            </tr>
    """

    # 添加设备行
    for device in summary_data["devices"]:
        status_class = "pass" if device["passed"] else "fail"
        html_content += f"""
            <tr>
                <td>{device["name"]}</td>
                <td class="{status_class}">{device["status"]}</td>
                <td><a href="{device["report"]}">查看报告</a></td>
            </tr>
        """

    # 完成HTML
    html_content += """
        </table>
    </body>
    </html>
    """

    # 保存汇总报告
    report_file = f"summary_report_{timestamp}.html"
    report_path = os.path.join(summary_reports_dir, report_file)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html_content)    # 创建latest_report.html
    latest_report_path = os.path.join(summary_reports_dir, "latest_report.html")
    shutil.copy(report_path, latest_report_path)

    print(f"[OK] 汇总报告已生成: {report_path}")
    print(f"[OK] 最新报告链接已更新: {latest_report_path}")

    return report_path


if __name__ == "__main__":
    print("开始生成测试报告来验证目录结构...")

    # 生成测试设备报告
    device_reports = []
    for i in range(3):  # 生成3个设备报告
        device_report = generate_test_device_report()
        device_reports.append(device_report)    # 生成汇总报告
    summary_report = generate_test_summary_report(device_reports)

    print("\n=== 测试报告生成完成 ===")
    print(f"[OK] 生成了 {len(device_reports)} 个设备报告")
    print(f"[OK] 生成了汇总报告: {os.path.basename(summary_report)}")
    print("\n你可以通过Web服务访问这些报告来验证统一目录结构是否工作正常。")
