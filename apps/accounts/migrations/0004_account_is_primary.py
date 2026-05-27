# Generated manually

from django.db import migrations, models


def backfill_primary_account(apps, schema_editor):
    Account = apps.get_model('accounts', 'Account')
    owner_ids = Account.objects.values_list('owner_id', flat=True).distinct()
    for owner_id in owner_ids:
        qs = Account.objects.filter(owner_id=owner_id).order_by('created_at')
        first_pk = qs.values_list('pk', flat=True).first()
        if first_pk is None:
            continue
        Account.objects.filter(owner_id=owner_id).exclude(pk=first_pk).update(is_primary=False)
        Account.objects.filter(pk=first_pk).update(is_primary=True)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_account_iban_and_types'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='is_primary',
            field=models.BooleanField(
                default=False,
                help_text='Default account shown on login; one per customer.',
            ),
        ),
        migrations.RunPython(backfill_primary_account, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='account',
            constraint=models.UniqueConstraint(
                condition=models.Q(('is_primary', True)),
                fields=('owner',),
                name='unique_primary_account_per_owner',
            ),
        ),
    ]
