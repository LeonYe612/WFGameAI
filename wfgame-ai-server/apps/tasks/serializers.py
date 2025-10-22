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
            'id', 'name', 'group', 'group_name', 'status', 'status_display',
            'priority', 'priority_display', 'description', 'schedule_time',
            'start_time', 'end_time', 'execution_time', 'creator_name',
            'creator_id', 'created_at', 'updater_id', 'updated_at', 'updater_name',
            'devices_count', 'devices_list', 'scripts_count','scripts_list', 'task_type', 'run_type', 'run_info'
        ]

    def get_devices_count(self, obj):
        """获取关联设备数量"""
        return TaskDevice.objects.filter(task=obj).count()

    def get_devices_list(self, obj):
        """获取关联设备名称列表"""
        return [td.device.name for td in TaskDevice.objects.filter(task=obj).select_related('device')]

    def get_scripts_count(self, obj):
        """获取关联脚本数量"""
        return TaskScript.objects.filter(task=obj).count()

    def get_scripts_list(self, obj):
        """获取关联脚本名称列表"""
        return [ts.script.name for ts in TaskScript.objects.filter(task=obj).select_related('script')]


class TaskDetailSerializer(serializers.ModelSerializer):
    """任务详情序列化器（完整版）"""
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
            'id', 'name', 'group', 'group_name',
            'status', 'status_display', 'priority', 'priority_display', 'task_type', 'run_type', 'run_info', 'description',
            'schedule_time', 'start_time', 'end_time', 'execution_time',
            'creator_name', 'creator_id', 'created_at', 'updater_name', 'updater_id', 'updated_at',
            'devices_count', 'devices_list', 'scripts_count', 'scripts_list',
        ]

    def get_devices_list(self, obj):
        """获取关联设备名称列表"""
        return [td.device.name for td in TaskDevice.objects.filter(task=obj).select_related('device')]

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
    """任务创建序列化器"""
    script_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        help_text="关联的脚本ID列表"
    )
    device_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        help_text="关联的设备ID列表"
    )

    class Meta:
        model = Task
        fields = [
            'id', 'name', 'group', 'status', 'priority', 'description',
            'schedule_time', 'script_ids', 'device_ids', 'task_type', 'run_type', 'run_info'
        ]


    def create(self, validated_data):
        script_ids = validated_data.pop('script_ids', [])
        device_ids = validated_data.pop('device_ids', [])
        task = Task.objects.create(**validated_data)

        # 校验脚本 id
        valid_script_ids = set(Script.objects.filter(id__in=script_ids).values_list('id', flat=True))
        for i, script_id in enumerate(script_ids):
            if script_id in valid_script_ids:
                TaskScript.objects.create(
                    task=task,
                    script_id=script_id,
                    order=i + 1
                )
            else:
                raise serializers.ValidationError(f"脚本ID {script_id} 不存在")

        # 校验设备 id
        valid_device_ids = set(Device.objects.filter(id__in=device_ids).values_list('id', flat=True))
        for device_id in device_ids:
            if device_id in valid_device_ids:
                TaskDevice.objects.create(
                    task=task,
                    device_id=device_id
                )
            else:
                raise serializers.ValidationError(f"设备ID {device_id} 不存在")
        return task


class TaskUpdateSerializer(serializers.ModelSerializer):
    """任务更新序列化器"""

    class Meta:
        model = Task
        fields = [
            'name', 'group', 'status', 'priority', 'description',
            'schedule_time', 'start_time', 'end_time', 'execution_time'
        ]
