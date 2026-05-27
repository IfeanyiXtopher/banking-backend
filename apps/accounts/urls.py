from django.urls import path
from . import views

urlpatterns = [
    path('', views.AccountListCreateView.as_view(), name='account-list'),
    path('<uuid:pk>/', views.AccountDetailView.as_view(), name='account-detail'),
    path('currencies/', views.CurrencyListView.as_view(), name='currency-list'),
]
