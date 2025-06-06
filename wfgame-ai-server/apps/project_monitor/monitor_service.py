"""
项目性能监控服务 - Django版本
"""
import os
import yaml
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from django.db.models import Avg, Count, Q, F
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

    def create_project(self, db: Session, name: str, yaml_path: str, description: str = None) -> Project:
        """创建新项目"""
        try:
            # 检查项目配置文件是否存在
            if not os.path.exists(yaml_path):
                raise ValueError(f"项目配置文件不存在: {yaml_path}")

            # 检查项目名称是否已存在
            existing = db.query(Project).filter(Project.name == name).first()
            if existing:
                raise ValueError(f"项目名称已存在: {name}")

            project = Project(
                name=name,
                yaml_path=yaml_path,
                description=description
            )
            db.add(project)
            db.commit()
            db.refresh(project)

            # 初始化类统计记录
            self._init_class_statistics(db, project)

            logger.info(f"创建项目成功: {name}")
            return project

        except Exception as e:
            db.rollback()
            logger.error(f"创建项目失败: {e}")
            raise

    def _init_class_statistics(self, db: Session, project: Project):
        """初始化项目的类统计记录"""
        try:
            config = self.load_project_config(project.yaml_path)
            button_classes = config.get('button_classes', {})

            for class_name in button_classes.keys():
                stat = ClassStatistics(
                    project_id=project.id,
                    button_class=class_name,
                    total_executions=0,
                    total_successes=0,
                    total_failures=0,
                    success_rate=0.0
                )
                db.add(stat)

            db.commit()
            logger.info(f"初始化项目 {project.name} 的类统计记录")

        except Exception as e:
            logger.error(f"初始化类统计失败: {e}")
            db.rollback()

    def log_execution(self, db: Session, log_data: Dict) -> ExecutionLog:
        """记录执行日志"""
        try:
            execution_log = ExecutionLog(**log_data)
            db.add(execution_log)

            # 更新类统计
            self._update_class_statistics(db, execution_log)

            db.commit()
            db.refresh(execution_log)

            return execution_log

        except Exception as e:
            db.rollback()
            logger.error(f"记录执行日志失败: {e}")
            raise

    def _update_class_statistics(self, db: Session, execution_log: ExecutionLog):
        """更新类统计数据"""
        try:
            stat = db.query(ClassStatistics).filter(
                ClassStatistics.project_id == execution_log.project_id,
                ClassStatistics.button_class == execution_log.button_class
            ).first()

            if not stat:
                # 创建新的统计记录
                stat = ClassStatistics(
                    project_id=execution_log.project_id,
                    button_class=execution_log.button_class,
                    total_executions=0,
                    total_successes=0,
                    total_failures=0,
                    success_rate=0.0
                )
                db.add(stat)

            # 更新统计数据
            stat.total_executions += 1
            if execution_log.success:
                stat.total_successes += 1
            else:
                stat.total_failures += 1

            stat.success_rate = stat.total_successes / stat.total_executions if stat.total_executions > 0 else 0.0
            stat.last_executed_at = execution_log.executed_at
            stat.last_updated = datetime.utcnow()

            # 更新平均检测时间
            if execution_log.detection_time_ms:
                avg_time = db.query(func.avg(ExecutionLog.detection_time_ms)).filter(
                    ExecutionLog.project_id == execution_log.project_id,
                    ExecutionLog.button_class == execution_log.button_class,
                    ExecutionLog.detection_time_ms.isnot(None)
                ).scalar()
                stat.avg_detection_time_ms = float(avg_time) if avg_time else None

        except Exception as e:
            logger.error(f"更新类统计失败: {e}")
            raise

    def get_project_dashboard(self, db: Session, project_id: int) -> ProjectDashboard:
        """获取项目仪表板数据"""
        try:
            # 获取项目信息
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                raise ValueError(f"项目不存在: {project_id}")

            # 获取总体统计
            total_executions = db.query(func.sum(ClassStatistics.total_executions)).filter(
                ClassStatistics.project_id == project_id
            ).scalar() or 0

            avg_success_rate = db.query(func.avg(ClassStatistics.success_rate)).filter(
                ClassStatistics.project_id == project_id
            ).scalar() or 0.0

            avg_detection_time = db.query(func.avg(ClassStatistics.avg_detection_time_ms)).filter(
                ClassStatistics.project_id == project_id,
                ClassStatistics.avg_detection_time_ms.isnot(None)
            ).scalar() or 0.0

            # 获取类统计数据
            class_stats = db.query(ClassStatistics).filter(
                ClassStatistics.project_id == project_id
            ).all()

            class_statistics = []
            for stat in class_stats:
                performance_level = self._get_performance_level(stat.success_rate)
                class_statistics.append(ClassStatisticsResponse(
                    button_class=stat.button_class,
                    total_executions=stat.total_executions,
                    total_successes=stat.total_successes,
                    total_failures=stat.total_failures,
                    success_rate=stat.success_rate,
                    avg_detection_time_ms=stat.avg_detection_time_ms,
                    last_executed_at=stat.last_executed_at,
                    performance_level=performance_level
                ))

            # 获取最近失败记录
            recent_failures = self._get_recent_failures(db, project_id)

            # 生成优化建议
            optimization_suggestions = self._generate_optimization_suggestions(class_statistics)

            return ProjectDashboard(
                project_info=ProjectInfo(
                    id=project.id,
                    name=project.name,
                    yaml_path=project.yaml_path,
                    description=project.description,
                    status=project.status,
                    created_at=project.created_at
                ),
                total_executions=total_executions,
                avg_success_rate=avg_success_rate,
                avg_detection_time=avg_detection_time,
                class_statistics=class_statistics,
                recent_failures=recent_failures,
                optimization_suggestions=optimization_suggestions
            )

        except Exception as e:
            logger.error(f"获取项目仪表板数据失败: {e}")
            raise

    def _get_performance_level(self, success_rate: float) -> str:
        """根据成功率确定性能等级"""
        if success_rate >= self.performance_thresholds['excellent']:
            return 'excellent'
        elif success_rate >= self.performance_thresholds['good']:
            return 'good'
        elif success_rate >= self.performance_thresholds['poor']:
            return 'poor'
        else:
            return 'critical'

    def _get_recent_failures(self, db: Session, project_id: int, limit: int = 10) -> List[Dict]:
        """获取最近的失败记录"""
        try:
            failures = db.query(ExecutionLog).filter(
                ExecutionLog.project_id == project_id,
                ExecutionLog.success == False
            ).order_by(desc(ExecutionLog.executed_at)).limit(limit).all()

            return [
                {
                    'button_class': f.button_class,
                    'scenario': f.scenario,
                    'executed_at': f.executed_at.isoformat(),
                    'coordinates': {'x': f.coordinates_x, 'y': f.coordinates_y},
                    'detection_time_ms': f.detection_time_ms
                }
                for f in failures
            ]
        except Exception as e:
            logger.error(f"获取最近失败记录失败: {e}")
            return []

    def _generate_optimization_suggestions(self, class_statistics: List[ClassStatisticsResponse]) -> List[Dict]:
        """生成优化建议"""
        suggestions = []

        # 找出问题最严重的类
        critical_classes = [stat for stat in class_statistics if stat.performance_level == 'critical']
        poor_classes = [stat for stat in class_statistics if stat.performance_level == 'poor']

        for stat in critical_classes:
            suggestions.append({
                'type': 'critical',
                'button_class': stat.button_class,
                'issue': f'成功率过低 ({stat.success_rate:.1%})',
                'suggestion': '建议重新训练AI模型或调整检测参数',
                'priority': 'high'
            })

        for stat in poor_classes:
            suggestions.append({
                'type': 'performance',
                'button_class': stat.button_class,
                'issue': f'成功率偏低 ({stat.success_rate:.1%})',
                'suggestion': '建议增加训练样本或优化检测阈值',
                'priority': 'medium'
            })

        # 检测时间过长的类
        slow_classes = [stat for stat in class_statistics
                       if stat.avg_detection_time_ms and stat.avg_detection_time_ms > 1000]

        for stat in slow_classes:
            suggestions.append({
                'type': 'performance',
                'button_class': stat.button_class,
                'issue': f'检测时间过长 ({stat.avg_detection_time_ms:.0f}ms)',
                'suggestion': '建议优化模型推理速度或调整检测区域',
                'priority': 'low'
            })

        return suggestions

    def get_class_trend(self, db: Session, project_id: int, button_class: str, days: int = 7) -> Dict:
        """获取类性能趋势数据"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)

            # 按天分组统计
            daily_stats = db.query(
                func.date(ExecutionLog.executed_at).label('date'),
                func.count(ExecutionLog.id).label('total'),
                func.sum(func.cast(ExecutionLog.success, db.bind.dialect.name == 'sqlite' and 'INTEGER' or None)).label('successes')
            ).filter(
                ExecutionLog.project_id == project_id,
                ExecutionLog.button_class == button_class,
                ExecutionLog.executed_at >= start_date
            ).group_by(
                func.date(ExecutionLog.executed_at)
            ).all()

            trend_data = []
            for stat in daily_stats:
                success_rate = stat.successes / stat.total if stat.total > 0 else 0
                trend_data.append({
                    'date': stat.date.isoformat(),
                    'total_executions': stat.total,
                    'successes': stat.successes,
                    'success_rate': success_rate
                })

            return {
                'button_class': button_class,
                'period_days': days,
                'trend_data': trend_data
            }

        except Exception as e:
            logger.error(f"获取类趋势数据失败: {e}")
            return {'button_class': button_class, 'period_days': days, 'trend_data': []}

# 全局服务实例
monitor_service = ProjectMonitorService()
