"""
Add 100 extra transactions for user "Test Three" (deposits + withdrawals).

Idempotency keys: seed-bulk-three-001 … seed-bulk-three-100 (safe to re-run).

Some descriptions are short; ~40%% use narrations of 10–20 words (bank-style, under 255 chars).

Usage:
  python manage.py seed_test_three_bulk
  python manage.py seed_test_three_bulk --count 100
"""
from __future__ import annotations

import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import Account
from apps.transactions import services
from apps.transactions.models import Transaction
from apps.users.models import CustomUser

DEPOSIT_LABELS = [
    'Salary deposit',
    'Refund — online order',
    'Dividend payout',
    'Transfer in',
    'Cashback reward',
    'Interest credit',
    'Peer payment received',
    'Client invoice #1042',
]

WITHDRAWAL_LABELS = [
    'Grocery store',
    'Coffee & bakery',
    'Pet care & vet',
    'Fuel station',
    'Streaming subscription',
    'Pharmacy',
    'Restaurant',
    'Utility bill',
    'Online marketplace',
    'Transit pass',
]

# Hand-crafted 10–20 word narrations (realistic statement-style; all under 255 chars).
LONG_NARRATIONS = [
    'Mobile transfer to external payee for invoice settlement and scheduled quarterly service renewal payment.',
    'Outgoing domestic wire to supplier for office equipment purchase per approved procurement request reference.',
    'Internal credit from payroll processing batch for the current pay period ending last Friday afternoon.',
    'POS purchase at retail merchant with cashback promotion applied according to cardholder rewards program rules.',
    'Scheduled recurring payment to utility company for electricity and gas combined billing cycle this month.',
    'Peer to peer transfer received from family member toward shared vacation rental deposit and booking fees.',
    'ACH debit initiated by insurance carrier for annual policy premium renewal on automobile coverage plan.',
    'Online marketplace refund credited back to primary checking after return shipment warehouse confirmation.',
    'Dividend distribution from brokerage sweep account based on qualified holdings statement end of quarter.',
    'ATM cash withdrawal surcharge reimbursement credit posted following customer dispute resolution team review.',
    'International remittance fee adjustment credit related to prior cross border transfer exchange rate review.',
    'Loan disbursement credit to designated operating account per signed promissory note and draw schedule.',
    'Merchant settlement batch credit from card processor for weekend point of sale transaction clearing window.',
    'Subscription service charge for premium cloud storage tier billed annually with prorated first month.',
    'Charitable donation debit to registered nonprofit organization using verified tax exempt routing instructions.',
    'Property management payment for monthly rent parking and storage locker fees per lease addendum schedule.',
    'Tuition installment debit to educational institution student portal autopay plan semester two balance.',
    'Healthcare copayment debit to clinic network after insurance adjudication explanation of benefits summary.',
    'Freelance client retainer deposit for creative project milestone one deliverables per signed contract.',
    'Fuel and fleet card charge at highway service plaza during business travel reimbursement policy window.',
    'Grocery delivery order including fresh produce dairy and household staples from national chain partner.',
    'Home improvement store purchase materials for kitchen renovation phase two contractor supplied list.',
    'Telecommunications bundle charge internet voice and entertainment package promotional rate first year.',
    'Gym membership annual renewal debit with corporate wellness discount code applied at checkout.',
    'Pet insurance premium withdrawal for policy covering veterinary accidents and illness rider options.',
    'Airline ticket purchase domestic round trip conference attendance company travel authorization code.',
    'Hotel accommodation charge business trip three nights city center property corporate negotiated rate.',
    'Restaurant group dining expense client entertainment receipt attached for accounts payable audit trail.',
    'Parking garage monthly pass renewal downtown office location contactless badge billing cycle rollover.',
    'Courier express shipping fee debit for time sensitive documents signature required delivery service.',
    'Software license annual renewal enterprise seats including priority support and maintenance agreement.',
    'Hardware upgrade purchase laptops docking stations monitors for new hire onboarding equipment bundle.',
    'Coworking space day pass debit shared workspace hot desk booking same day reservation confirmation.',
    'Childcare weekly tuition payment early learning center autopay from joint household operating account.',
    'Music streaming family plan charge annual billing cycle shared profiles parental controls enabled.',
    'Electric vehicle charging network session debit highway corridor fast charger kilowatt hour pricing.',
    'Farmers market vendor payment local organic produce eggs honey community supported agriculture share.',
    'Bookstore academic texts purchase semester reading list digital access codes bundled with hardcover.',
    'Veterinary wellness visit vaccination lab work prescription medication pet care clinic statement.',
    'Dental office copay restorative procedure insurance estimate patient responsibility portion due today.',
    'Optical retailer contact lens annual supply order shipping to home address verified prescription file.',
]


class Command(BaseCommand):
    help = 'Add bulk transactions (default 100) for user "Test Three" with mixed narration lengths.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=100,
            help='Number of transactions to seed (default: 100).',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=150,
            help='Spread transaction timestamps over this many days in the past (default: 150).',
        )

    def handle(self, *args, **options):
        count: int = max(1, options['count'])
        days: int = max(1, options['days'])

        user = CustomUser.objects.filter(full_name__iexact='Test Three').first()
        if not user:
            user = CustomUser.objects.filter(full_name__icontains='Test Three').first()
        if not user:
            self.stderr.write(self.style.ERROR('No user with full name "Test Three" found.'))
            return

        account = (
            Account.objects.filter(owner=user, is_primary=True).first()
            or Account.objects.filter(owner=user).order_by('-created_at').first()
        )
        if not account:
            self.stderr.write(self.style.ERROR(f'User {user.email} has no accounts.'))
            return

        rng = random.Random(20250509)
        now = timezone.now()
        day_floor = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)

        # Evenly spaced anchors with jitter, then sort oldest → first for balance safety
        slots: list = []
        for i in range(count):
            frac = i / max(count - 1, 1)
            base = day_floor + timedelta(days=frac * days)
            jitter_h = rng.randint(0, 23)
            jitter_m = rng.randint(0, 59)
            jitter_s = rng.randint(0, 59)
            dt = base.replace(hour=jitter_h, minute=jitter_m, second=jitter_s)
            if dt > now - timedelta(minutes=5):
                dt = now - timedelta(hours=rng.randint(2, 72), minutes=rng.randint(0, 59))
            slots.append(dt)
        slots.sort()

        created = 0
        skipped = 0
        withdraw_fail = 0
        backfill: list[tuple] = []

        for idx, dt in enumerate(slots, start=1):
            idem_key = f'seed-bulk-three-{idx:03d}'
            if Transaction.objects.filter(idempotency_key=idem_key).exists():
                skipped += 1
                continue

            use_long = rng.random() < 0.42
            if use_long:
                description = rng.choice(LONG_NARRATIONS)
            else:
                description = rng.choice(DEPOSIT_LABELS + WITHDRAWAL_LABELS)

            want_withdraw = rng.random() < 0.38 and idx > 8

            amt_dep = Decimal(str(rng.randint(80, 4200))) + Decimal(str(rng.choice([0, 49, 99]))) / 100
            amt_wd = Decimal(str(rng.randint(12, 380))) + Decimal(str(rng.choice([0, 25, 50, 99]))) / 100

            tx = None
            if want_withdraw:
                try:
                    tx = services.withdraw(
                        str(account.id),
                        amt_wd,
                        description,
                        user,
                        idempotency_key=idem_key,
                    )
                except services.InsufficientFundsError:
                    withdraw_fail += 1
                    tx = None

            if tx is None:
                tx = services.deposit(
                    str(account.id),
                    amt_dep,
                    description,
                    user,
                    idempotency_key=idem_key,
                )

            backfill.append((tx.pk, dt))
            created += 1

        if backfill:
            for pk, dt in backfill:
                Transaction.objects.filter(pk=pk).update(created_at=dt, completed_at=dt)

        self.stdout.write(
            self.style.SUCCESS(
                f'Done. User={user.email} account={account.account_number} '
                f'created={created} skipped(existing)={skipped} '
                f'withdraw_fallbacks={withdraw_fail}'
            )
        )
