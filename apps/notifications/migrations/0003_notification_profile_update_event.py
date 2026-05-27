# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0002_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='event_type',
            field=models.CharField(
                choices=[
                    ('TRANSACTION', 'Transaction'),
                    ('LOW_BALANCE', 'Low Balance'),
                    ('LOAN_APPROVED', 'Loan Approved'),
                    ('LOAN_REJECTED', 'Loan Rejected'),
                    ('LOAN_PAYMENT_DUE', 'Loan Payment Due'),
                    ('PASSWORD_RESET', 'Password Reset'),
                    ('MFA_OTP', 'MFA OTP'),
                    ('REGISTRATION', 'Registration'),
                    ('STATEMENT_READY', 'Statement Ready'),
                    ('SUPPORT_UPDATE', 'Support Update'),
                    ('SECURITY_ALERT', 'Security Alert'),
                    ('PROFILE_UPDATE_APPROVED', 'Profile update approved'),
                ],
                max_length=30,
            ),
        ),
    ]
