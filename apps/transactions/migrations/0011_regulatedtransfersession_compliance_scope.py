from django.db import migrations, models


def backfill_compliance_scope(apps, schema_editor):
    Session = apps.get_model('transactions', 'RegulatedTransferSession')
    Line = apps.get_model('transactions', 'RegulatedTransferSessionLine')
    for session in Session.objects.all().iterator():
        has_personal = Line.objects.filter(
            session_id=session.id,
            fee_line__user_id__isnull=False,
        ).exists()
        scope = 'PERSONAL' if has_personal else 'GLOBAL'
        Session.objects.filter(pk=session.pk).update(compliance_scope=scope)


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0010_regulatedtransfersessionline_customer_self_charge_allowed'),
    ]

    operations = [
        migrations.AddField(
            model_name='regulatedtransfersession',
            name='compliance_scope',
            field=models.CharField(
                choices=[('GLOBAL', 'Global'), ('PERSONAL', 'Personal (per user)')],
                default='GLOBAL',
                max_length=20,
            ),
        ),
        migrations.RunPython(backfill_compliance_scope, migrations.RunPython.noop),
    ]
