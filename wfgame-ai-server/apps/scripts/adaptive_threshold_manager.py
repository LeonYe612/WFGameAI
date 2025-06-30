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

    def get_performance_trend(self) -> str:
        """
        分析性能趋势

        Returns:
            str: 趋势描述 ("improving", "declining", "stable")
        """
        if len(self.performance_history) < 5:
            return "insufficient_data"

        # 分析最近5次和前面5次的性能对比
        recent_5 = self.performance_history[-5:]
        previous_5 = self.performance_history[-10:-5] if len(self.performance_history) >= 10 else []

        if not previous_5:
            return "insufficient_data"

        recent_avg = sum(recent_5) / len(recent_5)
        previous_avg = sum(previous_5) / len(previous_5)

        improvement_threshold = 0.1  # 10%改善阈值

        if recent_avg > previous_avg + improvement_threshold:
            return "improving"
        elif recent_avg < previous_avg - improvement_threshold:
            return "declining"
        else:
            return "stable"

    def predict_optimal_threshold(self, device_count: int) -> int:
        """
        基于设备数量和历史性能预测最优阈值

        Args:
            device_count: 当前设备数量

        Returns:
            int: 预测的最优阈值
        """
        base_optimal = self.get_optimal_threshold()

        # 基于设备数量调整
        if device_count <= 2:
            # 小规模设备，可以更激进
            return min(base_optimal + 2, 16)
        elif device_count <= 5:
            # 中等规模
            return base_optimal
        elif device_count <= 10:
            # 较大规模，保守一些
            return max(base_optimal - 1, 4)
        else:
            # 大规模设备，使用智能管理
            return max(base_optimal - 2, 6)

    def get_system_load_factor(self) -> float:
        """
        获取系统负载因子

        Returns:
            float: 负载因子 (0.0-1.0)
        """
        try:
            import psutil

            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            # 综合CPU和内存使用率计算负载因子
            load_factor = (cpu_percent + memory_percent) / 200.0
            return min(max(load_factor, 0.0), 1.0)

        except ImportError:
            # 如果没有psutil，返回中等负载
            return 0.5
        except Exception:
            return 0.5

    def auto_adjust_threshold(self) -> int:
        """
        自动调整阈值 - 综合考虑性能历史、趋势和系统负载

        Returns:
            int: 调整后的阈值
        """
        base_threshold = self.get_optimal_threshold()
        trend = self.get_performance_trend()
        load_factor = self.get_system_load_factor()

        # 基于趋势调整
        if trend == "improving":
            threshold_adjustment = 1
        elif trend == "declining":
            threshold_adjustment = -1
        else:
            threshold_adjustment = 0

        # 基于系统负载调整
        if load_factor < 0.3:  # 系统负载低
            load_adjustment = 2
        elif load_factor < 0.6:  # 系统负载中等
            load_adjustment = 0
        elif load_factor < 0.8:  # 系统负载较高
            load_adjustment = -1
        else:  # 系统负载很高
            load_adjustment = -2

        # 计算最终阈值
        adjusted_threshold = base_threshold + threshold_adjustment + load_adjustment

        # 确保阈值在合理范围内
        final_threshold = min(max(adjusted_threshold, 4), 16)

        print(f"🎯 自动阈值调整: 基础={base_threshold}, 趋势调整={threshold_adjustment}, "
              f"负载调整={load_adjustment}, 最终={final_threshold}")

        return final_threshold

    def get_performance_recommendations(self) -> List[str]:
        """
        基于历史性能数据生成优化建议

        Returns:
            List[str]: 优化建议列表
        """
        recommendations = []

        if len(self.performance_history) < 5:
            recommendations.append("需要更多历史数据进行分析")
            return recommendations

        trend = self.get_performance_trend()
        avg_performance = sum(self.performance_history) / len(self.performance_history)
        recent_performance = sum(self.performance_history[-5:]) / 5
        load_factor = self.get_system_load_factor()

        # 基于趋势的建议
        if trend == "declining":
            recommendations.append("性能呈下降趋势，建议降低并发数或检查系统资源")
        elif trend == "improving":
            recommendations.append("性能呈上升趋势，可以考虑适当增加并发数")

        # 基于性能水平的建议
        if recent_performance < 0.05:
            recommendations.append("当前性能较低，建议优化脚本执行效率或减少并发数")
        elif recent_performance > 0.15:
            recommendations.append("当前性能良好，可以考虑增加设备并发数")

        # 基于系统负载的建议
        if load_factor > 0.8:
            recommendations.append("系统负载较高，建议降低并发数或等待系统负载降低")
        elif load_factor < 0.3:
            recommendations.append("系统资源充足，可以考虑增加并发数提高效率")

        # 基于历史波动的建议
        if len(self.performance_history) >= 10:
            performance_std = self._calculate_std(self.performance_history[-10:])
            if performance_std > 0.05:
                recommendations.append("性能波动较大，建议检查系统稳定性或调整策略")

        return recommendations if recommendations else ["系统运行稳定，当前配置良好"]

    def _calculate_std(self, data: List[float]) -> float:
        """计算标准差"""
        if len(data) < 2:
            return 0.0

        mean = sum(data) / len(data)
        variance = sum((x - mean) ** 2 for x in data) / len(data)
        return variance ** 0.5


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
