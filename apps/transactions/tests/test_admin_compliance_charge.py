"""Staff-only compliance fee code generation."""
import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import Account, Currency
from apps.transactions.regulated_models import ComplianceFeeLine
from apps.users.models import CustomUser
from apps.transactions.regulated_flow import start_international_session
from apps.transactions.tests.test_intl_wire import _full_raw
from apps.transactions.intl_wire import validate_and_normalize_international_details

User = get_user_model()


@pytest.fixture
def currency(db):
    return Currency.objects.create(code='USD', name='US Dollar', symbol='$')


@pytest.fixture
def customer(db):
    return User.objects.create_user(email='cust@example.com', full_name='Customer', password='TestPass123!')


@pytest.fixture
def staff(db):
    return CustomUser.objects.create_user(
        email='staff@example.com',
        full_name='Staff',
        password='TestPass123!',
        role=CustomUser.Role.SUPER_ADMIN,
    )


@pytest.fixture
def sender(db, customer, currency):
    return Account.objects.create(
        owner=customer,
        currency=currency,
        account_type=Account.AccountType.CHECKING,
        balance=Decimal('50000.00'),
        available_balance=Decimal('50000.00'),
        account_number='1111111111111111',
    )


@pytest.fixture
def compliance_line(db):
    return ComplianceFeeLine.objects.create(
        name='AML',
        code='aml',
        applies_to=ComplianceFeeLine.AppliesTo.INTERNATIONAL_TRANSFER,
        flat_amount=Decimal('25.00'),
    )


@pytest.fixture
def wire():
    return validate_and_normalize_international_details(_full_raw())


@pytest.mark.django_db
class TestAdminComplianceCharge:
    def test_customer_charge_blocked(self, customer, sender, compliance_line, wire):
        session = start_international_session(
            customer,
            sender,
            '2222222222222222',
            Decimal('1000'),
            'TRANSFER_INTERNATIONAL',
            international_wire_details=wire,
        )
        line = session.lines.first()
        client = APIClient()
        client.force_authenticate(user=customer)
        url = reverse(
            'regulated-line-charge-send-otp',
            kwargs={'session_id': session.id, 'line_id': line.id},
        )
        res = client.post(url)
        assert res.status_code == 400
        assert res.data['detail'] == 'Insufficient funds.'

    def test_admin_charge_sends_otp(self, customer, staff, sender, compliance_line, wire):
        session = start_international_session(
            customer,
            sender,
            '2222222222222222',
            Decimal('1000'),
            'TRANSFER_INTERNATIONAL',
            international_wire_details=wire,
        )
        line = session.lines.first()
        client = APIClient()
        client.force_authenticate(user=staff)
        url = reverse(
            'admin-regulated-line-charge-send-otp',
            kwargs={'session_id': session.id, 'line_id': line.id},
        )
        res = client.post(url)
        assert res.status_code == 200, res.data
        assert res.data.get('otp')
        assert len(res.data['otp']) == 6
        line.refresh_from_db()
        assert line.status == 'CHARGED'

    def test_allow_then_customer_can_charge(self, customer, staff, sender, compliance_line, wire):
        session = start_international_session(
            customer,
            sender,
            '2222222222222222',
            Decimal('1000'),
            'TRANSFER_INTERNATIONAL',
            international_wire_details=wire,
        )
        line = session.lines.first()
        admin = APIClient()
        admin.force_authenticate(user=staff)
        allow_url = reverse(
            'admin-regulated-line-allow-customer-charge',
            kwargs={'session_id': session.id, 'line_id': line.id},
        )
        assert admin.post(allow_url).status_code == 200
        line.refresh_from_db()
        assert line.customer_self_charge_allowed is True

        cust = APIClient()
        cust.force_authenticate(user=customer)
        charge_url = reverse(
            'regulated-line-charge-send-otp',
            kwargs={'session_id': session.id, 'line_id': line.id},
        )
        res = cust.post(charge_url)
        assert res.status_code == 200
        line.refresh_from_db()
        assert line.status == 'CHARGED'

    def test_allow_blocked_when_insufficient_funds(self, customer, staff, sender, compliance_line, wire):
        session = start_international_session(
            customer,
            sender,
            '2222222222222222',
            Decimal('1000'),
            'TRANSFER_INTERNATIONAL',
            international_wire_details=wire,
        )
        line = session.lines.first()
        sender.available_balance = Decimal('0')
        sender.balance = Decimal('0')
        sender.save(update_fields=['available_balance', 'balance'])
        admin = APIClient()
        admin.force_authenticate(user=staff)
        allow_url = reverse(
            'admin-regulated-line-allow-customer-charge',
            kwargs={'session_id': session.id, 'line_id': line.id},
        )
        res = admin.post(allow_url)
        assert res.status_code == 400
        assert 'Admin → Accounts' in res.data['detail']
        line.refresh_from_db()
        assert line.customer_self_charge_allowed is False
