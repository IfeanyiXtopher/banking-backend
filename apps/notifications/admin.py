from django.contrib import admin
from .models import Notification, NotificationPreference


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'event_type', 'subject', 'is_read', 'sent_at', 'email_status']
    list_filter = ['event_type', 'is_read', 'email_status']
    search_fields = ['user__email', 'subject']


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'transaction_alerts', 'low_balance_alerts', 'loan_alerts']
