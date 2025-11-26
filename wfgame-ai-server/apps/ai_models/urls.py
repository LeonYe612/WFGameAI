from django.urls import path
from .views import AIModelListView, AIModelDetailView, AIModelFileListView

urlpatterns = [
    path('models/', AIModelListView.as_view(), name='model-list'),
    path('models/<int:pk>/', AIModelDetailView.as_view(), name='model-detail'),
    path('files/', AIModelFileListView.as_view(), name='model-files'),
]
