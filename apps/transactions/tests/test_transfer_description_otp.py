"""Transfer description normalization and domestic OTP requirements."""
import pytest
from decimal import Decimal

from django.contrib.auth import get_user_model

from apps.accounts.models import Account, Currency
from apps.transactions.models import Transaction
from apps.transactions.serializers import TransferSerializer
from apps.transactions.services import preview_transfer_fees_for_account_number

User = get_user_model()


@pytest.fixture
def currency(db):
    return Currency.objects.create(code='USD', name='US Dollar', symbol='$')


@pytest.fixture
def user(db):
    return User.objects.create_user(email='sender@example.com', full_name='Sender', password='TestPass123!')


@pytest.fixture
def sender(db, user, currency):
    return Account.objects.create(
        owner=user,
        currency=currency,
        account_type=Account.AccountType.CHECKING,
        balance=Decimal('5000.00'),
        available_balance=Decimal('5000.00'),
        account_number='1111111111111111',
    )


@pytest.mark.unit
class TestTransferDescriptionSerializer:
    def test_blank_description_defaults_for_domestic(self, sender):
        ser = TransferSerializer(
            data={
                'from_account_id': str(sender.id),
                'to_account_id': '2536627728123456',
                'amount': '50.00',
                'description': '',
                'transfer_type': 'TRANSFER_INTERNAL',
                'account_holder_name': 'Jane Recipient',
            },
        )
        assert ser.is_valid(), ser.errors
        assert ser.validated_data['description'] == 'Transfer'


@pytest.mark.unit
class TestDomesticTransferOtpPreview:
    def test_internal_and_external_always_require_otp(self, sender):
        for tx_type in (
            Transaction.TransactionType.TRANSFER_INTERNAL,
            Transaction.TransactionType.TRANSFER_EXTERNAL,
        ):
            preview = preview_transfer_fees_for_account_number(
                str(sender.id),
                '2536627728123456',
                Decimal('100.00'),
                tx_type,
            )
            assert preview['requires_otp'] is True
