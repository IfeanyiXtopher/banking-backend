from django.contrib import admin
from .models import SupportTicket, TicketMessage


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ['ticket_number', 'customer', 'subject', 'status', 'priority', 'assigned_to', 'created_at']
    list_filter = ['status', 'priority']
    search_fields = ['ticket_number', 'customer__email', 'subject']


@admin.register(TicketMessage)
class TicketMessageAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'author', 'created_at', 'is_internal_note']
    list_filter = ['is_internal_note']
