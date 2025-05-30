#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务管理应用的序列化器
"""

from rest_framework import serializers
from .models import TaskGroup, Task, TaskScript, TaskDevice


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
    script_count = serializers.SerializerMethodField()
    device_count = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)

    class Meta:
        model = Task
        fields = [
            'id', 'name', 'group', 'group_name', 'status', 'status_display',
            'priority', 'priority_display', 'description', 'schedule_time',
            'start_time', 'end_time', 'execution_time', 'created_by',
            'created_by_name', 'created_at', 'updated_at', 'script_count',
            'device_count'
        ]

    def get_script_count(self, obj):
        """获取关联脚本数量"""
        return obj.scripts.count()

    def get_device_count(self, obj):
        """获取关联设备数量"""
        return obj.devices.count()


class TaskDetailSerializer(serializers.ModelSerializer):
    """任务详情序列化器（完整版）"""
    scripts = TaskScriptSerializer(source='taskscript_set', many=True, read_only=True)
    devices = TaskDeviceSerializer(source='taskdevice_set', many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)

    class Meta:
        model = Task
        fields = [
            'id', 'name', 'group', 'group_name', 'status', 'status_display',
            'priority', 'priority_display', 'description', 'schedule_time',
            'start_time', 'end_time', 'execution_time', 'created_by',
            'created_by_name', 'created_at', 'updated_at', 'scripts', 'devices'
        ]


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
            'name', 'group', 'status', 'priority', 'description',
            'schedule_time', 'script_ids', 'device_ids'
        ]

    def create(self, validated_data):
        """创建任务和关联关系"""
        script_ids = validated_data.pop('script_ids', [])
        device_ids = validated_data.pop('device_ids', [])

        # 创建任务
        task = Task.objects.create(**validated_data)

        # 创建脚本关联
        for i, script_id in enumerate(script_ids):
            TaskScript.objects.create(
                task=task,
                script_id=script_id,
                order=i + 1
            )

        # 创建设备关联
        for device_id in device_ids:
            TaskDevice.objects.create(
                task=task,
                device_id=device_id
            )

        return task


class TaskUpdateSerializer(serializers.ModelSerializer):
    """任务更新序列化器"""

    class Meta:
        model = Task
        fields = [
            'name', 'group', 'status', 'priority', 'description',
            'schedule_time', 'start_time', 'end_time', 'execution_time'
        ]
