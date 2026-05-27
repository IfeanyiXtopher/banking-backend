"""Ensure default catalog rows exist for each LoanProduct.loan_type."""

from decimal import Decimal

from django.db import migrations


def seed_loan_products(apps, schema_editor):
    LoanProduct = apps.get_model('loans', 'LoanProduct')
    products = [
        {
            'name': 'Personal Loan',
            'loan_type': 'PERSONAL',
            'interest_rate': Decimal('0.1200'),
            'min_amount': Decimal('1000'),
            'max_amount': Decimal('50000'),
            'min_term_months': 6,
            'max_term_months': 60,
            'description': 'Flexible personal loans for any need.',
            'is_active': True,
        },
        {
            'name': 'Auto Loan',
            'loan_type': 'AUTO',
            'interest_rate': Decimal('0.0850'),
            'min_amount': Decimal('5000'),
            'max_amount': Decimal('150000'),
            'min_term_months': 12,
            'max_term_months': 84,
            'description': 'Finance your vehicle purchase.',
            'is_active': True,
        },
        {
            'name': 'Home Mortgage',
            'loan_type': 'MORTGAGE',
            'interest_rate': Decimal('0.0650'),
            'min_amount': Decimal('50000'),
            'max_amount': Decimal('2000000'),
            'min_term_months': 60,
            'max_term_months': 360,
            'description': 'Make homeownership achievable.',
            'is_active': True,
        },
        {
            'name': 'Business Term Loan',
            'loan_type': 'BUSINESS',
            'interest_rate': Decimal('0.0950'),
            'min_amount': Decimal('25000'),
            'max_amount': Decimal('750000'),
            'min_term_months': 12,
            'max_term_months': 120,
            'description': 'Growth and working capital for qualifying businesses.',
            'is_active': True,
        },
        {
            'name': 'Education Loan',
            'loan_type': 'EDUCATION',
            'interest_rate': Decimal('0.0725'),
            'min_amount': Decimal('2000'),
            'max_amount': Decimal('120000'),
            'min_term_months': 12,
            'max_term_months': 180,
            'description': 'Tuition and study costs with structured repayment.',
            'is_active': True,
        },
    ]
    for row in products:
        LoanProduct.objects.update_or_create(loan_type=row['loan_type'], defaults=row)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('loans', '0002_initial'),
    ]

    operations = [
        migrations.RunPython(seed_loan_products, noop_reverse),
    ]
