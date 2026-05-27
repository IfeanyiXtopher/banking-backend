# Generated manually

import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_profile_setup_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProfileChangeRequest',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('status', models.CharField(
                    choices=[('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected')],
                    default='PENDING',
                    max_length=20,
                )),
                ('proposed_full_name', models.CharField(max_length=255)),
                ('proposed_phone', models.CharField(blank=True, max_length=20)),
                ('proposed_address', models.TextField(blank=True)),
                ('proposed_date_of_birth', models.DateField(blank=True, null=True)),
                ('proposed_nationality', models.CharField(blank=True, max_length=100)),
                ('proposed_email', models.EmailField(blank=True, max_length=254)),
                ('proposed_id_document_type', models.CharField(blank=True, max_length=30)),
                ('proposed_id_document_number', models.CharField(blank=True, max_length=64)),
                ('proposed_profile_picture', models.ImageField(blank=True, null=True, upload_to='profile_requests/')),
                ('rejection_reason', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('reviewed_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='reviewed_profile_requests',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='profile_change_requests',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
