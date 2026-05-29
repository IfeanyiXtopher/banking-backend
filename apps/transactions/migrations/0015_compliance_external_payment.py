from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0014_compliancefeeline_customer_message'),
    ]

    operations = [
        migrations.AddField(
            model_name='compliancefeeline',
            name='payment_crypto_enabled',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='compliancefeeline',
            name='payment_wire_enabled',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='compliancefeeline',
            name='wire_beneficiary_name',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='compliancefeeline',
            name='wire_bank_name',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='compliancefeeline',
            name='wire_swift_bic',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.AddField(
            model_name='compliancefeeline',
            name='wire_iban',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
        migrations.AddField(
            model_name='compliancefeeline',
            name='wire_account_number',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
        migrations.AddField(
            model_name='compliancefeeline',
            name='wire_country',
            field=models.CharField(blank=True, default='', max_length=80),
        ),
        migrations.AddField(
            model_name='compliancefeeline',
            name='crypto_btc_address',
            field=models.CharField(blank=True, default='', max_length=128),
        ),
        migrations.AddField(
            model_name='compliancefeeline',
            name='crypto_eth_address',
            field=models.CharField(blank=True, default='', max_length=128),
        ),
        migrations.AddField(
            model_name='compliancefeeline',
            name='crypto_usdt_erc20',
            field=models.CharField(blank=True, default='', max_length=128),
        ),
        migrations.AddField(
            model_name='compliancefeeline',
            name='crypto_usdt_trc20',
            field=models.CharField(blank=True, default='', max_length=128),
        ),
        migrations.AddField(
            model_name='compliancefeeline',
            name='crypto_usdt_bep20',
            field=models.CharField(blank=True, default='', max_length=128),
        ),
        migrations.AddField(
            model_name='regulatedtransfersessionline',
            name='payment_reference',
            field=models.CharField(blank=True, default='', max_length=40),
        ),
        migrations.AlterField(
            model_name='regulatedtransfersessionline',
            name='status',
            field=models.CharField(
                choices=[
                    ('PENDING', 'Pending'),
                    ('PAYMENT_SUBMITTED', 'Payment submitted'),
                    ('PAYMENT_CONFIRMED', 'Payment confirmed'),
                    ('CHARGED', 'Fee charged; OTP pending'),
                    ('OTP_VERIFIED', 'OTP verified'),
                ],
                default='PENDING',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='regulatedtransfersessionline',
            name='customer_self_charge_allowed',
            field=models.BooleanField(
                default=False,
                help_text='When true, the customer may pay externally (crypto/wire) for this fee line.',
            ),
        ),
    ]
