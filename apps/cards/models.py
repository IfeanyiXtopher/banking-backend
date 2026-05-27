import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.accounts.models import Account


class CardProductConfig(models.Model):
    """
    Admin-defined issuance fee and monthly spending cap per account product.
    One active row per account_type (enforced by unique constraint).
    """

    class CardTier(models.TextChoices):
        STANDARD = 'STANDARD', 'Standard (Visa Debit)'
        PREMIUM = 'PREMIUM', 'Premium'
        CREDIT_LINE = 'CREDIT_LINE', 'Credit-line design'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account_type = models.CharField(max_length=20, choices=Account.AccountType.choices, unique=True)
    card_tier = models.CharField(max_length=20, choices=CardTier.choices, default=CardTier.STANDARD)
    issue_fee = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    monthly_spending_limit = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('5000'))
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['account_type']

    def __str__(self):
        return f'{self.account_type} card · fee {self.issue_fee} · cap {self.monthly_spending_limit}'


class CardIssuance(models.Model):
    """One physical/digital card program enrollment per account (request → pay fee → active)."""

    class Status(models.TextChoices):
        PENDING_PAYMENT = 'PENDING_PAYMENT', 'Pending payment'
        ACTIVE = 'ACTIVE', 'Active'
        TERMINATED = 'TERMINATED', 'Terminated'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name='card_issuances',
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_card_issuances',
    )
    card_tier = models.CharField(max_length=20, choices=CardProductConfig.CardTier.choices)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.PENDING_PAYMENT)
    issue_fee = models.DecimalField(max_digits=12, decimal_places=2)
    monthly_spending_limit = models.DecimalField(max_digits=18, decimal_places=2)
    requested_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-requested_at']

    def __str__(self):
        return f'{self.account_id} {self.status}'
