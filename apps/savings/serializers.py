from decimal import Decimal

from rest_framework import serializers

from .models import SavingsGoal

_SERVER_AUTOSAVE_META_KEYS = frozenset(
    {'weekly_contrib_week', 'roundup_week', 'smart_month', 'insufficient_alert_day'}
)


class SavingsGoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavingsGoal
        fields = [
            'id', 'title', 'category', 'target_amount', 'target_date',
            'saved_balance', 'rules', 'status', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'saved_balance', 'status', 'created_at', 'updated_at']


class SavingsGoalCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavingsGoal
        fields = ['title', 'category', 'target_amount', 'target_date', 'rules']

    def validate_target_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Target amount must be positive.')
        return value


class SavingsGoalUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavingsGoal
        fields = ['title', 'category', 'target_amount', 'target_date', 'rules']

    def validate_target_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Target amount must be positive.')
        return value

    def update(self, instance, validated_data):
        rules = validated_data.get('rules')
        if isinstance(rules, dict):
            old_rules = dict(instance.rules or {})
            old_meta = old_rules.get('autosave_meta')
            old_meta = old_meta if isinstance(old_meta, dict) else {}
            new_rules = dict(rules)
            inc = new_rules.get('autosave_meta')
            inc = inc if isinstance(inc, dict) else {}
            preserved = {k: v for k, v in old_meta.items() if k in _SERVER_AUTOSAVE_META_KEYS}
            new_rules['autosave_meta'] = {**inc, **preserved}
            validated_data['rules'] = new_rules
        return super().update(instance, validated_data)


class SavingsGoalAllocateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=Decimal('0.01'))
