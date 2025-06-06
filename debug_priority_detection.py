#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Priority检测问题诊断工具
用于分析Priority机制中AI检测失败的原因
"""

import re
import json
import os
import sys
from datetime import datetime
from pathlib import Path

def analyze_log_file(log_file_path):
    """分析日志文件，提取Priority检测相关信息"""
    print(f"分析日志文件: {log_file_path}")

    detection_attempts = []
    fallback_executions = []
    ai_results = []

    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                # 查找AI检测相关日志
                if "正在等待AI检测结果:" in line:
                    target_class = line.split("正在等待AI检测结果:")[-1].strip()
                    detection_attempts.append({
                        'line': line_num,
                        'target_class': target_class,
                        'timestamp': extract_timestamp(line)
                    })

                elif "AI检测完成" in line:
                    # 解析AI检测结果
                    result_info = parse_ai_result(line)
                    if result_info:
                        result_info['line'] = line_num
                        ai_results.append(result_info)

                elif "[FALLBACK]" in line:
                    fallback_executions.append({
                        'line': line_num,
                        'content': line,
                        'timestamp': extract_timestamp(line)
                    })

    except Exception as e:
        print(f"读取日志文件出错: {e}")
        return None

    return {
        'detection_attempts': detection_attempts,
        'ai_results': ai_results,
        'fallback_executions': fallback_executions
    }

def parse_ai_result(line):
    """解析AI检测结果日志"""
    try:
        # 提取success、detected_class、expected_class
        success_match = re.search(r'success: (\w+)', line)
        detected_match = re.search(r'detected_class: ([^,]+)', line)
        expected_match = re.search(r'expected_class: (.+)$', line)

        return {
            'success': success_match.group(1) if success_match else 'Unknown',
            'detected_class': detected_match.group(1).strip() if detected_match else 'Unknown',
            'expected_class': expected_match.group(1).strip() if expected_match else 'Unknown'
        }
    except Exception as e:
        print(f"解析AI结果出错: {e}")
        return None

def extract_timestamp(line):
    """从日志行中提取时间戳"""
    # 尝试提取常见的时间戳格式
    timestamp_patterns = [
        r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',
        r'\d{2}:\d{2}:\d{2}',
    ]

    for pattern in timestamp_patterns:
        match = re.search(pattern, line)
        if match:
            return match.group(0)

    return 'Unknown'

def analyze_detection_issues(analysis_result):
    """分析检测问题"""
    print("\n" + "="*60)
    print("Priority检测问题分析报告")
    print("="*60)

    detection_attempts = analysis_result['detection_attempts']
    ai_results = analysis_result['ai_results']
    fallback_executions = analysis_result['fallback_executions']

    print(f"\n📊 统计信息:")
    print(f"   - 检测尝试次数: {len(detection_attempts)}")
    print(f"   - AI检测结果: {len(ai_results)}")
    print(f"   - Fallback执行次数: {len(fallback_executions)}")

    # 分析AI检测结果
    if ai_results:
        print(f"\n🔍 AI检测结果分析:")
        success_count = 0
        failure_reasons = {}

        for result in ai_results:
            if result['success'] == 'True':
                success_count += 1
            else:
                # 分析失败原因
                expected = result['expected_class']
                detected = result['detected_class']

                if detected == 'None' or detected == 'Unknown':
                    reason = "AI未检测到任何目标"
                elif detected != expected:
                    reason = f"类别不匹配 (期望:{expected}, 实际:{detected})"
                else:
                    reason = "其他原因"

                failure_reasons[reason] = failure_reasons.get(reason, 0) + 1

        print(f"   - 成功检测: {success_count}/{len(ai_results)} ({success_count/len(ai_results)*100:.1f}%)")
        print(f"   - 失败检测: {len(ai_results)-success_count}/{len(ai_results)} ({(len(ai_results)-success_count)/len(ai_results)*100:.1f}%)")

        if failure_reasons:
            print(f"\n❌ 失败原因分布:")
            for reason, count in failure_reasons.items():
                print(f"   - {reason}: {count}次")

    # 分析Fallback执行
    if fallback_executions:
        print(f"\n🔄 Fallback执行分析:")
        for i, fallback in enumerate(fallback_executions, 1):
            print(f"   {i}. 行{fallback['line']}: {fallback['content']}")

    # 给出建议
    print(f"\n💡 优化建议:")

    if len(ai_results) == 0:
        print("   - ⚠️  没有找到AI检测结果，可能是检测超时或进程异常")
        print("   - 建议检查AI检测服务是否正常运行")

    elif ai_results:
        failure_rate = (len(ai_results) - success_count) / len(ai_results)
        if failure_rate > 0.5:
            print("   - ⚠️  AI检测失败率较高，建议:")
            print("     * 检查AI模型是否适合当前应用界面")
            print("     * 调整检测置信度阈值")
            print("     * 优化截图质量或分辨率")

        if "AI未检测到任何目标" in failure_reasons:
            print("   - 🎯 目标识别问题:")
            print("     * 确认目标元素在屏幕上是否可见")
            print("     * 检查class名称是否与实际界面元素匹配")
            print("     * 考虑使用更通用的class名称")

        if any("类别不匹配" in reason for reason in failure_reasons):
            print("   - 🏷️  类别匹配问题:")
            print("     * 检查JSON脚本中的class名称是否正确")
            print("     * 确认AI模型的训练数据包含相关类别")

def find_latest_log_files():
    """查找最新的日志文件"""
    log_base_dir = Path("wfgame-ai-server/staticfiles/reports")

    if not log_base_dir.exists():
        print(f"日志目录不存在: {log_base_dir}")
        return []

    # 查找设备日志目录
    device_dirs = []
    for item in log_base_dir.rglob("*"):
        if item.is_dir() and re.match(r'.*\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}', item.name):
            device_dirs.append(item)

    # 按修改时间排序
    device_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)

    log_files = []
    for device_dir in device_dirs[:5]:  # 只看最新的5个设备日志
        log_file = device_dir / "log.txt"
        if log_file.exists():
            log_files.append(log_file)

    return log_files

def main():
    """主函数"""
    print("Priority检测问题诊断工具")
    print("=" * 40)

    # 如果提供了具体日志文件路径
    if len(sys.argv) > 1:
        log_file_path = sys.argv[1]
        if not os.path.exists(log_file_path):
            print(f"日志文件不存在: {log_file_path}")
            return

        analysis_result = analyze_log_file(log_file_path)
        if analysis_result:
            analyze_detection_issues(analysis_result)
    else:
        # 自动查找最新的日志文件
        log_files = find_latest_log_files()

        if not log_files:
            print("未找到日志文件，请确认路径正确")
            print("用法: python debug_priority_detection.py [日志文件路径]")
            return

        print(f"找到 {len(log_files)} 个最新日志文件:")
        for i, log_file in enumerate(log_files, 1):
            print(f"  {i}. {log_file}")

        # 分析第一个（最新的）日志文件
        if log_files:
            print(f"\n分析最新日志文件: {log_files[0]}")
            analysis_result = analyze_log_file(log_files[0])
            if analysis_result:
                analyze_detection_issues(analysis_result)

if __name__ == "__main__":
    main()
