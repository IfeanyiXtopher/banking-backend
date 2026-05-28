"""Align Business Term Loan limits with product spec (min 100K, max 5B, term up to 180 mo)."""
from decimal import Decimal

from django.db import migrations


def fix_business_limits(apps, schema_editor):
    LoanProduct = apps.get_model('loans', 'LoanProduct')
    LoanProduct.objects.filter(loan_type='BUSINESS').update(
        min_amount=Decimal('100000'),
        max_amount=Decimal('5000000000'),
        max_term_months=180,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('loans', '0006_fix_business_loan_min_amount'),
    ]

    operations = [
        migrations.RunPython(fix_business_limits, migrations.RunPython.noop),
    ]
