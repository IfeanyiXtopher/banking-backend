from django.urls import path
from apps.transactions import regulated_views

from . import views

urlpatterns = [
    path('products/', views.LoanProductListView.as_view(), name='loan-products'),
    path('applications/', views.LoanApplicationListCreateView.as_view(), name='loan-applications'),
    path('applications/<uuid:pk>/', views.LoanApplicationDetailView.as_view(), name='loan-application-detail'),
    path(
        'applications/<uuid:application_id>/regulated-payout/context/',
        regulated_views.loan_payout_context_view,
    ),
    path('applications/<uuid:application_id>/regulated-payout/start/', regulated_views.loan_regulated_payout_start),
    path('applications/<uuid:application_id>/regulated-payout/complete/', regulated_views.loan_regulated_payout_complete),
    path('accounts/', views.LoanAccountListView.as_view(), name='loan-accounts'),
    path('accounts/<uuid:pk>/', views.LoanAccountDetailView.as_view(), name='loan-account-detail'),
    path('payment/', views.loan_payment, name='loan-payment'),
]
