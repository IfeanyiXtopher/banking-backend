# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='account',
            name='account_type',
            field=models.CharField(
                choices=[
                    ('CHECKING', 'Checking'),
                    ('SAVINGS', 'Savings'),
                    ('BUSINESS', 'Business'),
                    ('FIXED_TERM', 'Fixed deposit'),
                    ('CREDIT', 'Credit'),
                ],
                default='CHECKING',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='account',
            name='iban',
            field=models.CharField(blank=True, max_length=34, null=True, unique=True),
        ),
    ]
