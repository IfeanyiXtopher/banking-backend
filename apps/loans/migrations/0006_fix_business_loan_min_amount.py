"""Correct Business Term Loan minimum from 100M to 100K."""
from decimal import Decimal

from django.db import migrations


def fix_business_min(apps, schema_editor):
    LoanProduct = apps.get_model('loans', 'LoanProduct')
    LoanProduct.objects.filter(loan_type='BUSINESS', min_amount=Decimal('100000000')).update(
        min_amount=Decimal('100000'),
    )


class Migration(migrations.Migration):

    dependencies = [
        ('loans', '0005_alter_loanproduct_description_and_more'),
    ]

    operations = [
        migrations.RunPython(fix_business_min, migrations.RunPython.noop),
    ]
