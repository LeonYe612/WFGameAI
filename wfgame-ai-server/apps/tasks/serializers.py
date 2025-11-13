#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务管理应用的序列化器
"""

from rest_framework import serializers
from .models import TaskGroup, Task, TaskScript, TaskDevice
from ..devices.models import Device
from ..scripts.models import Script


class TaskGroupSerializer(serializers.ModelSerializer):
    """任务组序列化器"""

    class Meta:
        model = TaskGroup
        fields = [
            'id', 'name', 'description', 'created_by',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TaskScriptSerializer(serializers.ModelSerializer):
    """任务脚本关联序列化器"""
    script_name = serializers.CharField(source='script.name', read_only=True)
    script_path = serializers.CharField(source='script.path', read_only=True)

    class Meta:
        model = TaskScript
        fields = [
            'id', 'script', 'script_name', 'script_path',
            'order', 'timeout', 'retry_count', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class TaskDeviceSerializer(serializers.ModelSerializer):
    """任务设备关联序列化器"""
    device_name = serializers.CharField(source='device.name', read_only=True)
    device_id = serializers.CharField(source='device.device_id', read_only=True)

    class Meta:
        model = TaskDevice
        fields = [
            'id', 'device', 'device_name', 'device_id',
            'status', 'start_time', 'end_time', 'execution_time',
            'error_message', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class TaskListSerializer(serializers.ModelSerializer):
    """任务列表序列化器（简化版）"""
    device_ids = serializers.SerializerMethodField()
    script_ids = serializers.SerializerMethodField()
    scripts_count = serializers.SerializerMethodField()
    devices_count = serializers.SerializerMethodField()
    devices_list = serializers.SerializerMethodField()
    scripts_list = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)

    class Meta:
        model = Task
        fields = [
            'id', 'name', 'group', 'group_name', 'status', 'status_display', 'celery_id', 'script_params',
            'priority', 'priority_display', 'description', 'schedule_time',
            'start_time', 'end_time', 'execution_time', 'creator_name',
            'creator_id', 'created_at', 'updater_id', 'updated_at', 'updater_name',
            'device_ids', 'devices_list', 'devices_count', 'script_ids', 'scripts_list', 'scripts_count',
            'task_type', 'run_type', 'run_info'
        ]
    def get_device_ids(self, obj):
        """获取关联设备ID列表"""
        return list(TaskDevice.objects.filter(task=obj).values_list('device_id', flat=True))


    def get_devices_count(self, obj):
        """获取关联设备数量"""
        return TaskDevice.objects.filter(task=obj).count()

    def get_devices_list(self, obj):
        """获取关联设备名称列表"""
        return [td.device.name for td in TaskDevice.objects.filter(task=obj).select_related('device')]

    def get_script_ids(self, obj):
        """获取关联脚本ID列表"""
        return list(TaskScript.objects.filter(task=obj).values_list('script_id', flat=True))

    def get_scripts_count(self, obj):
        """获取关联脚本数量"""
        return TaskScript.objects.filter(task=obj).count()

    def get_scripts_list(self, obj):
        """获取关联脚本名称列表"""
        return [ts.script.name for ts in TaskScript.objects.filter(task=obj).select_related('script')]


class TaskDetailSerializer(serializers.ModelSerializer):
    """任务详情序列化器（完整版）"""
    device_ids = serializers.SerializerMethodField()
    script_ids = serializers.SerializerMethodField()
    devices_list = serializers.SerializerMethodField()
    scripts_list = serializers.SerializerMethodField()
    devices_count = serializers.SerializerMethodField()
    scripts_count = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)

    class Meta:
        model = Task
        fields = [
            'id', 'name', 'group', 'group_name', 'celery_id', 'script_params',
            'status', 'status_display', 'priority', 'priority_display', 'task_type', 'run_type', 'run_info', 'description',
            'schedule_time', 'start_time', 'end_time', 'execution_time',
            'creator_name', 'creator_id', 'created_at', 'updater_name', 'updater_id', 'updated_at',
            'device_ids', 'devices_list', 'devices_count', 'script_ids', 'scripts_list', 'scripts_count'
        ]

    def get_device_ids(self, obj):
        """获取关联设备ID列表"""
        return list(TaskDevice.objects.filter(task=obj).values_list('device_id', flat=True))

    def get_devices_list(self, obj):
        """获取关联设备名称列表"""
        return [td.device.name for td in TaskDevice.objects.filter(task=obj).select_related('device')]

    def get_script_ids(self, obj):
        """获取关联脚本ID列表"""
        return list(TaskScript.objects.filter(task=obj).values_list('script_id', flat=True))

    def get_scripts_list(self, obj):
        """获取关联脚本名称列表"""
        return [ts.script.name for ts in TaskScript.objects.filter(task=obj).select_related('script')]

    def get_devices_count(self, obj):
        """获取关联设备数量"""
        return TaskDevice.objects.filter(task=obj).count()

    def get_scripts_count(self, obj):
        """获取关联脚本数量"""
        return TaskScript.objects.filter(task=obj).count()


class TaskCreateSerializer(serializers.ModelSerializer):
    """任务创建序列化器（接受新的结构化载荷）"""

    # 新结构：脚本为对象数组，包含 id、loop-count、max-duration
    script_ids = serializers.ListField(
        child=serializers.DictField(child=serializers.JSONField()),
        write_only=True,
        required=False,
        help_text="[{id, loop-count, max-duration?}, ...]"
    )
    # 新结构：设备为对象数组，包含 id、serial
    device_ids = serializers.ListField(
        child=serializers.DictField(child=serializers.JSONField()),
        write_only=True,
        required=False,
        help_text="[{id, serial}, ...]"
    )
    # 新增：额外参数对象（例如 version 等）
    params = serializers.JSONField(write_only=True, required=False)

    class Meta:
        model = Task
        fields = [
            'id', 'name', 'group', 'status', 'priority', 'description', 'celery_id',
            'schedule_time', 'script_ids', 'device_ids', 'task_type', 'run_type', 'run_info',
            'params', 'script_params'
        ]

    def validate_script_ids(self, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("script_ids 必须为数组(list)")
        parsed = []
        for idx, item in enumerate(value):
            if not isinstance(item, dict):
                raise serializers.ValidationError(f"script_ids 第 {idx} 项必须为对象")
            if 'id' not in item:
                raise serializers.ValidationError(f"script_ids 第 {idx} 项缺少 id 字段")
            sid = item.get('id')
            if not isinstance(sid, int):
                raise serializers.ValidationError(f"script_ids 第 {idx} 项的 id 必须为整数")
            lc = item.get('loop-count', 1)
            if not isinstance(lc, int) or lc <= 0:
                raise serializers.ValidationError(f"script_ids 第 {idx} 项的 loop-count 必须为正整数")
            md = item.get('max-duration', None)
            if md is not None and (not isinstance(md, int) or md <= 0):
                raise serializers.ValidationError(f"script_ids 第 {idx} 项的 max-duration 必须为正整数")
            parsed.append({'id': sid, 'loop-count': lc, 'max-duration': md})
        return parsed

    def validate_device_ids(self, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("device_ids 必须为数组(list)")
        parsed = []
        for idx, item in enumerate(value):
            if not isinstance(item, dict):
                raise serializers.ValidationError(f"device_ids 第 {idx} 项必须为对象")
            if 'id' not in item:
                raise serializers.ValidationError(f"device_ids 第 {idx} 项缺少 id 字段")
            did = item.get('id')
            if not isinstance(did, int):
                raise serializers.ValidationError(f"device_ids 第 {idx} 项的 id 必须为整数")
            serial = item.get('serial', '')
            if serial is not None and not isinstance(serial, str):
                raise serializers.ValidationError(f"device_ids 第 {idx} 项的 serial 必须为字符串")
            parsed.append({'id': did, 'serial': serial or ''})
        return parsed

    def create(self, validated_data):
        # 弹出新结构字段
        script_objs = validated_data.pop('script_ids', [])
        device_objs = validated_data.pop('device_ids', [])
        params = validated_data.pop('params', {}) or {}

        # 生成 Task，并将完整的新结构快照保存到 script_params 以便追溯
        snapshot = {
            'script_ids': script_objs,
            'device_ids': device_objs,
            'params': params
        }
        validated_data['script_params'] = snapshot
        task = Task.objects.create(**validated_data)

        # 关联脚本（按顺序）
        script_id_list = [item['id'] for item in script_objs]
        valid_script_ids = set(Script.objects.filter(id__in=script_id_list).values_list('id', flat=True))
        for i, script_id in enumerate(script_id_list):
            if script_id in valid_script_ids:
                TaskScript.objects.create(task=task, script_id=script_id, order=i + 1)
            else:
                raise serializers.ValidationError(f"脚本ID {script_id} 不存在")

        # 关联设备
        device_id_list = [item['id'] for item in device_objs]
        valid_device_ids = set(Device.objects.filter(id__in=device_id_list).values_list('id', flat=True))
        for device_id in device_id_list:
            if device_id in valid_device_ids:
                TaskDevice.objects.create(task=task, device_id=device_id)
            else:
                raise serializers.ValidationError(f"设备ID {device_id} 不存在")
        return task


class TaskUpdateSerializer(serializers.ModelSerializer):
    """任务更新序列化器"""

    class Meta:
        model = Task
        fields = [
            'name', 'group', 'status', 'priority', 'description', 'celery_id',
            'schedule_time', 'start_time', 'end_time', 'execution_time'
        ]
