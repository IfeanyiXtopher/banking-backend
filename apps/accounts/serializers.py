from rest_framework import serializers
from .models import Account, Currency


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ['id', 'code', 'name', 'symbol']


class AccountSerializer(serializers.ModelSerializer):
    currency = CurrencySerializer(read_only=True)
    currency_id = serializers.PrimaryKeyRelatedField(
        queryset=Currency.objects.filter(is_active=True),
        source='currency',
        write_only=True,
    )
    owner_name = serializers.CharField(source='owner.full_name', read_only=True)

    class Meta:
        model = Account
        fields = [
            'id', 'account_number', 'iban', 'account_type', 'currency', 'currency_id',
            'balance', 'available_balance', 'status', 'nickname', 'is_primary',
            'interest_rate', 'credit_limit', 'owner_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'account_number', 'iban', 'balance', 'available_balance',
            'created_at', 'updated_at', 'owner_name', 'is_primary',
        ]


class AccountCreateSerializer(serializers.ModelSerializer):
    currency_id = serializers.PrimaryKeyRelatedField(
        queryset=Currency.objects.filter(is_active=True),
        source='currency',
    )

    class Meta:
        model = Account
        fields = ['account_type', 'currency_id', 'nickname']

    def validate(self, attrs):
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None
        if user and user.is_authenticated:
            account_type = attrs.get('account_type')
            # Multiple SAVINGS accounts are allowed (each goal is its own savings account).
            if account_type and account_type != Account.AccountType.SAVINGS:
                if Account.objects.filter(owner=user, account_type=account_type).exists():
                    raise serializers.ValidationError(
                        {
                            'account_type': (
                                'You already have an account of this type. '
                                'Each product type can only be opened once per customer.'
                            ),
                        },
                    )
        return attrs


class AccountPartialUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['nickname', 'is_primary']

    def validate_is_primary(self, value):
        if value is False:
            raise serializers.ValidationError(
                'You cannot clear the primary flag here. Open another account and set it as primary.',
            )
        return value


class AccountStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['status']

    def validate_status(self, value):
        if value not in [Account.Status.ACTIVE, Account.Status.FROZEN, Account.Status.CLOSED]:
            raise serializers.ValidationError('Invalid status.')
        return value
