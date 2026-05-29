"""
Execute internal, external, and international transfers for user "Test Three".

Usage:
  python manage.py run_test_three_transfers
"""
from datetime import timedelta
from decimal import Decimal
import uuid

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import Account
from apps.transactions.intl_wire import validate_and_normalize_international_details
from apps.transactions.models import Transaction
from apps.transactions.regulated_flow import (
    PURPOSE_REGULATED_FEE,
    allow_customer_self_charge,
    charge_line_and_send_otp,
    confirm_external_payment,
    mark_international_session_completed,
    start_international_session,
    submit_external_payment,
    verify_line_otp,
)
from apps.transactions.services import (
    build_transfer_recipient_metadata,
    complete_pending_international_transfer,
    record_outbound_transfer,
)
from apps.users.models import EmailOTPToken

User = get_user_model()

WIRE_SAMPLE = {
    'beneficiary_legal_name': 'Euro Test Beneficiary GmbH',
    'beneficiary_address_line1': '42 Random Strasse',
    'beneficiary_city': 'Munich',
    'beneficiary_postal_code': '80331',
    'beneficiary_country': 'DE',
    'beneficiary_bank_name': 'Deutsche Test Bank AG',
    'beneficiary_bank_address_line1': 'Marienplatz 1',
    'beneficiary_bank_city': 'Munich',
    'beneficiary_bank_country': 'DE',
    'beneficiary_bic_swift': 'DEUTDEFF',
    'beneficiary_iban': 'DE89370400440532013000',
    'purpose_of_payment': 'QA international wire test',
    'remittance_reference': f'QA-{uuid.uuid4().hex[:8].upper()}',
    'charges_option': 'SHA',
}


class Command(BaseCommand):
    help = 'Run internal, external, and international outbound transfers for Test Three.'

    def handle(self, *args, **options):
        user = User.objects.filter(full_name__icontains='Test Three').first()
        if not user:
            self.stderr.write(self.style.ERROR('User "Test Three" not found.'))
            return

        from_acc = (
            Account.objects.filter(owner=user, account_type=Account.AccountType.BUSINESS, status=Account.Status.ACTIVE)
            .select_related('currency')
            .first()
        )
        if not from_acc:
            from_acc = Account.objects.filter(owner=user, status=Account.Status.ACTIVE).select_related('currency').first()
        if not from_acc:
            self.stderr.write(self.style.ERROR('Test Three has no active account.'))
            return

        # Any 16-digit beneficiary number (does not need to exist in SafaPay Bank).
        dest_number = '8374837483748373'

        self.stdout.write(
            self.style.SUCCESS(
                f'Sender: {user.full_name} ({from_acc.account_number})\n'
                f'Beneficiary account (recorded only): {dest_number}\n',
            ),
        )

        results = []

        try:
            meta = build_transfer_recipient_metadata(
                transfer_type=Transaction.TransactionType.TRANSFER_INTERNAL,
                to_account_number=dest_number,
                account_holder_name='Internal QA Recipient',
            )
            tx = record_outbound_transfer(
                str(from_acc.id),
                dest_number,
                Decimal('127.43'),
                'QA internal transfer — automated test',
                user,
                tx_type=Transaction.TransactionType.TRANSFER_INTERNAL,
                idempotency_key=f'qa-test3-internal-{uuid.uuid4().hex}',
                recipient_metadata=meta,
            )
            results.append(('INTERNAL', tx.reference_number, tx.status, str(tx.amount)))
        except Exception as e:
            results.append(('INTERNAL', 'FAILED', str(e), ''))

        try:
            meta = build_transfer_recipient_metadata(
                transfer_type=Transaction.TransactionType.TRANSFER_EXTERNAL,
                to_account_number=dest_number,
                account_holder_name='External QA Recipient',
                external_bank_name='Random External Bank PLC',
            )
            tx = record_outbound_transfer(
                str(from_acc.id),
                dest_number,
                Decimal('88.90'),
                'QA external transfer — automated test',
                user,
                tx_type=Transaction.TransactionType.TRANSFER_EXTERNAL,
                idempotency_key=f'qa-test3-external-{uuid.uuid4().hex}',
                recipient_metadata=meta,
            )
            results.append(('EXTERNAL', tx.reference_number, tx.status, str(tx.amount)))
        except Exception as e:
            results.append(('EXTERNAL', 'FAILED', str(e), ''))

        try:
            wire = validate_and_normalize_international_details(dict(WIRE_SAMPLE))
            amount = Decimal('215.75')
            meta = build_transfer_recipient_metadata(
                transfer_type=Transaction.TransactionType.TRANSFER_INTERNATIONAL,
                to_account_number=dest_number,
                account_holder_name='Intl QA Recipient',
            )
            session = start_international_session(
                user,
                from_acc,
                dest_number,
                amount,
                Transaction.TransactionType.TRANSFER_INTERNATIONAL,
                description='QA international transfer — automated test',
                idempotency_key=f'qa-test3-intl-{uuid.uuid4().hex}',
                international_wire_details=wire,
                recipient_metadata=meta,
            )
            pending = session.transfer_transaction
            self.stdout.write(f'  Intl session {session.id} pending tx {pending.reference_number if pending else "—"}')

            for line in session.lines.order_by('sequence'):
                allow_customer_self_charge(line.id)
                submit_external_payment(line.id, user)
                confirm_external_payment(line.id)
                charge_line_and_send_otp(line.id, user, staff_issued=True)
                EmailOTPToken.objects.create(
                    user=user,
                    token='847291',
                    purpose=PURPOSE_REGULATED_FEE,
                    context_id=line.id,
                    expires_at=timezone.now() + timedelta(minutes=15),
                )
                verify_line_otp(line.id, user, '847291')

            tx = complete_pending_international_transfer(str(session.transfer_transaction_id), user)
            mark_international_session_completed(session.id)
            results.append(('INTERNATIONAL', tx.reference_number, tx.status, str(tx.amount)))
        except Exception as e:
            results.append(('INTERNATIONAL', 'FAILED', str(e), ''))

        self.stdout.write('\n--- Results ---')
        for kind, ref, status, amt in results:
            if ref == 'FAILED':
                self.stdout.write(self.style.ERROR(f'{kind}: {status}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'{kind}: {ref} [{status}] amount={amt}'))

        recent = Transaction.objects.filter(initiated_by=user).order_by('-created_at')[:8]
        self.stdout.write('\nRecent Test Three transactions:')
        for t in recent:
            dest = (t.metadata or {}).get('destination_account_number', '—')
            self.stdout.write(
                f'  {t.created_at:%Y-%m-%d %H:%M} {t.transaction_type} {t.reference_number} '
                f'{t.amount} {t.currency} [{t.status}] → {dest}',
            )
