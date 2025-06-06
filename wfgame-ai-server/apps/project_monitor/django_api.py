"""
项目监控API接口 - Django REST Framework实现
严格遵循编码标准：MySQL数据库、ai_前缀表名、POST-only API
"""
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Avg, Count, Q
from django.utils import timezone
from typing import List, Dict, Optional
import json
from datetime import datetime, timedelta

from .models import ProjectMonitor, ExecutionLog, ClassStatistics
from .django_monitor_service import MonitorService

# 实例化监控服务
monitor_service = MonitorService()


# ==================== POST-only API端点 ====================

@api_view(['POST'])
@csrf_exempt
@permission_classes([AllowAny])
def get_projects(request):
    """获取所有项目列表 - 使用POST请求符合项目规范"""
    try:
        projects = ProjectMonitor.objects.all()

        project_list = []
        for project in projects:
            project_list.append({
                'id': project.id,
                'name': project.name,
                'yaml_path': project.yaml_path,
                'description': project.description,
                'status': project.status,
                'created_at': project.created_at.isoformat()
            })

        return Response({
            'success': True,
            'projects': project_list
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': f'获取项目列表失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@csrf_exempt
@permission_classes([AllowAny])
def create_project(request):
    """创建新项目"""
    try:
        data = request.data
        name = data.get('name')
        yaml_path = data.get('yaml_path')
        description = data.get('description', '')

        if not name or not yaml_path:
            return Response({
                'success': False,
                'error': '项目名称和YAML路径不能为空'
            }, status=status.HTTP_400_BAD_REQUEST)

        # 检查项目名称是否已存在
        if ProjectMonitor.objects.filter(name=name).exists():
            return Response({
                'success': False,
                'error': f'项目名称 "{name}" 已存在'
            }, status=status.HTTP_400_BAD_REQUEST)

        # 创建项目
        project = ProjectMonitor.objects.create(
            name=name,
            yaml_path=yaml_path,
            description=description
        )

        return Response({
            'success': True,
            'project': {
                'id': project.id,
                'name': project.name,
                'yaml_path': project.yaml_path,
                'description': project.description,
                'status': project.status,
                'created_at': project.created_at.isoformat()
            }
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': f'创建项目失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@csrf_exempt
@permission_classes([AllowAny])
def get_project_dashboard(request):
    """获取项目仪表板"""
    try:
        data = request.data
        project_id = data.get('project_id')

        if not project_id:
            return Response({
                'success': False,
                'error': '项目ID不能为空'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            project = ProjectMonitor.objects.get(id=project_id)
        except ProjectMonitor.DoesNotExist:
            return Response({
                'success': False,
                'error': f'项目不存在: {project_id}'
            }, status=status.HTTP_404_NOT_FOUND)

        # 获取项目统计数据
        dashboard_data = monitor_service.get_project_dashboard_data(project)

        return Response({
            'success': True,
            'dashboard': dashboard_data
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': f'获取项目仪表板失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@csrf_exempt
@permission_classes([AllowAny])
def log_execution(request):
    """记录执行日志"""
    try:
        data = request.data
        project_id = data.get('project_id')
        button_class = data.get('button_class')
        success = data.get('success')

        if not all([project_id, button_class, success is not None]):
            return Response({
                'success': False,
                'error': '项目ID、按钮类名和执行结果不能为空'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            project = ProjectMonitor.objects.get(id=project_id)
        except ProjectMonitor.DoesNotExist:
            return Response({
                'success': False,
                'error': f'项目不存在: {project_id}'
            }, status=status.HTTP_404_NOT_FOUND)

        # 创建执行记录
        execution_log = ExecutionLog.objects.create(
            project=project,
            button_class=button_class,
            scenario=data.get('scenario', ''),
            success=success,
            detection_time_ms=data.get('detection_time_ms'),
            coordinates_x=data.get('coordinates_x'),
            coordinates_y=data.get('coordinates_y'),
            screenshot_path=data.get('screenshot_path', ''),
            device_id=data.get('device_id', '')
        )

        # 更新类统计
        monitor_service.update_class_statistics(project, button_class, success,
                                               data.get('detection_time_ms'))

        return Response({
            'success': True,
            'execution_id': execution_log.id
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': f'记录执行日志失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@csrf_exempt
@permission_classes([AllowAny])
def get_class_trend(request):
    """获取类性能趋势"""
    try:
        data = request.data
        project_id = data.get('project_id')
        button_class = data.get('button_class')
        days = data.get('days', 7)

        if not all([project_id, button_class]):
            return Response({
                'success': False,
                'error': '项目ID和按钮类名不能为空'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            project = ProjectMonitor.objects.get(id=project_id)
        except ProjectMonitor.DoesNotExist:
            return Response({
                'success': False,
                'error': f'项目不存在: {project_id}'
            }, status=status.HTTP_404_NOT_FOUND)

        # 获取趋势数据
        trend_data = monitor_service.get_class_trend_data(project, button_class, days)

        return Response({
            'success': True,
            'trend_data': trend_data
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': f'获取趋势数据失败: {str(e)}'        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@csrf_exempt
@permission_classes([AllowAny])
def get_project_statistics(request):
    """获取项目详细统计数据"""
    try:
        data = request.data
        project_id = data.get('project_id')

        if not project_id:
            return Response({
                'success': False,
                'error': '项目ID不能为空'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            project = ProjectMonitor.objects.get(id=project_id)
        except ProjectMonitor.DoesNotExist:
            return Response({
                'success': False,
                'error': f'项目不存在: {project_id}'
            }, status=status.HTTP_404_NOT_FOUND)

        # 获取详细统计数据
        statistics = monitor_service.get_detailed_statistics(project)

        return Response({
            'success': True,
            'statistics': statistics
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': f'获取项目统计失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_dashboard_page(request):
    """获取监控仪表板页面"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>WFGame AI - 项目监控仪表板</title>
        <meta charset="utf-8">
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
                text-align: center;
            }
            .dashboard {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin-top: 20px;
            }
            .card {
                background: white;
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .card h3 {
                margin-top: 0;
                color: #333;
            }
            .status {
                display: flex;
                align-items: center;
                margin: 10px 0;
            }
            .status-indicator {
                width: 12px;
                height: 12px;
                border-radius: 50%;
                margin-right: 10px;
            }
            .status-indicator.excellent { background: #4CAF50; }
            .status-indicator.good { background: #8BC34A; }
            .status-indicator.poor { background: #FF9800; }
            .status-indicator.critical { background: #F44336; }
            .progress-bar {
                width: 100%;
                height: 10px;
                background: #e0e0e0;
                border-radius: 5px;
                overflow: hidden;
                margin: 5px 0;
            }
            .progress-fill {
                height: 100%;
                transition: width 0.3s ease;
            }
            .progress-fill.excellent { background: #4CAF50; }
            .progress-fill.good { background: #8BC34A; }
            .progress-fill.poor { background: #FF9800; }
            .progress-fill.critical { background: #F44336; }
            .stats {
                display: flex;
                justify-content: space-between;
                margin: 15px 0;
            }
            .stat {
                text-align: center;
            }
            .stat-value {
                font-size: 24px;
                font-weight: bold;
                color: #667eea;
            }
            .stat-label {
                font-size: 12px;
                color: #666;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>WFGame AI - 项目监控仪表板</h1>
            <p>实时监控AI检测性能和执行状态</p>
        </div>

        <div id="projectSelector">
            <label for="projectSelect">选择项目: </label>
            <select id="projectSelect" onchange="loadProject()">
                <option value="">请选择项目...</option>
            </select>
        </div>

        <div id="dashboard" class="dashboard" style="display: none;">
            <div class="card">
                <h3>项目概览</h3>
                <div class="stats">
                    <div class="stat">
                        <div class="stat-value" id="totalExecutions">0</div>
                        <div class="stat-label">总执行次数</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value" id="avgSuccessRate">0%</div>
                        <div class="stat-label">平均成功率</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value" id="avgDetectionTime">0ms</div>
                        <div class="stat-label">平均检测时间</div>
                    </div>
                </div>
            </div>

            <div class="card">
                <h3>按钮类性能</h3>
                <div id="classStatistics"></div>
            </div>

            <div class="card">
                <h3>优化建议</h3>
                <div id="optimizationSuggestions"></div>
            </div>

            <div class="card">
                <h3>最近失败记录</h3>
                <div id="recentFailures"></div>
            </div>
        </div>

        <script>
            let currentProjectId = null;

            // 加载项目列表
            async function loadProjects() {
                try {
                    const response = await fetch('/api/project-monitor/projects/list/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({})
                    });
                    const result = await response.json();

                    if (result.success) {
                        const select = document.getElementById('projectSelect');
                        select.innerHTML = '<option value="">请选择项目...</option>';

                        result.projects.forEach(project => {
                            const option = document.createElement('option');
                            option.value = project.id;
                            option.textContent = project.name;
                            select.appendChild(option);
                        });
                    }
                } catch (error) {
                    console.error('加载项目列表失败:', error);
                }
            }

            // 加载项目数据
            async function loadProject() {
                const projectId = document.getElementById('projectSelect').value;
                if (!projectId) {
                    document.getElementById('dashboard').style.display = 'none';
                    return;
                }

                currentProjectId = projectId;

                try {
                    const response = await fetch('/api/project-monitor/dashboard/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            project_id: parseInt(projectId)
                        })
                    });
                    const result = await response.json();

                    if (result.success) {
                        updateDashboard(result.dashboard);
                        document.getElementById('dashboard').style.display = 'grid';
                    }
                } catch (error) {
                    console.error('加载项目数据失败:', error);
                }
            }

            // 更新仪表板
            function updateDashboard(dashboard) {
                document.getElementById('totalExecutions').textContent = dashboard.total_executions;
                document.getElementById('avgSuccessRate').textContent = (dashboard.avg_success_rate * 100).toFixed(1) + '%';
                document.getElementById('avgDetectionTime').textContent = Math.round(dashboard.avg_detection_time) + 'ms';

                // 更新类统计
                const classStats = document.getElementById('classStatistics');
                classStats.innerHTML = '';

                dashboard.class_statistics.forEach(stat => {
                    const div = document.createElement('div');
                    div.className = 'status';

                    const indicator = document.createElement('div');
                    indicator.className = `status-indicator ${stat.performance_level}`;

                    const info = document.createElement('div');
                    info.style.flex = '1';
                    info.innerHTML = `
                        <strong>${stat.button_class}</strong><br>
                        成功率: ${(stat.success_rate * 100).toFixed(1)}% (${stat.total_successes}/${stat.total_executions})
                        <div class="progress-bar">
                            <div class="progress-fill ${stat.performance_level}" style="width: ${stat.success_rate * 100}%"></div>
                        </div>
                    `;

                    div.appendChild(indicator);
                    div.appendChild(info);
                    classStats.appendChild(div);
                });

                // 更新优化建议
                const suggestions = document.getElementById('optimizationSuggestions');
                suggestions.innerHTML = '';

                if (dashboard.optimization_suggestions.length === 0) {
                    suggestions.innerHTML = '<p style="color: #4CAF50;">所有按钮类性能良好！</p>';
                } else {
                    dashboard.optimization_suggestions.forEach(suggestion => {
                        const div = document.createElement('div');
                        div.style.margin = '10px 0';
                        div.style.padding = '10px';
                        div.style.borderLeft = `4px solid ${suggestion.priority === 'high' ? '#F44336' : suggestion.priority === 'medium' ? '#FF9800' : '#2196F3'}`;
                        div.style.backgroundColor = '#f9f9f9';

                        div.innerHTML = `
                            <strong>${suggestion.button_class}</strong><br>
                            问题: ${suggestion.issue}<br>
                            建议: ${suggestion.suggestion}
                        `;
                        suggestions.appendChild(div);
                    });
                }

                // 更新最近失败记录
                const failures = document.getElementById('recentFailures');
                failures.innerHTML = '';

                if (dashboard.recent_failures.length === 0) {
                    failures.innerHTML = '<p style="color: #4CAF50;">暂无失败记录</p>';
                } else {
                    dashboard.recent_failures.slice(0, 5).forEach(failure => {
                        const div = document.createElement('div');
                        div.style.margin = '5px 0';
                        div.style.padding = '8px';
                        div.style.backgroundColor = '#ffebee';
                        div.style.borderRadius = '4px';

                        const time = new Date(failure.executed_at).toLocaleString();
                        div.innerHTML = `
                            <strong>${failure.button_class}</strong> - ${failure.scenario || '未知场景'}<br>
                            时间: ${time}
                        `;
                        failures.appendChild(div);
                    });
                }
            }

            // 页面加载时初始化
            window.onload = function() {
                loadProjects();
            };
        </script>
    </body>
    </html>
    """
    return HttpResponse(html_content, content_type='text/html')


# ==================== 数据收集钩子函数 ====================

def log_ai_execution(
    project_name: str,
    button_class: str,
    success: bool,
    scenario: str = None,
    detection_time_ms: int = None,
    coordinates: tuple = None,
    screenshot_path: str = None,
    device_id: str = None
):
    """
    AI执行记录收集钩子函数
    供Priority系统和其他组件调用
    """
    try:
        # 查找项目
        try:
            project = ProjectMonitor.objects.get(name=project_name)
        except ProjectMonitor.DoesNotExist:
            print(f"项目不存在: {project_name}")
            return

        # 创建执行记录
        execution_log = ExecutionLog.objects.create(
            project=project,
            button_class=button_class,
            scenario=scenario or '',
            success=success,
            detection_time_ms=detection_time_ms,
            coordinates_x=coordinates[0] if coordinates else None,
            coordinates_y=coordinates[1] if coordinates else None,
            screenshot_path=screenshot_path or '',
            device_id=device_id or ''
        )

        # 更新类统计
        monitor_service.update_class_statistics(project, button_class, success, detection_time_ms)

        print(f"记录AI执行日志: {project_name}.{button_class} - {'成功' if success else '失败'}")

    except Exception as e:
        print(f"记录AI执行日志失败: {e}")
