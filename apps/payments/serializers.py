from decimal import Decimal

from rest_framework import serializers

from .models import PaymentFeeSettings, PaymentManagementFeeOverride


class PaymentFeeSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentFeeSettings
        fields = ['id', 'default_management_fee', 'updated_at']
        read_only_fields = ['id', 'updated_at']


class PaymentManagementFeeOverrideSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentManagementFeeOverride
        fields = ['id', 'service_id', 'biller_id', 'biller_label', 'management_fee', 'updated_at']
        read_only_fields = ['id', 'updated_at']

    def validate_management_fee(self, value: Decimal) -> Decimal:
        if value < 0:
            raise serializers.ValidationError('Fee cannot be negative.')
        return value


class BillPaySerializer(serializers.Serializer):
    account_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=Decimal('0.01'))
    service_id = serializers.CharField(max_length=64)
    biller_id = serializers.CharField(max_length=64)
    description = serializers.CharField(max_length=4000)
    idempotency_key = serializers.CharField(max_length=128, required=False, allow_blank=True)

    def validate_description(self, value: str) -> str:
        """Transaction.description is max 255; tolerate long client strings without hard-failing."""
        value = (value or '').strip()
        if len(value) > 255:
            return value[:252] + '...'
        return value
