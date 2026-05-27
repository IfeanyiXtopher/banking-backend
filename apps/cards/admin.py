from django.contrib import admin

from .models import CardIssuance, CardProductConfig


@admin.register(CardProductConfig)
class CardProductConfigAdmin(admin.ModelAdmin):
    list_display = ['account_type', 'card_tier', 'issue_fee', 'monthly_spending_limit', 'is_active', 'updated_at']
    list_filter = ['is_active', 'card_tier']


@admin.register(CardIssuance)
class CardIssuanceAdmin(admin.ModelAdmin):
    list_display = ['id', 'account', 'owner', 'status', 'issue_fee', 'monthly_spending_limit', 'requested_at', 'paid_at']
    list_filter = ['status', 'card_tier']
    raw_id_fields = ['account', 'owner']
