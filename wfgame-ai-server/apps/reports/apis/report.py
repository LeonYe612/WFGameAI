import logging

from rest_framework import status
from rest_framework.views import APIView

from apps.core.utils.response import api_response, CommonPagination
from apps.core.serializers.common import CommonFieldsModelSerializer
from apps.reports.models import Report, ReportDetail
from apps.devices.models import Device
from apps.tasks.serializers import TaskDetailSerializer

logger = logging.getLogger(__name__)


class ReportSerializer(CommonFieldsModelSerializer):
    task = TaskDetailSerializer(read_only=True)
    class Meta:
        model = Report
        fields = '__all__'


class DeviceSerializer(CommonFieldsModelSerializer):
    class Meta:
        model = Device
        fields = '__all__'


class ReportDetailSerializer(CommonFieldsModelSerializer):
    device = DeviceSerializer(read_only=True)
    report = ReportSerializer(read_only=True)

    def __init__(self, *args, **kwargs):
        hidden_fields = kwargs.pop('hidden_fields', [])
        super().__init__(*args, **kwargs)
        for field in hidden_fields:
            self.fields.pop(field, None)

    class Meta:
        model = ReportDetail
        fields = '__all__'


class ReportListView(APIView):
    """
    - get: 查询报告列表 (支持分页和过滤)
    """

    def get(self, request):
        queryset = Report.objects.all().order_by("-id")

        # Filtering
        keyword = request.query_params.get('keyword')
        if keyword:
            if "id=" in keyword:
                try:
                    search_id = int(keyword.replace("id=", "").strip())
                    queryset = queryset.filter(id=search_id)
                except ValueError:
                    pass
            else:
                queryset = queryset.filter(name__icontains=keyword)

        # Pagination
        return CommonPagination().paginate_response(
            queryset,
            request,
            view=self,
            serializer_class=ReportSerializer,
            serializer_kwargs={'many': True}
        )


class ReportDetailListView(APIView):
    """
    - get: 根据 report_id 查询报告详情列表
    """

    def get(self, request):
        report_id = request.query_params.get('report_id')
        if not report_id:
            return api_response(code=status.HTTP_400_BAD_REQUEST, msg='report_id is required')

        queryset = ReportDetail.objects.filter(report_id=report_id).select_related('device')
        serializer = ReportDetailSerializer(queryset, many=True, hidden_fields=['report', 'step_results'])
        return api_response(data=serializer.data)


class ReportDetailItemView(APIView):
    """
    - get: 查询单个报告详情
    """

    @staticmethod
    def get_object(pk):
        obj = ReportDetail.objects.all_teams().filter(id=pk).select_related('device').first()
        if not obj:
            raise Exception(f"报告详情ID {pk} 不存在")
        return obj

    def handle_exception(self, exc):
        logger.error(exc)
        return api_response(code=status.HTTP_500_INTERNAL_SERVER_ERROR, msg=str(exc))

    def get(self, request, pk):
        try:
            obj = self.get_object(pk)
            serializer = ReportDetailSerializer(obj)
            return api_response(data=serializer.data)
        except Exception as e:
            return self.handle_exception(e)

