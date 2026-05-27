from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0009_alter_compliancefeeline_code'),
    ]

    operations = [
        migrations.AddField(
            model_name='regulatedtransfersessionline',
            name='customer_self_charge_allowed',
            field=models.BooleanField(
                default=False,
                help_text='When true, the customer may charge this fee and receive a verification code themselves.',
            ),
        ),
    ]
