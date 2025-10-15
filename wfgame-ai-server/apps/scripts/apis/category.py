import logging

from rest_framework import status
from rest_framework.views import APIView

from apps.core.utils.response import api_response
from apps.core.serializers.common import CommonFieldsModelSerializer
from apps.scripts.models import ScriptCategory

logger = logging.getLogger(__name__)

class ScriptCategorySerializer(CommonFieldsModelSerializer):

    class Meta:
        model = ScriptCategory
        fields = '__all__'

class CategoryListView(APIView):
    """
    - get: 查询列表
    - post: 创建 record
    """

    def get(self, request):
        queryset = ScriptCategory.objects.all()
        serializer = ScriptCategorySerializer(queryset, many=True)
        return api_response(data=serializer.data)

    def post(self, request):
        serializer = ScriptCategorySerializer(data=request.data)
        if serializer.is_valid():
            instance = serializer.save()
            return api_response(data=ScriptCategorySerializer(instance).data)
        return api_response(code=status.HTTP_400_BAD_REQUEST, msg=serializer.errors)


class CategoryTreeView(APIView):
    """
    - get: 获取分类树形结构
    """

    def get(self, request):
        # 如果未传递 team_id，表示查询当前用户所激活团队下的分类
        # 如果传递了 team_id，则查询指定团队下的分类
        team_id = request.query_params.get('team_id', None)
        queryset = ScriptCategory.objects.all() if not team_id else ScriptCategory.objects.for_team(team_id)

        # 1. 数据库层排序，减少后续排序压力
        category_list = queryset.order_by('sort_order', 'id').values('id', 'name', 'parent', 'sort_order')

        # 2. 构建 parent_id 到子节点的映射
        from collections import defaultdict
        children_map = defaultdict(list)
        for category in category_list:
            parent = category['parent']
            children_map[parent].append(category)

        # 3. 递归构建树
        def build_tree(parent_id=None):
            nodes = children_map.get(parent_id, [])
            for node in nodes:
                node['children'] = build_tree(node['id'])
                if not node['children']:
                    node.pop('children')
            return nodes

        category_tree = build_tree()
        return api_response(data=category_tree)


class CategoryDetailView(APIView):
    """
    - get: 查询单个 record
    - put: 修改单个 record
    - delete: 删除单个 record
    """

    @staticmethod
    def get_object(pk):
        obj = ScriptCategory.objects.filter(id=pk).first()
        if not obj:
            raise Exception(f"目录ID {pk} 不存在")
        return obj

    def handle_exception(self, exc):
        logger.error(exc)
        return api_response(code=status.HTTP_500_INTERNAL_SERVER_ERROR, msg=str(exc))

    def get(self, request, pk):
        obj = self.get_object(pk)
        serializer = ScriptCategorySerializer(obj)
        return api_response(data=serializer.data)

    def put(self, request, pk):
        obj = self.get_object(pk)
        serializer = ScriptCategorySerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            instance = serializer.save()
            return api_response(data=ScriptCategorySerializer(instance).data)
        return api_response(code=status.HTTP_400_BAD_REQUEST, msg=serializer.errors)

    def delete(self, request, pk):
        obj = self.get_object(pk)
        obj.delete()
        return api_response()
