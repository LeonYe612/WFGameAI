#!/usr/bin/env python3
# -*- coding: utf-8 -*-n/env python3
# -*- coding: utclass TaskViewSet(viewsets.ModelViewSet):

"""
任务管理应用的视图
"""

import logging
import copy
from datetime import datetime
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.conf import settings
from rest_framework import viewsets, status, views, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from apps.reports.models import Report, ReportDetail

from .models import TaskGroup, Task, TaskScript, TaskDevice
from ..devices.models import Device
from .serializers import (
    TaskGroupSerializer, TaskListSerializer, TaskDetailSerializer,
    TaskCreateSerializer, TaskUpdateSerializer, TaskScriptSerializer,
    TaskDeviceSerializer
)
from ..core.utils.response import api_response, CustomResponseModelViewSet
from apps.core.models.common import get_current_user, get_current_team_id

from .tasks import replay_task

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
    ordering_fields = ['created_at', 'priority']
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

        # 判断绑定设备是否在线
        task_devices = TaskDevice.objects.filter(task=task).select_related('device')
        no_online_devices = [td.device.name for td in task_devices if td.device.status != "online"]
        if no_online_devices:
            return api_response(
                msg=f"以下设备不在线，无法启动任务: {', '.join(no_online_devices)}",
                code=status.HTTP_400_BAD_REQUEST
            )
        no_idle_devices = [td.device.name for td in task_devices if not td.device.is_idle]
        if no_idle_devices:
            return api_response(
                msg=f"以下设备不空闲，无法启动任务: {', '.join(no_idle_devices)}",
                code=status.HTTP_400_BAD_REQUEST
            )
        # 设备占用要求：
        # 1. 未占用（None）
        # 2. 被其他用户占用
        current_user = get_current_user()
        unoccupied_devices = []
        occupied_by_others = []
        for td in task_devices:
            device = td.device
            if not getattr(device, 'current_user', None):
                unoccupied_devices.append(device.name)
            elif device.current_user != current_user:
                occupied_by_others.append(device.name)
        if unoccupied_devices:
            return api_response(
                msg=f"以下设备未被任何人占用，无法启动任务: {', '.join(unoccupied_devices)}",
                code=status.HTTP_400_BAD_REQUEST
            )
        if occupied_by_others:
            return api_response(
                msg=f"以下设备已被其他用户占用，无法启动任务: {', '.join(occupied_by_others)}",
                code=status.HTTP_400_BAD_REQUEST
            )
        try:
            with transaction.atomic():
                # 更新任务状态
                task.status = 'running'
                task.start_time = datetime.now()
                task.end_time = None
                task.execution_time = None
                task.updater_id = get_current_user().id if get_current_user() else None
                task.updater_name = get_current_user().username if get_current_user() else '系统'
                task.updated_at = datetime.now()

                # 清理旧 Redis 缓存（只在校验通过后执行）
                redis_client = getattr(settings.REDIS, 'client', None)
                if redis_client:
                    try:
                        pattern = f"wfgame:replay:task:{task.id}:device:*:steps"
                        for key in redis_client.scan_iter(match=pattern):
                            try:
                                redis_client.delete(key)
                            except Exception:
                                pass
                        try:
                            redis_client.delete(f"wfgame:replay:task:{task.id}:primary_device")
                        except Exception:
                            pass
                        # 同时清理错误信息 Key
                        pattern_error = f"wfgame:replay:task:{task.id}:device:*:error"
                        for key in redis_client.scan_iter(match=pattern_error):
                            try:
                                redis_client.delete(key)
                            except Exception:
                                pass
                    except Exception:
                        logger.warning("启动任务时清理Redis缓存失败")

                logger.info(f"回放任务开始投递: {task.name}")
                async_res = replay_task.delay(task.id)
                if async_res is None:
                    # 显式标记任务失败，避免列表仍显示为“成功/已完成”
                    task.status = 'failed'
                    task.end_time = datetime.now()
                    if task.start_time:
                        task.execution_time = (task.end_time - task.start_time).total_seconds()
                    task.save(update_fields=['status', 'end_time', 'execution_time', 'updated_at'])
                    return api_response(
                        msg="当前无可用 Celery Worker，任务未投递",
                        code=status.HTTP_503_SERVICE_UNAVAILABLE
                    )
                task.celery_id = getattr(async_res, 'id', None)
                task.save(update_fields=['celery_id', 'status', 'updated_at', 'updater_id', 'updater_name', 'start_time', 'end_time', 'execution_time'])

                # 重启成功后，恢复 TaskDevice 到初始状态（清空错误信息与时间，回到 pending）
                try:
                    TaskDevice.objects.filter(task=task).update(
                        status='pending',
                        start_time=None,
                        end_time=None,
                        execution_time=None,
                        error_message=''  # 清空设备级错误信息
                    )
                except Exception:
                    logger.warning(f"重启任务时重置 TaskDevice 状态失败: task_id={task.id}")

                # Report 仅维护一条记录：若存在则复用并重置；若有多条保留第一条并警告
                reports = list(Report.objects.all_teams().filter(task=task).order_by('id'))
                if reports:
                    report = reports[0]
                    if len(reports) > 1:
                        logger.warning(f"Task {task.id} 存在多个报告记录，保留第一条 (id={report.id}) 其余不处理")
                    report.status = 'generating'
                    report.duration = 0
                    # 保持 report_path 稳定：/apps/reports/tmp/replay/task_<id>/index.html
                    report.report_path = f"/apps/reports/tmp/replay/task_{task.id}/index.html"
                    report.save(update_fields=['status','duration','report_path'])
                else:
                    report = Report.objects.all_teams().create(
                        task=task,
                        name=f"Task-{task.id} Report",
                        duration=0,
                        report_path=f"/apps/reports/tmp/replay/task_{task.id}/index.html",
                        status='generating'
                    )

                # 准备脚本骨架
                ts_qs = TaskScript.objects.filter(task=task).select_related('script').order_by('order')
                initial_records = []
                for ts in ts_qs:
                    s = getattr(ts, 'script', None)
                    if not s:
                        continue
                    raw_steps = (getattr(s, 'steps', None) or [])
                    new_steps = []
                    for step_def in raw_steps:
                        try:
                            st = dict(step_def) if isinstance(step_def, dict) else {"value": step_def}
                        except Exception:
                            st = {"value": step_def}
                        st['result'] = {
                            "status": "pending",
                            "display_status": "等待中",
                            "start_time": None,
                            "end_time": None,
                            "local_pic_pth": "",
                            "oss_pic_pth": "",
                            "error_msg": "",
                        }
                        new_steps.append(st)
                    initial_records.append({
                        "meta": {
                            "id": getattr(s, 'id', None),
                            "name": getattr(s, 'name', ""),
                            "loop-count": 1,
                            "max-duration": None,
                            "loop-index": None,
                        },
                        "steps": new_steps,
                        "summary": {
                            "total": len(new_steps),
                            "success": 0,
                            "failed": 0,
                            "skipped": 0,
                            "duration": None,
                            "duration_ms": None,
                        }
                    })

                # 初始化 ReportDetail（复用或创建），为每台设备提供独立拷贝，避免引用共享导致第二脚本丢失
                td_qs = TaskDevice.objects.filter(task=task).select_related('device')
                for td in td_qs:
                    device = td.device
                    if not device:
                        continue
                    detail, _ = ReportDetail.objects.all_teams().get_or_create(
                        report=report,
                        device=device,
                        defaults={
                            'duration': 0,
                            'error_message': '',
                        }
                    )
                    detail.duration = 0
                    detail.error_message = ''
                    detail.step_results = copy.deepcopy(initial_records)
                    detail.save(update_fields=['duration', 'error_message', 'step_results'])

                # 返回任务信息
                serializer = self.get_serializer(task)
                return api_response(
                    msg="任务启动成功",
                    data={
                    "message": "任务启动成功",
                    "task": serializer.data,
                    "celery_task_id": async_res.id,
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
                # 不再使用 end_time/start_time 计算，保留 execution_time 若之前设置过
                task.save()

                # 更新关联设备状态
                task_devices = TaskDevice.objects.filter(task=task, status='running')
                for task_device in task_devices:
                    task_device.status = 'cancelled'
                    # 不再维护设备的独立 start/end 时间
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
        # 避免与 start 重复校验：在 restart 内自行完成校验与启动，不再调用 start
        # 1) 运行中阻断
        if task.status == 'running':
            return api_response(
                msg="任务已在执行中",
                code=status.HTTP_400_BAD_REQUEST
            )

        # 2) 前置校验（顺序：在线 -> 空闲 -> 占用）
        task_devices = TaskDevice.objects.filter(task=task).select_related('device')
        no_online_devices = [td.device.name for td in task_devices if td.device.status != "online"]
        if no_online_devices:
            return api_response(
                msg=f"以下设备不在线，无法重启任务: {', '.join(no_online_devices)}",
                code=status.HTTP_400_BAD_REQUEST
            )
        no_idle_devices = [td.device.name for td in task_devices if not td.device.is_idle]
        if no_idle_devices:
            return api_response(
                msg=f"以下设备不空闲，无法重启任务: {', '.join(no_idle_devices)}",
                code=status.HTTP_400_BAD_REQUEST
            )
        current_user = get_current_user()
        unoccupied_devices = []
        occupied_by_others = []
        for td in task_devices:
            device = td.device
            if not getattr(device, 'current_user', None):
                unoccupied_devices.append(device.name)
            elif device.current_user != current_user:
                occupied_by_others.append(device.name)
        if unoccupied_devices:
            return api_response(
                msg=f"以下设备未被任何人占用，无法重启任务: {', '.join(unoccupied_devices)}",
                code=status.HTTP_400_BAD_REQUEST
            )
        if occupied_by_others:
            return api_response(
                msg=f"以下设备已被其他用户占用，无法重启任务: {', '.join(occupied_by_others)}",
                code=status.HTTP_400_BAD_REQUEST
            )

        # 3) 校验通过后，执行状态更新、清理缓存、投递任务与初始化报告（与 start 统一逻辑）
        try:
            with transaction.atomic():
                # 更新任务为 running（不再先置 pending，避免状态漂移）
                task.status = 'running'
                task.start_time = datetime.now()
                task.end_time = None
                task.execution_time = None
                task.updater_id = get_current_user().id if get_current_user() else None
                task.updater_name = get_current_user().username if get_current_user() else '系统'
                task.updated_at = datetime.now()

                # 清理旧 Redis 缓存
                redis_client = getattr(settings.REDIS, 'client', None)
                if redis_client:
                    try:
                        pattern = f"wfgame:replay:task:{task.id}:device:*:steps"
                        for key in redis_client.scan_iter(match=pattern):
                            try:
                                redis_client.delete(key)
                            except Exception:
                                pass
                        try:
                            redis_client.delete(f"wfgame:replay:task:{task.id}:primary_device")
                        except Exception:
                            pass
                        # 同时清理错误信息 Key
                        pattern_error = f"wfgame:replay:task:{task.id}:device:*:error"
                        for key in redis_client.scan_iter(match=pattern_error):
                            try:
                                redis_client.delete(key)
                            except Exception:
                                pass
                    except Exception:
                        logger.warning("重启任务时清理Redis缓存失败")

                # 投递 Celery 任务
                logger.info(f"回放任务重启投递: {task.name}")
                async_res = replay_task.delay(task.id)
                if async_res is None:
                    # 显式标记任务失败，避免列表仍显示为“成功/已完成”
                    task.status = 'failed'
                    task.end_time = datetime.now()
                    if task.start_time:
                        task.execution_time = (task.end_time - task.start_time).total_seconds()
                    task.save(update_fields=['status', 'end_time', 'execution_time', 'updated_at'])
                    return api_response(
                        msg="当前无可用 Celery Worker，任务未投递",
                        code=status.HTTP_503_SERVICE_UNAVAILABLE
                    )
                task.celery_id = getattr(async_res, 'id', None)
                task.save(update_fields=['celery_id', 'status', 'updated_at', 'updater_id', 'updater_name', 'start_time', 'end_time', 'execution_time'])

                # 复用或创建单一 Report 记录
                reports = list(Report.objects.all_teams().filter(task=task).order_by('id'))
                if reports:
                    report = reports[0]
                    if len(reports) > 1:
                        logger.warning(f"Task {task.id} 存在多个报告记录，保留第一条 (id={report.id}) 其余不处理")
                    report.status = 'generating'
                    report.duration = 0
                    report.report_path = f"/apps/reports/tmp/replay/task_{task.id}/index.html"
                    report.save(update_fields=['status','duration','report_path'])
                else:
                    report = Report.objects.all_teams().create(
                        task=task,
                        name=f"Task-{task.id} Report",
                        duration=0,
                        report_path=f"/apps/reports/tmp/replay/task_{task.id}/index.html",
                        status='generating'
                    )

                # 准备脚本骨架
                ts_qs = TaskScript.objects.filter(task=task).select_related('script').order_by('order')
                initial_records = []
                for ts in ts_qs:
                    s = getattr(ts, 'script', None)
                    if not s:
                        continue
                    raw_steps = (getattr(s, 'steps', None) or [])
                    new_steps = []
                    for step_def in raw_steps:
                        try:
                            st = dict(step_def) if isinstance(step_def, dict) else {"value": step_def}
                        except Exception:
                            st = {"value": step_def}
                        st['result'] = {
                            "status": "pending",
                            "display_status": "等待中",
                            "start_time": None,
                            "end_time": None,
                            "local_pic_pth": "",
                            "oss_pic_pth": "",
                            "error_msg": "",
                        }
                        new_steps.append(st)
                    initial_records.append({
                        "meta": {
                            "id": getattr(s, 'id', None),
                            "name": getattr(s, 'name', ""),
                            "loop-count": 1,
                            "max-duration": None,
                            "loop-index": None,
                        },
                        "steps": new_steps,
                        "summary": {
                            "total": len(new_steps),
                            "success": 0,
                            "failed": 0,
                            "skipped": 0,
                            "duration": None,
                            "duration_ms": None,
                        }
                    })

                td_qs = TaskDevice.objects.filter(task=task).select_related('device')
                for td in td_qs:
                    device = td.device
                    if not device:
                        continue
                    detail, _ = ReportDetail.objects.all_teams().get_or_create(
                        report=report,
                        device=device,
                        defaults={
                            'duration': 0,
                            'error_message': '',
                        }
                    )
                    detail.duration = 0
                    detail.error_message = ''
                    detail.step_results = copy.deepcopy(initial_records)
                    detail.save(update_fields=['duration', 'error_message', 'step_results'])

                serializer = self.get_serializer(task)
                return api_response(
                    msg="任务重启成功",
                    data={
                        "message": "任务重启成功",
                        "task": serializer.data,
                        "celery_task_id": async_res.id,
                    }
                )

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
        # todo 通过弹窗确认复制任务而不是直接后端操作
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
        # 复制脚本和设备（按新结构组织）
        script_ids = list(orig_task.taskscript_set.order_by('order').values_list('script_id', flat=True))
        new_data['script_ids'] = [{
            'id': int(sid),
            'loop-count': 1
        } for sid in script_ids]

        device_ids = list(orig_task.taskdevice_set.values_list('device_id', flat=True))
        devices = {d.id: d for d in Device.objects.filter(id__in=device_ids)}
        new_data['device_ids'] = [{
            'id': int(did),
            'serial': devices.get(int(did)).device_id if devices.get(int(did)) else ''
        } for did in device_ids]
        new_data['params'] = {}
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
                        task.status = 'running'
                        # 移除 start_time 使用
                        task.save()
                        success_count += 1
                    elif operation == 'stop':
                        task.status = 'cancelled'
                        # 移除 end_time 使用
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
