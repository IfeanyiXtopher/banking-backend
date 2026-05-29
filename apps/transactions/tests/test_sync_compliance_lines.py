"""Compliance fee lines sync to active sessions (scope-isolated) and session cancel/retry."""
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts.models import Account, Currency
from apps.loans.models import LoanApplication, LoanProduct
from apps.transactions.models import Transaction
from apps.transactions.regulated_flow import (
    cancel_compliance_session,
    compliance_resume_for_transaction,
    start_international_session,
    start_loan_payout_session,
    sync_session_compliance_lines,
)
from apps.transactions.regulated_models import (
    ComplianceFeeLine,
    RegulatedTransferSession,
    RegulatedTransferSessionLine,
)
from apps.transactions.tests.test_intl_wire import _full_raw
from apps.transactions.intl_wire import validate_and_normalize_international_details
from apps.users.models import CustomUser

User = CustomUser


@pytest.fixture
def currency(db):
    return Currency.objects.create(code='USD', name='US Dollar', symbol='$')


@pytest.fixture
def customer(db):
    return User.objects.create_user(email='sync-cust@example.com', full_name='Sync User', password='TestPass123!')


@pytest.fixture
def account(db, customer, currency):
    return Account.objects.create(
        owner=customer,
        currency=currency,
        account_type=Account.AccountType.CHECKING,
        balance=Decimal('50000.00'),
        available_balance=Decimal('50000.00'),
    )


@pytest.fixture
def loan_product(db):
    return LoanProduct.objects.create(
        name='Personal',
        loan_type=LoanProduct.LoanType.PERSONAL,
        interest_rate=Decimal('0.10'),
        min_amount=Decimal('1000'),
        max_amount=Decimal('50000'),
        min_term_months=6,
        max_term_months=60,
        is_active=True,
    )


@pytest.fixture
def approved_application(db, customer, loan_product):
    return LoanApplication.objects.create(
        applicant=customer,
        product=loan_product,
        requested_amount=Decimal('1000.00'),
        term_months=12,
        status=LoanApplication.Status.APPROVED,
    )


@pytest.fixture
def first_line(db, customer):
    return ComplianceFeeLine.objects.create(
        user=customer,
        name='LoanFee',
        code='loan_fee',
        applies_to=ComplianceFeeLine.AppliesTo.LOAN_PAYOUT,
        flat_amount=Decimal('50.00'),
    )


@pytest.fixture
def intl_compliance_line(db, customer):
    return ComplianceFeeLine.objects.create(
        user=customer,
        name='AML check',
        code='aml_intl',
        applies_to=ComplianceFeeLine.AppliesTo.INTERNATIONAL_TRANSFER,
        flat_amount=Decimal('25.00'),
    )


@pytest.fixture
def wire():
    return validate_and_normalize_international_details(_full_raw())


@pytest.mark.django_db
class TestSyncComplianceLines:
    def test_new_user_line_appended_to_active_loan_session(
        self, customer, account, approved_application, first_line,
    ):
        session = start_loan_payout_session(customer, account, approved_application)
        assert session.compliance_scope == RegulatedTransferSession.ComplianceScope.PERSONAL
        assert session.lines.count() == 1

        ComplianceFeeLine.objects.create(
            user=customer,
            name='TheeTLoan',
            code='thee_t_loan',
            applies_to=ComplianceFeeLine.AppliesTo.LOAN_PAYOUT,
            flat_amount=Decimal('75.00'),
        )

        added = sync_session_compliance_lines(session)
        assert added == 1
        session.refresh_from_db()
        assert session.lines.count() == 2

    def test_global_fee_does_not_sync_to_personal_intl_session(
        self, customer, account, intl_compliance_line, wire,
    ):
        ComplianceFeeLine.objects.create(
            user=customer,
            name='MMM',
            code='mmm',
            applies_to=ComplianceFeeLine.AppliesTo.INTERNATIONAL_TRANSFER,
            flat_amount=Decimal('100.00'),
        )
        session = start_international_session(
            customer,
            account,
            '9999999999999999',
            Decimal('500.00'),
            Transaction.TransactionType.TRANSFER_INTERNATIONAL,
            international_wire_details=wire,
        )
        assert session.compliance_scope == RegulatedTransferSession.ComplianceScope.PERSONAL
        assert session.lines.count() == 2

        ComplianceFeeLine.objects.create(
            name='Global surcharge',
            code='global_surcharge',
            applies_to=ComplianceFeeLine.AppliesTo.INTERNATIONAL_TRANSFER,
            flat_amount=Decimal('15.00'),
        )

        added = sync_session_compliance_lines(session)
        assert added == 0
        assert session.lines.count() == 2

    def test_global_fee_syncs_to_global_intl_session(
        self, customer, account, wire,
    ):
        ComplianceFeeLine.objects.create(
            name='AML global',
            code='aml_global',
            applies_to=ComplianceFeeLine.AppliesTo.INTERNATIONAL_TRANSFER,
            flat_amount=Decimal('25.00'),
        )
        session = start_international_session(
            customer,
            account,
            '9999999999999999',
            Decimal('500.00'),
            Transaction.TransactionType.TRANSFER_INTERNATIONAL,
            international_wire_details=wire,
        )
        assert session.compliance_scope == RegulatedTransferSession.ComplianceScope.GLOBAL
        assert session.lines.count() == 1

        ComplianceFeeLine.objects.create(
            name='Global surcharge',
            code='global_surcharge',
            applies_to=ComplianceFeeLine.AppliesTo.INTERNATIONAL_TRANSFER,
            flat_amount=Decimal('15.00'),
        )

        added = sync_session_compliance_lines(session)
        assert added == 1
        assert session.lines.count() == 2

    def test_pending_line_amount_refreshed_when_fee_pricing_changes(
        self, customer, account, approved_application, first_line,
    ):
        session = start_loan_payout_session(customer, account, approved_application)
        line = session.lines.first()
        assert line.amount == Decimal('50.00')

        first_line.flat_amount = Decimal('100.00')
        first_line.save(update_fields=['flat_amount', 'updated_at'])

        assert sync_session_compliance_lines(session) == 0
        line.refresh_from_db()
        assert line.amount == Decimal('100.00')

    def test_charged_line_amount_not_refreshed(
        self, customer, account, approved_application, first_line,
    ):
        session = start_loan_payout_session(customer, account, approved_application)
        line = session.lines.first()
        line.status = RegulatedTransferSessionLine.Status.CHARGED
        line.save(update_fields=['status', 'updated_at'])

        first_line.flat_amount = Decimal('999.00')
        first_line.save(update_fields=['flat_amount', 'updated_at'])

        sync_session_compliance_lines(session)
        line.refresh_from_db()
        assert line.amount == Decimal('50.00')

    def test_personal_fee_does_not_sync_to_global_intl_session(
        self, customer, account, wire,
    ):
        ComplianceFeeLine.objects.create(
            name='AML global',
            code='aml_global',
            applies_to=ComplianceFeeLine.AppliesTo.INTERNATIONAL_TRANSFER,
            flat_amount=Decimal('25.00'),
        )
        session = start_international_session(
            customer,
            account,
            '9999999999999999',
            Decimal('500.00'),
            Transaction.TransactionType.TRANSFER_INTERNATIONAL,
            international_wire_details=wire,
        )
        assert session.compliance_scope == RegulatedTransferSession.ComplianceScope.GLOBAL

        ComplianceFeeLine.objects.create(
            user=customer,
            name='Personal only',
            code='personal_only',
            applies_to=ComplianceFeeLine.AppliesTo.INTERNATIONAL_TRANSFER,
            flat_amount=Decimal('99.00'),
        )

        added = sync_session_compliance_lines(session)
        assert added == 0
        assert session.lines.count() == 1

    def test_cancelled_session_allows_new_intl_session_reusing_pending_tx(
        self, customer, account, intl_compliance_line, wire,
    ):
        session = start_international_session(
            customer,
            account,
            '9999999999999999',
            Decimal('500.00'),
            Transaction.TransactionType.TRANSFER_INTERNATIONAL,
            international_wire_details=wire,
        )
        tx = session.transfer_transaction
        assert tx is not None
        tx_id = tx.id

        cancel_compliance_session(session.id)
        tx.refresh_from_db()
        assert tx.status == Transaction.Status.PENDING
        assert 'regulated_session_id' not in (tx.metadata or {})

        resume = compliance_resume_for_transaction(tx)
        assert resume is None

        session2 = start_international_session(
            customer,
            account,
            '9999999999999999',
            Decimal('500.00'),
            Transaction.TransactionType.TRANSFER_INTERNATIONAL,
            international_wire_details=wire,
        )
        assert session2.id != session.id
        assert session2.transfer_transaction_id == tx_id
        assert session2.lines.count() == 1

    def test_cancelled_loan_session_allows_new_loan_session(
        self, customer, account, approved_application, first_line,
    ):
        session = start_loan_payout_session(customer, account, approved_application)
        cancel_compliance_session(session.id)

        session2 = start_loan_payout_session(customer, account, approved_application)
        assert session2.id != session.id
        assert session2.status != RegulatedTransferSession.Status.CANCELLED
        assert session2.lines.count() == 1
