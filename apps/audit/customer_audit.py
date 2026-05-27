"""Customer-facing activity audit helpers."""

from __future__ import annotations

import json
import re
from typing import Any

from django.contrib.auth import get_user_model

from .middleware import AuditMiddleware
from .models import AuditLog, log_action

User = get_user_model()

_SENSITIVE_KEYS = frozenset({
    'password', 'old_password', 'new_password', 'current_password',
    'otp', 'token', 'refresh', 'access', 'secret', 'mfa_secret',
})

_SKIP_PREFIXES = (
    '/api/admin-portal/',
    '/api/schema/',
    '/api/docs/',
    '/api/redoc/',
    '/django-admin/',
    '/__debug__/',
)

_SKIP_EXACT = {
    '/api/auth/token/refresh/',
}

_SKIP_CONTAINS = (
    '/preview/',
    '/transfer/preview/',
)

_MUTATING = frozenset({'POST', 'PUT', 'PATCH', 'DELETE'})

_UUID_RE = re.compile(
    r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
    re.I,
)


def mark_audit_handled(request) -> None:
    request._customer_audit_handled = True


def is_audit_handled(request) -> bool:
    return getattr(request, '_customer_audit_handled', False)


def sanitize_payload(data: Any, *, max_str: int = 500) -> Any:
    if isinstance(data, dict):
        out = {}
        for k, v in data.items():
            key = str(k).lower()
            if key in _SENSITIVE_KEYS:
                out[k] = '[redacted]'
            else:
                out[k] = sanitize_payload(v, max_str=max_str)
        return out
    if isinstance(data, list):
        return [sanitize_payload(x, max_str=max_str) for x in data[:50]]
    if isinstance(data, str) and len(data) > max_str:
        return data[:max_str] + '…'
    return data


def request_payload(request) -> dict:
    try:
        if hasattr(request, 'data') and request.data:
            raw = request.data
            if hasattr(raw, 'dict'):
                return sanitize_payload(dict(raw))
            if isinstance(raw, dict):
                return sanitize_payload(raw)
    except Exception:
        pass
    return {}


def response_payload(response) -> dict:
    try:
        if getattr(response, 'content', None):
            body = json.loads(response.content.decode('utf-8'))
            if isinstance(body, dict):
                return sanitize_payload(body)
    except Exception:
        pass
    return {}


def log_customer_activity(
    request,
    *,
    action: str,
    target_model: str = '',
    target_id: str = '',
    description: str = '',
    old_value: dict | None = None,
    new_value: dict | None = None,
    actor=None,
) -> None:
    user = actor or getattr(request, 'user', None)
    if not user or not getattr(user, 'is_authenticated', False):
        return
    if not getattr(user, 'is_customer', False):
        return
    log_action(
        actor=user,
        action=action,
        target_model=target_model,
        target_id=target_id,
        old_value=old_value,
        new_value=new_value,
        description=description,
        ip_address=AuditMiddleware.get_client_ip(request),
        user_agent=(request.META.get('HTTP_USER_AGENT') or '')[:512],
    )
    mark_audit_handled(request)


def log_customer_by_email(
    request,
    email: str,
    *,
    action: str,
    target_model: str = '',
    target_id: str = '',
    description: str = '',
    new_value: dict | None = None,
) -> None:
    """Log activity for a customer identified by email (e.g. before session exists)."""
    actor = None
    desc = description
    try:
        user = User.objects.get(email__iexact=email.strip())
        if user.is_customer:
            actor = user
        elif not desc:
            desc = f'Non-customer account: {email}'
    except User.DoesNotExist:
        if not desc:
            desc = f'Unknown email: {email}'
    log_action(
        actor=actor,
        action=action,
        target_model=target_model,
        target_id=target_id or (str(actor.pk) if actor else ''),
        new_value=new_value,
        description=desc or description,
        ip_address=AuditMiddleware.get_client_ip(request),
        user_agent=(request.META.get('HTTP_USER_AGENT') or '')[:512],
    )


def _first_uuid(*candidates: str) -> str:
    for c in candidates:
        if not c:
            continue
        m = _UUID_RE.search(str(c))
        if m:
            return m.group(0)
    return ''


def resolve_customer_activity(request, response) -> tuple[str, str, str, str, dict | None] | None:
    """Return (action, target_model, target_id, description, new_value) or None to skip."""
    path = request.path.rstrip('/') or '/'
    method = request.method.upper()

    if method not in _MUTATING:
        return None
    if any(path.startswith(p) for p in _SKIP_PREFIXES):
        return None
    if path in _SKIP_EXACT or any(s in path for s in _SKIP_CONTAINS):
        return None

    body = request_payload(request)
    resp = response_payload(response) if 200 <= response.status_code < 300 else {}

    # ── Auth (authenticated) ─────────────────────────────────────────────
    if path == '/api/auth/logout' and method == 'POST':
        return (
            AuditLog.Action.LOGOUT,
            'Session',
            '',
            'Customer signed out',
            body,
        )
    if path == '/api/auth/profile' and method in ('PUT', 'PATCH'):
        return (
            AuditLog.Action.UPDATE,
            'CustomUser',
            str(request.user.pk),
            'Updated profile',
            {**body, **{k: resp.get(k) for k in ('email', 'full_name', 'phone') if k in resp}},
        )
    if path == '/api/auth/profile/update-request' and method == 'POST':
        return (
            AuditLog.Action.CREATE,
            'ProfileChangeRequest',
            _first_uuid(str(resp.get('id', ''))),
            'Submitted profile change for admin approval',
            body,
        )
    if path == '/api/auth/change-password' and method == 'POST':
        return (
            AuditLog.Action.UPDATE,
            'CustomUser',
            str(request.user.pk),
            'Changed account password',
            None,
        )
    if path == '/api/auth/kyc/upload' and method == 'POST':
        return (
            AuditLog.Action.KYC_UPDATE,
            'CustomUser',
            str(request.user.pk),
            'Submitted KYC document',
            {'kyc_status': resp.get('kyc_status', 'SUBMITTED')},
        )
    if path == '/api/auth/mfa/toggle' and method == 'POST':
        return (
            AuditLog.Action.UPDATE,
            'CustomUser',
            str(request.user.pk),
            resp.get('detail', 'Toggled MFA'),
            {'is_mfa_enabled': request.user.is_mfa_enabled},
        )

    # ── Accounts ───────────────────────────────────────────────────────────
    if path == '/api/accounts' and method == 'POST':
        acc = resp.get('id') or resp.get('account_number', '')
        return (
            AuditLog.Action.CREATE,
            'Account',
            _first_uuid(str(acc)),
            f"Opened account {resp.get('account_type', '')} {resp.get('currency', '')}".strip(),
            resp,
        )
    m = re.match(r'^/api/accounts/([0-9a-f-]{36})$', path, re.I)
    if m and method in ('PUT', 'PATCH'):
        return (
            AuditLog.Action.UPDATE,
            'Account',
            m.group(1),
            'Updated account settings',
            body,
        )

    # ── Transactions ─────────────────────────────────────────────────────
    if path == '/api/transactions/deposit' and method == 'POST':
        return _transaction_audit('Deposit', body, resp)
    if path == '/api/transactions/withdraw' and method == 'POST':
        return _transaction_audit('Withdrawal', body, resp)
    if path == '/api/transactions/transfer' and method == 'POST':
        return _transaction_audit('Transfer', body, resp)
    if path == '/api/transactions/transfer/send-otp' and method == 'POST':
        return (
            AuditLog.Action.UPDATE,
            'Transfer',
            body.get('from_account_id', ''),
            'Requested transfer email verification code',
            sanitize_payload(body),
        )

    if path.startswith('/api/transactions/regulated-sessions/'):
        return _regulated_session_audit(path, method, body, resp)

    # ── Loans ──────────────────────────────────────────────────────────────
    if path == '/api/loans/applications' and method == 'POST':
        return (
            AuditLog.Action.CREATE,
            'LoanApplication',
            _first_uuid(str(resp.get('id', ''))),
            _loan_application_description(body, resp),
            resp,
        )
    if '/regulated-payout/' in path and method == 'POST':
        app_id = _first_uuid(path)
        if 'start' in path:
            return (
                AuditLog.Action.UPDATE,
                'LoanApplication',
                app_id,
                'Started loan payout compliance session',
                body,
            )
        return (
            AuditLog.Action.TRANSACTION,
            'LoanApplication',
            app_id,
            'Completed loan payout / disbursement to account',
            {**body, **{k: resp[k] for k in ('reference_number', 'transaction_id') if k in resp}},
        )
    if path == '/api/loans/payment' and method == 'POST':
        return (
            AuditLog.Action.TRANSACTION,
            'LoanAccount',
            str(body.get('loan_account_id', '')),
            f"Loan repayment {body.get('amount', '')} from account {body.get('account_id', '')}".strip(),
            resp,
        )

    # ── Cards ──────────────────────────────────────────────────────────────
    if path == '/api/cards/request' and method == 'POST':
        return (
            AuditLog.Action.CREATE,
            'CardIssuance',
            _first_uuid(str(resp.get('id', ''))),
            'Requested new debit card',
            resp,
        )
    if path == '/api/cards/request-replacement' and method == 'POST':
        return (
            AuditLog.Action.CREATE,
            'CardIssuance',
            _first_uuid(str(resp.get('id', ''))),
            'Requested card replacement',
            resp,
        )
    if re.match(r'^/api/cards/issuances/[0-9a-f-]{36}/pay$', path, re.I) and method == 'POST':
        return (
            AuditLog.Action.TRANSACTION,
            'CardIssuance',
            _first_uuid(path),
            'Paid card issuance fee',
            resp,
        )

    # ── Payments ─────────────────────────────────────────────────────────
    if path == '/api/payments/bill-pay' and method == 'POST':
        return (
            AuditLog.Action.TRANSACTION,
            'BillPayment',
            _first_uuid(str(resp.get('id', resp.get('reference_number', '')))),
            _bill_pay_description(body, resp),
            resp,
        )

    # ── Savings ──────────────────────────────────────────────────────────
    if path == '/api/savings-goals' and method == 'POST':
        return (
            AuditLog.Action.CREATE,
            'SavingsGoal',
            _first_uuid(str(resp.get('id', ''))),
            f"Created savings goal: {body.get('name') or resp.get('name', '')}".strip(),
            resp,
        )
    m = re.match(r'^/api/savings-goals/([0-9a-f-]{36})$', path, re.I)
    if m and method in ('PUT', 'PATCH'):
        return (
            AuditLog.Action.UPDATE,
            'SavingsGoal',
            m.group(1),
            'Updated savings goal',
            body,
        )
    if re.match(r'^/api/savings-goals/[0-9a-f-]{36}/cancel$', path, re.I) and method == 'POST':
        return (
            AuditLog.Action.UPDATE,
            'SavingsGoal',
            _first_uuid(path),
            'Cancelled savings goal',
            body,
        )
    if re.match(r'^/api/savings-goals/[0-9a-f-]{36}/allocate$', path, re.I) and method == 'POST':
        return (
            AuditLog.Action.TRANSACTION,
            'SavingsGoal',
            _first_uuid(path),
            f"Allocated {body.get('amount', '')} to savings goal",
            resp,
        )

    # ── Support ────────────────────────────────────────────────────────────
    if path == '/api/support' and method == 'POST':
        return (
            AuditLog.Action.CREATE,
            'SupportTicket',
            _first_uuid(str(resp.get('id', ''))),
            f"Opened support ticket: {body.get('subject') or resp.get('subject', '')}".strip(),
            resp,
        )
    if re.match(r'^/api/support/[0-9a-f-]{36}/message$', path, re.I) and method == 'POST':
        return (
            AuditLog.Action.UPDATE,
            'SupportTicket',
            _first_uuid(path),
            'Added message to support ticket',
            sanitize_payload({'message_preview': str(body.get('body', ''))[:200]}),
        )
    if re.match(r'^/api/support/[0-9a-f-]{36}/close$', path, re.I) and method == 'POST':
        return (
            AuditLog.Action.UPDATE,
            'SupportTicket',
            _first_uuid(path),
            'Closed support ticket',
            None,
        )

    # ── Statements ─────────────────────────────────────────────────────────
    if path == '/api/statements/request' and method == 'POST':
        return (
            AuditLog.Action.CREATE,
            'Statement',
            _first_uuid(str(resp.get('id', ''))),
            'Requested account statement',
            body,
        )
    if re.match(r'^/api/statements/[0-9a-f-]{36}/download$', path, re.I) and method in ('GET', 'POST'):
        return (
            AuditLog.Action.VIEW_SENSITIVE,
            'Statement',
            _first_uuid(path),
            'Downloaded account statement',
            None,
        )

    # ── Notifications ──────────────────────────────────────────────────────
    if path == '/api/notifications/read-all' and method == 'POST':
        return (
            AuditLog.Action.UPDATE,
            'Notification',
            '',
            'Marked all notifications as read',
            None,
        )
    if path == '/api/notifications/preferences' and method in ('PUT', 'PATCH'):
        return (
            AuditLog.Action.UPDATE,
            'NotificationPreference',
            str(request.user.pk),
            'Updated notification preferences',
            body,
        )
    if re.match(r'^/api/notifications/[0-9a-f-]{36}/read$', path, re.I) and method == 'POST':
        return (
            AuditLog.Action.UPDATE,
            'Notification',
            _first_uuid(path),
            'Marked notification as read',
            None,
        )
    if re.match(r'^/api/notifications/[0-9a-f-]{36}$', path, re.I) and method == 'DELETE':
        return (
            AuditLog.Action.DELETE,
            'Notification',
            _first_uuid(path),
            'Deleted notification',
            None,
        )

    # Fallback for any other customer API mutation
    if path.startswith('/api/'):
        label = path.replace('/api/', '').replace('/', ' › ')
        return (
            AuditLog.Action.UPDATE,
            'API',
            '',
            f'{method} {label}',
            {'request': body, 'response': resp} if body or resp else None,
        )
    return None


def _transaction_audit(label: str, body: dict, resp: dict):
    ref = resp.get('reference_number', '')
    amount = resp.get('amount') or body.get('amount', '')
    tx_type = resp.get('transaction_type', label)
    desc = f'{label}: {amount} ({tx_type})'
    if ref:
        desc += f' ref {ref}'
    return (
        AuditLog.Action.TRANSACTION,
        'Transaction',
        _first_uuid(str(resp.get('id', ''))),
        desc,
        resp,
    )


def _regulated_session_audit(path: str, method: str, body: dict, resp: dict):
    sid = _first_uuid(path)
    if 'intl/start' in path:
        return (
            AuditLog.Action.CREATE,
            'RegulatedSession',
            sid or str(resp.get('session_id', '')),
            'Started international transfer compliance session',
            resp,
        )
    if 'complete-transfer' in path:
        return (
            AuditLog.Action.TRANSACTION,
            'RegulatedSession',
            sid,
            'Completed international transfer after compliance',
            resp,
        )
    if 'charge-send-otp' in path:
        return (
            AuditLog.Action.UPDATE,
            'RegulatedSession',
            sid,
            'Paid compliance fee line (OTP sent)',
            body,
        )
    if 'verify-otp' in path:
        return (
            AuditLog.Action.UPDATE,
            'RegulatedSession',
            sid,
            'Verified compliance fee line OTP',
            None,
        )
    return (
        AuditLog.Action.UPDATE,
        'RegulatedSession',
        sid,
        f'Regulated session {method}',
        body,
    )


def _loan_application_description(body: dict, resp: dict) -> str:
    product = resp.get('product_name') or body.get('product_id', 'loan')
    amount = resp.get('requested_amount') or body.get('requested_amount', '')
    term = resp.get('term_months') or body.get('term_months', '')
    parts = [f'Applied for {product}']
    if amount:
        parts.append(f'amount {amount}')
    if term:
        parts.append(f'term {term} mo')
    return ', '.join(parts)


def _bill_pay_description(body: dict, resp: dict) -> str:
    service = body.get('service_id') or body.get('biller_name', 'bill')
    amount = body.get('amount') or resp.get('amount', '')
    return f'Bill payment to {service}: {amount}'.strip()


def maybe_audit_customer_request(request, response) -> None:
    if is_audit_handled(request):
        return
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return
    if not getattr(request.user, 'is_customer', False):
        return
    if response.status_code < 200 or response.status_code >= 300:
        return

    # Sensitive read: statement PDF download
    if request.method == 'GET' and re.match(
        r'^/api/statements/[0-9a-f-]{36}/download$', request.path.rstrip('/'), re.I
    ):
        log_customer_activity(
            request,
            action=AuditLog.Action.VIEW_SENSITIVE,
            target_model='Statement',
            target_id=_first_uuid(request.path),
            description='Downloaded account statement',
        )
        return

    if request.method.upper() not in _MUTATING:
        return

    resolved = resolve_customer_activity(request, response)
    if not resolved:
        return
    action, target_model, target_id, description, new_value = resolved
    log_customer_activity(
        request,
        action=action,
        target_model=target_model,
        target_id=target_id,
        description=description,
        new_value=new_value,
    )
