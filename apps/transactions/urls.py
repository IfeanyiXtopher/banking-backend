from django.urls import path
from . import views, regulated_views

urlpatterns = [
    path('', views.TransactionListView.as_view(), name='transaction-list'),
    path('<uuid:pk>/', views.TransactionDetailView.as_view(), name='transaction-detail'),
    path('deposit/', views.deposit_view, name='transaction-deposit'),
    path('withdraw/', views.withdraw_view, name='transaction-withdraw'),
    path('transfer/', views.transfer_view, name='transaction-transfer'),
    path('transfer/preview/', views.transfer_preview_view, name='transaction-transfer-preview'),
    path('transfer/send-otp/', views.transfer_send_otp_view, name='transaction-transfer-send-otp'),
    path(
        'regulated-sessions/intl/start/',
        regulated_views.regulated_intl_session_start,
        name='regulated-intl-session-start',
    ),
    path(
        'regulated-sessions/<uuid:session_id>/',
        regulated_views.regulated_session_detail,
        name='regulated-session-detail',
    ),
    path(
        'regulated-sessions/<uuid:session_id>/complete-transfer/',
        regulated_views.regulated_session_complete_transfer,
        name='regulated-session-complete-transfer',
    ),
    path(
        'regulated-sessions/<uuid:session_id>/lines/<uuid:line_id>/charge-send-otp/',
        regulated_views.regulated_line_charge_send_otp,
        name='regulated-line-charge-send-otp',
    ),
    path(
        'regulated-sessions/<uuid:session_id>/lines/<uuid:line_id>/verify-otp/',
        regulated_views.regulated_line_verify_otp,
        name='regulated-line-verify-otp',
    ),
    path('fees/', views.TransactionFeeListView.as_view(), name='transaction-fees'),
    path('exchange-rates/', views.ExchangeRateListView.as_view(), name='exchange-rates'),
]
