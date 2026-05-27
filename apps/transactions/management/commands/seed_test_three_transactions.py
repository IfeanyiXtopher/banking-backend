"""
Seed recent transactions for the customer "Test Three" (max two per calendar day).

Uses deposit/withdraw services so balances stay consistent, then backdates created_at.

Usage:
  python manage.py seed_test_three_transactions
  python manage.py seed_test_three_transactions --days 14

Re-running is safe: same idempotency keys are skipped.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import Account
from apps.transactions import services
from apps.transactions.models import Transaction
from apps.users.models import CustomUser


# Realistic labels (deposits / withdrawals)
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


class Command(BaseCommand):
    help = 'Add recent transactions for user "Test Three" (up to 2 per day).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=21,
            help='Number of days back from today to fill (default: 21).',
        )
    def handle(self, *args, **options):
        days: int = options['days']

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

        # Build plan: per day, morning deposit + afternoon withdrawal (2 per day)
        now = timezone.now()
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        rng = random.Random(42)  # stable amounts across runs

        planned: list[tuple[datetime, str, Decimal, str, str]] = []
        for i in range(days):
            day = day_start - timedelta(days=i)
            date_str = day.date().isoformat()

            amt_in = Decimal(str(rng.randint(120, 4500))) + Decimal(str(rng.choice([0, 25, 50, 99]))) / 100
            # Keep withdrawal below same-day deposit so seed works from a low balance
            pct = Decimal(str(rng.uniform(0.04, 0.28)))
            amt_out = (amt_in * pct).quantize(Decimal('0.01'))
            if amt_out < Decimal('5'):
                amt_out = Decimal('5.00')
            if amt_out >= amt_in:
                amt_out = (amt_in * Decimal('0.2')).quantize(Decimal('0.01'))

            t_morning = day.replace(hour=9, minute=rng.randint(5, 55))
            t_afternoon = day.replace(hour=rng.randint(14, 18), minute=rng.randint(5, 55))

            planned.append(
                (
                    t_morning,
                    'deposit',
                    amt_in,
                    rng.choice(DEPOSIT_LABELS),
                    f'seed-test-three-{date_str}-a-deposit',
                )
            )
            planned.append(
                (
                    t_afternoon,
                    'withdraw',
                    amt_out,
                    rng.choice(WITHDRAWAL_LABELS),
                    f'seed-test-three-{date_str}-b-withdraw',
                )
            )

        # Oldest first so withdrawals never fail for insufficient funds
        planned.sort(key=lambda x: x[0])

        created = 0
        skipped = 0
        backfill: list[tuple] = []

        for dt, kind, amount, description, idem_key in planned:
            if Transaction.objects.filter(idempotency_key=idem_key).exists():
                skipped += 1
                continue
            try:
                if kind == 'deposit':
                    tx = services.deposit(
                        str(account.id),
                        amount,
                        description,
                        user,
                        idempotency_key=idem_key,
                    )
                else:
                    tx = services.withdraw(
                        str(account.id),
                        amount,
                        description,
                        user,
                        idempotency_key=idem_key,
                    )
            except services.InsufficientFundsError:
                self.stderr.write(
                    self.style.WARNING(
                        f'Skipping {idem_key}: insufficient funds (balance may need a deposit).'
                    )
                )
                continue
            backfill.append((tx.pk, dt))
            created += 1

        if backfill:
            for pk, dt in backfill:
                Transaction.objects.filter(pk=pk).update(created_at=dt, completed_at=dt)

        self.stdout.write(
            self.style.SUCCESS(
                f'Done. User={user.email} account={account.account_number} '
                f'created={created} skipped(existing)={skipped}'
            )
        )
