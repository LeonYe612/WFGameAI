#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================
Description:
脚本管理应用的序列化器
Author: WFGame AI Team
CreateDate: 2024-05-15
Version: 1.0
===============================
"""

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from .models import Script, ScriptCategory, ScriptExecution, ScriptVersion, ScriptFile


class ScriptCategorySerializer(serializers.ModelSerializer):
    """
    脚本分类序列化器
    """
    scripts_count = serializers.SerializerMethodField()

    class Meta:
        model = ScriptCategory
        fields = ['id', 'name', 'description', 'scripts_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_scripts_count(self, obj):
        """获取该分类下的脚本数量"""
        return obj.scripts.count()


class ScriptFileSerializer(serializers.ModelSerializer):
    """
    脚本文件序列化器
    """
    category_name = serializers.ReadOnlyField(source='category.name')
    uploaded_by_name = serializers.ReadOnlyField(source='uploaded_by.username')
    type_display = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = ScriptFile
        fields = [
            'id', 'filename', 'file_path', 'file_size', 'step_count',
            'type', 'type_display', 'category', 'category_name',
            'description', 'status', 'status_display', 'uploaded_by',
            'uploaded_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_type_display(self, obj):
        """获取脚本类型的显示名称"""
        return obj.get_type_display()

    def get_status_display(self, obj):
        """获取状态的显示名称"""
        return obj.get_status_display()


class ScriptCreateSerializer(serializers.ModelSerializer):
    """
    创建脚本序列化器
    """
    class Meta:
        model = Script
        fields = [
            'id', 'name', 'type', 'category', 'content', 'description',
            'is_active', 'include_in_log', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'author', 'execution_count', 'created_at', 'updated_at']

    def validate_name(self, value):
        """验证脚本名称唯一性"""
        if Script.objects.filter(name=value).exists():
            raise serializers.ValidationError(_("同名脚本已存在"))
        return value


class ScriptUpdateSerializer(serializers.ModelSerializer):
    """
    更新脚本序列化器
    """
    class Meta:
        model = Script
        fields = [
            'id', 'name', 'type', 'category', 'content', 'description',
            'is_active', 'include_in_log', 'updated_at'
        ]
        read_only_fields = ['id', 'author', 'execution_count', 'created_at', 'updated_at']

    def validate_name(self, value):
        """验证脚本名称唯一性（排除当前实例）"""
        if Script.objects.filter(name=value).exclude(id=self.instance.id).exists():
            raise serializers.ValidationError(_("同名脚本已存在"))
        return value


class ScriptSerializer(serializers.ModelSerializer):
    """
    脚本详情序列化器
    """
    category_name = serializers.ReadOnlyField(source='category.name')
    author_name = serializers.ReadOnlyField(source='author.username')
    type_display = serializers.SerializerMethodField()
    executions_count = serializers.SerializerMethodField()

    class Meta:
        model = Script
        fields = [
            'id', 'name', 'type', 'type_display', 'category', 'category_name',
            'content', 'description', 'author', 'author_name', 'is_active',
            'include_in_log', 'execution_count', 'executions_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_type_display(self, obj):
        """获取脚本类型的显示名称"""
        return obj.get_type_display()

    def get_executions_count(self, obj):
        """获取该脚本的执行记录数量"""
        return obj.executions.count()


class ScriptExecutionSerializer(serializers.ModelSerializer):
    """
    脚本执行记录序列化器
    """
    script_name = serializers.ReadOnlyField(source='script.name')
    executed_by_name = serializers.ReadOnlyField(source='executed_by.username')
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = ScriptExecution
        fields = [
            'id', 'script', 'script_name', 'status', 'status_display',
            'start_time', 'end_time', 'execution_time', 'result', 'error_message',
            'executed_by', 'executed_by_name', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_status_display(self, obj):
        """获取执行状态的显示名称"""
        return obj.get_status_display()


class ScriptVersionSerializer(serializers.ModelSerializer):
    """脚本版本序列化器"""
    created_by_name = serializers.ReadOnlyField(source='created_by.username')

    class Meta:
        model = ScriptVersion
        fields = ['id', 'script', 'version', 'content', 'comment',
                 'created_by', 'created_by_name', 'created_at']
        read_only_fields = ['created_at']


class ScriptListSerializer(serializers.ModelSerializer):
    """脚本列表序列化器 - 用于列表显示，不包含完整脚本内容"""
    category_name = serializers.ReadOnlyField(source='category.name')
    author_name = serializers.ReadOnlyField(source='author.username')
    version_count = serializers.SerializerMethodField()

    class Meta:
        model = Script
        fields = ['id', 'name', 'description', 'category', 'category_name',
                 'status', 'version', 'author', 'author_name',
                 'is_template', 'created_at', 'updated_at', 'version_count']
        read_only_fields = ['created_at', 'updated_at', 'version_count']

    def get_version_count(self, obj):
        """获取脚本版本数量"""
        return obj.versions.count()


class ScriptDetailSerializer(serializers.ModelSerializer):
    """脚本详情序列化器 - 用于详细视图，包含完整脚本内容"""
    category_name = serializers.ReadOnlyField(source='category.name')
    author_name = serializers.ReadOnlyField(source='author.username')
    versions = ScriptVersionSerializer(many=True, read_only=True)

    class Meta:
        model = Script
        fields = ['id', 'name', 'description', 'content', 'category', 'category_name',
                 'status', 'version', 'author', 'author_name', 'is_template',
                 'created_at', 'updated_at', 'versions']
        read_only_fields = ['created_at', 'updated_at', 'versions']


class ScriptImportSerializer(serializers.Serializer):
    """脚本导入序列化器"""
    file = serializers.FileField()
    category = serializers.PrimaryKeyRelatedField(
        queryset=ScriptCategory.objects.all(),
        required=False
    )

    def validate_file(self, value):
        """验证上传的文件"""
        # 检查文件扩展名
        if not value.name.endswith('.json'):
            raise serializers.ValidationError("只支持JSON格式的脚本文件")
        return value