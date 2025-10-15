import logging
from collections import defaultdict

from rest_framework import status
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.views import APIView

from apps.core.utils.response import api_response
from apps.core.serializers.common import CommonFieldsModelSerializer
from apps.scripts.models import ActionType, ActionParam
from apps.notifications.services import send_message, SSEEvent

logger = logging.getLogger(__name__)

def notify_action_update():
    send_message(None, SSEEvent.ACTION_UPDATE.value)

# =======================================
# ActionType
# =======================================

class ActionTypeSerializer(CommonFieldsModelSerializer):
    class Meta:
        model = ActionType
        fields = '__all__'


class ActionTypeListView(APIView):
    """
    - get: 查询列表
    - post: 创建 record
    """

    def get(self, request):
        queryset = ActionType.objects.all_teams().order_by("sort_order", "id")
        serializer = ActionTypeSerializer(queryset, many=True)
        return api_response(data=serializer.data)

    def post(self, request):
        serializer = ActionTypeSerializer(data=request.data)
        if serializer.is_valid():
            instance = serializer.save()
            notify_action_update()
            return api_response(data=ActionTypeSerializer(instance).data)
        return api_response(code=status.HTTP_400_BAD_REQUEST, msg=serializer.errors)

class ActionSortView(APIView):
    """
    - post: Action的通用排序接口
      1. sorted_ids = [id1, id2, id3, ...], 索引即为新的 sort_order
      2. model = action_type or action_param
    """

    def post(self, request):
        sorted_ids = request.data.get('sorted_ids', [])
        if not isinstance(sorted_ids, list) or not all(isinstance(i, int) for i in sorted_ids):
            return api_response(code=status.HTTP_400_BAD_REQUEST, msg="sorted_ids 必须是整数列表")
        index_map = {id: index for index, id in enumerate(sorted_ids)}

        model_map = {
            'action_type': ActionType,
            'action_param': ActionParam,
        }
        model_name = request.data.get('model')
        if model_name not in model_map:
            return api_response(code=status.HTTP_400_BAD_REQUEST, msg="model 必须是 'action_type' 或 'action_param'")

        model_class = model_map[model_name]
        targets = model_class.objects.all_teams().filter(id__in=sorted_ids)
        if targets.count() != len(sorted_ids):
            return api_response(code=status.HTTP_400_BAD_REQUEST, msg="部分目标ID不存在")

        update_obj = []
        for obj in targets:
            new_order = index_map[obj.id]
            if obj.sort_order != new_order:
                obj.sort_order = new_order
                update_obj.append(obj)

        if update_obj:
            model_class.objects.bulk_update(update_obj, ['sort_order'])
        notify_action_update()
        return api_response()


class ActionTypeDetailView(APIView):
    """
    - get: 查询单个 record
    - put: 修改单个 record
    - delete: 删除单个 record
    """

    @staticmethod
    def get_object(pk):
        obj = ActionType.objects.all_teams().filter(id=pk).first()
        if not obj:
            raise Exception(f"操作类型ID {pk} 不存在")
        return obj

    def handle_exception(self, exc):
        logger.error(exc)
        return api_response(code=status.HTTP_500_INTERNAL_SERVER_ERROR, msg=str(exc))

    def get(self, request, pk):
        obj = self.get_object(pk)
        serializer = ActionTypeSerializer(obj)
        return api_response(data=serializer.data)

    def put(self, request, pk):
        obj = self.get_object(pk)
        serializer = ActionTypeSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            instance = serializer.save()
            notify_action_update()
            return api_response(data=ActionTypeSerializer(instance).data)
        return api_response(code=status.HTTP_400_BAD_REQUEST, msg=serializer.errors)

    def delete(self, request, pk):
        obj = self.get_object(pk)
        obj.delete()
        notify_action_update()
        return api_response()


# =======================================
# ActionParam
# =======================================

class ActionParamSerializer(CommonFieldsModelSerializer):
    action_library = PrimaryKeyRelatedField(label="操作类型", queryset=ActionType.objects.all_teams(), required=True)
    class Meta:
        model = ActionParam
        fields = '__all__'


class ActionParamListView(APIView):
    """
    - get: 查询列表
    - post: 创建 record
    """

    def get(self, request):
        queryset = ActionParam.objects.all_teams().order_by("sort_order", "id")
        serializer = ActionParamSerializer(queryset, many=True)
        return api_response(data=serializer.data)

    def post(self, request):
        serializer = ActionParamSerializer(data=request.data)
        if serializer.is_valid():
            instance = serializer.save()
            notify_action_update()
            return api_response(data=ActionParamSerializer(instance).data)
        return api_response(code=status.HTTP_400_BAD_REQUEST, msg=serializer.errors)


class ActionParamDetailView(APIView):
    """
    - get: 查询单个 record
    - put: 修改单个 record
    - delete: 删除单个 record
    """

    @staticmethod
    def get_object(pk):
        obj = ActionParam.objects.all_teams().filter(id=pk).first()
        if not obj:
            raise Exception(f"动作参数ID {pk} 不存在")
        return obj

    def handle_exception(self, exc):
        logger.error(exc)
        return api_response(code=status.HTTP_500_INTERNAL_SERVER_ERROR, msg=str(exc))

    def get(self, request, pk):
        obj = self.get_object(pk)
        serializer = ActionParamSerializer(obj)
        return api_response(data=serializer.data)

    def put(self, request, pk):
        obj = self.get_object(pk)
        serializer = ActionParamSerializer(obj, data=request.data, partial=True)
        if not serializer.is_valid():
            return api_response(code=status.HTTP_400_BAD_REQUEST, msg=serializer.errors)
        instance = serializer.save()
        notify_action_update()
        return api_response(data=ActionParamSerializer(instance).data)

    def delete(self, request, pk):
        obj = self.get_object(pk)
        obj.delete()
        notify_action_update()
        return api_response()


# =======================================
# ActionType with Params
# =======================================

class ActionTypeWithParamsView(APIView):
    """
    - get: 获取操作类型及参数的树形结构
    """

    def get(self, request):
        action_types = ActionType.objects.all_teams().order_by("sort_order", "id").prefetch_related('params')

        action_type_serializer = ActionTypeSerializer(action_types, many=True)
        action_types_data = action_type_serializer.data

        param_serializer = ActionParamSerializer(ActionParam.objects.all_teams(), many=True)
        params_data = param_serializer.data

        params_map = defaultdict(list)
        for param in params_data:
            params_map[param['action_library']].append(param)

        for action_type in action_types_data:
            action_type['params'] = params_map.get(action_type['id'], [])

        return api_response(data=action_types_data)

