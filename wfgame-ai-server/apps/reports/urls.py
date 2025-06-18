from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import (
    get_report_list, get_device_performance, summary_list,
    report_detail, report_delete,
    # New unified report management functions
    get_unified_report_list, unified_summary_list, unified_report_detail,
    unified_report_delete, get_unified_device_performance,
    # Unified report management API endpoints
    device_reports_view, summary_reports_view, report_stats_view,
    cleanup_reports_view, create_device_report_view
)

urlpatterns = [
    # Legacy endpoints for backward compatibility
    path('', get_report_list, name='reports-list'),
    path('performance/', get_device_performance, name='device-performance'),
    path('summary_list/', summary_list, name='summary-list'),
    path('<str:report_id>/', report_detail, name='report-detail'),
    path('<str:report_id>/delete/', report_delete, name='report-delete'),

    # New unified report management endpoints
    path('unified/', get_unified_report_list, name='unified-reports-list'),
    path('unified/summary/', unified_summary_list, name='unified-summary-list'),
    path('unified/<str:report_id>/', unified_report_detail, name='unified-report-detail'),
    path('unified/<str:report_id>/delete/', unified_report_delete, name='unified-report-delete'),
    path('unified/performance/', get_unified_device_performance, name='unified-device-performance'),

    # Unified report management API endpoints
    path('api/devices/', device_reports_view, name='api-device-reports'),
    path('api/summary/', summary_reports_view, name='api-summary-reports'),
    path('api/stats/', report_stats_view, name='api-report-stats'),    path('api/cleanup/', cleanup_reports_view, name='api-cleanup-reports'),
    path('api/create/', create_device_report_view, name='api-create-device-report'),
]

# 添加静态资源URL配置
import os
urlpatterns += static('/static/reports/static/', document_root=os.path.join(settings.BASE_DIR, 'staticfiles', 'reports', 'static'))