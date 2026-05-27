import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cards', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='cardissuance',
            name='owner',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='owned_card_issuances',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name='cardissuance',
            name='status',
            field=models.CharField(
                choices=[
                    ('PENDING_PAYMENT', 'Pending payment'),
                    ('ACTIVE', 'Active'),
                    ('TERMINATED', 'Terminated'),
                ],
                default='PENDING_PAYMENT',
                max_length=24,
            ),
        ),
        migrations.AlterField(
            model_name='cardissuance',
            name='account',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='card_issuances',
                to='accounts.account',
            ),
        ),
    ]
