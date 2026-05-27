"""Transfer preview serializer accepts decimal amounts (no min_value type error)."""
import pytest
from decimal import Decimal

from django.contrib.auth import get_user_model

from apps.accounts.models import Account, Currency
from apps.transactions.serializers import TransferPreviewSerializer
from apps.transactions.services import preview_transfer_fees_for_account_number

User = get_user_model()


@pytest.fixture
def currency(db):
    return Currency.objects.create(code='USD', name='US Dollar', symbol='$')


@pytest.fixture
def user(db):
    return User.objects.create_user(email='prev@example.com', full_name='Preview User', password='TestPass123!')


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


@pytest.mark.unit
class TestTransferPreviewSerializer:
    def test_validates_amount_without_type_error(self, sender):
        ser = TransferPreviewSerializer(
            data={
                'from_account_id': str(sender.id),
                'to_account_id': '8230343052496520',
                'amount': '6500.00',
                'transfer_type': 'TRANSFER_INTERNAL',
            },
        )
        assert ser.is_valid(), ser.errors

    def test_preview_omits_fee_line_when_no_fee_row(self, sender, db):
        from apps.transactions.models import TransactionFee

        TransactionFee.objects.filter(fee_type=TransactionFee.FeeType.TRANSFER_LOCAL).delete()
        ser = TransferPreviewSerializer(
            data={
                'from_account_id': str(sender.id),
                'to_account_id': '8230343052496520',
                'amount': '100.00',
                'transfer_type': 'TRANSFER_INTERNAL',
            },
        )
        assert ser.is_valid(), ser.errors
        data = ser.validated_data
        preview = preview_transfer_fees_for_account_number(
            str(sender.id),
            data['to_account_number'],
            data['amount'],
            data['transfer_type'],
        )
        assert preview['fees'] == []
        assert preview['fee_total'] == '0'
        assert preview['total_debit'] == '100.00'
