"""
项目性能监控服务 - Django版本
"""
import os
import yaml
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from django.db.models import Avg, Count, Q, F, Sum
from django.utils import timezone
from .models import ProjectMonitor, ExecutionLog, ClassStatistics

logger = logging.getLogger(__name__)

class MonitorService:
    """项目监控服务"""

    def __init__(self):
        self.performance_thresholds = {
            'excellent': 0.95,  # 95%以上成功率
            'good': 0.85,      # 85-95%成功率
            'poor': 0.60,      # 60-85%成功率
            # 60%以下为critical
        }

    def load_project_config(self, yaml_path: str) -> Dict:
        """加载项目配置文件"""
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return config
        except Exception as e:
            logger.error(f"加载项目配置失败 {yaml_path}: {e}")
            return {}

    def update_class_statistics(self, project: ProjectMonitor, button_class: str,
                               success: bool, detection_time_ms: int = None):
        """更新类统计数据"""
        try:
            # 获取或创建类统计记录
            stat, created = ClassStatistics.objects.get_or_create(
                project=project,
                button_class=button_class,
                defaults={
                    'total_executions': 0,
                    'total_successes': 0,
                    'total_failures': 0,
                    'success_rate': 0.0,
                    'avg_detection_time_ms': 0.0
                }
            )

            # 更新统计数据
            stat.total_executions += 1
            if success:
                stat.total_successes += 1
            else:
                stat.total_failures += 1

            # 重新计算成功率
            stat.success_rate = stat.total_successes / stat.total_executions

            # 更新平均检测时间
            if detection_time_ms:
                if stat.avg_detection_time_ms:
                    # 计算加权平均
                    total_weight = stat.total_executions
                    old_weight = total_weight - 1
                    stat.avg_detection_time_ms = (
                        (stat.avg_detection_time_ms * old_weight + detection_time_ms) / total_weight
                    )
                else:
                    stat.avg_detection_time_ms = detection_time_ms

            stat.last_executed_at = timezone.now()
            stat.save()

        except Exception as e:
            logger.error(f"更新类统计失败: {e}")

    def get_project_dashboard_data(self, project: ProjectMonitor) -> Dict:
        """获取项目仪表板数据"""
        try:
            # 获取总体统计
            class_stats = ClassStatistics.objects.filter(project=project)

            total_executions = class_stats.aggregate(
                total=Sum('total_executions')
            )['total'] or 0

            if total_executions > 0:
                # 计算加权平均成功率
                weighted_success_rate = 0
                weighted_detection_time = 0
                total_weight = 0

                for stat in class_stats:
                    if stat.total_executions > 0:
                        weight = stat.total_executions
                        weighted_success_rate += stat.success_rate * weight
                        if stat.avg_detection_time_ms:
                            weighted_detection_time += stat.avg_detection_time_ms * weight
                        total_weight += weight

                avg_success_rate = weighted_success_rate / total_weight if total_weight > 0 else 0
                avg_detection_time = weighted_detection_time / total_weight if total_weight > 0 else 0
            else:
                avg_success_rate = 0
                avg_detection_time = 0

            # 获取类统计详情
            class_statistics = []
            for stat in class_stats.order_by('-success_rate'):
                performance_level = self._get_performance_level(stat.success_rate)
                class_statistics.append({
                    'button_class': stat.button_class,
                    'total_executions': stat.total_executions,
                    'total_successes': stat.total_successes,
                    'total_failures': stat.total_failures,
                    'success_rate': stat.success_rate,
                    'avg_detection_time_ms': stat.avg_detection_time_ms or 0,
                    'last_executed_at': stat.last_executed_at.isoformat() if stat.last_executed_at else None,
                    'performance_level': performance_level
                })

            # 获取最近失败记录
            recent_failures = []
            failures = ExecutionLog.objects.filter(
                project=project,
                success=False
            ).order_by('-executed_at')[:10]

            for failure in failures:
                recent_failures.append({
                    'button_class': failure.button_class,
                    'scenario': failure.scenario,
                    'executed_at': failure.executed_at.isoformat(),
                    'device_id': failure.device_id
                })

            # 生成优化建议
            optimization_suggestions = self._generate_optimization_suggestions(class_stats)

            return {
                'project_info': {
                    'id': project.id,
                    'name': project.name,
                    'yaml_path': project.yaml_path,
                    'description': project.description,
                    'status': project.status,
                    'created_at': project.created_at.isoformat()
                },
                'total_executions': total_executions,
                'avg_success_rate': avg_success_rate,
                'avg_detection_time': avg_detection_time,
                'class_statistics': class_statistics,
                'recent_failures': recent_failures,
                'optimization_suggestions': optimization_suggestions
            }

        except Exception as e:
            logger.error(f"获取项目仪表板数据失败: {e}")
            return {}

    def get_class_trend_data(self, project: ProjectMonitor, button_class: str, days: int = 7) -> Dict:
        """获取类性能趋势数据"""
        try:
            start_date = timezone.now() - timedelta(days=days)

            # 获取每日执行统计
            daily_logs = ExecutionLog.objects.filter(
                project=project,
                button_class=button_class,
                executed_at__gte=start_date
            ).extra(
                select={'date': 'DATE(executed_at)'}
            ).values('date').annotate(
                total=Count('id'),
                successes=Count('id', filter=Q(success=True)),
                avg_time=Avg('detection_time_ms')
            ).order_by('date')

            trend_data = []
            for entry in daily_logs:
                success_rate = entry['successes'] / entry['total'] if entry['total'] > 0 else 0
                trend_data.append({
                    'date': entry['date'],
                    'total': entry['total'],
                    'successes': entry['successes'],
                    'failures': entry['total'] - entry['successes'],
                    'success_rate': success_rate,
                    'avg_detection_time': entry['avg_time'] or 0
                })

            return {
                'button_class': button_class,
                'days': days,
                'trend_data': trend_data
            }

        except Exception as e:
            logger.error(f"获取趋势数据失败: {e}")
            return {}

    def get_detailed_statistics(self, project: ProjectMonitor) -> Dict:
        """获取项目详细统计数据"""
        try:
            # 基础统计
            dashboard_data = self.get_project_dashboard_data(project)

            # 时间段统计
            now = timezone.now()
            periods = {
                'today': now.replace(hour=0, minute=0, second=0, microsecond=0),
                'this_week': now - timedelta(days=now.weekday()),
                'this_month': now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            }

            period_stats = {}
            for period_name, start_time in periods.items():
                logs = ExecutionLog.objects.filter(
                    project=project,
                    executed_at__gte=start_time
                )

                total = logs.count()
                successes = logs.filter(success=True).count()
                success_rate = successes / total if total > 0 else 0

                period_stats[period_name] = {
                    'total_executions': total,
                    'successes': successes,
                    'failures': total - successes,
                    'success_rate': success_rate
                }

            # 设备统计
            device_stats = ExecutionLog.objects.filter(
                project=project
            ).exclude(device_id='').values('device_id').annotate(
                total=Count('id'),
                successes=Count('id', filter=Q(success=True))
            ).order_by('-total')

            device_statistics = []
            for stat in device_stats:
                success_rate = stat['successes'] / stat['total'] if stat['total'] > 0 else 0
                device_statistics.append({
                    'device_id': stat['device_id'],
                    'total_executions': stat['total'],
                    'successes': stat['successes'],
                    'failures': stat['total'] - stat['successes'],
                    'success_rate': success_rate
                })

            return {
                **dashboard_data,
                'period_statistics': period_stats,
                'device_statistics': device_statistics
            }

        except Exception as e:
            logger.error(f"获取详细统计失败: {e}")
            return {}

    def _get_performance_level(self, success_rate: float) -> str:
        """根据成功率获取性能等级"""
        if success_rate >= self.performance_thresholds['excellent']:
            return 'excellent'
        elif success_rate >= self.performance_thresholds['good']:
            return 'good'
        elif success_rate >= self.performance_thresholds['poor']:
            return 'poor'
        else:
            return 'critical'

    def _generate_optimization_suggestions(self, class_stats) -> List[Dict]:
        """生成优化建议"""
        suggestions = []

        for stat in class_stats:
            if stat.success_rate < self.performance_thresholds['poor']:
                priority = 'high' if stat.success_rate < 0.5 else 'medium'

                # 根据具体情况生成建议
                if stat.avg_detection_time_ms and stat.avg_detection_time_ms > 5000:
                    # 检测时间过长
                    suggestions.append({
                        'button_class': stat.button_class,
                        'priority': priority,
                        'issue': f'检测时间过长 ({stat.avg_detection_time_ms:.0f}ms)',
                        'suggestion': '考虑优化识别算法或调整检测参数'
                    })
                else:
                    # 成功率低
                    suggestions.append({
                        'button_class': stat.button_class,
                        'priority': priority,
                        'issue': f'成功率低 ({stat.success_rate:.1%})',
                        'suggestion': '检查按钮识别配置或更新训练模型'
                    })

        return sorted(suggestions, key=lambda x: (
            {'high': 0, 'medium': 1, 'low': 2}[x['priority']],
            x['button_class']
        ))

# 全局服务实例
monitor_service = MonitorService()
