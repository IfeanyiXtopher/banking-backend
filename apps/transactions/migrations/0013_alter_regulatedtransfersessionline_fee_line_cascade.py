import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0012_alter_regulatedtransfersession_compliance_scope'),
    ]

    operations = [
        migrations.AlterField(
            model_name='regulatedtransfersessionline',
            name='fee_line',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='session_lines',
                to='transactions.compliancefeeline',
            ),
        ),
    ]
