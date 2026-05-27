from rest_framework import serializers

from .models import CardIssuance, CardProductConfig


class CardProductConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = CardProductConfig
        fields = [
            'id',
            'account_type',
            'card_tier',
            'issue_fee',
            'monthly_spending_limit',
            'is_active',
            'updated_at',
        ]
        read_only_fields = ['id', 'account_type', 'updated_at']


class CardIssuanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CardIssuance
        fields = [
            'id',
            'account',
            'card_tier',
            'status',
            'issue_fee',
            'monthly_spending_limit',
            'requested_at',
            'paid_at',
        ]
        read_only_fields = [
            'id',
            'account',
            'card_tier',
            'status',
            'issue_fee',
            'monthly_spending_limit',
            'requested_at',
            'paid_at',
        ]
