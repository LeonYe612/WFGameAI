#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================
Description:
脚本管理应用的视图函数
Author: WFGame AI Team
CreateDate: 2024-05-15
Version: 1.0
===============================
"""

import logging
from datetime import datetime

import json
import uuid
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from rest_framework import viewsets, status, views, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import ScriptCategory, Script, ScriptVersion, ScriptExecution
from .serializers import (
    ScriptCategorySerializer,
    ScriptListSerializer,
    ScriptDetailSerializer,
    ScriptVersionSerializer,
    ScriptImportSerializer,
    ScriptExecutionSerializer,
    ScriptCreateSerializer,
    ScriptUpdateSerializer,
    ScriptSerializer
)

logger = logging.getLogger(__name__)


class ScriptCategoryViewSet(viewsets.ModelViewSet):
    """
    脚本分类管理视图集
    
    提供脚本分类的CRUD操作
    """
    queryset = ScriptCategory.objects.all()
    serializer_class = ScriptCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """
        根据查询参数过滤分类列表
        """
        queryset = ScriptCategory.objects.all()
        name = self.request.query_params.get('name', None)
        
        if name:
            queryset = queryset.filter(name__icontains=name)
            
        return queryset
    
    def perform_create(self, serializer):
        """
        创建分类并记录日志
        """
        serializer.save()
        logger.info(
            f"脚本分类已创建: {serializer.instance.name} - 用户: {self.request.user.username}"
        )


class ScriptViewSet(viewsets.ModelViewSet):
    """
    脚本管理视图集
    
    提供脚本的CRUD操作和执行功能
    """
    queryset = Script.objects.all()
    serializer_class = ScriptSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        """
        根据操作类型返回不同的序列化器
        """
        if self.action == 'create':
            return ScriptCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ScriptUpdateSerializer
        return ScriptSerializer
    
    def get_queryset(self):
        """
        根据查询参数过滤脚本列表
        """
        queryset = Script.objects.all()
        
        # 名称过滤
        name = self.request.query_params.get('name')
        if name:
            queryset = queryset.filter(name__icontains=name)
        
        # 类型过滤
        script_type = self.request.query_params.get('type')
        if script_type:
            queryset = queryset.filter(type=script_type)
        
        # 分类过滤
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__id=category)
            
        # 状态过滤（是否激活）
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            is_active = is_active.lower() == 'true'
            queryset = queryset.filter(is_active=is_active)
            
        return queryset
    
    def perform_create(self, serializer):
        """
        创建脚本时设置作者为当前用户
        """
        serializer.save(author=self.request.user)
        logger.info(
            f"脚本已创建: {serializer.instance.name} - 用户: {self.request.user.username}"
        )
    
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """
        执行脚本
        
        创建脚本执行记录并更新执行次数
        """
        script = self.get_object()
        
        # 检查脚本是否启用
        if not script.is_active:
            return Response(
                {"error": _("无法执行未启用的脚本")},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            # 创建执行记录
            execution = ScriptExecution.objects.create(
                script=script,
                status='running',
                start_time=datetime.now(),
                executed_by=request.user
            )
            
            # 更新脚本执行次数
            script.execution_count += 1
            script.save(update_fields=['execution_count'])
        
        # 这里应该有实际的脚本执行逻辑，可能通过异步任务处理
        # 为了演示，我们假设脚本执行成功
        
        serializer = ScriptExecutionSerializer(execution)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def executions(self, request, pk=None):
        """
        获取脚本的执行历史记录
        """
        script = self.get_object()
        executions = script.executions.all()
        
        # 分页
        page = self.paginate_queryset(executions)
        if page is not None:
            serializer = ScriptExecutionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ScriptExecutionSerializer(executions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """
        启用/禁用脚本
        """
        script = self.get_object()
        script.is_active = not script.is_active
        script.save(update_fields=['is_active'])
        
        status_str = "启用" if script.is_active else "禁用"
        logger.info(f"脚本已{status_str}: {script.name} - 用户: {request.user.username}")
        
        return Response({
            "id": script.id,
            "name": script.name,
            "is_active": script.is_active
        })


class ScriptVersionViewSet(viewsets.ReadOnlyModelViewSet):
    """脚本版本视图集 - 只读"""
    queryset = ScriptVersion.objects.all()
    serializer_class = ScriptVersionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['script']


class CloneScriptView(views.APIView):
    """克隆脚本"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, pk):
        # 获取源脚本
        source_script = get_object_or_404(Script, pk=pk)
        
        # 创建新脚本对象
        new_script = Script.objects.create(
            name=f"{source_script.name} - 副本",
            description=source_script.description,
            content=source_script.content,
            category=source_script.category,
            status='draft',  # 新克隆的脚本默认为草稿状态
            version='1.0.0',  # 重置版本号
            author=request.user,
            is_template=source_script.is_template
        )
        
        # 返回新脚本数据
        serializer = ScriptDetailSerializer(new_script)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ExportScriptView(views.APIView):
    """导出脚本为JSON文件"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, pk):
        script = get_object_or_404(Script, pk=pk)
        
        # 准备导出数据
        export_data = {
            'name': script.name,
            'description': script.description,
            'content': script.content,
            'version': script.version,
            'is_template': script.is_template,
            'exported_at': script.updated_at.isoformat(),
            'exported_by': request.user.username
        }
        
        # 生成JSON响应
        response = HttpResponse(
            json.dumps(export_data, indent=2, ensure_ascii=False),
            content_type='application/json'
        )
        response['Content-Disposition'] = f'attachment; filename="{script.name.replace(" ", "_")}.json"'
        return response


class ImportScriptView(views.APIView):
    """导入脚本"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ScriptImportSerializer(data=request.data)
        if serializer.is_valid():
            # 读取上传的JSON文件
            uploaded_file = serializer.validated_data['file']
            try:
                script_data = json.load(uploaded_file)
                
                # 创建新脚本
                script = Script.objects.create(
                    name=script_data.get('name', f'导入脚本_{uuid.uuid4().hex[:8]}'),
                    description=script_data.get('description', ''),
                    content=script_data.get('content', {}),
                    category=serializer.validated_data.get('category'),
                    status='draft',  # 导入的脚本默认为草稿状态
                    version=script_data.get('version', '1.0.0'),
                    author=request.user,
                    is_template=script_data.get('is_template', False)
                )
                
                # 返回新创建的脚本
                response_serializer = ScriptDetailSerializer(script)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
                
            except json.JSONDecodeError:
                return Response(
                    {"error": "无效的JSON文件格式"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RollbackScriptView(views.APIView):
    """回滚脚本到指定版本"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, pk, version):
        script = get_object_or_404(Script, pk=pk)
        version_obj = get_object_or_404(ScriptVersion, script=script, version=version)
        
        # 更新当前脚本为指定版本的内容
        script.content = version_obj.content
        script.save()
        
        # 返回更新后的脚本
        serializer = ScriptDetailSerializer(script)
        return Response(serializer.data)


class ScriptExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    脚本执行记录视图集
    
    提供脚本执行记录的查询功能
    """
    queryset = ScriptExecution.objects.all()
    serializer_class = ScriptExecutionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """
        根据查询参数过滤执行记录
        """
        queryset = ScriptExecution.objects.all()
        
        # 按脚本过滤
        script_id = self.request.query_params.get('script')
        if script_id:
            queryset = queryset.filter(script_id=script_id)
        
        # 按状态过滤
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        
        # 按执行人过滤
        executed_by = self.request.query_params.get('executed_by')
        if executed_by:
            queryset = queryset.filter(executed_by_id=executed_by)
        
        # 按日期范围过滤
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
            
        return queryset 