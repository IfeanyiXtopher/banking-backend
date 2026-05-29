from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0016_alter_regulatedtransfersessionline_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='regulatedtransfersessionline',
            name='payment_proof',
            field=models.FileField(
                blank=True,
                null=True,
                upload_to='compliance-payment-proofs/',
                help_text='Optional receipt or screenshot uploaded when the customer submits payment.',
            ),
        ),
    ]
