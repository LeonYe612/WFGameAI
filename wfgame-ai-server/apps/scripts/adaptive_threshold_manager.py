# -*- coding: utf-8 -*-
"""
自适应阈值管理器
基于历史性能动态调整执行策略阈值
严格按照WFGameAI多设备并发执行优化方案实现
"""

import json
import os
from typing import List
from datetime import datetime


class AdaptiveThresholdManager:
    """自适应阈值管理器"""

    def __init__(self, config_file: str = None):
        """
        初始化自适应阈值管理器

        Args:
            config_file: 配置文件路径
        """
        self.base_threshold = 8
        self.performance_history = []
        self.max_history_size = 20

        # 设置配置文件路径
        if config_file is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_file = os.path.join(current_dir, 'adaptive_threshold_config.json')

        self.config_file = config_file
        self._load_config()

    def _load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                self.base_threshold = config.get('base_threshold', 8)
                self.performance_history = config.get('performance_history', [])
                self.max_history_size = config.get('max_history_size', 20)

                print(f"✅ 加载阈值配置: 基准阈值={self.base_threshold}, 历史记录={len(self.performance_history)}条")
            else:
                print(f"📄 配置文件不存在，使用默认配置: {self.config_file}")

        except Exception as e:
            print(f"❌ 加载配置文件失败: {e}")

    def _save_config(self):
        """保存配置文件"""
        try:
            config = {
                'base_threshold': self.base_threshold,
                'performance_history': self.performance_history,
                'max_history_size': self.max_history_size,
                'last_updated': datetime.now().isoformat()
            }

            # 确保目录存在
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"❌ 保存配置文件失败: {e}")

    def get_optimal_threshold(self) -> int:
        """
        基于历史性能动态调整阈值

        Returns:
            int: 最优阈值
        """
        if not self.performance_history:
            return self.base_threshold

        # 基于系统性能历史调整
        recent_performance = self.performance_history[-5:]  # 取最近5次
        avg_performance = sum(recent_performance) / len(recent_performance)

        if avg_performance > 0.9:  # 系统性能良好
            optimal_threshold = min(self.base_threshold + 2, 12)
            print(f"🚀 系统性能良好(avg={avg_performance:.2f})，提升阈值至 {optimal_threshold}")
        elif avg_performance < 0.6:  # 系统性能较差
            optimal_threshold = max(self.base_threshold - 2, 4)
            print(f"⚠️ 系统性能较差(avg={avg_performance:.2f})，降低阈值至 {optimal_threshold}")
        else:
            optimal_threshold = self.base_threshold
            print(f"📊 系统性能正常(avg={avg_performance:.2f})，保持基准阈值 {optimal_threshold}")

        return optimal_threshold

    def record_performance(self, device_count: int, execution_time: float):
        """
        记录性能数据

        Args:
            device_count: 设备数量
            execution_time: 执行时间（秒）
        """
        if execution_time <= 0:
            print("⚠️ 执行时间无效，跳过性能记录")
            return

        # 计算性能指标（设备数/执行时间）
        performance_score = device_count / execution_time
        normalized_score = min(performance_score / 10, 1.0)  # 归一化到0-1

        self.performance_history.append(normalized_score)

        # 保持历史记录在合理范围内
        if len(self.performance_history) > self.max_history_size:
            self.performance_history.pop(0)

        print(f"📈 记录性能数据: {device_count}设备/{execution_time:.2f}秒 = {normalized_score:.3f}")

        # 保存配置
        self._save_config()

    def get_performance_summary(self) -> dict:
        """
        获取性能摘要

        Returns:
            dict: 性能摘要信息
        """
        if not self.performance_history:
            return {
                'total_records': 0,
                'average_performance': 0.0,
                'trend': 'unknown',
                'recommendation': 'insufficient_data'
            }

        avg_performance = sum(self.performance_history) / len(self.performance_history)

        # 计算趋势
        if len(self.performance_history) >= 3:
            recent_avg = sum(self.performance_history[-3:]) / 3
            early_avg = sum(self.performance_history[:3]) / 3

            if recent_avg > early_avg * 1.1:
                trend = 'improving'
            elif recent_avg < early_avg * 0.9:
                trend = 'declining'
            else:
                trend = 'stable'
        else:
            trend = 'insufficient_data'

        # 生成建议
        if avg_performance > 0.8:
            recommendation = 'increase_concurrency'
        elif avg_performance < 0.5:
            recommendation = 'decrease_concurrency'
        else:
            recommendation = 'maintain_current'

        return {
            'total_records': len(self.performance_history),
            'average_performance': avg_performance,
            'recent_performance': sum(self.performance_history[-5:]) / min(5, len(self.performance_history)),
            'trend': trend,
            'recommendation': recommendation,
            'base_threshold': self.base_threshold,
            'optimal_threshold': self.get_optimal_threshold()
        }

    def reset_performance_history(self):
        """重置性能历史记录"""
        self.performance_history = []
        self._save_config()
        print("✅ 性能历史记录已重置")

    def adjust_base_threshold(self, new_threshold: int):
        """
        调整基准阈值

        Args:
            new_threshold: 新的基准阈值
        """
        if not (4 <= new_threshold <= 16):
            print(f"❌ 基准阈值超出范围(4-16): {new_threshold}")
            return

        old_threshold = self.base_threshold
        self.base_threshold = new_threshold
        self._save_config()

        print(f"✅ 基准阈值已调整: {old_threshold} -> {new_threshold}")


# 全局自适应阈值管理器实例
_threshold_manager = None


def get_adaptive_threshold_manager() -> AdaptiveThresholdManager:
    """获取自适应阈值管理器实例"""
    global _threshold_manager

    if _threshold_manager is None:
        _threshold_manager = AdaptiveThresholdManager()

    return _threshold_manager


if __name__ == "__main__":
    print("=== 自适应阈值管理器测试 ===")

    # 初始化管理器
    manager = get_adaptive_threshold_manager()

    # 显示当前状态
    print(f"\n📊 当前状态:")
    summary = manager.get_performance_summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")

    # 模拟性能记录
    print(f"\n🔄 模拟性能记录:")
    test_scenarios = [
        (4, 10.5),    # 4设备，10.5秒
        (6, 12.0),    # 6设备，12秒
        (8, 15.0),    # 8设备，15秒
        (10, 25.0),   # 10设备，25秒
        (12, 30.0),   # 12设备，30秒
    ]

    for device_count, execution_time in test_scenarios:
        manager.record_performance(device_count, execution_time)
        optimal = manager.get_optimal_threshold()
        print(f"   -> 最优阈值: {optimal}")

    # 显示更新后的状态
    print(f"\n📈 更新后状态:")
    summary = manager.get_performance_summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")

    # 测试阈值调整
    print(f"\n⚙️ 测试阈值调整:")
    manager.adjust_base_threshold(10)
    print(f"   新的最优阈值: {manager.get_optimal_threshold()}")
