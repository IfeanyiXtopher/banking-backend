from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='transactionfee',
            name='requires_otp',
            field=models.BooleanField(
                default=False,
                help_text='When true, customer must verify an email OTP before this transaction completes.',
            ),
        ),
        migrations.AddField(
            model_name='transactionfee',
            name='charge_upfront',
            field=models.BooleanField(
                default=True,
                help_text='When true, fee is added on top of the transfer amount (sender pays amount + fee). '
                'When false, fee is deducted from the amount the recipient receives (same-currency only).',
            ),
        ),
    ]
