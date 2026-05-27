# Generated manually: customer-level admin assignments + ADMIN role

import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


def migrate_account_assignments_to_customers(apps, schema_editor):
    StaffAccountAssignment = apps.get_model('users', 'StaffAccountAssignment')
    StaffCustomerAssignment = apps.get_model('users', 'StaffCustomerAssignment')
    Account = apps.get_model('accounts', 'Account')

    seen = set()
    for row in StaffAccountAssignment.objects.select_related('account').iterator():
        key = (row.staff_id, row.account_id)
        if key in seen:
            continue
        seen.add(key)
        try:
            owner_id = Account.objects.values_list('owner_id', flat=True).get(pk=row.account_id)
        except Account.DoesNotExist:
            continue
        StaffCustomerAssignment.objects.get_or_create(
            staff_id=row.staff_id,
            customer_id=owner_id,
            defaults={'assigned_by_id': row.assigned_by_id, 'assigned_at': row.assigned_at},
        )


def migrate_legacy_staff_roles(apps, schema_editor):
    CustomUser = apps.get_model('users', 'CustomUser')
    legacy = [
        'OPERATIONS_TELLER',
        'COMPLIANCE_AUDITOR',
        'LOAN_OFFICER',
        'SUPPORT_STAFF',
    ]
    CustomUser.objects.filter(role__in=legacy).update(role='ADMIN')


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_staff_account_assignments'),
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='admin_account_scope',
            field=models.CharField(
                choices=[('ALL', 'All customers'), ('SELECTED', 'Selected customers only')],
                default='ALL',
                help_text='Admin desk only: ALL = every customer; SELECTED = assigned customers (all their accounts).',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='customuser',
            name='role',
            field=models.CharField(
                choices=[
                    ('CUSTOMER', 'Customer'),
                    ('SUPER_ADMIN', 'Super Admin'),
                    ('ADMIN', 'Admin'),
                    ('OPERATIONS_TELLER', 'Operations / Teller'),
                    ('COMPLIANCE_AUDITOR', 'Compliance / Auditor'),
                    ('LOAN_OFFICER', 'Loan Officer'),
                    ('SUPPORT_STAFF', 'Support Staff'),
                ],
                default='CUSTOMER',
                max_length=30,
            ),
        ),
        migrations.CreateModel(
            name='StaffCustomerAssignment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('assigned_at', models.DateTimeField(default=django.utils.timezone.now)),
                (
                    'assigned_by',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='customer_assignments_made',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'customer',
                    models.ForeignKey(
                        limit_choices_to={'role': 'CUSTOMER'},
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='assigned_admins',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'staff',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='customer_assignments',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'ordering': ['-assigned_at'],
                'unique_together': {('staff', 'customer')},
            },
        ),
        migrations.RunPython(migrate_account_assignments_to_customers, migrations.RunPython.noop),
        migrations.RunPython(migrate_legacy_staff_roles, migrations.RunPython.noop),
        migrations.DeleteModel(
            name='StaffAccountAssignment',
        ),
    ]
