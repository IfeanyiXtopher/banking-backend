from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0013_alter_regulatedtransfersessionline_fee_line_cascade'),
    ]

    operations = [
        migrations.AddField(
            model_name='compliancefeeline',
            name='customer_message',
            field=models.TextField(
                blank=True,
                default='',
                help_text='Shown to the customer during verification (loan payout or compliance modal).',
            ),
        ),
    ]
