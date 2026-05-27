from rest_framework import serializers
from .models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'event_type', 'subject', 'body', 'is_read', 'sent_at']
        read_only_fields = fields


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            'transaction_alerts', 'low_balance_alerts', 'low_balance_threshold',
            'loan_alerts', 'security_alerts', 'statement_alerts',
        ]
