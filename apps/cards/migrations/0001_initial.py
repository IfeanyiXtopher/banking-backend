import uuid
from decimal import Decimal

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def seed_card_products(apps, schema_editor):
    CardProductConfig = apps.get_model('cards', 'CardProductConfig')
    rows = [
        ('CHECKING', 'STANDARD', Decimal('25.00'), Decimal('8000.00')),
        ('SAVINGS', 'CREDIT_LINE', Decimal('15.00'), Decimal('5000.00')),
        ('BUSINESS', 'PREMIUM', Decimal('49.00'), Decimal('150000.00')),
        ('FIXED_TERM', 'STANDARD', Decimal('0.00'), Decimal('3000.00')),
        ('CREDIT', 'PREMIUM', Decimal('99.00'), Decimal('200000.00')),
    ]
    for account_type, card_tier, issue_fee, monthly_spending_limit in rows:
        CardProductConfig.objects.update_or_create(
            account_type=account_type,
            defaults={
                'card_tier': card_tier,
                'issue_fee': issue_fee,
                'monthly_spending_limit': monthly_spending_limit,
                'is_active': True,
            },
        )


def unseed(apps, schema_editor):
    CardProductConfig = apps.get_model('cards', 'CardProductConfig')
    CardProductConfig.objects.all().delete()


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0006_account_unique_type_per_owner'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CardProductConfig',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    'account_type',
                    models.CharField(
                        choices=[
                            ('CHECKING', 'Checking'),
                            ('SAVINGS', 'Savings'),
                            ('BUSINESS', 'Business'),
                            ('FIXED_TERM', 'Fixed deposit'),
                            ('CREDIT', 'Credit'),
                        ],
                        max_length=20,
                        unique=True,
                    ),
                ),
                (
                    'card_tier',
                    models.CharField(
                        choices=[
                            ('STANDARD', 'Standard (Visa Debit)'),
                            ('PREMIUM', 'Premium'),
                            ('CREDIT_LINE', 'Credit-line design'),
                        ],
                        default='STANDARD',
                        max_length=20,
                    ),
                ),
                ('issue_fee', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=12)),
                (
                    'monthly_spending_limit',
                    models.DecimalField(decimal_places=2, default=Decimal('5000'), max_digits=18),
                ),
                ('is_active', models.BooleanField(default=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['account_type'],
            },
        ),
        migrations.CreateModel(
            name='CardIssuance',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    'card_tier',
                    models.CharField(
                        choices=[
                            ('STANDARD', 'Standard (Visa Debit)'),
                            ('PREMIUM', 'Premium'),
                            ('CREDIT_LINE', 'Credit-line design'),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    'status',
                    models.CharField(
                        choices=[('PENDING_PAYMENT', 'Pending payment'), ('ACTIVE', 'Active')],
                        default='PENDING_PAYMENT',
                        max_length=24,
                    ),
                ),
                ('issue_fee', models.DecimalField(decimal_places=2, max_digits=12)),
                ('monthly_spending_limit', models.DecimalField(decimal_places=2, max_digits=18)),
                ('requested_at', models.DateTimeField(auto_now_add=True)),
                ('paid_at', models.DateTimeField(blank=True, null=True)),
                (
                    'account',
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='card_issuance',
                        to='accounts.account',
                    ),
                ),
                (
                    'owner',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='card_issuances',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'ordering': ['-requested_at'],
            },
        ),
        migrations.RunPython(seed_card_products, unseed),
    ]
