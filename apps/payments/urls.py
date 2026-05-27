from django.urls import path

from . import views

urlpatterns = [
    path('resolve-management-fee/', views.resolve_management_fee_view, name='payment-resolve-mgmt-fee'),
    path('bill-pay/', views.bill_pay_view, name='payment-bill-pay'),
]
