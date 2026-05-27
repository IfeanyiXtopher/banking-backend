from django.contrib import admin
from .models import Transaction, TransactionFee, ExchangeRate


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['reference_number', 'transaction_type', 'amount', 'currency', 'status', 'from_account', 'to_account', 'created_at']
    list_filter = ['transaction_type', 'status', 'currency']
    search_fields = ['reference_number', 'description', 'from_account__account_number', 'to_account__account_number']
    readonly_fields = ['id', 'reference_number', 'created_at', 'completed_at']


@admin.register(TransactionFee)
class TransactionFeeAdmin(admin.ModelAdmin):
    list_display = ['fee_type', 'flat_amount', 'percentage', 'min_amount', 'max_amount', 'is_active']
    list_filter = ['is_active']


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ['from_currency', 'to_currency', 'rate', 'fetched_at']
    ordering = ['from_currency', 'to_currency']
