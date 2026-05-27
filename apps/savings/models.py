import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models


class SavingsGoal(models.Model):
    """Customer savings goal — not a separate bank account; funds may live in a shared goals pocket."""

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        CANCELLED = 'CANCELLED', 'Cancelled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='savings_goals',
    )
    title = models.CharField(max_length=100)
    category = models.CharField(max_length=20, default='other')
    target_amount = models.DecimalField(max_digits=18, decimal_places=2)
    target_date = models.DateField(null=True, blank=True)
    saved_balance = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0'))
    rules = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} ({self.owner_id})'
