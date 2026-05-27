import uuid
from decimal import Decimal

from django.db import models


class PaymentFeeSettings(models.Model):
    """Singleton row (pk=1): default bill-payment management fee when no per-biller override exists."""

    default_management_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.99'),
        help_text='Applied when no override exists for a biller.',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Payment fee settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls) -> 'PaymentFeeSettings':
        obj, _ = cls.objects.get_or_create(
            pk=1,
            defaults={'default_management_fee': Decimal('0.99')},
        )
        return obj


class PaymentManagementFeeOverride(models.Model):
    """Per (service, biller) management fee in account currency (USD)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service_id = models.CharField(max_length=64, db_index=True)
    biller_id = models.CharField(max_length=64, db_index=True)
    biller_label = models.CharField(max_length=255, blank=True, help_text='Optional display name for admin lists.')
    management_fee = models.DecimalField(max_digits=10, decimal_places=2)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['service_id', 'biller_id']
        constraints = [
            models.UniqueConstraint(fields=['service_id', 'biller_id'], name='uniq_payment_mgmt_fee_service_biller'),
        ]

    def __str__(self):
        return f'{self.service_id}/{self.biller_id} → {self.management_fee}'
