"""Customer activity audit logging."""
from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Account, Currency
from apps.audit.models import AuditLog
from apps.loans.models import LoanApplication, LoanProduct
from apps.users.models import CustomUser

User = CustomUser


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def customer(db):
    return User.objects.create_user(
        email='audit-cust@example.com',
        full_name='Audit Customer',
        password='TestPass123!',
        role=User.Role.CUSTOMER,
    )


@pytest.fixture
def currency(db):
    return Currency.objects.create(code='USD', name='US Dollar', symbol='$')


@pytest.fixture
def account(db, customer, currency):
    return Account.objects.create(
        owner=customer,
        currency=currency,
        account_type=Account.AccountType.CHECKING,
        balance=Decimal('1000.00'),
        available_balance=Decimal('1000.00'),
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
def admin_user(db):
    return User.objects.create_user(
        email='audit-admin@example.com',
        full_name='Admin',
        password='TestPass123!',
        role=User.Role.SUPER_ADMIN,
        is_staff=True,
    )


@pytest.mark.django_db
class TestCustomerAudit:
    def test_login_success_creates_audit(self, api_client, customer):
        url = reverse('auth-login')
        res = api_client.post(
            url,
            {'email': customer.email, 'password': 'TestPass123!'},
            format='json',
        )
        assert res.status_code == status.HTTP_200_OK
        assert AuditLog.objects.filter(actor=customer, action=AuditLog.Action.LOGIN).exists()

    def test_failed_login_creates_audit(self, api_client, customer):
        url = reverse('auth-login')
        api_client.post(
            url,
            {'email': customer.email, 'password': 'wrong'},
            format='json',
        )
        assert AuditLog.objects.filter(action=AuditLog.Action.FAILED_LOGIN).exists()

    def test_deposit_creates_transaction_audit(self, api_client, customer, account):
        api_client.force_authenticate(user=customer)
        url = reverse('transaction-deposit')
        res = api_client.post(
            url,
            {'account_id': str(account.id), 'amount': '50.00', 'description': 'Test deposit'},
            format='json',
        )
        assert res.status_code == status.HTTP_201_CREATED
        assert AuditLog.objects.filter(
            actor=customer,
            action=AuditLog.Action.TRANSACTION,
            target_model='Transaction',
            description__icontains='Deposit',
        ).exists()

    def test_loan_application_creates_audit(self, api_client, customer, loan_product):
        api_client.force_authenticate(user=customer)
        url = reverse('loan-applications')
        res = api_client.post(
            url,
            {
                'product': str(loan_product.id),
                'requested_amount': '10000.00',
                'term_months': 24,
            },
            format='json',
        )
        assert res.status_code == status.HTTP_201_CREATED
        assert AuditLog.objects.filter(
            actor=customer,
            action=AuditLog.Action.CREATE,
            target_model='LoanApplication',
            description__icontains='Applied',
        ).exists()

    def test_customer_scope_excludes_staff(self, api_client, admin_user, customer):
        AuditLog.objects.create(
            actor=admin_user,
            action=AuditLog.Action.UPDATE,
            target_model='Config',
            description='Staff change',
        )
        AuditLog.objects.create(
            actor=customer,
            action=AuditLog.Action.LOGIN,
            target_model='Session',
            description='Customer signed in',
        )
        api_client.force_authenticate(user=admin_user)
        url = reverse('admin-audit-logs')
        res = api_client.get(url, {'actor_scope': 'customer'})
        assert res.status_code == status.HTTP_200_OK
        rows = res.data.get('results', res.data)
        emails = {r.get('actor_email') for r in rows}
        assert customer.email in emails
        assert admin_user.email not in emails
