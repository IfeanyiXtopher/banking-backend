import uuid
from decimal import Decimal

from django.db import migrations, models


def seed_default_settings(apps, schema_editor):
    PaymentFeeSettings = apps.get_model('payments', 'PaymentFeeSettings')
    PaymentFeeSettings.objects.get_or_create(
        pk=1,
        defaults={'default_management_fee': Decimal('0.99')},
    )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='PaymentFeeSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'default_management_fee',
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal('0.99'),
                        help_text='Applied when no override exists for a biller.',
                        max_digits=10,
                    ),
                ),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Payment fee settings',
            },
        ),
        migrations.CreateModel(
            name='PaymentManagementFeeOverride',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('service_id', models.CharField(db_index=True, max_length=64)),
                ('biller_id', models.CharField(db_index=True, max_length=64)),
                (
                    'biller_label',
                    models.CharField(
                        blank=True,
                        help_text='Optional display name for admin lists.',
                        max_length=255,
                    ),
                ),
                ('management_fee', models.DecimalField(decimal_places=2, max_digits=10)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['service_id', 'biller_id'],
            },
        ),
        migrations.AddConstraint(
            model_name='paymentmanagementfeeoverride',
            constraint=models.UniqueConstraint(
                fields=('service_id', 'biller_id'),
                name='uniq_payment_mgmt_fee_service_biller',
            ),
        ),
        migrations.RunPython(seed_default_settings, noop_reverse),
    ]
