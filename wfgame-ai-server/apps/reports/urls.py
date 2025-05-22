from django.urls import path
from .views import get_report_list, get_device_performance, summary_list

urlpatterns = [
    path('', get_report_list, name='reports-list'),
    path('performance/', get_device_performance, name='device-performance'),
    path('summary_list/', summary_list, name='summary-list'),
]