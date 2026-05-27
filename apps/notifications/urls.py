from django.urls import path
from . import views

urlpatterns = [
    path('read-all/', views.mark_all_read, name='notification-read-all'),
    path('preferences/', views.NotificationPreferenceView.as_view(), name='notification-preferences'),
    path('<uuid:pk>/read/', views.mark_read, name='notification-read'),
    path('<uuid:pk>/', views.NotificationDestroyView.as_view(), name='notification-delete'),
    path('', views.NotificationListView.as_view(), name='notification-list'),
]
