import logging

from rest_framework import status
from rest_framework.views import APIView

from apps.core.utils.response import api_response, CommonPagination
from apps.core.serializers.common import CommonFieldsModelSerializer
from apps.scripts.models import Script, ScriptCategory

logger = logging.getLogger(__name__)


class ScriptSerializer(CommonFieldsModelSerializer):
    def __init__(self, *args, **kwargs):
        hidden_fields = kwargs.pop('hidden_fields', [])
        super().__init__(*args, **kwargs)
        for field in hidden_fields:
            self.fields.pop(field, None)

    class Meta:
        model = Script
        fields = '__all__'


class ScriptListView(APIView):
    """
    - get: 查询脚本列表 (支持分页和过滤)
    - post: 创建新脚本
    """

    def get(self, request):
        queryset = Script.objects.all().order_by("-id")

        # Filtering
        filters = {}
        keyword = request.query_params.get('keyword')
        script_type = request.query_params.get('type')
        category = request.query_params.get('category')
        version = request.query_params.get('version')
        is_active = request.query_params.get('is_active')
        include_in_log = request.query_params.get('include_in_log')

        if keyword:
            filters['name__icontains'] = keyword
        if script_type:
            filters['type'] = script_type
        if category:
            # 当传递目录id的时候，需要查询指定id目录和所有子目录下的脚本
            # filters['category_id__in'] = self.get_related_category_ids(int(category))
            filters['category'] = category
        if version:
            filters['version'] = version
        if is_active:
            filters['is_active'] = is_active.lower() in ['true', '1']
        if include_in_log:
            filters['include_in_log'] = include_in_log.lower() in ['true', '1']

        if filters:
            queryset = queryset.filter(**filters)

        # Pagination
        return CommonPagination().paginate_response(
            queryset,
            request,
            view=self,
            serializer_class=ScriptSerializer,
            serializer_kwargs={'many': True, 'hidden_fields': ['steps']}
        )

    def post(self, request):
        serializer = ScriptSerializer(data=request.data)
        if serializer.is_valid():
            # 根据 steps 字段自动设置 steps_count 字段
            steps = request.data.get('steps', [])
            serializer.validated_data['steps_count'] = len(steps)
            instance = serializer.save()
            return api_response(data=ScriptSerializer(instance).data)
        return api_response(code=status.HTTP_400_BAD_REQUEST, msg=serializer.errors)

    @staticmethod
    def get_related_category_ids(category_id: int):
        """
        获取指定分类及其所有子分类的ID列表（优化版，减少数据库查询）
        """
        item: ScriptCategory = ScriptCategory.objects.filter(id=category_id).first()
        if not item:
            return []
        # 一次性查出所有分类的 id 和 parent_id
        categories = ScriptCategory.objects.for_team(item.team_id).values('id', 'parent_id')
        parent_map = {}
        for cat in categories:
            parent_map.setdefault(cat['parent_id'], []).append(cat['id'])

        related_ids = set()

        def fetch_children(cat_id):
            related_ids.add(cat_id)
            for child_id in parent_map.get(cat_id, []):
                fetch_children(child_id)

        fetch_children(category_id)
        return list(related_ids)


class ScriptDetailView(APIView):
    """
    - get: 查询单个脚本
    - put: 修改单个脚本
    - delete: 删除单个脚本
    """

    @staticmethod
    def get_object(pk):
        obj = Script.objects.filter(id=pk).first()
        if not obj:
            raise Exception(f"脚本ID {pk} 不存在")
        return obj

    def handle_exception(self, exc):
        logger.error(exc)
        return api_response(code=status.HTTP_500_INTERNAL_SERVER_ERROR, msg=str(exc))

    def get(self, request, pk):
        try:
            obj = self.get_object(pk)
            serializer = ScriptSerializer(obj)
            return api_response(data=serializer.data)
        except Exception as e:
            return self.handle_exception(e)

    def put(self, request, pk):
        try:
            obj = self.get_object(pk)
            serializer = ScriptSerializer(obj, data=request.data, partial=True)
            if serializer.is_valid():
                # 根据 steps 字段自动设置 steps_count 字段
                steps = request.data.get('steps', [])
                serializer.validated_data['steps_count'] = len(steps)
                instance = serializer.save()
                return api_response(data=ScriptSerializer(instance).data)
            return api_response(code=status.HTTP_400_BAD_REQUEST, msg=serializer.errors)
        except Exception as e:
            return self.handle_exception(e)

    def delete(self, request, pk):
        try:
            obj = self.get_object(pk)
            obj.delete()
            return api_response()
        except Exception as e:
            return self.handle_exception(e)

class ScriptDeleteView(APIView):
    """
    - post: 批量删除脚本
    """

    def post(self, request):
        try:
            script_ids = request.data.get('ids')
            if not script_ids or not isinstance(script_ids, list):
                return api_response(code=status.HTTP_400_BAD_REQUEST, msg="ids 必须是一个非空列表")
            scripts = Script.objects.filter(id__in=script_ids)
            deleted_count, _ = scripts.delete()
            return api_response(data={"deleted_count": deleted_count})
        except Exception as e:
            logger.error(e)
            return api_response(code=status.HTTP_500_INTERNAL_SERVER_ERROR, msg=str(e))


class ScriptMoveView(APIView):
    """
    - post: 移动脚本到指定分类
    """

    def post(self, request):
        try:
            category_id = request.data.get('category_id')
            script_ids = request.data.get('script_ids')
            if not category_id or not script_ids:
                return api_response(code=status.HTTP_400_BAD_REQUEST, msg="category_id 和 script_ids 是必需的")
            scripts = Script.objects.filter(id__in=script_ids)
            updated_count = scripts.update(category_id=category_id)
            return api_response(data={"updated_count": updated_count})
        except Exception as e:
            logger.error(e)
            return api_response(code=status.HTTP_500_INTERNAL_SERVER_ERROR, msg=str(e))


class ScriptCopyView(APIView):
    """
    - post: 复制脚本（支持单个脚本拷贝和跨团队批量拷贝）
    参数说明：
      1. 单个脚本拷贝：copy_id
      2. 跨团队批量拷贝：script_ids, target_team_id, target_category_id
    """

    def post(self, request):
        copy_id = request.data.get('copy_id')
        script_ids = request.data.get('script_ids')
        target_team_id = request.data.get('target_team_id')
        target_category_id = request.data.get('target_category_id', None)

        # 单个脚本拷贝（当前团队内）
        if copy_id:
            item = Script.objects.filter(id=copy_id).first()
            if not item:
                return api_response(code=status.HTTP_400_BAD_REQUEST, msg=f"脚本ID {copy_id} 不存在")
            item.pk = None  # 设置主键为 None 以创建新记录
            item.name = f"{item.name}"
            item.creator_id = None
            item.creator_name = None
            item.updator_id = None
            item.updator_name = None
            item.save()
            serializer = ScriptSerializer(item, many=False, hidden_fields=['steps'])
            return api_response(data=serializer.data)

        # 跨团队批量拷贝
        if script_ids and target_team_id and target_category_id:
            category = ScriptCategory.objects.for_team(target_team_id).filter(id=target_category_id).first()
            if not category:
                return api_response(code=status.HTTP_400_BAD_REQUEST, msg=f"目标目录ID {target_category_id} 不存在")
            scripts = Script.objects.filter(id__in=script_ids)
            new_scripts = []
            for script in scripts:
                script.pk = None  # 设置主键为 None 以创建新记录
                script.team_id = target_team_id
                script.category_id = target_category_id
                script.name = f"{script.name}"
                script.creator_id = None
                script.creator_name = None
                script.updator_id = None
                script.updator_name = None
                new_scripts.append(script)
            Script.objects.bulk_create(new_scripts)
            return api_response(data={"copied_count": len(new_scripts)})

        return api_response(
            code=status.HTTP_400_BAD_REQUEST,
            msg="参数错误：请传递 copy_id 或 (script_ids、target_team_id和target_category_id)"
        )
