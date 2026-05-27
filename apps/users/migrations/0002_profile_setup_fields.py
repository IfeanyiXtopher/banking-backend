from django.db import migrations, models


def set_existing_users_profile_complete(apps, schema_editor):
    User = apps.get_model('users', 'CustomUser')
    User.objects.update(profile_setup_completed=True)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='profile_setup_completed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='customuser',
            name='intended_account_type',
            field=models.CharField(
                blank=True,
                choices=[
                    ('SAVINGS', 'Savings'),
                    ('CHECKING', 'Checking'),
                    ('BUSINESS', 'Business'),
                    ('FIXED_TERM', 'Fixed deposit'),
                    ('CREDIT', 'Credit'),
                ],
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='customuser',
            name='id_document_type',
            field=models.CharField(
                blank=True,
                choices=[
                    ('PASSPORT', 'International passport'),
                    ('DRIVERS_LICENSE', "Driver's license"),
                    ('NATIONAL_ID', 'National ID'),
                    ('RESIDENCE_PERMIT', 'Residence permit'),
                    ('OTHER', 'Other'),
                ],
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name='customuser',
            name='id_document_number',
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.RunPython(set_existing_users_profile_complete, migrations.RunPython.noop),
    ]
