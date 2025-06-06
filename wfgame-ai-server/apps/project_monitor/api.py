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
from django.db import models
from django.utils import timezone
from typing import List, Dict, Optional
import json
from datetime import datetime, timedelta

from .models import ProjectMonitor, ExecutionLog, ClassStatistics
from .monitor_service import monitor_service

router = APIRouter(prefix="/api/project-monitor", tags=["Project Monitor"])

# WebSocket连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                disconnected.append(connection)

        # 清理断开的连接
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

# 遵循项目规范：全部使用POST请求
@router.post("/projects/list", response_model=List[ProjectInfo])
async def get_projects(db: Session = Depends(get_db)):
    """获取所有项目列表 - 使用POST请求符合项目规范"""
    try:
        projects = db.query(Project).all()
        return [
            ProjectInfo(
                id=p.id,
                name=p.name,
                yaml_path=p.yaml_path,
                description=p.description,
                status=p.status,
                created_at=p.created_at
            )
            for p in projects
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取项目列表失败: {str(e)}")

@router.post("/projects", response_model=ProjectInfo)
async def create_project(
    name: str,
    yaml_path: str,
    description: str = None,
    db: Session = Depends(get_db)
):
    """创建新项目"""
    try:
        project = monitor_service.create_project(db, name, yaml_path, description)

        # 广播项目创建事件
        await manager.broadcast({
            "event": "project_created",
            "data": {
                "id": project.id,
                "name": project.name,
                "created_at": project.created_at.isoformat()
            }
        })

        return ProjectInfo(
            id=project.id,
            name=project.name,
            yaml_path=project.yaml_path,
            description=project.description,
            status=project.status,
            created_at=project.created_at
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建项目失败: {str(e)}")

@router.get("/projects/{project_id}/dashboard", response_model=ProjectDashboard)
async def get_project_dashboard(project_id: int, db: Session = Depends(get_db)):
    """获取项目仪表板"""
    try:
        dashboard = monitor_service.get_project_dashboard(db, project_id)
        return dashboard
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取项目仪表板失败: {str(e)}")

@router.post("/projects/{project_id}/executions")
async def log_execution(
    project_id: int,
    execution_data: ExecutionLogCreate,
    db: Session = Depends(get_db)
):
    """记录执行日志"""
    try:
        # 确保project_id一致
        execution_data.project_id = project_id

        log_data = execution_data.dict()
        execution_log = monitor_service.log_execution(db, log_data)

        # 广播执行事件
        await manager.broadcast({
            "event": "execution_logged",
            "data": {
                "project_id": project_id,
                "button_class": execution_data.button_class,
                "success": execution_data.success,
                "executed_at": datetime.utcnow().isoformat()
            }
        })

        return {"status": "success", "execution_id": execution_log.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"记录执行日志失败: {str(e)}")

@router.get("/projects/{project_id}/classes/{button_class}/trend")
async def get_class_trend(
    project_id: int,
    button_class: str,
    days: int = 7,
    db: Session = Depends(get_db)
):
    """获取类性能趋势"""
    try:
        trend_data = monitor_service.get_class_trend(db, project_id, button_class, days)
        return trend_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取趋势数据失败: {str(e)}")

@router.get("/projects/{project_id}/statistics")
async def get_project_statistics(project_id: int, db: Session = Depends(get_db)):
    """获取项目详细统计数据"""
    try:
        dashboard = monitor_service.get_project_dashboard(db, project_id)

        # 构建详细统计响应
        return {
            "project_info": dashboard.project_info,
            "summary": {
                "total_executions": dashboard.total_executions,
                "avg_success_rate": dashboard.avg_success_rate,
                "avg_detection_time": dashboard.avg_detection_time
            },
            "class_statistics": dashboard.class_statistics,
            "recent_failures": dashboard.recent_failures,
            "optimization_suggestions": dashboard.optimization_suggestions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取项目统计失败: {str(e)}")

@router.websocket("/ws/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: int):
    """项目实时监控WebSocket"""
    await manager.connect(websocket)
    try:
        while True:
            # 等待客户端消息或保持连接
            data = await websocket.receive_text()

            # 可以处理客户端发送的命令
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except:
                pass

    except WebSocketDisconnect:
        manager.disconnect(websocket)

@router.get("/dashboard")
async def get_dashboard_page():
    """获取监控仪表板页面"""
    return HTMLResponse(content="""
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
            #connectionStatus {
                position: fixed;
                top: 10px;
                right: 10px;
                padding: 10px;
                border-radius: 5px;
                color: white;
                font-weight: bold;
            }
            .connected { background: #4CAF50; }
            .disconnected { background: #F44336; }
        </style>
    </head>
    <body>
        <div id="connectionStatus" class="disconnected">连接断开</div>

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
            let ws = null;

            // 加载项目列表
            async function loadProjects() {
                try {
                    const response = await fetch('/api/project-monitor/projects');
                    const projects = await response.json();

                    const select = document.getElementById('projectSelect');
                    select.innerHTML = '<option value="">请选择项目...</option>';

                    projects.forEach(project => {
                        const option = document.createElement('option');
                        option.value = project.id;
                        option.textContent = project.name;
                        select.appendChild(option);
                    });
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
                    const response = await fetch(`/api/project-monitor/projects/${projectId}/dashboard`);
                    const dashboard = await response.json();

                    updateDashboard(dashboard);
                    document.getElementById('dashboard').style.display = 'grid';

                    // 建立WebSocket连接
                    connectWebSocket(projectId);

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

            // WebSocket连接
            function connectWebSocket(projectId) {
                if (ws) {
                    ws.close();
                }

                ws = new WebSocket(`ws://localhost:8000/api/project-monitor/ws/${projectId}`);

                ws.onopen = function() {
                    document.getElementById('connectionStatus').className = 'connected';
                    document.getElementById('connectionStatus').textContent = '已连接';
                };

                ws.onclose = function() {
                    document.getElementById('connectionStatus').className = 'disconnected';
                    document.getElementById('connectionStatus').textContent = '连接断开';
                };

                ws.onmessage = function(event) {
                    const message = JSON.parse(event.data);
                    if (message.event === 'execution_logged') {
                        // 实时更新数据
                        loadProject();
                    }
                };

                // 心跳包
                setInterval(() => {
                    if (ws && ws.readyState === WebSocket.OPEN) {
                        ws.send(JSON.stringify({type: 'ping'}));
                    }
                }, 30000);
            }

            // 页面加载时初始化
            window.onload = function() {
                loadProjects();
            };
        </script>
    </body>
    </html>
    """)

# 数据收集钩子函数，供外部调用
async def log_ai_execution(
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
    from .database import db_manager

    try:
        db = db_manager.get_session()

        # 查找项目
        project = db.query(Project).filter(Project.name == project_name).first()
        if not project:
            print(f"项目不存在: {project_name}")
            return

        # 构建日志数据
        log_data = {
            'project_id': project.id,
            'button_class': button_class,
            'scenario': scenario,
            'success': success,
            'detection_time_ms': detection_time_ms,
            'device_id': device_id,
            'screenshot_path': screenshot_path
        }

        if coordinates:
            log_data['coordinates_x'] = coordinates[0]
            log_data['coordinates_y'] = coordinates[1]

        # 记录执行日志
        execution_log = monitor_service.log_execution(db, log_data)

        # 广播实时更新
        await manager.broadcast({
            "event": "execution_logged",
            "data": {
                "project_id": project.id,
                "button_class": button_class,
                "success": success,
                "executed_at": datetime.utcnow().isoformat()
            }
        })

        print(f"记录AI执行日志: {project_name}.{button_class} - {'成功' if success else '失败'}")

    except Exception as e:
        print(f"记录AI执行日志失败: {e}")
    finally:
        db.close()
