"""Admin compliance fee line create (including sync with active sessions)."""
from decimal import Decimal
from unittest.mock import patch

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


@pytest.mark.django_db
def test_create_per_user_line_accepts_blank_min_principal(super_admin, customer):
    client = APIClient()
    client.force_authenticate(user=super_admin)
    url = reverse('admin-compliance-fee-line-list')
    res = client.post(
        url,
        {
            'name': 'GTYY',
            'code': 'gtyy-blank-principal',
            'user': str(customer.id),
            'applies_to': 'INTERNATIONAL_TRANSFER',
            'min_principal_threshold': '',
            'flat_amount': '650',
            'percentage': '0',
            'min_amount': '0',
            'max_amount': '0',
            'is_active': True,
        },
        format='json',
    )
    assert res.status_code == 201, res.data
    assert res.data['min_principal_threshold'] in ('0.00', '0', 0, '0.0')


@pytest.mark.django_db
def test_create_global_both_applies_to_with_active_session(super_admin, customer, account, wire):
    """Matches production: global line, applies_to BOTH, flat fee, active intl session."""
    ComplianceFeeLine.objects.create(
        name='AML',
        code='aml',
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
            'name': 'compliance-fee',
            'code': 'compliance-fee-new',
            'user': None,
            'applies_to': 'BOTH',
            'min_principal_threshold': '0',
            'flat_amount': '450',
            'percentage': '0',
            'min_amount': '0',
            'max_amount': '0',
            'is_active': True,
        },
        format='json',
    )
    assert res.status_code == 201, res.data


@pytest.mark.django_db
@patch('apps.transactions.regulated_flow.sync_all_active_compliance_sessions', side_effect=RuntimeError('sync failed'))
def test_create_succeeds_when_session_sync_fails(mock_sync, super_admin, customer):
    client = APIClient()
    client.force_authenticate(user=super_admin)
    url = reverse('admin-compliance-fee-line-list')
    res = client.post(
        url,
        {
            'name': 'Resilient',
            'code': 'resilient-line',
            'user': str(customer.id),
            'applies_to': 'INTERNATIONAL_TRANSFER',
            'min_principal_threshold': '0',
            'flat_amount': '10',
            'percentage': '0',
            'min_amount': '0',
            'max_amount': '0',
            'is_active': True,
        },
        format='json',
    )
    assert res.status_code == 201, res.data
    mock_sync.assert_called_once()
