from django.contrib import admin
from .models import Statement


@admin.register(Statement)
class StatementAdmin(admin.ModelAdmin):
    list_display = ['account', 'period_start', 'period_end', 'generated_at']
    list_filter = ['is_paperless']
    search_fields = ['account__account_number']
