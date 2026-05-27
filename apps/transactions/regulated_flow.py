"""Session-based compliance fees: charge each line, then one OTP per line, then complete transfer/payout."""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db import transaction as db_transaction
from django.db.models import Max
from django.utils import timezone

from apps.accounts.models import Account
from apps.users.email_otp import create_email_otp
from apps.users.models import EmailOTPToken
from apps.notifications.services import send_email_notification

from .models import Transaction
from .regulated_models import ComplianceFeeLine, RegulatedTransferSession, RegulatedTransferSessionLine


PURPOSE_REGULATED_FEE = 'regulated_fee'

SESSION_TTL = timedelta(minutes=45)

_ACTIVE_SESSION_STATUSES = (
    RegulatedTransferSession.Status.PENDING,
    RegulatedTransferSession.Status.IN_PROGRESS,
    RegulatedTransferSession.Status.LINES_VERIFIED,
)


class RegulatedFlowError(Exception):
    pass


def _flow_matches_line(line: ComplianceFeeLine, flow: str) -> bool:
    if line.applies_to == ComplianceFeeLine.AppliesTo.BOTH:
        return True
    return line.applies_to == flow


def _resolve_compliance_user(account: Account | None, user=None):
    if user is not None:
        return user
    if account is not None:
        return account.owner
    return None


def applicable_compliance_lines(
    flow: str,
    principal: Decimal,
    account: Account | None = None,
    user=None,
) -> list[ComplianceFeeLine]:
    """
    Return compliance fee lines for a flow and principal amount.
    Per-user lines for this flow take precedence; otherwise global lines for this flow are used.
    """
    customer = _resolve_compliance_user(account, user)
    p = Decimal(str(principal))
    base_qs = ComplianceFeeLine.objects.filter(is_active=True, min_principal_threshold__lte=p).order_by(
        'sort_order', 'name',
    )

    if customer is not None:
        user_lines = [x for x in base_qs.filter(user=customer) if _flow_matches_line(x, flow)]
        if user_lines:
            return user_lines

    return [x for x in base_qs.filter(user__isnull=True) if _flow_matches_line(x, flow)]


def resolve_compliance_scope_at_start(
    flow: str,
    principal: Decimal,
    account: Account | None = None,
    user=None,
) -> str:
    """GLOBAL if session is built from global fee lines; PERSONAL if from per-user lines."""
    customer = _resolve_compliance_user(account, user)
    p = Decimal(str(principal))
    base_qs = ComplianceFeeLine.objects.filter(is_active=True, min_principal_threshold__lte=p)
    if customer is not None:
        user_lines = [x for x in base_qs.filter(user=customer) if _flow_matches_line(x, flow)]
        if user_lines:
            return RegulatedTransferSession.ComplianceScope.PERSONAL
    return RegulatedTransferSession.ComplianceScope.GLOBAL


def applicable_compliance_lines_for_session_sync(
    session: RegulatedTransferSession,
) -> list[ComplianceFeeLine]:
    """
    New fee definitions that may be appended to an open session (same scope only).
    Global sessions only pick up new global lines; personal sessions only new personal lines.
    """
    flow = session.flow
    p = Decimal(str(session.principal_amount))
    base_qs = ComplianceFeeLine.objects.filter(
        is_active=True,
        min_principal_threshold__lte=p,
    ).order_by('sort_order', 'name')

    scope = session.compliance_scope or RegulatedTransferSession.ComplianceScope.GLOBAL
    if scope == RegulatedTransferSession.ComplianceScope.PERSONAL:
        return [x for x in base_qs.filter(user=session.user_id) if _flow_matches_line(x, flow)]
    return [x for x in base_qs.filter(user__isnull=True) if _flow_matches_line(x, flow)]


def international_requires_regulated_session(
    principal: Decimal,
    account: Account | None = None,
    user=None,
) -> bool:
    return bool(
        applicable_compliance_lines(
            RegulatedTransferSession.Flow.INTERNATIONAL_TRANSFER, principal, account, user=user,
        ),
    )


def loan_payout_requires_regulated_session(
    principal: Decimal,
    account: Account | None = None,
    user=None,
) -> bool:
    return bool(applicable_compliance_lines(RegulatedTransferSession.Flow.LOAN_PAYOUT, principal, account, user=user))


@db_transaction.atomic
def sync_session_compliance_lines(session: RegulatedTransferSession) -> int:
    """
    Append newly configured compliance fee lines to an active session.
    Returns the number of lines added.
    """
    if session.status not in _ACTIVE_SESSION_STATUSES:
        return 0
    if timezone.now() > session.expires_at:
        return 0

    session = (
        RegulatedTransferSession.objects.select_for_update()
        .select_related('from_account', 'user')
        .prefetch_related('lines')
        .get(pk=session.pk)
    )
    applicable = applicable_compliance_lines_for_session_sync(session)
    existing_fee_line_ids = {ln.fee_line_id for ln in session.lines.all()}
    max_seq = session.lines.aggregate(m=Max('sequence'))['m']
    next_seq = (max_seq if max_seq is not None else -1) + 1
    added = 0

    for fl in applicable:
        if fl.id in existing_fee_line_ids:
            continue
        amt = fl.calculate(session.principal_amount)
        RegulatedTransferSessionLine.objects.create(
            session=session,
            fee_line=fl,
            sequence=next_seq,
            amount=amt,
            status=RegulatedTransferSessionLine.Status.PENDING,
        )
        next_seq += 1
        added += 1

    if added and session.status == RegulatedTransferSession.Status.LINES_VERIFIED:
        session.status = RegulatedTransferSession.Status.IN_PROGRESS
        session.save(update_fields=['status', 'updated_at'])
    elif added and session.status == RegulatedTransferSession.Status.PENDING:
        session.status = RegulatedTransferSession.Status.IN_PROGRESS
        session.save(update_fields=['status', 'updated_at'])

    return added


def sync_all_active_compliance_sessions(*, user=None) -> int:
    """Sync every non-expired active session (optionally for one user). Returns total lines added."""
    now = timezone.now()
    qs = RegulatedTransferSession.objects.filter(
        status__in=_ACTIVE_SESSION_STATUSES,
        expires_at__gt=now,
    ).select_related('from_account', 'user')
    if user is not None:
        qs = qs.filter(user=user)
    total = 0
    for session in qs:
        total += sync_session_compliance_lines(session)
    return total


def _session_is_active(session: RegulatedTransferSession) -> bool:
    return session.status in _ACTIVE_SESSION_STATUSES and timezone.now() <= session.expires_at


def _find_reusable_pending_international_tx(from_account: Account, user) -> Transaction | None:
    """Pending intl transfer with no active compliance session (e.g. after admin cancelled session)."""
    for tx in (
        Transaction.objects.filter(
            from_account=from_account,
            initiated_by=user,
            status=Transaction.Status.PENDING,
            transaction_type=Transaction.TransactionType.TRANSFER_INTERNATIONAL,
        )
        .order_by('-created_at')[:20]
    ):
        meta = tx.metadata or {}
        if not meta.get('awaiting_compliance'):
            continue
        sid = meta.get('regulated_session_id')
        if not sid:
            return tx
        linked = RegulatedTransferSession.objects.filter(pk=sid).first()
        if linked is None or linked.status == RegulatedTransferSession.Status.CANCELLED:
            return tx
        if not _session_is_active(linked):
            return tx
    return None


@db_transaction.atomic
def cancel_compliance_session(session_id, *, staff_user=None) -> RegulatedTransferSession:
    """
    Admin: cancel compliance workflow only. Does not reverse/delete the pending transfer or loan.
    Customer must start a new compliance session to continue.
    """
    session = RegulatedTransferSession.objects.select_for_update().get(id=session_id)
    if session.status in (
        RegulatedTransferSession.Status.COMPLETED,
        RegulatedTransferSession.Status.CANCELLED,
    ):
        raise RegulatedFlowError('This session is already closed.')

    session.status = RegulatedTransferSession.Status.CANCELLED
    session.save(update_fields=['status', 'updated_at'])

    tx = session.transfer_transaction
    if tx:
        meta = dict(tx.metadata or {})
        meta.pop('regulated_session_id', None)
        tx.metadata = meta
        tx.save(update_fields=['metadata'])

    return session


def _attach_pending_transfer_to_session(
    session: RegulatedTransferSession,
    user,
    from_account: Account,
    destination_account_number: str,
    amount: Decimal,
    transfer_type: str,
    description: str,
    idempotency_key: str | None,
    international_wire_details: dict | None,
    recipient_metadata: dict | None = None,
) -> RegulatedTransferSession:
    if session.transfer_transaction_id:
        tx = session.transfer_transaction
        meta = dict(tx.metadata or {})
        meta['regulated_session_id'] = str(session.id)
        meta['awaiting_compliance'] = True
        tx.metadata = meta
        tx.save(update_fields=['metadata'])
        return session

    from .services import InsufficientFundsError, build_transfer_recipient_metadata, create_pending_international_transfer

    meta = recipient_metadata or build_transfer_recipient_metadata(
        transfer_type=transfer_type,
        to_account_number=destination_account_number,
    )
    pending_tx = _find_reusable_pending_international_tx(from_account, user)
    if not pending_tx:
        try:
            pending_tx = create_pending_international_transfer(
                str(from_account.id),
                amount,
                description or 'International transfer',
                user,
                destination_account_number=destination_account_number,
                tx_type=transfer_type,
                idempotency_key=idempotency_key,
                international_wire_details=international_wire_details,
                recipient_metadata=meta,
            )
        except InsufficientFundsError as e:
            raise RegulatedFlowError(str(e)) from e
    session.transfer_transaction = pending_tx
    session.save(update_fields=['transfer_transaction', 'updated_at'])
    meta = dict(pending_tx.metadata or {})
    meta['regulated_session_id'] = str(session.id)
    meta['awaiting_compliance'] = True
    pending_tx.metadata = meta
    pending_tx.save(update_fields=['metadata'])
    return session


@db_transaction.atomic
def start_international_session(
    user,
    from_account: Account,
    destination_account_number: str,
    amount: Decimal,
    transfer_type: str,
    description: str = '',
    idempotency_key: str | None = None,
    international_wire_details: dict | None = None,
    recipient_metadata: dict | None = None,
) -> RegulatedTransferSession:
    if transfer_type != Transaction.TransactionType.TRANSFER_INTERNATIONAL:
        raise RegulatedFlowError('Regulated session only applies to international transfers.')
    amount = Decimal(str(amount))
    lines = applicable_compliance_lines(
        RegulatedTransferSession.Flow.INTERNATIONAL_TRANSFER, amount, from_account, user=user,
    )
    if not lines:
        raise RegulatedFlowError('No compliance fee lines configured for this transfer.')

    scope = resolve_compliance_scope_at_start(
        RegulatedTransferSession.Flow.INTERNATIONAL_TRANSFER, amount, from_account, user=user,
    )

    if idempotency_key:
        existing = RegulatedTransferSession.objects.filter(idempotency_key=idempotency_key).first()
        if existing and _session_is_active(existing):
            if (
                international_wire_details is not None
                and existing.international_wire_details is not None
                and existing.international_wire_details != international_wire_details
            ):
                raise RegulatedFlowError(
                    'This idempotency key was already used with different international beneficiary details.',
                )
            sync_session_compliance_lines(existing)
            return _attach_pending_transfer_to_session(
                existing,
                user,
                from_account,
                destination_account_number,
                amount,
                transfer_type,
                description,
                idempotency_key,
                international_wire_details,
                recipient_metadata,
            )

    session = RegulatedTransferSession.objects.create(
        user=user,
        flow=RegulatedTransferSession.Flow.INTERNATIONAL_TRANSFER,
        status=RegulatedTransferSession.Status.PENDING,
        compliance_scope=scope,
        from_account=from_account,
        to_account=None,
        loan_application=None,
        principal_amount=amount,
        transfer_type=transfer_type,
        description=description or 'International transfer',
        international_wire_details=international_wire_details,
        idempotency_key=idempotency_key or None,
        expires_at=timezone.now() + SESSION_TTL,
    )
    for i, fl in enumerate(lines):
        amt = fl.calculate(amount)
        RegulatedTransferSessionLine.objects.create(
            session=session,
            fee_line=fl,
            sequence=i,
            amount=amt,
            status=RegulatedTransferSessionLine.Status.PENDING,
        )
    session.status = RegulatedTransferSession.Status.IN_PROGRESS
    session.save(update_fields=['status', 'updated_at'])
    return _attach_pending_transfer_to_session(
        session,
        user,
        from_account,
        destination_account_number,
        amount,
        transfer_type,
        description,
        idempotency_key,
        international_wire_details,
        recipient_metadata,
    )


@db_transaction.atomic
def start_loan_payout_session(user, from_account: Account, loan_application, idempotency_key: str | None = None):
    from apps.loans.models import LoanApplication

    if not isinstance(loan_application, LoanApplication):
        raise RegulatedFlowError('Invalid loan application.')
    if loan_application.applicant_id != user.id:
        raise RegulatedFlowError('This application does not belong to you.')
    if loan_application.status != LoanApplication.Status.APPROVED:
        raise RegulatedFlowError('Loan must be approved before payout.')
    if hasattr(loan_application, 'loan_account'):
        raise RegulatedFlowError('This loan has already been disbursed.')

    principal = Decimal(str(loan_application.requested_amount))
    lines = applicable_compliance_lines(
        RegulatedTransferSession.Flow.LOAN_PAYOUT, principal, from_account, user=user,
    )
    if not lines:
        raise RegulatedFlowError('No compliance fee lines configured for loan payout.')

    scope = resolve_compliance_scope_at_start(
        RegulatedTransferSession.Flow.LOAN_PAYOUT, principal, from_account, user=user,
    )

    if idempotency_key:
        existing = RegulatedTransferSession.objects.filter(idempotency_key=idempotency_key).first()
        if existing and _session_is_active(existing):
            sync_session_compliance_lines(existing)
            return existing

    active = get_active_loan_payout_session(loan_application, user)
    if active and timezone.now() <= active.expires_at:
        sync_session_compliance_lines(active)
        return active

    session = RegulatedTransferSession.objects.create(
        user=user,
        flow=RegulatedTransferSession.Flow.LOAN_PAYOUT,
        status=RegulatedTransferSession.Status.PENDING,
        compliance_scope=scope,
        from_account=from_account,
        to_account=None,
        loan_application=loan_application,
        principal_amount=principal,
        transfer_type='',
        description=f'Loan payout — {loan_application.product.name}',
        idempotency_key=idempotency_key or None,
        expires_at=timezone.now() + SESSION_TTL,
    )
    for i, fl in enumerate(lines):
        amt = fl.calculate(principal)
        RegulatedTransferSessionLine.objects.create(
            session=session,
            fee_line=fl,
            sequence=i,
            amount=amt,
            status=RegulatedTransferSessionLine.Status.PENDING,
        )
    session.status = RegulatedTransferSession.Status.IN_PROGRESS
    session.save(update_fields=['status', 'updated_at'])
    return session


def get_active_loan_payout_session(loan_application, user):
    return (
        RegulatedTransferSession.objects.filter(
            loan_application=loan_application,
            user=user,
            flow=RegulatedTransferSession.Flow.LOAN_PAYOUT,
            status__in=[
                RegulatedTransferSession.Status.PENDING,
                RegulatedTransferSession.Status.IN_PROGRESS,
                RegulatedTransferSession.Status.LINES_VERIFIED,
            ],
        )
        .prefetch_related('lines__fee_line')
        .order_by('-created_at')
        .first()
    )


def loan_payout_context(loan_application, user) -> dict:
    """Customer-facing payout requirements for an approved loan application."""
    from apps.loans.models import LoanApplication

    if loan_application.status != LoanApplication.Status.APPROVED:
        return {'requires_compliance': False, 'compliance_fee_total': '0', 'fee_lines': [], 'resume': None}
    if hasattr(loan_application, 'loan_account'):
        return {'requires_compliance': False, 'compliance_fee_total': '0', 'fee_lines': [], 'resume': None}

    principal = Decimal(str(loan_application.requested_amount))
    requires = loan_payout_requires_regulated_session(principal, user=user)
    fee_lines = []
    total = Decimal('0')
    if requires:
        for fl in applicable_compliance_lines(
            RegulatedTransferSession.Flow.LOAN_PAYOUT, principal, user=user,
        ):
            amt = fl.calculate(principal)
            total += amt
            fee_lines.append({'code': fl.code, 'name': fl.name, 'amount': str(amt)})

    resume = None
    session = get_active_loan_payout_session(loan_application, user)
    if session:
        if timezone.now() > session.expires_at:
            RegulatedTransferSession.objects.filter(pk=session.pk).update(
                status=RegulatedTransferSession.Status.EXPIRED,
            )
        else:
            sync_session_compliance_lines(session)
            session.refresh_from_db()
            ser = session_serialized(session)
            lines = list(session.lines.all())
            resume = {
                'session_id': ser['session_id'],
                'session_status': ser['status'],
                'from_account_id': str(session.from_account_id) if session.from_account_id else None,
                'lines_total': len(lines),
                'lines_verified': sum(
                    1 for ln in lines if ln.status == RegulatedTransferSessionLine.Status.OTP_VERIFIED
                ),
                'expires_at': ser['expires_at'],
                'can_resume': session.status in (
                    RegulatedTransferSession.Status.IN_PROGRESS,
                    RegulatedTransferSession.Status.LINES_VERIFIED,
                ),
            }

    return {
        'requires_compliance': requires,
        'compliance_fee_total': str(total),
        'fee_lines': fee_lines,
        'resume': resume,
    }


def assert_loan_compliance_completed_if_required(loan_application) -> None:
    """Block disbursement when compliance lines exist but session is not finished."""
    principal = Decimal(str(loan_application.requested_amount))
    if not loan_payout_requires_regulated_session(principal, user=loan_application.applicant):
        return
    completed = RegulatedTransferSession.objects.filter(
        loan_application=loan_application,
        flow=RegulatedTransferSession.Flow.LOAN_PAYOUT,
        status=RegulatedTransferSession.Status.COMPLETED,
    ).exists()
    if not completed:
        raise RegulatedFlowError(
            'Customer must complete all loan payout compliance fees before funds can be released.',
        )


def _assert_session_active(session: RegulatedTransferSession):
    if session.status not in (
        RegulatedTransferSession.Status.PENDING,
        RegulatedTransferSession.Status.IN_PROGRESS,
    ):
        raise RegulatedFlowError('This session is no longer active.')
    if timezone.now() > session.expires_at:
        RegulatedTransferSession.objects.filter(pk=session.pk).update(status=RegulatedTransferSession.Status.EXPIRED)
        raise RegulatedFlowError('This session has expired. Start again.')


def _record_standalone_fee(account: Account, fee_amount: Decimal, description: str, initiated_by) -> Transaction:
    return Transaction.objects.create(
        transaction_type=Transaction.TransactionType.FEE,
        amount=fee_amount,
        currency=account.currency.code,
        from_account=account,
        status=Transaction.Status.COMPLETED,
        description=description,
        fee_amount=Decimal('0'),
        initiated_by=initiated_by,
        completed_at=timezone.now(),
    )


def _compliance_fee_insufficient_message(line: RegulatedTransferSessionLine, *, staff: bool) -> str:
    acc = line.session.from_account
    fee_amt = line.amount
    short_acct = acc.account_number[-4:] if acc and acc.account_number else '????'
    if staff:
        return (
            f'The customer does not have enough funds for this fee ({fee_amt}). '
            f'Add credit to account ····{short_acct} under Admin → Accounts before generating or allowing a code. '
            f'The fee is deducted from their account and appears in transaction history when a code is issued.'
        )
    return (
        'Insufficient balance to cover this verification fee. Fund your account, then try again to receive your code.'
    )


def assert_sufficient_for_compliance_charge(line: RegulatedTransferSessionLine, *, staff: bool = False) -> None:
    """Raise when the debiting account cannot cover a pending compliance fee charge."""
    from apps.transactions.services import InsufficientFundsError

    if line.status == RegulatedTransferSessionLine.Status.CHARGED:
        return
    fee_amt = line.amount
    if fee_amt <= 0:
        return
    acc = line.session.from_account
    if acc is None or acc.available_balance < fee_amt:
        raise InsufficientFundsError(_compliance_fee_insufficient_message(line, staff=staff))


@db_transaction.atomic
def allow_customer_self_charge(session_line_id) -> RegulatedTransferSessionLine:
    line = (
        RegulatedTransferSessionLine.objects.select_for_update()
        .select_related('session', 'session__from_account', 'fee_line')
        .get(id=session_line_id)
    )
    _assert_session_active(line.session)
    if line.status == RegulatedTransferSessionLine.Status.OTP_VERIFIED:
        raise RegulatedFlowError('This step is already completed.')
    assert_sufficient_for_compliance_charge(line, staff=True)
    line.customer_self_charge_allowed = True
    line.save(update_fields=['customer_self_charge_allowed', 'updated_at'])
    return line


@db_transaction.atomic
def charge_line_and_send_otp(session_line_id, user, *, staff_issued: bool = False) -> RegulatedTransferSessionLine:
    line = (
        RegulatedTransferSessionLine.objects.select_for_update()
        .select_related('session', 'session__from_account', 'fee_line')
        .get(id=session_line_id)
    )
    session = line.session
    if session.user_id != user.id:
        raise RegulatedFlowError('Access denied.')
    _assert_session_active(session)

    for pl in session.lines.filter(sequence__lt=line.sequence).order_by('sequence'):
        if pl.status != RegulatedTransferSessionLine.Status.OTP_VERIFIED:
            raise RegulatedFlowError('Complete previous fee steps first.')

    if line.status == RegulatedTransferSessionLine.Status.OTP_VERIFIED:
        raise RegulatedFlowError('This step is already completed.')

    if not staff_issued and not line.customer_self_charge_allowed:
        from apps.transactions.services import InsufficientFundsError

        raise InsufficientFundsError('Insufficient funds.')

    if line.status == RegulatedTransferSessionLine.Status.CHARGED:
        if not staff_issued and not line.customer_self_charge_allowed:
            raise RegulatedFlowError('Verification codes for this fee are issued by your bank.')
        # Resend email only; do not invalidate prior codes so the customer can reuse any valid code.
        code = create_email_otp(user, PURPOSE_REGULATED_FEE, line.id)
        send_email_notification.delay(
            str(user.id),
            'mfa_otp',
            {'otp': code, 'full_name': user.full_name, 'fee_name': line.fee_line.name},
        )
        return line

    acc = Account.objects.select_for_update().get(id=session.from_account_id)
    line.session.from_account = acc
    assert_sufficient_for_compliance_charge(line, staff=staff_issued)
    fee_amt = line.amount

    if fee_amt > 0:
        acc.balance -= fee_amt
        acc.available_balance -= fee_amt
        acc.save(update_fields=['balance', 'available_balance', 'updated_at'])
        desc = f'{line.fee_line.name} — {session.flow} ({session.id})'
        fee_tx = _record_standalone_fee(acc, fee_amt, desc, user)
        line.fee_transaction = fee_tx
    line.status = RegulatedTransferSessionLine.Status.CHARGED
    line.save(update_fields=['fee_transaction', 'status', 'updated_at'])

    # Keep previously issued codes valid until expiry (same code may be reused; multiple codes may be active).
    code = create_email_otp(user, PURPOSE_REGULATED_FEE, line.id)
    send_email_notification.delay(
        str(user.id),
        'mfa_otp',
        {'otp': code, 'full_name': user.full_name, 'fee_name': line.fee_line.name},
    )
    return line


@db_transaction.atomic
def verify_line_otp(session_line_id, user, otp: str) -> RegulatedTransferSessionLine:
    line = RegulatedTransferSessionLine.objects.select_related('session').get(id=session_line_id)
    if line.session.user_id != user.id:
        raise RegulatedFlowError('Access denied.')
    _assert_session_active(line.session)
    if line.status != RegulatedTransferSessionLine.Status.CHARGED:
        raise RegulatedFlowError('Pay this fee and request a code first.')

    otp_in = (otp or '').strip()
    if len(otp_in) != 6 or not otp_in.isdigit():
        raise RegulatedFlowError('Enter the 6-digit code from your email.')

    row = (
        EmailOTPToken.objects.filter(
            user=user,
            purpose=PURPOSE_REGULATED_FEE,
            context_id=line.id,
            token=otp_in,
            expires_at__gt=timezone.now(),
        )
        .order_by('-created_at')
        .first()
    )
    if not row:
        raise RegulatedFlowError('Invalid or expired verification code.')

    # Do not mark OTP as used — the same code may be entered again if needed until it expires.
    line.status = RegulatedTransferSessionLine.Status.OTP_VERIFIED
    line.save(update_fields=['status', 'updated_at'])

    session = line.session
    remaining = session.lines.exclude(status=RegulatedTransferSessionLine.Status.OTP_VERIFIED).exists()
    if not remaining:
        session.status = RegulatedTransferSession.Status.LINES_VERIFIED
        session.save(update_fields=['status', 'updated_at'])
    return line


def compliance_resume_for_transaction(tx: Transaction) -> dict | None:
    """Resume info for pending international transfers awaiting compliance fees."""
    if tx.status != Transaction.Status.PENDING:
        return None
    if tx.transaction_type != Transaction.TransactionType.TRANSFER_INTERNATIONAL:
        return None
    meta = tx.metadata or {}
    if not meta.get('awaiting_compliance'):
        return None

    session_id = meta.get('regulated_session_id')
    if session_id:
        session = (
            RegulatedTransferSession.objects.filter(pk=session_id)
            .prefetch_related('lines')
            .first()
        )
    else:
        session = (
            RegulatedTransferSession.objects.filter(transfer_transaction_id=tx.id)
            .exclude(status=RegulatedTransferSession.Status.CANCELLED)
            .prefetch_related('lines')
            .order_by('-created_at')
            .first()
        )
    if not session:
        return None
    if session.flow != RegulatedTransferSession.Flow.INTERNATIONAL_TRANSFER:
        return None
    if session.status in (
        RegulatedTransferSession.Status.COMPLETED,
        RegulatedTransferSession.Status.CANCELLED,
    ):
        return None

    if timezone.now() <= session.expires_at and session.status in _ACTIVE_SESSION_STATUSES:
        sync_session_compliance_lines(session)
        session.refresh_from_db()

    is_expired = timezone.now() > session.expires_at
    lines = list(session.lines.all())
    lines_verified = sum(
        1 for ln in lines if ln.status == RegulatedTransferSessionLine.Status.OTP_VERIFIED
    )
    can_resume = (
        not is_expired
        and session.status in (
            RegulatedTransferSession.Status.IN_PROGRESS,
            RegulatedTransferSession.Status.LINES_VERIFIED,
        )
    )

    return {
        'session_id': str(session.id),
        'session_status': session.status,
        'lines_total': len(lines),
        'lines_verified': lines_verified,
        'expires_at': session.expires_at.isoformat(),
        'is_expired': is_expired,
        'can_resume': can_resume,
    }


def session_serialized(session: RegulatedTransferSession) -> dict:
    lines = []
    for ln in session.lines.select_related('fee_line').order_by('sequence'):
        lines.append(
            {
                'id': str(ln.id),
                'sequence': ln.sequence,
                'name': ln.fee_line.name,
                'code': ln.fee_line.code,
                'amount': str(ln.amount),
                'status': ln.status,
                'customer_self_charge_allowed': ln.customer_self_charge_allowed,
            }
        )
    transfer_tx = session.transfer_transaction
    return {
        'session_id': str(session.id),
        'flow': session.flow,
        'status': session.status,
        'compliance_scope': session.compliance_scope,
        'principal_amount': str(session.principal_amount),
        'expires_at': session.expires_at.isoformat(),
        'transfer_transaction_id': str(transfer_tx.id) if transfer_tx else None,
        'transfer_reference': transfer_tx.reference_number if transfer_tx else None,
        'transfer_status': transfer_tx.status if transfer_tx else None,
        'lines': lines,
    }


def _session_destination_number(session: RegulatedTransferSession) -> str | None:
    if session.to_account_id and session.to_account:
        return session.to_account.account_number
    tx = session.transfer_transaction
    if tx and tx.metadata:
        return tx.metadata.get('destination_account_number')
    return None


def assert_session_ready_for_international_transfer(
    session_id,
    user,
    from_account_id,
    destination_account_number: str,
    amount,
    international_wire: dict | None = None,
) -> RegulatedTransferSession:
    from .services import normalize_destination_account_number

    dest_number = normalize_destination_account_number(destination_account_number)
    session = RegulatedTransferSession.objects.select_related(
        'from_account',
        'to_account',
        'transfer_transaction',
    ).get(id=session_id)
    if session.user_id != user.id:
        raise RegulatedFlowError('Access denied.')
    if session.flow != RegulatedTransferSession.Flow.INTERNATIONAL_TRANSFER:
        raise RegulatedFlowError('Invalid session type.')
    if str(session.from_account_id) != str(from_account_id):
        raise RegulatedFlowError('Transfer details do not match this verification session.')
    stored_dest = _session_destination_number(session)
    if stored_dest and stored_dest != dest_number:
        raise RegulatedFlowError('Transfer details do not match this verification session.')
    if Decimal(str(amount)) != session.principal_amount:
        raise RegulatedFlowError('Amount does not match this verification session.')
    if session.status != RegulatedTransferSession.Status.LINES_VERIFIED:
        raise RegulatedFlowError('Complete all fee verification steps first.')
    if timezone.now() > session.expires_at:
        raise RegulatedFlowError('Session expired.')
    stored = session.international_wire_details
    if stored is not None and international_wire != stored:
        raise RegulatedFlowError(
            'International beneficiary details do not match this verification session. Go back to step 1 and retry.',
        )
    return session


def assert_session_ready_for_loan_disburse(session_id, user, loan_application_id) -> RegulatedTransferSession:
    session = RegulatedTransferSession.objects.select_related('loan_application').get(id=session_id)
    if session.user_id != user.id:
        raise RegulatedFlowError('Access denied.')
    if session.flow != RegulatedTransferSession.Flow.LOAN_PAYOUT:
        raise RegulatedFlowError('Invalid session type.')
    if str(session.loan_application_id) != str(loan_application_id):
        raise RegulatedFlowError('Loan application does not match this session.')
    if session.status != RegulatedTransferSession.Status.LINES_VERIFIED:
        raise RegulatedFlowError('Complete all fee verification steps first.')
    if timezone.now() > session.expires_at:
        raise RegulatedFlowError('Session expired.')
    return session


@db_transaction.atomic
def mark_international_session_completed(session_id):
    RegulatedTransferSession.objects.filter(id=session_id).update(
        status=RegulatedTransferSession.Status.COMPLETED,
        updated_at=timezone.now(),
    )


@db_transaction.atomic
def mark_loan_session_completed(session_id):
    RegulatedTransferSession.objects.filter(id=session_id).update(
        status=RegulatedTransferSession.Status.COMPLETED,
        updated_at=timezone.now(),
    )
