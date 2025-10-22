#!/usr/bin/env python3
# -*- coding: utf-8 -*-n/env python3
# -*- coding: utclass TaskViewSet(viewsets.ModelViewSet):

"""
任务管理应用的视图
"""

import logging
from datetime import datetime
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import viewsets, status, views, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from .models import TaskGroup, Task, TaskScript, TaskDevice
from .serializers import (
    TaskGroupSerializer, TaskListSerializer, TaskDetailSerializer,
    TaskCreateSerializer, TaskUpdateSerializer, TaskScriptSerializer,
    TaskDeviceSerializer
)
from ..core.utils.response import api_response, CustomResponseModelViewSet
from apps.core.models.common import get_current_user, get_current_team_id

logger = logging.getLogger(__name__)


class TaskGroupViewSet(viewsets.ModelViewSet):
    queryset = TaskGroup.objects.all_teams()
    serializer_class = TaskGroupSerializer
    permission_classes = (AllowAny,)
    http_method_names = ['get', 'post', 'put', 'patch', 'delete']


    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user if self.request.user.is_authenticated else None)

class TaskViewSet(CustomResponseModelViewSet):
    """任务管理视图集"""
    queryset = Task.objects.all_teams()
    permission_classes = (AllowAny,)
    http_method_names = ['get', 'post', 'put', 'patch', 'delete']
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'priority', 'group']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'priority', 'start_time']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action in ['list', 'destroy']:
            return api_response(data=TaskListSerializer, msg="查询任务列表成功")
        elif self.action == 'create':
            return api_response(data=TaskCreateSerializer, msg="创建任务成功")
        elif self.action in ['update', 'partial_update']:
            return TaskUpdateSerializer
        return TaskDetailSerializer

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """启动任务执行"""
        task = self.get_object()

        # 检查任务状态
        if task.status == 'running':
            return api_response(
                msg="任务已在执行中",
                code=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                # 更新任务状态
                task.status = 'running'
                task.start_time = datetime.now()
                task.end_time = None
                task.execution_time = None
                task.save()

                # 更新关联设备状态
                TaskDevice.objects.filter(task=task).update(
                    status='running',
                    start_time=datetime.now(),
                    end_time=None,
                    execution_time=None,
                    error_message=''
                )

                # 这里应该触发实际的任务执行逻辑
                # 可以通过Celery任务队列或其他异步处理方式实现
                logger.info(f"任务开始执行: {task.name}")

                # 返回任务信息
                serializer = self.get_serializer(task)
                return api_response(
                    msg="任务启动成功",
                    data={
                    "message": "任务启动成功",
                    "task": serializer.data
                })

        except Exception as e:
            logger.error(f"启动任务失败: {str(e)}")
            return api_response(
                msg=f"启动任务失败: {str(e)}",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """停止任务执行"""
        task = self.get_object()

        if task.status != 'running':
            return api_response(
                msg="任务未在执行中",
                code=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                # 更新任务状态
                task.status = 'cancelled'
                task.end_time = datetime.now()
                if task.start_time:
                    task.execution_time = (task.end_time - task.start_time).total_seconds()
                task.save()

                # 更新关联设备状态
                task_devices = TaskDevice.objects.filter(task=task, status='running')
                for task_device in task_devices:
                    task_device.status = 'cancelled'
                    task_device.end_time = datetime.now()
                    if task_device.start_time:
                        task_device.execution_time = (task_device.end_time - task_device.start_time).total_seconds()
                    task_device.save()

                logger.info(f"任务已停止: {task.name}")

                serializer = self.get_serializer(task)
                return api_response(
                    msg="任务停止成功",
                    data={
                    "message": "任务停止成功",
                    "task": serializer.data
                })

        except Exception as e:
            logger.error(f"停止任务失败: {str(e)}")
            return api_response(
                msg= f"停止任务失败: {str(e)}",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def restart(self, request, pk=None):
        """重新执行任务"""
        task = self.get_object()

        # 重置任务状态
        try:
            with transaction.atomic():
                task.status = 'pending'
                task.start_time = None
                task.end_time = None
                task.execution_time = None
                task.save()

                # 重置关联设备状态
                TaskDevice.objects.filter(task=task).update(
                    status='pending',
                    start_time=None,
                    end_time=None,
                    execution_time=None,
                    error_message=''
                )

                logger.info(f"任务已重置: {task.name}")

                # 然后启动任务
                return self.start(request, pk)

        except Exception as e:
            logger.error(f"重新执行任务失败: {str(e)}")
            return api_response(
                msg=f"重新执行任务失败: {str(e)}",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def scripts(self, request, pk=None):
        """获取任务关联的脚本"""
        task = self.get_object()
        task_scripts = TaskScript.objects.filter(task=task).order_by('order')
        serializer = TaskScriptSerializer(task_scripts, many=True)
        return api_response(data=serializer.data)

    @action(detail=True, methods=['post'])
    def devices(self, request, pk=None):
        """获取任务关联的设备"""
        task = self.get_object()
        task_devices = TaskDevice.objects.filter(task=task)
        serializer = TaskDeviceSerializer(task_devices, many=True)
        return api_response(data=serializer.data)

    @action(detail=True, methods=['post'])
    def status_update(self, request, pk=None):
        """更新任务状态（用于外部系统调用）"""
        task = self.get_object()
        new_status = request.data.get('status')
        error_message = request.data.get('error_message', '')

        if new_status not in [choice[0] for choice in Task.STATUS_CHOICES]:
            return api_response(
                msg="无效的状态",
                code=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                old_status = task.status
                task.status = new_status

                # 如果任务完成或失败，设置结束时间
                if new_status in ['completed', 'failed', 'cancelled']:
                    task.end_time = datetime.now()
                    if task.start_time:
                        task.execution_time = (task.end_time - task.start_time).total_seconds()

                task.save()

                # 记录状态变更日志
                logger.info(f"任务状态更新: {task.name} {old_status} -> {new_status}")

                if error_message:
                    logger.error(f"任务错误信息: {task.name} - {error_message}")

                serializer = self.get_serializer(task)
                return api_response(data=serializer.data)

        except Exception as e:
            logger.error(f"更新任务状态失败: {str(e)}")
            return api_response(
                msg=f"更新任务状态失败: {str(e)}",
                data={"error": f"更新任务状态失败: {str(e)}"},
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """复制任务接口：入参为任务id，复制任务及其关联设备和脚本"""
        orig_task = self.get_object()
        # 复制字段（可根据需要调整）
        copy_fields = [
            'name', 'group', 'status', 'priority', 'description',
            'schedule_time', 'task_type', 'run_type', 'run_info'
        ]
        new_data = {field: getattr(orig_task, field) for field in copy_fields}
        # 名称加后缀
        new_data['name'] = f"{orig_task.name}_副本"
        # 复制脚本和设备
        script_ids = list(orig_task.taskscript_set.order_by('order').values_list('script_id', flat=True))
        device_ids = list(orig_task.taskdevice_set.values_list('device_id', flat=True))
        new_data['script_ids'] = script_ids
        new_data['device_ids'] = device_ids
        # 创建新任务
        serializer = TaskCreateSerializer(data=new_data)
        serializer.is_valid(raise_exception=True)
        new_task = serializer.save()
        # 返回完整详情
        detail_serializer = TaskDetailSerializer(new_task)
        return api_response(
            msg=f"任务 [{orig_task.id}] 复制成功, 新任务ID: [{new_task.id}]",
            data=detail_serializer.data
        )

@api_view(['POST'])
@permission_classes((AllowAny,))
def task_bulk_operations(request):
    """任务批量操作"""
    operation = request.data.get('operation')
    task_ids = request.data.get('task_ids', [])

    if not operation or not task_ids:
        return api_response(
            msg="缺少操作类型或任务ID",
            code=status.HTTP_400_BAD_REQUEST
        )

    tasks = Task.objects.filter(id__in=task_ids)
    if not tasks.exists():
        return api_response(
            msg="未找到指定的任务",
            code=status.HTTP_404_NOT_FOUND
        )

    try:
        with transaction.atomic():
            success_count = 0
            error_count = 0

            for task in tasks:
                try:
                    if operation == 'start':
                        if task.status != 'running':
                            task.status = 'running'
                            task.start_time = datetime.now()
                            task.save()
                            success_count += 1
                    elif operation == 'stop':
                        if task.status == 'running':
                            task.status = 'cancelled'
                            task.end_time = datetime.now()
                            if task.start_time:
                                task.execution_time = (task.end_time - task.start_time).total_seconds()
                            task.save()
                            success_count += 1
                    elif operation == 'delete':
                        task.delete()
                        success_count += 1
                    else:
                        error_count += 1
                except Exception as e:
                    logger.error(f"批量操作任务失败: {task.name} - {str(e)}")
                    error_count += 1

            return api_response(
                msg=f"批量操作完成",
                data={
                "success_count": success_count,
                "error_count": error_count,
                "operation": operation
            })

    except Exception as e:
        logger.error(f"批量操作失败: {str(e)}")
        return api_response(
            msg=f"批量操作失败: {str(e)}",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes((AllowAny,))
def task_execution_logs(request, task_id):
    """获取任务执行日志"""
    task = get_object_or_404(Task, id=task_id)

    # 这里可以实现具体的日志查询逻辑
    # 暂时返回模拟数据
    logs = [
        {
            "timestamp": datetime.now().isoformat(),
            "level": "INFO",
            "message": f"任务 {task.name} 开始执行",
            "step": 1
        },
        {
            "timestamp": datetime.now().isoformat(),
            "level": "INFO",
            "message": "正在初始化执行环境",
            "step": 2
        }
    ]

    return api_response(
        data={
        "task_id": task_id,
        "task_name": task.name,
        "logs": logs
    })
