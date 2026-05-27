from decimal import Decimal

from django.db import transaction as db_transaction
from django.utils import timezone

from apps.accounts.models import Account
from apps.transactions.models import Transaction
from apps.transactions.services import InsufficientFundsError

from .models import CardIssuance, CardProductConfig


class CardServiceError(Exception):
    pass


@db_transaction.atomic
def debit_card_issuance_fee(account: Account, amount: Decimal, user, description: str) -> Transaction:
    """Debit linked account for card issuance (no extra withdrawal fee tier)."""
    amount = Decimal(str(amount))
    if amount <= 0:
        raise CardServiceError('Fee amount must be positive.')
    acc = Account.objects.select_for_update().get(pk=account.pk)
    if not acc.is_active:
        raise CardServiceError('Account is not active.')
    if acc.available_balance < amount:
        raise InsufficientFundsError('Insufficient available balance for card fee.')

    tx = Transaction.objects.create(
        transaction_type=Transaction.TransactionType.FEE,
        amount=amount,
        currency=acc.currency.code,
        from_account=acc,
        status=Transaction.Status.COMPLETED,
        description=description,
        fee_amount=Decimal('0'),
        initiated_by=user,
        completed_at=timezone.now(),
    )
    acc.balance -= amount
    acc.available_balance -= amount
    acc.save(update_fields=['balance', 'available_balance', 'updated_at'])
    return tx


def _has_open_issuance(account: Account) -> bool:
    return CardIssuance.objects.filter(
        account=account,
        status__in=(CardIssuance.Status.PENDING_PAYMENT, CardIssuance.Status.ACTIVE),
    ).exists()


@db_transaction.atomic
def request_card_for_account(user, account: Account) -> CardIssuance:
    if account.owner_id != user.id:
        raise CardServiceError('Account does not belong to you.')
    if _has_open_issuance(account):
        raise CardServiceError('A card has already been requested for this account.')
    cfg = CardProductConfig.objects.filter(account_type=account.account_type, is_active=True).first()
    if not cfg:
        raise CardServiceError(
            'Card issuing is not configured for this account type. Please contact support or try again later.',
        )
    issuance = CardIssuance.objects.create(
        account=account,
        owner=user,
        card_tier=cfg.card_tier,
        status=CardIssuance.Status.PENDING_PAYMENT,
        issue_fee=cfg.issue_fee,
        monthly_spending_limit=cfg.monthly_spending_limit,
    )
    return issuance


@db_transaction.atomic
def request_card_replacement(user, account: Account, *, terminate_previous: bool) -> CardIssuance:
    if account.owner_id != user.id:
        raise CardServiceError('Account does not belong to you.')
    if CardIssuance.objects.filter(account=account, status=CardIssuance.Status.PENDING_PAYMENT).exists():
        raise CardServiceError('Complete payment for your pending card request first.')

    active_qs = CardIssuance.objects.select_for_update().filter(
        account=account,
        status=CardIssuance.Status.ACTIVE,
    )
    if not active_qs.exists():
        raise CardServiceError('You need an active card before requesting a replacement.')

    cfg = CardProductConfig.objects.filter(account_type=account.account_type, is_active=True).first()
    if not cfg:
        raise CardServiceError(
            'Card issuing is not configured for this account type. Please contact support or try again later.',
        )

    if terminate_previous:
        active_qs.update(status=CardIssuance.Status.TERMINATED)

    return CardIssuance.objects.create(
        account=account,
        owner=user,
        card_tier=cfg.card_tier,
        status=CardIssuance.Status.PENDING_PAYMENT,
        issue_fee=cfg.issue_fee,
        monthly_spending_limit=cfg.monthly_spending_limit,
    )


@db_transaction.atomic
def pay_card_issuance_fee(user, issuance_id) -> CardIssuance:
    try:
        issuance = CardIssuance.objects.select_related('account').select_for_update().get(
            id=issuance_id,
            owner=user,
        )
    except CardIssuance.DoesNotExist as e:
        raise CardServiceError('Card request not found.') from e
    if issuance.status != CardIssuance.Status.PENDING_PAYMENT:
        raise CardServiceError('This card is not awaiting payment.')
    account = Account.objects.select_for_update().get(pk=issuance.account_id)
    if account.owner_id != user.id:
        raise CardServiceError('Invalid account.')

    fee = issuance.issue_fee
    if fee > 0:
        debit_card_issuance_fee(
            account,
            fee,
            user,
            description=f'Physical card fee ({issuance.card_tier})',
        )
    CardIssuance.objects.filter(
        account_id=issuance.account_id,
        status=CardIssuance.Status.ACTIVE,
    ).exclude(pk=issuance.pk).update(status=CardIssuance.Status.TERMINATED)
    issuance.status = CardIssuance.Status.ACTIVE
    issuance.paid_at = timezone.now()
    issuance.save(update_fields=['status', 'paid_at'])
    return issuance
