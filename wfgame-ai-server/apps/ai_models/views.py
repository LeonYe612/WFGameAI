import logging
import os
from django.conf import settings
from rest_framework import status, serializers
from rest_framework.views import APIView

from apps.core.utils.response import api_response
from apps.core.serializers.common import CommonFieldsModelSerializer
from apps.ai_models.models import AIModel

logger = logging.getLogger(__name__)

class AIModelSerializer(CommonFieldsModelSerializer):
    version = serializers.CharField(max_length=50, required=False, default="", allow_blank=True)

    class Meta:
        model = AIModel
        fields = '__all__'

    def validate_path(self, value):
        # 1. 如果是绝对路径，直接检查
        if os.path.isabs(value):
            if not os.path.exists(value):
                raise serializers.ValidationError(f"绝对路径不存在: {value}")
            if not os.path.isfile(value):
                raise serializers.ValidationError(f"路径指向的不是一个文件: {value}")
            return value
            
        # 2. 如果是相对路径，尝试在项目根目录下的 models 目录查找
        # 假设项目结构中有一个 models 目录用于存放模型文件
        # e:\projects\WFGameAI\models
        # 注意：settings.BASE_DIR 指向 wfgame-ai-server，我们需要往上一级找，或者假设 models 在 server 目录下
        # 根据 workspace_info，models 目录在 e:\projects\WFGameAI\models，而 BASE_DIR 是 e:\projects\WFGameAI\wfgame-ai-server
        # 所以应该是 settings.BASE_DIR.parent / 'models'
        
        project_root = settings.BASE_DIR.parent
        models_dir = os.path.join(project_root, 'models')
        target_path = os.path.join(models_dir, value)
        
        if os.path.exists(target_path) and os.path.isfile(target_path):
            # 找到了文件，返回绝对路径或者保持相对路径
            # 为了兼容性，建议存储绝对路径，或者存储相对于 models 目录的路径
            # 这里我们返回绝对路径，确保后续使用方便
            return target_path
            
        raise serializers.ValidationError(f"在路径 {value} 或默认模型目录 {models_dir} 下未找到该文件")

class AIModelFileListView(APIView):
    """
    - get: 获取可用模型文件列表（树形结构）
    """
    def get(self, request):
        models_dir = settings.CFG.get('paths', 'weights_dir', '')
        if not models_dir:
            return api_response(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                msg="config.ini 配置中未找到模型文件目录: paths.weights_dir"
            )
        
        def build_tree(directory):
            tree = []
            if not os.path.exists(directory):
                return tree
                
            try:
                items = sorted(os.listdir(directory))
            except PermissionError:
                return []

            for item in items:
                # 忽略隐藏文件
                if item.startswith('.'):
                    continue
                    
                full_path = os.path.join(directory, item)
                
                if os.path.isdir(full_path):
                    children = build_tree(full_path)
                    # 只有当目录下有符合条件的文件时才显示该目录
                    if children: 
                        node = {
                            'label': item,
                            'value': full_path,
                            'children': children,
                            'disabled': True # 目录不可选，只能选文件
                        }
                        tree.append(node)
                elif os.path.isfile(full_path):
                    # 过滤支持的模型文件后缀
                    if item.lower().endswith(('.pt', '.onnx', '.engine', '.bin', '.yaml')):
                        node = {
                            'label': item,
                            'value': full_path
                        }
                        tree.append(node)
            return tree

        tree_data = build_tree(models_dir)
        return api_response(data=tree_data)

class AIModelListView(APIView):
    """
    - get: 查询列表
    - post: 创建 record
    """

    def get(self, request):
        queryset = AIModel.objects.all().order_by('-id')
        # 支持按类型筛选
        model_type = request.query_params.get('type')
        enable = request.query_params.get('enable')
        if enable is not None:
            if enable.lower() in ['true', '1']:
                queryset = queryset.filter(enable=True)
            elif enable.lower() in ['false', '0']:
                queryset = queryset.filter(enable=False)
        if model_type:
            queryset = queryset.filter(type=model_type)
            
        serializer = AIModelSerializer(queryset, many=True)
        return api_response(data=serializer.data)

    def post(self, request):
        serializer = AIModelSerializer(data=request.data)
        if serializer.is_valid():
            instance = serializer.save()
            return api_response(data=AIModelSerializer(instance).data)
        return api_response(code=status.HTTP_400_BAD_REQUEST, msg=serializer.errors)


class AIModelDetailView(APIView):
    """
    - get: 查询单个 record
    - put: 修改单个 record
    - delete: 删除单个 record
    """

    @staticmethod
    def get_object(pk):
        obj = AIModel.objects.filter(id=pk).first()
        if not obj:
            raise Exception(f"模型ID {pk} 不存在")
        return obj

    def handle_exception(self, exc):
        logger.error(exc)
        return api_response(code=status.HTTP_500_INTERNAL_SERVER_ERROR, msg=str(exc))

    def get(self, request, pk):
        obj = self.get_object(pk)
        serializer = AIModelSerializer(obj)
        return api_response(data=serializer.data)

    def put(self, request, pk):
        obj = self.get_object(pk)
        serializer = AIModelSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            instance = serializer.save()
            return api_response(data=AIModelSerializer(instance).data)
        return api_response(code=status.HTTP_400_BAD_REQUEST, msg=serializer.errors)

    def delete(self, request, pk):
        obj = self.get_object(pk)
        obj.delete()
        return api_response()
