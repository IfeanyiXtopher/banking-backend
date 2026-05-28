"""Admin compliance fee line create (including sync with active sessions)."""
from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import Account, Currency
from apps.transactions.regulated_models import ComplianceFeeLine
from apps.transactions.regulated_flow import start_international_session
from apps.transactions.tests.test_intl_wire import _full_raw
from apps.transactions.intl_wire import validate_and_normalize_international_details
from apps.users.models import CustomUser


@pytest.fixture
def currency(db):
    return Currency.objects.create(code='USD', name='US Dollar', symbol='$')


@pytest.fixture
def customer(db):
    return CustomUser.objects.create_user(
        email='fee-line-cust@example.com',
        full_name='Fee Line Customer',
        password='TestPass123!',
    )


@pytest.fixture
def super_admin(db):
    return CustomUser.objects.create_user(
        email='fee-line-admin@example.com',
        full_name='Fee Line Admin',
        password='TestPass123!',
        role=CustomUser.Role.SUPER_ADMIN,
    )


@pytest.fixture
def account(db, customer, currency):
    return Account.objects.create(
        owner=customer,
        currency=currency,
        account_type=Account.AccountType.CHECKING,
        balance=Decimal('50000.00'),
        available_balance=Decimal('50000.00'),
        account_number='9999999999999999',
    )


@pytest.fixture
def wire():
    return validate_and_normalize_international_details(_full_raw())


@pytest.mark.django_db
def test_create_per_user_compliance_line_with_active_session(super_admin, customer, account, wire):
    ComplianceFeeLine.objects.create(
        name='AML',
        code='aml',
        user=customer,
        applies_to=ComplianceFeeLine.AppliesTo.INTERNATIONAL_TRANSFER,
        flat_amount=Decimal('25.00'),
    )
    start_international_session(
        customer,
        account,
        '2222222222222222',
        Decimal('1000'),
        'TRANSFER_INTERNATIONAL',
        international_wire_details=wire,
    )

    client = APIClient()
    client.force_authenticate(user=super_admin)
    url = reverse('admin-compliance-fee-line-list')
    res = client.post(
        url,
        {
            'name': 'EQD',
            'code': 'eqd',
            'user': str(customer.id),
            'applies_to': 'INTERNATIONAL_TRANSFER',
            'min_principal_threshold': '0',
            'flat_amount': '0',
            'percentage': '0',
            'min_amount': '0',
            'max_amount': '0',
            'is_active': True,
        },
        format='json',
    )
    assert res.status_code == 201, res.data
