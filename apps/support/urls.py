from django.urls import path
from . import views

urlpatterns = [
    path('', views.TicketListCreateView.as_view(), name='ticket-list'),
    path('<uuid:pk>/', views.TicketDetailView.as_view(), name='ticket-detail'),
    path('<uuid:pk>/message/', views.add_message, name='ticket-message'),
    path('<uuid:pk>/close/', views.close_ticket, name='ticket-close'),
]
