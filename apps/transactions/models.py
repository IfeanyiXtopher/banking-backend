import uuid
from django.db import models
from django.conf import settings


class TransactionFee(models.Model):
    class FeeType(models.TextChoices):
        TRANSFER_LOCAL = 'TRANSFER_LOCAL', 'Local Transfer'
        TRANSFER_INTERNATIONAL = 'TRANSFER_INTERNATIONAL', 'International Transfer'
        WITHDRAWAL = 'WITHDRAWAL', 'Withdrawal'
        DEPOSIT = 'DEPOSIT', 'Deposit'
        SERVICE_CHARGE = 'SERVICE_CHARGE', 'Service Charge'

    fee_type = models.CharField(max_length=40, choices=FeeType.choices, unique=True)
    flat_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    percentage = models.DecimalField(max_digits=5, decimal_places=4, default=0, help_text='e.g. 0.0150 = 1.5%')
    min_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='0 = no cap')
    is_active = models.BooleanField(default=True)
    requires_otp = models.BooleanField(
        default=False,
        help_text='When true, customer must verify an email OTP before this transaction completes.',
    )
    charge_upfront = models.BooleanField(
        default=True,
        help_text='When true, fee is added on top of the principal (sender pays amount + fee). '
        'When false, fee is deducted from the recipient credit (same-currency transfers only).',
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.fee_type} fee'

    def calculate(self, amount):
        if not self.is_active:
            return 0
        fee = self.flat_amount + (amount * self.percentage)
        fee = max(fee, self.min_amount)
        if self.max_amount > 0:
            fee = min(fee, self.max_amount)
        return round(fee, 2)


class ExchangeRate(models.Model):
    from_currency = models.CharField(max_length=3)
    to_currency = models.CharField(max_length=3)
    rate = models.DecimalField(max_digits=18, decimal_places=8)
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['from_currency', 'to_currency']
        ordering = ['-fetched_at']

    def __str__(self):
        return f'{self.from_currency}/{self.to_currency} = {self.rate}'


class Transaction(models.Model):
    class TransactionType(models.TextChoices):
        DEPOSIT = 'DEPOSIT', 'Deposit'
        WITHDRAWAL = 'WITHDRAWAL', 'Withdrawal'
        TRANSFER_INTERNAL = 'TRANSFER_INTERNAL', 'Internal Transfer'
        TRANSFER_EXTERNAL = 'TRANSFER_EXTERNAL', 'External Transfer'
        TRANSFER_INTERNATIONAL = 'TRANSFER_INTERNATIONAL', 'International Transfer'
        LOAN_DISBURSEMENT = 'LOAN_DISBURSEMENT', 'Loan Disbursement'
        LOAN_PAYMENT = 'LOAN_PAYMENT', 'Loan Payment'
        FEE = 'FEE', 'Fee'
        INTEREST = 'INTEREST', 'Interest'
        REVERSAL = 'REVERSAL', 'Reversal'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'
        REVERSED = 'REVERSED', 'Reversed'
        FLAGGED = 'FLAGGED', 'Flagged'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference_number = models.CharField(max_length=20, unique=True, blank=True)
    transaction_type = models.CharField(max_length=30, choices=TransactionType.choices)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    from_account = models.ForeignKey(
        'accounts.Account', null=True, blank=True,
        on_delete=models.PROTECT, related_name='debits',
    )
    to_account = models.ForeignKey(
        'accounts.Account', null=True, blank=True,
        on_delete=models.PROTECT, related_name='credits',
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    description = models.CharField(max_length=255, blank=True)
    fee_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    exchange_rate = models.DecimalField(max_digits=18, decimal_places=8, default=1)
    idempotency_key = models.CharField(max_length=128, unique=True, blank=True, null=True)
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='initiated_transactions',
    )
    reversed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.PROTECT,
        related_name='reversed_transactions',
    )
    original_transaction = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name='reversals',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['from_account', '-created_at']),
            models.Index(fields=['to_account', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['transaction_type']),
        ]

    def __str__(self):
        return f'{self.transaction_type} - {self.amount} {self.currency} [{self.status}]'

    def save(self, *args, **kwargs):
        if not self.reference_number:
            import random
            import string
            self.reference_number = 'TXN' + ''.join(random.choices(string.digits, k=10))
        super().save(*args, **kwargs)


from .regulated_models import ComplianceFeeLine, RegulatedTransferSession, RegulatedTransferSessionLine  # noqa: E402, F401
