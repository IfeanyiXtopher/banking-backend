"""
Scheduled savings-goal contributions (Celery).

Rules on SavingsGoal.rules (from customer UI):
- weeklyRecurring + weeklyAmount: once per ISO week, transfer weeklyAmount.
- roundUp: once per ISO week, transfer a small proxy (2% of primary available, max $25, min $1).
- smartSave: once per calendar month, transfer 5% of primary (min $5, max $100).

Server-only bookkeeping in rules['autosave_meta'] (preserved across customer rule edits).
"""
from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from django.utils import timezone

from apps.accounts.models import Account
from apps.notifications.services import send_email_notification, send_transaction_notification
from apps.transactions.services import InsufficientFundsError

from .models import SavingsGoal
from .services import allocate_to_goal

logger = logging.getLogger(__name__)


def _iso_week_key(d: date) -> str:
    y, w, _ = d.isocalendar()
    return f'{y}-W{w:02d}'


def _month_key(d: date) -> str:
    return d.strftime('%Y-%m')


def _meta(rules: dict) -> dict:
    m = rules.get('autosave_meta')
    return m if isinstance(m, dict) else {}


def _save_meta(goal: SavingsGoal, rules: dict, meta: dict) -> None:
    rules = dict(rules or {})
    rules['autosave_meta'] = meta
    goal.rules = rules
    goal.save(update_fields=['rules', 'updated_at'])


def _primary_available(owner) -> tuple[Decimal, Account | None]:
    acc = (
        Account.objects.filter(owner=owner, is_primary=True, exclude_from_card_summary=False)
        .select_related('currency')
        .first()
    )
    if not acc:
        return Decimal('0'), None
    return Decimal(str(acc.available_balance)), acc


def _notify_success(user_id: str, *, goal_title: str, amount: str, plan_label: str, new_saved: str):
    send_email_notification.delay(
        user_id,
        'goal_autosave_success',
        {
            'goal_title': goal_title,
            'amount': amount,
            'plan_label': plan_label,
            'new_saved_balance': new_saved,
        },
    )


def _notify_insufficient(
    user_id: str,
    *,
    goal_title: str,
    amount: str,
    plan_label: str,
    available: str,
    goal_id: str,
):
    send_email_notification.delay(
        user_id,
        'goal_autosave_insufficient',
        {
            'goal_title': goal_title,
            'amount': amount,
            'plan_label': plan_label,
            'available_balance': available,
            'goal_id': goal_id,
        },
    )


def _should_send_insufficient(meta: dict) -> bool:
    today = timezone.now().date().isoformat()
    return meta.get('insufficient_alert_day') != today


def _mark_insufficient(meta: dict) -> None:
    meta['insufficient_alert_day'] = timezone.now().date().isoformat()


def _try_allocate(goal: SavingsGoal, amount: Decimal, plan_label: str) -> bool:
    """
    Returns True if allocation succeeded.
    On InsufficientFundsError sends at most one alert per goal per calendar day.
    """
    if amount < Decimal('0.01'):
        return False
    owner = goal.owner
    rules = dict(goal.rules or {})
    meta = dict(_meta(rules))
    try:
        goal2, tx = allocate_to_goal(goal.id, owner, amount)
        send_transaction_notification.delay(str(tx.id))
        _notify_success(
            str(owner.id),
            goal_title=goal2.title,
            amount=str(amount),
            plan_label=plan_label,
            new_saved=str(goal2.saved_balance),
        )
        return True
    except InsufficientFundsError as e:
        logger.info('Goal autosave insufficient funds goal=%s plan=%s amount=%s err=%s', goal.id, plan_label, amount, e)
        goal.refresh_from_db()
        rules = dict(goal.rules or {})
        meta = dict(_meta(rules))
        if _should_send_insufficient(meta):
            avail, _ = _primary_available(owner)
            _notify_insufficient(
                str(owner.id),
                goal_title=goal.title,
                amount=str(amount),
                plan_label=plan_label,
                available=str(avail),
                goal_id=str(goal.id),
            )
            _mark_insufficient(meta)
            rules['autosave_meta'] = {**_meta(rules), **meta}
            goal.rules = rules
            goal.save(update_fields=['rules', 'updated_at'])
        return False
    except Exception as e:
        logger.exception('Goal autosave failed goal=%s plan=%s: %s', goal.id, plan_label, e)
        return False


def process_goal_autosave(goal: SavingsGoal) -> None:
    """Run all applicable autosave legs for one active goal (reload rules after each success)."""
    if goal.status != SavingsGoal.Status.ACTIVE:
        return

    today = timezone.now().date()
    week_k = _iso_week_key(today)
    month_k = _month_key(today)

    rules = dict(goal.rules or {})
    meta = dict(_meta(rules))

    # 1) Weekly fixed amount
    if rules.get('weeklyRecurring'):
        try:
            w_amt = Decimal(str(rules.get('weeklyAmount', 0) or 0))
        except Exception:
            w_amt = Decimal('0')
        if w_amt >= Decimal('0.01') and meta.get('weekly_contrib_week') != week_k:
            if _try_allocate(goal, w_amt, 'Weekly recurring savings'):
                meta['weekly_contrib_week'] = week_k
                _save_meta(goal, rules, meta)
                goal.refresh_from_db()
                rules = dict(goal.rules or {})
                meta = dict(_meta(rules))

    # 2) Round-up proxy (weekly small % sweep)
    if rules.get('roundUp') and meta.get('roundup_week') != week_k:
        avail, _ = _primary_available(goal.owner)
        amt = min(Decimal('25'), (avail * Decimal('0.02')).quantize(Decimal('0.01')))
        if amt >= Decimal('1'):
            if _try_allocate(goal, amt, 'Round-up savings'):
                meta['roundup_week'] = week_k
                _save_meta(goal, rules, meta)
                goal.refresh_from_db()
                rules = dict(goal.rules or {})
                meta = dict(_meta(rules))

    # 3) Smart save (monthly)
    if rules.get('smartSave') and meta.get('smart_month') != month_k:
        avail, _ = _primary_available(goal.owner)
        raw = (avail * Decimal('0.05')).quantize(Decimal('0.01'))
        amt = min(Decimal('100'), max(Decimal('5'), raw))
        if amt >= Decimal('1') and avail >= amt:
            if _try_allocate(goal, amt, 'Smart save'):
                meta['smart_month'] = month_k
                _save_meta(goal, rules, meta)
