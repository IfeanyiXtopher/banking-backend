from django.urls import path

from . import views

urlpatterns = [
    path('summary/', views.card_summary, name='card-summary'),
    path('request/', views.request_card, name='card-request'),
    path('request-replacement/', views.request_card_replacement_view, name='card-request-replacement'),
    path('issuances/<uuid:issuance_id>/pay/', views.pay_card_fee, name='card-pay-fee'),
]
