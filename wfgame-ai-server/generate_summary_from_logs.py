#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================
Description:
基于现有设备日志生成汇总报告
Author: WFGame AI Team
CreateDate: 2025-06-17
===============================
"""

import os
import json
import glob
import shutil
from datetime import datetime
from jinja2 import Template

# 项目路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEVICE_REPORTS_DIR = os.path.join(BASE_DIR, 'staticfiles', 'reports', 'ui_run', 'WFGameAI.air', 'log')
SUMMARY_REPORTS_DIR = os.path.join(BASE_DIR, 'staticfiles', 'reports', 'summary_reports')

# 确保目录存在
os.makedirs(DEVICE_REPORTS_DIR, exist_ok=True)
os.makedirs(SUMMARY_REPORTS_DIR, exist_ok=True)

def parse_device_log(device_dir):
    """解析设备日志文件"""
    log_file = os.path.join(device_dir, 'log.txt')
    if not os.path.exists(log_file):
        return None

    device_name = os.path.basename(device_dir)
    device_info = {
        'name': device_name,
        'status': '失败',
        'start_time': '',
        'end_time': '',
        'executed_scripts': 0,
        'success': False,
        'report_url': f'/static/reports/ui_run/WFGameAI.air/log/{device_name}/log.html'
    }

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        start_found = False
        end_found = False

        for line in lines:
            try:
                data = json.loads(line.strip())
                if data.get('tag') == 'function':
                    func_data = data.get('data', {})
                    func_name = func_data.get('name', '')

                    if func_name == '开始测试':
                        start_found = True
                        start_time = func_data.get('start_time', 0)
                        device_info['start_time'] = datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')
                        scripts = func_data.get('call_args', {}).get('scripts', [])
                        device_info['executed_scripts'] = len(scripts)

                    elif func_name == '结束测试':
                        end_found = True
                        end_time = func_data.get('end_time', 0)
                        device_info['end_time'] = datetime.fromtimestamp(end_time).strftime('%Y-%m-%d %H:%M:%S')
                        executed_scripts = func_data.get('call_args', {}).get('executed_scripts', 0)
                        if executed_scripts > 0:
                            device_info['success'] = True
                            device_info['status'] = '通过'
            except (json.JSONDecodeError, KeyError, ValueError):
                continue

        # 如果找到了开始和结束标记，认为执行成功
        if start_found and end_found:
            device_info['success'] = True
            device_info['status'] = '通过'

    except Exception as e:
        print(f"解析设备日志失败 {device_dir}: {e}")

    return device_info

def generate_summary_report(device_names=None):
    """生成汇总报告 - 基于指定的设备列表或最新执行的设备"""
    print("开始基于现有日志生成汇总报告...")

    # 确保汇总报告目录存在
    os.makedirs(SUMMARY_REPORTS_DIR, exist_ok=True)

    # 扫描所有设备目录
    all_device_dirs = [d for d in glob.glob(os.path.join(DEVICE_REPORTS_DIR, '*')) if os.path.isdir(d)]

    if not all_device_dirs:
        print("没有找到任何设备目录")
        return None

    target_device_dirs = []

    if device_names:
        # 如果提供了设备名称列表，只处理这些设备的最新目录
        print(f"处理指定的设备列表: {device_names}")
        for device_name in device_names:
            # 查找每个设备的最新目录
            device_dirs_for_name = [d for d in all_device_dirs if os.path.basename(d).startswith(device_name)]
            if device_dirs_for_name:
                # 取该设备的最新目录
                latest_dir = max(device_dirs_for_name,
                               key=lambda x: os.path.getmtime(os.path.join(x, 'log.txt')) if os.path.exists(os.path.join(x, 'log.txt')) else 0)
                target_device_dirs.append(latest_dir)
                print(f"发现设备 {device_name} 的最新目录: {os.path.basename(latest_dir)}")
    else:
        # 如果没有提供设备列表，使用最新的一组设备（同一时间戳的设备）
        print("未指定设备列表，查找最新的一组设备")

        # 按修改时间排序，获取最新的设备目录
        all_device_dirs.sort(key=lambda x: os.path.getmtime(os.path.join(x, 'log.txt')) if os.path.exists(os.path.join(x, 'log.txt')) else 0, reverse=True)

        if all_device_dirs:
            # 获取最新设备的修改时间
            latest_device_dir = all_device_dirs[0]
            latest_log_file = os.path.join(latest_device_dir, 'log.txt')
            if os.path.exists(latest_log_file):
                latest_time = datetime.fromtimestamp(os.path.getmtime(latest_log_file))

                # 查找与最新设备同一批次的所有设备（时间差在5分钟内）
                for device_dir in all_device_dirs:
                    log_file = os.path.join(device_dir, 'log.txt')
                    if os.path.exists(log_file):
                        device_time = datetime.fromtimestamp(os.path.getmtime(log_file))
                        time_diff = abs((latest_time - device_time).total_seconds())

                        # 只包含与最新设备时间相近的设备（5分钟内）
                        if time_diff <= 300:  # 5分钟 = 300秒
                            target_device_dirs.append(device_dir)
                            print(f"发现同批次设备: {os.path.basename(device_dir)}, 修改时间: {device_time}")
                        else:
                            break  # 因为已经按时间排序，遇到时间差大的就停止

    if not target_device_dirs:
        print("没有找到有效的设备目录")
        return None

    print(f"将处理 {len(target_device_dirs)} 个设备目录")

    devices = []
    total_devices = len(target_device_dirs)
    successful_devices = 0

    # 解析每个设备的日志
    for device_dir in target_device_dirs:
        device_info = parse_device_log(device_dir)
        if device_info:
            devices.append(device_info)
            if device_info['success']:
                successful_devices += 1
            print(f"解析设备 {device_info['name']}: {device_info['status']}")

    if not devices:
        print("没有找到有效的设备日志")
        return None

    # 按设备名排序
    devices.sort(key=lambda x: x['name'])

    # 计算统计信息
    success_rate = (successful_devices / total_devices * 100) if total_devices > 0 else 0

    # 生成时间戳
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")    # HTML模板
    html_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WFGameAI 测试汇总报告</title>
    <link href="https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        :root {
            --primary-color: #3f51b5;
            --success-color: #4caf50;
            --error-color: #f44336;
            --card-bg: #ffffff;
            --shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
            --border-radius: 8px;
        }

        body {
            font-family: "Microsoft YaHei", Arial, sans-serif;
            background-color: #f5f7fa;
            margin: 0;
            padding: 0;
            line-height: 1.6;
        }

        .header {
            background-color: var(--primary-color);
            color: white;
            padding: 30px 0;
            text-align: center;
            box-shadow: var(--shadow);
        }

        .header h1 {
            margin: 0;
            font-size: 32px;
            font-weight: 500;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }

        .card {
            background-color: var(--card-bg);
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
            margin-bottom: 30px;
            overflow: hidden;
        }

        .card-header {
            padding: 15px 20px;
            background-color: #fafafa;
            border-bottom: 1px solid #eee;
            font-weight: bold;
            color: var(--primary-color);
            font-size: 18px;
        }

        .card-body {
            padding: 20px;
        }

        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 0;
        }

        .summary-item {
            text-align: center;
            padding: 20px;
            background-color: white;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
        }

        .summary-icon {
            font-size: 28px;
            margin-bottom: 10px;
            color: var(--primary-color);
        }

        .summary-label {
            font-weight: 600;
            margin-bottom: 10px;
            color: #666;
            font-size: 14px;
        }

        .summary-value {
            font-size: 24px;
            font-weight: 700;
        }

        .summary-value.success {
            color: var(--success-color);
        }

        .summary-value.failed {
            color: var(--error-color);
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }

        th {
            background-color: #f5f5f5;
            font-weight: 600;
            color: #444;
        }

        .status {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }

        .status-success {
            background-color: rgba(76, 175, 80, 0.15);
            color: var(--success-color);
        }

        .status-failed {
            background-color: rgba(244, 67, 54, 0.15);
            color: var(--error-color);
        }

        .footer {
            text-align: center;
            margin-top: 40px;
            padding: 20px 0;
            color: #777;
            font-size: 14px;
            border-top: 1px solid #eee;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>WFGameAI 测试汇总报告</h1>
    </div>

    <div class="container">
        <div class="card">
            <div class="card-header">测试概览</div>
            <div class="card-body">                <div class="summary">
                    <div class="summary-item">
                        <div class="summary-icon">
                            <i class="fas fa-calendar-alt"></i>
                        </div>
                        <div class="summary-label">生成时间</div>
                        <div class="summary-value">{{ current_time }}</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-icon">
                            <i class="fas fa-mobile-alt"></i>
                        </div>
                        <div class="summary-label">测试设备总数</div>
                        <div class="summary-value">{{ total_devices }}</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-icon">
                            <i class="fas fa-check-circle"></i>
                        </div>
                        <div class="summary-label">成功设备数</div>
                        <div class="summary-value success">{{ successful_devices }}</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-icon">
                            <i class="fas fa-chart-pie"></i>
                        </div>
                        <div class="summary-label">成功率</div>
                        <div class="summary-value {% if success_rate >= 80 %}success{% else %}failed{% endif %}">{{ "%.1f"|format(success_rate) }}%</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="card">
            <div class="card-header">设备测试详情</div>
            <div class="card-body">
                <div class="table-responsive">
                    <table>
                        <thead>
                            <tr>
                                <th>设备名称</th>
                                <th>开始时间</th>
                                <th>结束时间</th>
                                <th>执行脚本数</th>
                                <th>测试状态</th>
                                <th>操作</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for device in devices %}
                            <tr>
                                <td class="device-name">{{ device.name }}</td>
                                <td>{{ device.start_time or '未知' }}</td>
                                <td>{{ device.end_time or '未知' }}</td>
                                <td>{{ device.executed_scripts }}</td>
                                <td>
                                    <span class="status status-{% if device.success %}success{% else %}failed{% endif %}">
                                        {{ device.status }}
                                    </span>
                                </td>
                                <td>
                                    <a href="{{ device.report_url }}" class="report-link" target="_blank">查看报告</a>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <div class="footer">
            <p>报告生成时间: {{ current_time }}</p>
            <p>© 2025 WFGame 自动化测试框架</p>
        </div>
    </div>
</body>
</html>"""    # 渲染模板
    try:
        template = Template(html_template)
        html_content = template.render(
            current_time=current_time,
            total_devices=total_devices,
            successful_devices=successful_devices,
            success_rate=success_rate,
            devices=devices
        )

        # 保存汇总报告，使用UTF-8编码并处理特殊字符
        report_filename = f"summary_report_{timestamp}.html"
        report_path = os.path.join(SUMMARY_REPORTS_DIR, report_filename)

        # 确保目录存在
        os.makedirs(os.path.dirname(report_path), exist_ok=True)

        # 安全地写入文件，处理编码问题
        try:
            with open(report_path, 'w', encoding='utf-8', errors='replace') as f:
                f.write(html_content)
        except UnicodeEncodeError as e:
            print(f"Unicode编码错误，尝试用替换方式处理: {e}")
            # 清理内容中可能导致编码问题的字符
            clean_content = html_content.encode('utf-8', errors='replace').decode('utf-8')
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(clean_content)

        # 更新latest_report.html
        latest_report_path = os.path.join(SUMMARY_REPORTS_DIR, "latest_report.html")
        try:
            shutil.copy(report_path, latest_report_path)
        except Exception as e:
            print(f"复制latest_report.html失败: {e}")

        print(f"[OK] 汇总报告已生成: {report_filename}")
        print(f"[OK] 最新报告已更新: latest_report.html")
        print(f"[OK] 统计信息: 总设备数 {total_devices}, 成功 {successful_devices}, 成功率 {success_rate:.1f}%")

        return report_path

    except Exception as e:
        print(f"生成汇总报告时发生错误: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    generate_summary_report()
