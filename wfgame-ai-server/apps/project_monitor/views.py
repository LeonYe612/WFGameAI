"""
项目监控Django API视图
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
import json
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def projects_list(request):
    """获取项目列表API"""
    try:
        # 使用非Django项目监控API
        from .django_api import _get_monitor_service

        monitor_service = _get_monitor_service()
        if not monitor_service:
            return JsonResponse({
                'success': False,
                'error': '项目监控服务不可用'
            }, status=503)

        # 获取项目列表
        projects = monitor_service.get_projects()

        # 格式化项目数据
        projects_data = []
        for project in projects:
            projects_data.append({
                'id': project.id,
                'name': project.name,
                'yaml_path': project.yaml_path,
                'description': project.description,
                'status': project.status,
                'created_at': project.created_at.isoformat() if project.created_at else None,
                'updated_at': project.updated_at.isoformat() if project.updated_at else None
            })

        return JsonResponse({
            'success': True,
            'projects': projects_data
        })

    except Exception as e:
        logger.error(f"获取项目列表失败: {e}")
        return JsonResponse({
            'success': False,
            'error': f'获取项目列表失败: {str(e)}'
        }, status=500)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def projects_create(request):
    """创建项目API"""
    try:
        data = json.loads(request.body)
        name = data.get('name')
        yaml_path = data.get('yaml_path')
        description = data.get('description', '')

        if not name or not yaml_path:
            return JsonResponse({
                'success': False,
                'error': '项目名称和YAML路径不能为空'
            }, status=400)

        # 使用非Django项目监控API
        from .django_api import _get_monitor_service

        monitor_service = _get_monitor_service()
        if not monitor_service:
            return JsonResponse({
                'success': False,
                'error': '项目监控服务不可用'
            }, status=503)

        # 创建项目
        project = monitor_service.create_project(
            name=name,
            yaml_path=yaml_path,
            description=description
        )

        return JsonResponse({
            'success': True,
            'project': {
                'id': project.id,
                'name': project.name,
                'yaml_path': project.yaml_path,
                'description': project.description,
                'status': project.status
            }
        })

    except Exception as e:
        logger.error(f"创建项目失败: {e}")
        return JsonResponse({
            'success': False,
            'error': f'创建项目失败: {str(e)}'
        }, status=500)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def dashboard(request):
    """获取项目仪表板数据API"""
    try:
        data = json.loads(request.body)
        project_id = data.get('project_id')

        # 如果没有提供project_id，返回空数据结构
        if not project_id:
            return JsonResponse({
                'success': True,
                'dashboard': {
                    'total_executions': 0,
                    'avg_success_rate': 0.0,
                    'avg_detection_time': 0,
                    'class_statistics': [],
                    'recent_failures': [],
                    'optimization_suggestions': []
                },
                'message': '无数据：未指定项目ID'
            })

        # 使用非Django项目监控API
        from .django_api import _get_monitor_service, _get_database_manager

        monitor_service = _get_monitor_service()
        db_manager = _get_database_manager()

        if not monitor_service or not db_manager:
            return JsonResponse({
                'success': False,
                'error': '项目监控服务不可用'
            }, status=503)

        # 获取数据库会话
        db = db_manager.get_session()
        try:
            # 获取仪表板数据
            dashboard_data = monitor_service.get_project_dashboard(db, project_id)
        except ValueError as e:
            # 项目不存在
            return JsonResponse({
                'success': True,
                'dashboard': {
                    'total_executions': 0,
                    'avg_success_rate': 0.0,
                    'avg_detection_time': 0,
                    'class_statistics': [],
                    'recent_failures': [],
                    'optimization_suggestions': []
                },
                'message': f'无数据：{str(e)}'
            })
        finally:
            db.close()

        # 格式化仪表板数据
        formatted_data = {
            'total_executions': dashboard_data.total_executions,
            'avg_success_rate': dashboard_data.avg_success_rate,
            'avg_detection_time': dashboard_data.avg_detection_time,
            'class_statistics': [],
            'recent_failures': [],
            'optimization_suggestions': []
        }

        # 格式化类统计数据
        for stat in dashboard_data.class_statistics:
            formatted_data['class_statistics'].append({
                'button_class': stat.button_class,
                'total_executions': stat.total_executions,
                'total_successes': stat.total_successes,
                'total_failures': stat.total_failures,
                'success_rate': stat.success_rate,
                'avg_detection_time_ms': stat.avg_detection_time_ms,
                'performance_level': stat.performance_level,
                'last_executed_at': stat.last_executed_at.isoformat() if stat.last_executed_at else None
            })

        # 格式化最近失败记录
        for failure in dashboard_data.recent_failures:
            formatted_data['recent_failures'].append({
                'button_class': failure.get('button_class', ''),
                'scenario': failure.get('scenario', ''),
                'executed_at': failure.get('executed_at'),
                'detection_time_ms': failure.get('detection_time_ms', 0)
            })

        # 格式化优化建议
        for suggestion in dashboard_data.optimization_suggestions:
            formatted_data['optimization_suggestions'].append({
                'button_class': suggestion.get('button_class', ''),
                'type': suggestion.get('type', ''),                'priority': suggestion.get('priority', 'low'),
                'issue': suggestion.get('issue', ''),
                'suggestion': suggestion.get('suggestion', '')
            })

        return JsonResponse({
            'success': True,
            'dashboard': formatted_data
        })

    except Exception as e:
        logger.error(f"获取仪表板数据失败: {e}")
        return JsonResponse({
            'success': False,
            'error': f'获取仪表板数据失败: {str(e)}'
        }, status=500)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def log_execution(request):
    """记录AI执行数据API"""
    try:
        data = json.loads(request.body)

        # 使用非Django项目监控API
        from .django_api import log_ai_execution_sync

        result = log_ai_execution_sync(
            project_name=data.get('project_name', 'default'),
            button_class=data.get('button_class', ''),
            success=data.get('success', False),
            scenario=data.get('scenario'),
            detection_time_ms=data.get('detection_time_ms'),
            coordinates=data.get('coordinates'),
            screenshot_path=data.get('screenshot_path'),
            device_id=data.get('device_id')
        )

        return JsonResponse({
            'success': True,
            'logged': result
        })

    except Exception as e:
        logger.error(f"记录执行数据失败: {e}")
        return JsonResponse({
            'success': False,
            'error': f'记录执行数据失败: {str(e)}'
        }, status=500)

@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """项目监控健康检查API"""
    try:
        from .django_api import _get_monitor_service, _get_database_manager

        monitor_service = _get_monitor_service()
        database_manager = _get_database_manager()

        return JsonResponse({
            'success': True,
            'status': 'healthy',
            'monitor_service_available': monitor_service is not None,
            'database_available': database_manager is not None,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return JsonResponse({
            'success': False,
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }, status=500)
