"""Development seed: creates currencies, fee structures, and exchange rates."""
from django.core.management.base import BaseCommand
from decimal import Decimal


class Command(BaseCommand):
    help = 'Seed initial reference data (currencies, fees, exchange rates)'

    def handle(self, *args, **options):
        self._seed_currencies()
        self._seed_fees()
        self._seed_compliance_fee_lines()
        self._seed_exchange_rates()
        self._seed_loan_products()
        self.stdout.write(self.style.SUCCESS('Seed data created successfully.'))

    def _seed_currencies(self):
        from apps.accounts.models import Currency
        currencies = [
            ('AED', 'UAE Dirham', 'د.إ'),
            ('USD', 'US Dollar', '$'),
            ('EUR', 'Euro', '€'),
            ('GBP', 'British Pound', '£'),
            ('NGN', 'Nigerian Naira', '₦'),
            ('GHS', 'Ghanaian Cedi', '₵'),
            ('KES', 'Kenyan Shilling', 'KSh'),
            ('ZAR', 'South African Rand', 'R'),
        ]
        for code, name, symbol in currencies:
            Currency.objects.get_or_create(code=code, defaults={'name': name, 'symbol': symbol})
        self.stdout.write(f'  Currencies: {len(currencies)} created.')

    def _seed_fees(self):
        from apps.transactions.models import TransactionFee
        fees = [
            ('TRANSFER_LOCAL', Decimal('0.50'), Decimal('0'), Decimal('0'), Decimal('0')),
            ('TRANSFER_INTERNATIONAL', Decimal('2.00'), Decimal('0.0100'), Decimal('2.00'), Decimal('50.00')),
            ('WITHDRAWAL', Decimal('0.00'), Decimal('0'), Decimal('0'), Decimal('0')),
            ('DEPOSIT', Decimal('0.00'), Decimal('0'), Decimal('0'), Decimal('0')),
        ]
        for fee_type, flat, pct, min_a, max_a in fees:
            TransactionFee.objects.get_or_create(
                fee_type=fee_type,
                defaults={'flat_amount': flat, 'percentage': pct, 'min_amount': min_a, 'max_amount': max_a},
            )
        self.stdout.write(f'  Fees: {len(fees)} created.')

    def _seed_compliance_fee_lines(self):
        from apps.transactions.models import ComplianceFeeLine

        rows = [
            ('Tax code', 'tax-code', ComplianceFeeLine.AppliesTo.BOTH, '0', 10, '25.00', '0', '0', '0'),
            ('AML code', 'aml-code', ComplianceFeeLine.AppliesTo.BOTH, '0', 20, '25.00', '0', '0', '0'),
            ('IRS code', 'irs-code', ComplianceFeeLine.AppliesTo.BOTH, '0', 30, '25.00', '0', '0', '0'),
            ('FTR code', 'ftr-code', ComplianceFeeLine.AppliesTo.BOTH, '0', 40, '25.00', '0', '0', '0'),
            ('Regulatory oversight code', 'regulatory-oversight', ComplianceFeeLine.AppliesTo.BOTH, '0', 50, '30.00', '0', '0', '0'),
            ('Sanctions check code', 'sanctions-check', ComplianceFeeLine.AppliesTo.BOTH, '0', 60, '30.00', '0', '0', '0'),
            ('Insurance', 'insurance', ComplianceFeeLine.AppliesTo.BOTH, '0', 70, '20.00', '0', '0', '0'),
            ('Insurance code', 'insurance-code', ComplianceFeeLine.AppliesTo.BOTH, '0', 80, '20.00', '0', '0', '0'),
            (
                'High-value international surcharge',
                'intl-high-threshold',
                ComplianceFeeLine.AppliesTo.INTERNATIONAL_TRANSFER,
                '10000.00',
                5,
                '50.00',
                '0',
                '0',
                '0',
            ),
        ]
        for name, code, applies, thresh, sort, flat, pct, min_a, max_a in rows:
            ComplianceFeeLine.objects.update_or_create(
                code=code,
                defaults={
                    'name': name,
                    'applies_to': applies,
                    'min_principal_threshold': Decimal(thresh),
                    'sort_order': sort,
                    'flat_amount': Decimal(flat),
                    'percentage': Decimal(pct),
                    'min_amount': Decimal(min_a),
                    'max_amount': Decimal(max_a),
                    'is_active': True,
                },
            )
        self.stdout.write(f'  Compliance fee lines: {len(rows)} upserted.')

    def _seed_exchange_rates(self):
        from apps.transactions.models import ExchangeRate
        rates = [
            ('USD', 'EUR', Decimal('0.92')),
            ('USD', 'GBP', Decimal('0.79')),
            ('USD', 'NGN', Decimal('1600.00')),
            ('USD', 'GHS', Decimal('15.80')),
            ('EUR', 'USD', Decimal('1.09')),
            ('GBP', 'USD', Decimal('1.27')),
        ]
        for from_c, to_c, rate in rates:
            ExchangeRate.objects.update_or_create(
                from_currency=from_c, to_currency=to_c,
                defaults={'rate': rate},
            )
        self.stdout.write(f'  Exchange rates: {len(rates)} seeded.')

    def _seed_loan_products(self):
        from apps.loans.models import LoanProduct
        products = [
            {'name': 'Personal Loan', 'loan_type': 'PERSONAL', 'interest_rate': Decimal('0.1200'), 'min_amount': Decimal('1000'), 'max_amount': Decimal('50000'), 'min_term_months': 6, 'max_term_months': 60, 'description': 'Flexible personal loans for any need.'},
            {'name': 'Auto Loan', 'loan_type': 'AUTO', 'interest_rate': Decimal('0.0850'), 'min_amount': Decimal('5000'), 'max_amount': Decimal('150000'), 'min_term_months': 12, 'max_term_months': 84, 'description': 'Finance your vehicle purchase.'},
            {'name': 'Home Mortgage', 'loan_type': 'MORTGAGE', 'interest_rate': Decimal('0.0650'), 'min_amount': Decimal('50000'), 'max_amount': Decimal('2000000'), 'min_term_months': 60, 'max_term_months': 360, 'description': 'Make homeownership achievable.'},
            {'name': 'Business Term Loan', 'loan_type': 'BUSINESS', 'interest_rate': Decimal('0.0950'), 'min_amount': Decimal('100000'), 'max_amount': Decimal('5000000000'), 'min_term_months': 12, 'max_term_months': 180, 'description': 'Growth and working capital for qualifying businesses.'},
            {'name': 'Education Loan', 'loan_type': 'EDUCATION', 'interest_rate': Decimal('0.0725'), 'min_amount': Decimal('2000'), 'max_amount': Decimal('120000'), 'min_term_months': 12, 'max_term_months': 180, 'description': 'Tuition and study costs with structured repayment.'},
        ]
        for product in products:
            loan_type = product['loan_type']
            LoanProduct.objects.update_or_create(loan_type=loan_type, defaults=product)
        self.stdout.write(f'  Loan products: {len(products)} upserted (by loan_type).')
