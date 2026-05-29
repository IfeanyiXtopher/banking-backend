"""Loan payout uses the same regulated compliance fee flow as international transfers."""
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Account, Currency
from apps.loans.models import LoanApplication, LoanProduct
from apps.loans.services import disburse_loan
from apps.transactions.regulated_flow import (
    PURPOSE_REGULATED_FEE,
    RegulatedFlowError,
    assert_loan_compliance_completed_if_required,
    charge_line_and_send_otp,
    confirm_external_payment,
    allow_customer_self_charge,
    submit_external_payment,
    start_loan_payout_session,
    verify_line_otp,
)
from apps.transactions.regulated_models import ComplianceFeeLine, RegulatedTransferSession
from apps.users.models import CustomUser, EmailOTPToken

User = get_user_model()


@pytest.fixture
def currency(db):
    return Currency.objects.create(code='USD', name='US Dollar', symbol='$')


@pytest.fixture
def customer(db):
    return User.objects.create_user(email='loan-cust@example.com', full_name='Borrower', password='TestPass123!')


@pytest.fixture
def officer(db):
    return CustomUser.objects.create_user(
        email='officer@example.com',
        full_name='Officer',
        password='TestPass123!',
        role=CustomUser.Role.LOAN_OFFICER,
    )


@pytest.fixture
def sender(db, customer, currency):
    return Account.objects.create(
        owner=customer,
        currency=currency,
        account_type=Account.AccountType.CHECKING,
        balance=Decimal('50000.00'),
        available_balance=Decimal('50000.00'),
        account_number='3333333333333333',
    )


@pytest.fixture
def disburse_account(db, customer, currency):
    return Account.objects.create(
        owner=customer,
        currency=currency,
        account_type=Account.AccountType.SAVINGS,
        balance=Decimal('0'),
        available_balance=Decimal('0'),
        account_number='4444444444444444',
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
        requested_amount=Decimal('10000.00'),
        term_months=12,
        status=LoanApplication.Status.APPROVED,
    )


@pytest.fixture
def loan_compliance_line(db):
    return ComplianceFeeLine.objects.create(
        name='Settlement fee',
        code='loan_settle',
        applies_to=ComplianceFeeLine.AppliesTo.LOAN_PAYOUT,
        flat_amount=Decimal('50.00'),
        payment_wire_enabled=True,
        wire_beneficiary_name='Compliance Desk',
        wire_bank_name='Example Bank',
        wire_swift_bic='EXAMUS33',
        wire_iban='GB00EXAM123456',
    )


@pytest.mark.django_db
class TestLoanRegulatedPayout:
    def test_session_lines_require_admin_or_allow_for_charge(
        self, customer, sender, approved_application, loan_compliance_line,
    ):
        session = start_loan_payout_session(customer, sender, approved_application)
        line = session.lines.first()
        assert line.customer_self_charge_allowed is False
        from apps.transactions.regulated_flow import RegulatedFlowError

        with pytest.raises(RegulatedFlowError, match='confirmed'):
            charge_line_and_send_otp(line.id, customer)

    def test_full_payout_after_compliance(
        self,
        customer,
        sender,
        disburse_account,
        approved_application,
        loan_compliance_line,
    ):
        with (
            patch('apps.transactions.regulated_flow.queue_email_notification'),
            patch('apps.transactions.regulated_flow.create_email_otp', return_value='123456'),
        ):
            session = start_loan_payout_session(customer, sender, approved_application)
            line = session.lines.first()
            allow_customer_self_charge(line.id)
            submit_external_payment(line.id, customer)
            confirm_external_payment(line.id)
            charge_line_and_send_otp(line.id, customer, staff_issued=True)
            EmailOTPToken.objects.create(
                user=customer,
                token='123456',
                purpose=PURPOSE_REGULATED_FEE,
                context_id=line.id,
                expires_at=timezone.now() + timedelta(minutes=10),
            )
            verify_line_otp(line.id, customer, '123456')
        session.refresh_from_db()
        assert session.status == RegulatedTransferSession.Status.LINES_VERIFIED

        loan_account = disburse_loan(
            str(approved_application.id),
            str(disburse_account.id),
            customer,
            enforce_applicant_account=True,
        )
        assert loan_account.principal_amount == Decimal('10000.00')
        approved_application.refresh_from_db()
        assert approved_application.status == LoanApplication.Status.DISBURSED

    def test_admin_disburse_blocked_until_compliance_done(
        self, officer, disburse_account, approved_application, loan_compliance_line,
    ):
        with pytest.raises(RegulatedFlowError, match='compliance fees'):
            assert_loan_compliance_completed_if_required(approved_application)

    def test_direct_complete_without_compliance_lines(
        self, customer, disburse_account, approved_application,
    ):
        client = APIClient()
        client.force_authenticate(user=customer)
        url = f'/api/loans/applications/{approved_application.id}/regulated-payout/complete/'
        res = client.post(url, {'disbursement_account_id': str(disburse_account.id)}, format='json')
        assert res.status_code == 200
        approved_application.refresh_from_db()
        assert approved_application.status == LoanApplication.Status.DISBURSED

    def test_payout_context_on_application_detail(
        self, customer, approved_application, loan_compliance_line,
    ):
        client = APIClient()
        client.force_authenticate(user=customer)
        res = client.get(f'/api/loans/applications/{approved_application.id}/')
        assert res.status_code == 200
        ctx = res.data['payout_context']
        assert ctx['requires_compliance'] is True
        assert len(ctx['fee_lines']) == 1
        assert Decimal(ctx['compliance_fee_total']) == Decimal('50.00')
