"""Savings goal funding uses one hidden 'Goals pocket' account per customer (not per goal)."""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction as db_transaction

from apps.accounts.models import Account
from apps.accounts.services import create_additional_uae_account, get_or_create_default_currency
from apps.transactions.services import transfer

from .models import SavingsGoal

GOALS_POCKET_NICKNAME = 'Goals pocket'


def goal_ledger_tag(goal_id) -> str:
    return f'SG_GOAL#{goal_id}'


def get_goals_pocket(owner) -> Account | None:
    return Account.objects.filter(owner=owner, exclude_from_card_summary=True).first()


def get_or_create_goals_pocket(owner) -> Account:
    pocket = get_goals_pocket(owner)
    if pocket:
        return pocket
    currency = get_or_create_default_currency()
    return create_additional_uae_account(
        owner,
        Account.AccountType.SAVINGS,
        currency,
        GOALS_POCKET_NICKNAME,
        exclude_from_card_summary=True,
    )


def _primary_account(owner) -> Account:
    acc = (
        Account.objects.filter(owner=owner, is_primary=True, exclude_from_card_summary=False)
        .select_related('currency')
        .first()
    )
    if not acc:
        raise ValueError('No primary account found. Complete onboarding first.')
    return acc


@db_transaction.atomic
def allocate_to_goal(goal_id, owner, amount: Decimal):
    """
    Move funds from primary checking to goals pocket and credit this goal's saved_balance.
    Returns (goal, transaction).
    """
    if amount <= 0:
        raise ValueError('Amount must be positive.')

    goal = SavingsGoal.objects.select_for_update().get(id=goal_id, owner=owner, status=SavingsGoal.Status.ACTIVE)
    primary = _primary_account(owner)
    pocket = get_or_create_goals_pocket(owner)

    if primary.currency_id != pocket.currency_id:
        raise ValueError('Primary account currency must match goals pocket.')

    tag = goal_ledger_tag(goal.id)
    tx = transfer(
        str(primary.id),
        str(pocket.id),
        amount,
        f'To goal: {goal.title[:80]} ({tag})',
        owner,
    )

    goal.saved_balance += amount
    goal.save(update_fields=['saved_balance', 'updated_at'])
    return goal, tx


@db_transaction.atomic
def cancel_savings_goal(goal_id, owner) -> SavingsGoal:
    """
    Cancel a goal. Any saved_balance is transferred from the goals pocket back to the primary account.
    """
    goal = SavingsGoal.objects.select_for_update().get(id=goal_id, owner=owner, status=SavingsGoal.Status.ACTIVE)
    amt = goal.saved_balance

    if amt > 0:
        primary = _primary_account(owner)
        pocket = get_goals_pocket(owner)
        if not pocket:
            raise ValueError('Goals pocket missing; contact support.')
        pocket = Account.objects.select_for_update().get(pk=pocket.pk)
        if pocket.available_balance < amt:
            raise ValueError('Goals pocket balance is insufficient to release this goal. Contact support.')

        transfer(
            str(pocket.id),
            str(primary.id),
            amt,
            f'Goal cancelled — {goal.title[:80]} ({goal_ledger_tag(goal.id)})',
            owner,
        )

    goal.saved_balance = Decimal('0')
    goal.status = SavingsGoal.Status.CANCELLED
    goal.save(update_fields=['saved_balance', 'status', 'updated_at'])
    return goal
