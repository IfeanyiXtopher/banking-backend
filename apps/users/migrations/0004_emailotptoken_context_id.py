from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_profilechangerequest'),
    ]

    operations = [
        migrations.AddField(
            model_name='emailotptoken',
            name='context_id',
            field=models.UUIDField(
                blank=True,
                db_index=True,
                help_text='Optional scope (e.g. regulated fee line id) so multiple OTPs can coexist per user.',
                null=True,
            ),
        ),
    ]
