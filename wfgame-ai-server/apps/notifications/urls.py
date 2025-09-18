from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('stream/', views.sse_stream, name='sse_stream'),
    path('send/', views.NotificationSendView.as_view(), name='notification_send'),
]
