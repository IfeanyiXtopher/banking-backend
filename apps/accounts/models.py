import uuid
import random
import string
from django.db import models
from django.conf import settings


def generate_account_number():
    return ''.join(random.choices(string.digits, k=10))


class Currency(models.Model):
    code = models.CharField(max_length=3, unique=True)
    name = models.CharField(max_length=50)
    symbol = models.CharField(max_length=5)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'Currencies'
        ordering = ['code']

    def __str__(self):
        return f'{self.code} - {self.name}'


class Account(models.Model):
    class AccountType(models.TextChoices):
        CHECKING = 'CHECKING', 'Checking'
        SAVINGS = 'SAVINGS', 'Savings'
        BUSINESS = 'BUSINESS', 'Business'
        FIXED_TERM = 'FIXED_TERM', 'Fixed deposit'
        CREDIT = 'CREDIT', 'Credit'

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        FROZEN = 'FROZEN', 'Frozen'
        CLOSED = 'CLOSED', 'Closed'
        PENDING = 'PENDING', 'Pending'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='accounts',
    )
    account_number = models.CharField(max_length=20, unique=True, default=generate_account_number)
    iban = models.CharField(max_length=34, unique=True, null=True, blank=True)
    account_type = models.CharField(max_length=20, choices=AccountType.choices, default=AccountType.CHECKING)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name='accounts')
    balance = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    available_balance = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    nickname = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0)
    credit_limit = models.DecimalField(max_digits=18, decimal_places=2, default=0, help_text='For credit accounts')
    is_primary = models.BooleanField(
        default=False,
        help_text='Default account shown on login; one per customer.',
    )
    exclude_from_card_summary = models.BooleanField(
        default=False,
        help_text='Internal pooled account (e.g. savings goals pocket). Hidden from cards and account list.',
    )

    class Meta:
        ordering = ['-is_primary', '-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['owner'],
                condition=models.Q(is_primary=True),
                name='unique_primary_account_per_owner',
            ),
            models.UniqueConstraint(
                fields=['owner', 'account_type'],
                condition=models.Q(
                    account_type__in=[
                        'CHECKING',
                        'BUSINESS',
                        'FIXED_TERM',
                        'CREDIT',
                    ],
                ),
                name='unique_non_savings_account_type_per_owner',
            ),
        ]

    def __str__(self):
        return f'{self.account_type} - {self.account_number} ({self.owner.email})'

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE

    def can_debit(self, amount):
        return self.is_active and self.available_balance >= amount
