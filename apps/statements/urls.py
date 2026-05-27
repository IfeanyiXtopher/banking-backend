from django.urls import path
from . import views

urlpatterns = [
    path('', views.StatementListView.as_view(), name='statement-list'),
    path('request/', views.request_statement, name='statement-request'),
    path('<uuid:pk>/download/', views.download_statement, name='statement-download'),
]
