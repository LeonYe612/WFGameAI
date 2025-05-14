"""
脚本管理应用的视图
"""

import json
import uuid
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from rest_framework import viewsets, status, views
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import ScriptCategory, Script, ScriptVersion
from .serializers import (
    ScriptCategorySerializer,
    ScriptListSerializer,
    ScriptDetailSerializer,
    ScriptVersionSerializer,
    ScriptImportSerializer
)


class ScriptCategoryViewSet(viewsets.ModelViewSet):
    """脚本分类视图集"""
    queryset = ScriptCategory.objects.all()
    serializer_class = ScriptCategorySerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=True, methods=['get'])
    def scripts(self, request, pk=None):
        """获取指定分类下的所有脚本"""
        category = self.get_object()
        scripts = Script.objects.filter(category=category)
        serializer = ScriptListSerializer(scripts, many=True)
        return Response(serializer.data)


class ScriptViewSet(viewsets.ModelViewSet):
    """脚本视图集"""
    queryset = Script.objects.all()
    permission_classes = [IsAuthenticated]
    filterset_fields = ['name', 'status', 'category', 'is_template']
    search_fields = ['name', 'description']
    
    def get_serializer_class(self):
        """根据操作选择适当的序列化器"""
        if self.action == 'list':
            return ScriptListSerializer
        return ScriptDetailSerializer
    
    def perform_create(self, serializer):
        """创建脚本时设置作者为当前用户"""
        serializer.save(author=self.request.user)
    
    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """获取脚本的所有版本"""
        script = self.get_object()
        versions = script.versions.all()
        serializer = ScriptVersionSerializer(versions, many=True)
        return Response(serializer.data)


class ScriptVersionViewSet(viewsets.ReadOnlyModelViewSet):
    """脚本版本视图集 - 只读"""
    queryset = ScriptVersion.objects.all()
    serializer_class = ScriptVersionSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['script']


class CloneScriptView(views.APIView):
    """克隆脚本"""
    permission_classes = [IsAuthenticated]
    
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
    permission_classes = [IsAuthenticated]
    
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
    permission_classes = [IsAuthenticated]
    
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
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk, version):
        script = get_object_or_404(Script, pk=pk)
        version_obj = get_object_or_404(ScriptVersion, script=script, version=version)
        
        # 更新当前脚本为指定版本的内容
        script.content = version_obj.content
        script.save()
        
        # 返回更新后的脚本
        serializer = ScriptDetailSerializer(script)
        return Response(serializer.data) 