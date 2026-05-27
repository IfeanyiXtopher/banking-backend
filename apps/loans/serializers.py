from rest_framework import serializers
from .models import LoanProduct, LoanApplication, LoanAccount, RepaymentSchedule
from .admin_serializers import LoanProductPublicSerializer as LoanProductSerializer


class LoanApplicationSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    applicant_name = serializers.CharField(source='applicant.full_name', read_only=True)

    class Meta:
        model = LoanApplication
        fields = [
            'id', 'product', 'product_name', 'applicant_name',
            'requested_amount', 'term_months', 'purpose', 'status',
            'review_notes', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'status', 'review_notes', 'created_at', 'updated_at', 'applicant_name']


class LoanApplicationCreateSerializer(serializers.ModelSerializer):
    """Accept either `product` (UUID) or `loan_type` (e.g. PERSONAL) to resolve an active product."""

    product = serializers.PrimaryKeyRelatedField(
        queryset=LoanProduct.objects.all(),
        required=False,
        allow_null=True,
    )
    loan_type = serializers.ChoiceField(
        choices=LoanProduct.LoanType.choices,
        required=False,
        write_only=True,
    )

    class Meta:
        model = LoanApplication
        fields = ['product', 'loan_type', 'requested_amount', 'term_months', 'purpose']

    def validate(self, attrs):
        loan_type = attrs.pop('loan_type', None)
        product = attrs.get('product')

        if product is None and loan_type:
            product = LoanProduct.objects.filter(loan_type=loan_type, is_active=True).first()
            if not product:
                raise serializers.ValidationError(
                    {'loan_type': 'No active loan product is configured for this loan type.'}
                )
            attrs['product'] = product
        elif product is None:
            raise serializers.ValidationError('Either product or loan_type is required.')

        product = attrs['product']
        if not product.is_active:
            raise serializers.ValidationError('This loan product is not available.')
        if attrs['requested_amount'] < product.min_amount or attrs['requested_amount'] > product.max_amount:
            raise serializers.ValidationError(
                f'Amount must be between {product.min_amount} and {product.max_amount}.'
            )
        if attrs['term_months'] < product.min_term_months or attrs['term_months'] > product.max_term_months:
            raise serializers.ValidationError(
                f'Term must be between {product.min_term_months} and {product.max_term_months} months.'
            )
        return attrs


class RepaymentScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = RepaymentSchedule
        fields = [
            'id', 'installment_number', 'due_date',
            'principal_amount', 'interest_amount', 'total_amount',
            'paid_amount', 'status', 'paid_at',
        ]


class LoanAccountSerializer(serializers.ModelSerializer):
    schedule = RepaymentScheduleSerializer(many=True, read_only=True)
    product_name = serializers.CharField(source='application.product.name', read_only=True)

    class Meta:
        model = LoanAccount
        fields = [
            'id', 'product_name', 'principal_amount', 'outstanding_balance',
            'interest_rate', 'term_months', 'monthly_payment', 'status',
            'disbursed_at', 'next_payment_due', 'schedule', 'created_at',
        ]


class LoanPaymentSerializer(serializers.Serializer):
    loan_account_id = serializers.UUIDField()
    account_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=18, decimal_places=2, min_value='0.01')
