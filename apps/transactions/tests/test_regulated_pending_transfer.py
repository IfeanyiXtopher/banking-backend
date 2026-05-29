"""Regulated international transfer: pending tx at session start, complete after compliance."""
import pytest
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.accounts.models import Account, Currency
from apps.transactions.models import Transaction, TransactionFee
from apps.transactions.regulated_models import ComplianceFeeLine, RegulatedTransferSession
from apps.users.models import EmailOTPToken
from apps.transactions.regulated_flow import (
    PURPOSE_REGULATED_FEE,
    start_international_session,
    verify_line_otp,
    charge_line_and_send_otp,
    confirm_external_payment,
    allow_customer_self_charge,
    submit_external_payment,
    assert_session_ready_for_international_transfer,
    RegulatedFlowError,
)
from apps.transactions.services import complete_pending_international_transfer
from apps.transactions.tests.test_intl_wire import _full_raw
from apps.transactions.intl_wire import validate_and_normalize_international_details

User = get_user_model()


@pytest.fixture
def currency(db):
    return Currency.objects.create(code='USD', name='US Dollar', symbol='$')


@pytest.fixture
def user(db):
    return User.objects.create_user(email='intl@example.com', full_name='Intl User', password='TestPass123!')


@pytest.fixture
def recipient(db, currency):
    other = User.objects.create_user(email='recv@example.com', full_name='Recipient', password='TestPass123!')
    return Account.objects.create(
        owner=other,
        currency=currency,
        account_type=Account.AccountType.CHECKING,
        balance=Decimal('0'),
        available_balance=Decimal('0'),
        account_number='2222222222222222',
    )


@pytest.fixture
def sender(db, user, currency):
    return Account.objects.create(
        owner=user,
        currency=currency,
        account_type=Account.AccountType.CHECKING,
        balance=Decimal('10000.00'),
        available_balance=Decimal('10000.00'),
        account_number='1111111111111111',
    )


@pytest.fixture
def compliance_line(db):
    return ComplianceFeeLine.objects.create(
        name='AML check',
        code='aml-test',
        applies_to=ComplianceFeeLine.AppliesTo.INTERNATIONAL_TRANSFER,
        flat_amount=Decimal('25.00'),
        sort_order=1,
        is_active=True,
        payment_wire_enabled=True,
        wire_beneficiary_name='Compliance Desk',
        wire_bank_name='Example Bank',
        wire_swift_bic='EXAMUS33',
        wire_iban='GB00EXAM123456',
    )


@pytest.fixture
def wire():
    return validate_and_normalize_international_details(_full_raw())


@pytest.mark.unit
class TestPendingInternationalTransfer:
    def test_session_start_debits_and_creates_pending(self, sender, recipient, user, compliance_line, wire):
        amount = Decimal('500.00')
        session = start_international_session(
            user,
            sender,
            recipient.account_number,
            amount,
            Transaction.TransactionType.TRANSFER_INTERNATIONAL,
            international_wire_details=wire,
        )
        session.refresh_from_db()
        sender.refresh_from_db()
        recipient.refresh_from_db()

        assert session.transfer_transaction_id is not None
        tx = session.transfer_transaction
        assert tx.status == Transaction.Status.PENDING
        assert tx.transaction_type == Transaction.TransactionType.TRANSFER_INTERNATIONAL
        assert tx.metadata.get('international_wire') == wire
        assert recipient.balance == Decimal('0')

        fee = TransactionFee.objects.filter(fee_type=TransactionFee.FeeType.TRANSFER_INTERNATIONAL).first()
        expected_fee = Decimal(str(fee.calculate(amount))) if fee else Decimal('0')
        assert sender.balance == Decimal('10000.00') - amount - expected_fee

    def test_abandoned_compliance_leaves_pending_on_list(self, sender, recipient, user, compliance_line, wire):
        session = start_international_session(
            user,
            sender,
            recipient.account_number,
            Decimal('200.00'),
            Transaction.TransactionType.TRANSFER_INTERNATIONAL,
            international_wire_details=wire,
        )
        tx = session.transfer_transaction
        assert Transaction.objects.filter(id=tx.id, status=Transaction.Status.PENDING).exists()
        assert session.status == RegulatedTransferSession.Status.IN_PROGRESS

    @patch('apps.transactions.regulated_flow.queue_email_notification')
    def test_complete_after_compliance_marks_completed_without_in_platform_credit(
        self,
        _mock_email,
        sender,
        recipient,
        user,
        compliance_line,
        wire,
    ):
        amount = Decimal('300.00')
        session = start_international_session(
            user,
            sender,
            recipient.account_number,
            amount,
            Transaction.TransactionType.TRANSFER_INTERNATIONAL,
            international_wire_details=wire,
        )
        line = session.lines.first()
        allow_customer_self_charge(line.id)
        submit_external_payment(line.id, user)
        confirm_external_payment(line.id)
        with patch('apps.transactions.regulated_flow.create_email_otp', return_value='123456'):
            charge_line_and_send_otp(line.id, user, staff_issued=True)
        EmailOTPToken.objects.create(
            user=user,
            token='123456',
            purpose=PURPOSE_REGULATED_FEE,
            context_id=line.id,
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        verify_line_otp(line.id, user, '123456')

        session.refresh_from_db()
        assert session.status == RegulatedTransferSession.Status.LINES_VERIFIED

        assert_session_ready_for_international_transfer(
            session.id,
            user,
            str(sender.id),
            recipient.account_number,
            amount,
            international_wire=wire,
        )
        tx = complete_pending_international_transfer(str(session.transfer_transaction_id), user)
        recipient.refresh_from_db()

        assert tx.status == Transaction.Status.COMPLETED
        assert recipient.balance == Decimal('0')
        assert tx.to_account_id is None

    def test_insufficient_funds_at_session_start_raises(self, sender, recipient, user, compliance_line, wire):
        sender.balance = Decimal('10.00')
        sender.available_balance = Decimal('10.00')
        sender.save()
        with pytest.raises(RegulatedFlowError, match='Insufficient'):
            start_international_session(
                user,
                sender,
                recipient.account_number,
                Decimal('500.00'),
                Transaction.TransactionType.TRANSFER_INTERNATIONAL,
                international_wire_details=wire,
            )
