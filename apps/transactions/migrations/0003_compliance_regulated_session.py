# Generated manually

from django.db import migrations, models
import django.db.models.deletion
import uuid
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('accounts', '0002_initial'),
        ('loans', '0003_seed_default_loan_products'),
        ('transactions', '0002_initial'),
        ('transactions', '0002_transactionfee_otp_upfront'),
    ]

    operations = [
        migrations.CreateModel(
            name='ComplianceFeeLine',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=120)),
                ('code', models.SlugField(help_text='Stable key for reporting.', max_length=40, unique=True)),
                ('applies_to', models.CharField(
                    choices=[
                        ('INTERNATIONAL_TRANSFER', 'International transfer'),
                        ('LOAN_PAYOUT', 'Loan payout'),
                        ('BOTH', 'Both'),
                    ],
                    default='INTERNATIONAL_TRANSFER',
                    max_length=30,
                )),
                ('min_principal_threshold', models.DecimalField(
                    decimal_places=2,
                    default=0,
                    help_text='Line applies when principal amount is >= this value (0 = always).',
                    max_digits=18,
                )),
                ('sort_order', models.PositiveSmallIntegerField(default=0)),
                ('flat_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('percentage', models.DecimalField(decimal_places=4, default=0, help_text='e.g. 0.0150 = 1.5%', max_digits=5)),
                ('min_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('max_amount', models.DecimalField(decimal_places=2, default=0, help_text='0 = no cap', max_digits=10)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ['sort_order', 'name']},
        ),
        migrations.CreateModel(
            name='RegulatedTransferSession',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('flow', models.CharField(
                    choices=[
                        ('INTERNATIONAL_TRANSFER', 'International transfer'),
                        ('LOAN_PAYOUT', 'Loan payout'),
                    ],
                    max_length=40,
                )),
                ('status', models.CharField(
                    choices=[
                        ('PENDING', 'Pending'),
                        ('IN_PROGRESS', 'In progress'),
                        ('LINES_VERIFIED', 'All fees verified'),
                        ('COMPLETED', 'Completed'),
                        ('EXPIRED', 'Expired'),
                        ('CANCELLED', 'Cancelled'),
                    ],
                    default='PENDING',
                    max_length=30,
                )),
                ('principal_amount', models.DecimalField(decimal_places=2, max_digits=18)),
                ('transfer_type', models.CharField(blank=True, default='', max_length=40)),
                ('description', models.CharField(blank=True, max_length=255)),
                ('idempotency_key', models.CharField(blank=True, max_length=128, null=True, unique=True)),
                ('expires_at', models.DateTimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('from_account', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='regulated_sessions_debiting',
                    to='accounts.account',
                )),
                ('loan_application', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='regulated_payout_sessions',
                    to='loans.loanapplication',
                )),
                ('to_account', models.ForeignKey(
                    blank=True,
                    help_text='International transfer destination; null for loan payout until completion.',
                    null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='regulated_sessions_credit',
                    to='accounts.account',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='regulated_transfer_sessions',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.AddIndex(
            model_name='regulatedtransfersession',
            index=models.Index(fields=['user', 'status'], name='trans_reg_ses_user_status_idx'),
        ),
        migrations.CreateModel(
            name='RegulatedTransferSessionLine',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('sequence', models.PositiveSmallIntegerField()),
                ('amount', models.DecimalField(decimal_places=2, max_digits=18)),
                ('status', models.CharField(
                    choices=[
                        ('PENDING', 'Pending'),
                        ('CHARGED', 'Fee charged; OTP pending'),
                        ('OTP_VERIFIED', 'OTP verified'),
                    ],
                    default='PENDING',
                    max_length=20,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('fee_line', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='session_lines',
                    to='transactions.compliancefeeline',
                )),
                ('fee_transaction', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='regulated_fee_line',
                    to='transactions.transaction',
                )),
                ('session', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='lines',
                    to='transactions.regulatedtransfersession',
                )),
            ],
            options={'ordering': ['session', 'sequence']},
        ),
        migrations.AlterUniqueTogether(
            name='regulatedtransfersessionline',
            unique_together={('session', 'sequence')},
        ),
    ]
