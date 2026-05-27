from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0004_rename_trans_reg_ses_user_status_idx_transaction_user_id_768e58_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='regulatedtransfersession',
            name='international_wire_details',
            field=models.JSONField(blank=True, null=True, help_text='Normalized beneficiary/bank snapshot at session start.'),
        ),
    ]
