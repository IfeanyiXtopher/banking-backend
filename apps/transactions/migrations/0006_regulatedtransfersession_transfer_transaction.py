from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0005_regulatedtransfersession_international_wire_details'),
    ]

    operations = [
        migrations.AddField(
            model_name='regulatedtransfersession',
            name='transfer_transaction',
            field=models.ForeignKey(
                blank=True,
                help_text='International transfer held as PENDING until compliance completes.',
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='regulated_transfer_session',
                to='transactions.transaction',
            ),
        ),
    ]
