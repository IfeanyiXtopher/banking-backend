"""Outbound transfers record beneficiary account numbers without a SafaPay Bank credit account."""
import pytest
from decimal import Decimal

from django.contrib.auth import get_user_model

from apps.accounts.models import Account, Currency
from apps.transactions.models import Transaction
from apps.transactions.services import record_outbound_transfer

User = get_user_model()


@pytest.fixture
def currency(db):
    return Currency.objects.create(code='USD', name='US Dollar', symbol='$')


@pytest.fixture
def user(db):
    return User.objects.create_user(email='out@example.com', full_name='Outbound User', password='TestPass123!')


@pytest.fixture
def sender(db, user, currency):
    return Account.objects.create(
        owner=user,
        currency=currency,
        account_type=Account.AccountType.BUSINESS,
        balance=Decimal('5000.00'),
        available_balance=Decimal('5000.00'),
        account_number='3333333333333333',
    )


@pytest.mark.unit
class TestRecordOutboundTransfer:
    def test_records_without_destination_account_row(self, sender, user):
        dest = '8374837483748373'
        tx = record_outbound_transfer(
            str(sender.id),
            dest,
            Decimal('100.00'),
            'Test outbound',
            user,
            Transaction.TransactionType.TRANSFER_INTERNAL,
            recipient_metadata={'recipient_account_holder_name': 'Jane Doe'},
        )
        sender.refresh_from_db()
        assert tx.to_account_id is None
        assert tx.status == Transaction.Status.COMPLETED
        assert tx.metadata['destination_account_number'] == dest
        assert tx.metadata['recipient_account_holder_name'] == 'Jane Doe'
        assert sender.balance < Decimal('5000.00')
