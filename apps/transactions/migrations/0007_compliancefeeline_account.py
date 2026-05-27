# Per-account compliance fee lines (override global lines for a bank account).

import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        ('transactions', '0006_regulatedtransfersession_transfer_transaction'),
    ]

    operations = [
        migrations.AddField(
            model_name='compliancefeeline',
            name='account',
            field=models.ForeignKey(
                blank=True,
                help_text='When set, this line applies only to that account and replaces global lines for it.',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='compliance_fee_lines',
                to='accounts.account',
            ),
        ),
        migrations.AlterField(
            model_name='compliancefeeline',
            name='code',
            field=models.SlugField(
                help_text='Stable key for reporting; unique per scope (global or account).',
                max_length=40,
            ),
        ),
        migrations.AddConstraint(
            model_name='compliancefeeline',
            constraint=models.UniqueConstraint(
                condition=Q(('account__isnull', True)),
                fields=('code',),
                name='uniq_compliance_fee_line_global_code',
            ),
        ),
        migrations.AddConstraint(
            model_name='compliancefeeline',
            constraint=models.UniqueConstraint(
                condition=Q(('account__isnull', False)),
                fields=('account', 'code'),
                name='uniq_compliance_fee_line_account_code',
            ),
        ),
    ]
