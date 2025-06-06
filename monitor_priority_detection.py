#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Priority检测实时监控工具
在测试执行期间实时显示Priority检测状态
"""

import time
import os
import re
import json
from pathlib import Path
from datetime import datetime

class PriorityMonitor:
    def __init__(self, log_file_path=None):
        self.log_file_path = log_file_path
        self.last_position = 0
        self.detection_count = 0
        self.success_count = 0
        self.fallback_count = 0
        self.start_time = datetime.now()

    def find_latest_log_file(self):
        """查找最新的设备日志文件"""
        log_base_dir = Path("wfgame-ai-server/staticfiles/reports")

        if not log_base_dir.exists():
            return None

        # 查找最新的设备日志目录
        device_dirs = []
        for item in log_base_dir.rglob("*"):
            if item.is_dir() and re.match(r'.*\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}', item.name):
                device_dirs.append(item)

        if not device_dirs:
            return None

        # 按修改时间排序，取最新的
        latest_dir = max(device_dirs, key=lambda x: x.stat().st_mtime)
        log_file = latest_dir / "log.txt"

        return log_file if log_file.exists() else None

    def parse_new_lines(self):
        """解析新的日志行"""
        if not self.log_file_path or not os.path.exists(self.log_file_path):
            return []

        new_events = []
        try:
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                f.seek(self.last_position)
                new_lines = f.readlines()
                self.last_position = f.tell()

                for line in new_lines:
                    line = line.strip()
                    if not line:
                        continue

                    # 检测AI检测开始
                    if "正在等待AI检测结果:" in line:
                        target_class = line.split("正在等待AI检测结果:")[-1].strip()
                        new_events.append({
                            'type': 'detection_start',
                            'target_class': target_class,
                            'timestamp': datetime.now()
                        })

                    # 检测AI检测结果
                    elif "AI检测完成" in line:
                        result_info = self.parse_ai_result(line)
                        if result_info:
                            self.detection_count += 1
                            if result_info['success'] == 'True':
                                self.success_count += 1

                            new_events.append({
                                'type': 'detection_result',
                                'result': result_info,
                                'timestamp': datetime.now()
                            })

                    # 检测Fallback执行
                    elif "[FALLBACK]" in line:
                        if "执行Priority" in line:
                            self.fallback_count += 1
                        new_events.append({
                            'type': 'fallback',
                            'content': line,
                            'timestamp': datetime.now()
                        })

                    # 检测优先级步骤尝试
                    elif "尝试优先级步骤" in line:
                        priority_match = re.search(r'P(\d+)', line)
                        class_match = re.search(r'P\d+: ([^,]+)', line)
                        new_events.append({
                            'type': 'priority_attempt',
                            'priority': priority_match.group(1) if priority_match else 'Unknown',
                            'target_class': class_match.group(1).strip() if class_match else 'Unknown',
                            'content': line,
                            'timestamp': datetime.now()
                        })

        except Exception as e:
            print(f"解析日志文件出错: {e}")

        return new_events

    def parse_ai_result(self, line):
        """解析AI检测结果"""
        try:
            success_match = re.search(r'success: (\w+)', line)
            detected_match = re.search(r'detected_class: ([^,]+)', line)
            expected_match = re.search(r'expected_class: (.+)$', line)

            return {
                'success': success_match.group(1) if success_match else 'Unknown',
                'detected_class': detected_match.group(1).strip() if detected_match else 'Unknown',
                'expected_class': expected_match.group(1).strip() if expected_match else 'Unknown'
            }
        except:
            return None

    def print_status(self):
        """打印当前状态"""
        elapsed = datetime.now() - self.start_time
        elapsed_str = str(elapsed).split('.')[0]  # 去掉微秒

        success_rate = (self.success_count / self.detection_count * 100) if self.detection_count > 0 else 0

        print(f"\r⏱️  运行时间: {elapsed_str} | "
              f"🔍 检测: {self.detection_count} | "
              f"✅ 成功: {self.success_count} ({success_rate:.1f}%) | "
              f"🔄 Fallback: {self.fallback_count}", end='', flush=True)

    def print_event(self, event):
        """打印事件信息"""
        timestamp = event['timestamp'].strftime("%H:%M:%S")

        if event['type'] == 'detection_start':
            print(f"\n🔍 [{timestamp}] 开始检测: {event['target_class']}")

        elif event['type'] == 'detection_result':
            result = event['result']
            if result['success'] == 'True':
                print(f"✅ [{timestamp}] 检测成功: {result['detected_class']}")
            else:
                print(f"❌ [{timestamp}] 检测失败: 期望 {result['expected_class']}, 实际 {result['detected_class']}")

        elif event['type'] == 'fallback':
            if "执行Priority" in event['content']:
                print(f"\n🔄 [{timestamp}] {event['content']}")
            else:
                print(f"   [{timestamp}] {event['content']}")

        elif event['type'] == 'priority_attempt':
            print(f"🎯 [{timestamp}] Priority {event['priority']}: {event['target_class']}")

    def start_monitoring(self):
        """开始监控"""
        if not self.log_file_path:
            self.log_file_path = self.find_latest_log_file()

        if not self.log_file_path:
            print("❌ 未找到日志文件，请确认测试是否已开始")
            return

        print(f"🚀 开始监控Priority检测状态")
        print(f"📁 日志文件: {self.log_file_path}")
        print(f"⏰ 开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

        try:
            while True:
                # 检查日志文件是否还存在
                if not os.path.exists(self.log_file_path):
                    print(f"\n❌ 日志文件已不存在，尝试查找新的日志文件...")
                    self.log_file_path = self.find_latest_log_file()
                    if not self.log_file_path:
                        print("❌ 未找到新的日志文件")
                        break
                    print(f"📁 切换到新日志文件: {self.log_file_path}")
                    self.last_position = 0

                # 解析新事件
                events = self.parse_new_lines()

                # 打印新事件
                for event in events:
                    self.print_event(event)

                # 打印状态行
                self.print_status()

                # 休眠
                time.sleep(1)

        except KeyboardInterrupt:
            print(f"\n\n🛑 监控已停止")
            print(f"📊 最终统计:")
            print(f"   - 总检测次数: {self.detection_count}")
            print(f"   - 成功次数: {self.success_count}")
            print(f"   - 成功率: {(self.success_count / self.detection_count * 100) if self.detection_count > 0 else 0:.1f}%")
            print(f"   - Fallback次数: {self.fallback_count}")

def main():
    """主函数"""
    import sys

    log_file_path = None
    if len(sys.argv) > 1:
        log_file_path = sys.argv[1]
        if not os.path.exists(log_file_path):
            print(f"❌ 日志文件不存在: {log_file_path}")
            return

    monitor = PriorityMonitor(log_file_path)
    monitor.start_monitoring()

if __name__ == "__main__":
    main()
