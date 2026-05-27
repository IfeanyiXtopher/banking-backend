# Per-user compliance fee lines (replaces per-account override).

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q


def copy_account_owner_to_user(apps, schema_editor):
    ComplianceFeeLine = apps.get_model('transactions', 'ComplianceFeeLine')
    for line in ComplianceFeeLine.objects.filter(account__isnull=False).select_related('account'):
        line.user_id = line.account.owner_id
        line.save(update_fields=['user_id'])


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('transactions', '0007_compliancefeeline_account'),
    ]

    operations = [
        migrations.AddField(
            model_name='compliancefeeline',
            name='user',
            field=models.ForeignKey(
                blank=True,
                help_text='When set, this line applies only to that customer and replaces global lines for them.',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='compliance_fee_lines',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(copy_account_owner_to_user, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name='compliancefeeline',
            name='uniq_compliance_fee_line_global_code',
        ),
        migrations.RemoveConstraint(
            model_name='compliancefeeline',
            name='uniq_compliance_fee_line_account_code',
        ),
        migrations.RemoveField(
            model_name='compliancefeeline',
            name='account',
        ),
        migrations.AddConstraint(
            model_name='compliancefeeline',
            constraint=models.UniqueConstraint(
                condition=Q(user__isnull=True),
                fields=('code',),
                name='uniq_compliance_fee_line_global_code',
            ),
        ),
        migrations.AddConstraint(
            model_name='compliancefeeline',
            constraint=models.UniqueConstraint(
                condition=Q(user__isnull=False),
                fields=('user', 'code'),
                name='uniq_compliance_fee_line_user_code',
            ),
        ),
    ]
