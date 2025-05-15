from django.urls import path
from .views import report_list, report_detail, report_delete

urlpatterns = [
    path('list/', report_list, name='reports-list'),
    path('view/<str:report_id>/', report_detail, name='view-report'),
    path('delete/<str:report_id>/', report_delete, name='delete-report'),
] 