from django.contrib import admin
from .models import Account, Currency


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'symbol', 'is_active']
    list_filter = ['is_active']


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['account_number', 'owner', 'account_type', 'currency', 'balance', 'status', 'created_at']
    list_filter = ['account_type', 'status', 'currency']
    search_fields = ['account_number', 'owner__email', 'owner__full_name']
    readonly_fields = ['id', 'account_number', 'created_at', 'updated_at']
