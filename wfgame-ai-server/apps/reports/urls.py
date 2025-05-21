from django.urls import path
from .views import get_report_list, get_device_performance

urlpatterns = [
    path('', get_report_list, name='reports-list'),
    path('performance/', get_device_performance, name='device-performance'),
] 