"""Unit tests for double-entry transaction services."""
import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from apps.accounts.models import Account, Currency
from apps.transactions.models import TransactionFee
from apps.transactions.services import deposit, withdraw, transfer, InsufficientFundsError, AccountStatusError

User = get_user_model()


@pytest.fixture
def currency(db):
    return Currency.objects.create(code='USD', name='US Dollar', symbol='$')


@pytest.fixture
def user(db):
    return User.objects.create_user(email='test@example.com', full_name='Test User', password='TestPass123!')


@pytest.fixture
def account(db, user, currency):
    return Account.objects.create(
        owner=user,
        currency=currency,
        account_type=Account.AccountType.CHECKING,
        balance=Decimal('1000.00'),
        available_balance=Decimal('1000.00'),
    )


@pytest.fixture
def second_account(db, user, currency):
    return Account.objects.create(
        owner=user,
        currency=currency,
        account_type=Account.AccountType.SAVINGS,
        balance=Decimal('500.00'),
        available_balance=Decimal('500.00'),
    )


@pytest.mark.unit
class TestDeposit:
    def test_deposit_increases_balance(self, account, user):
        tx = deposit(str(account.id), Decimal('200.00'), 'Test deposit', user)
        account.refresh_from_db()
        assert account.balance == Decimal('1200.00')
        assert tx.status == 'COMPLETED'
        assert tx.amount == Decimal('200.00')

    def test_deposit_idempotency(self, account, user):
        tx1 = deposit(str(account.id), Decimal('100.00'), 'Idempotent', user, idempotency_key='key123')
        tx2 = deposit(str(account.id), Decimal('100.00'), 'Idempotent', user, idempotency_key='key123')
        assert tx1.id == tx2.id

    def test_deposit_zero_raises(self, account, user):
        from apps.transactions.services import TransactionError
        with pytest.raises(TransactionError):
            deposit(str(account.id), Decimal('0'), 'Bad', user)

    def test_deposit_frozen_account_raises(self, account, user):
        account.status = Account.Status.FROZEN
        account.save()
        with pytest.raises(AccountStatusError):
            deposit(str(account.id), Decimal('100.00'), 'Bad', user)


@pytest.mark.unit
class TestWithdraw:
    def test_withdraw_decreases_balance(self, account, user):
        tx = withdraw(str(account.id), Decimal('300.00'), 'Test withdrawal', user)
        account.refresh_from_db()
        assert account.balance == Decimal('700.00')
        assert tx.status == 'COMPLETED'

    def test_withdraw_insufficient_funds_raises(self, account, user):
        with pytest.raises(InsufficientFundsError):
            withdraw(str(account.id), Decimal('9999.00'), 'Too much', user)

    def test_withdraw_inactive_account_raises(self, account, user):
        account.status = Account.Status.CLOSED
        account.save()
        with pytest.raises(AccountStatusError):
            withdraw(str(account.id), Decimal('100.00'), 'Closed', user)

    def test_withdraw_additional_management_fee(self, account, user):
        TransactionFee.objects.filter(fee_type=TransactionFee.FeeType.WITHDRAWAL).delete()
        account.balance = Decimal('500.00')
        account.available_balance = Decimal('500.00')
        account.save()
        tx = withdraw(
            str(account.id),
            Decimal('100.00'),
            'Bill pay',
            user,
            additional_fee=Decimal('1.25'),
        )
        account.refresh_from_db()
        assert account.available_balance == Decimal('398.75')
        assert tx.amount == Decimal('100.00')
        assert tx.fee_amount == Decimal('1.25')


@pytest.mark.unit
class TestTransfer:
    def test_transfer_moves_funds(self, account, second_account, user):
        tx = transfer(
            from_account_id=str(account.id),
            to_account_id=str(second_account.id),
            amount=Decimal('200.00'),
            description='Transfer test',
            initiated_by=user,
        )
        account.refresh_from_db()
        second_account.refresh_from_db()
        assert account.balance == Decimal('800.00')
        assert second_account.balance == Decimal('700.00')
        assert tx.status == 'COMPLETED'

    def test_transfer_same_account_raises(self, account, user):
        from rest_framework.exceptions import ValidationError
        from apps.transactions.services import TransactionError
        with pytest.raises(Exception):
            transfer(str(account.id), str(account.id), Decimal('100'), 'Bad', user)

    def test_transfer_insufficient_funds_raises(self, account, second_account, user):
        with pytest.raises(InsufficientFundsError):
            transfer(str(account.id), str(second_account.id), Decimal('99999'), 'Too much', user)
