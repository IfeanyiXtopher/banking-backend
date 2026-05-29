"""Short in-app notification copy (highlights only, max two sentences)."""
from __future__ import annotations

import re

_MAX_SENTENCES = 2


def _two_sentences(*parts: str) -> str:
    text = ' '.join(p.strip() for p in parts if p and p.strip())
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return ' '.join(sentences[:_MAX_SENTENCES]).strip()


def in_app_event_type_for_email(event_type: str, context: dict) -> str | None:
    if event_type == 'transaction' and context.get('direction') == 'credit':
        return 'DEPOSIT'
    if event_type == 'loan_approved':
        return 'LOAN_APPROVED'
    if event_type == 'compliance_fee_otp':
        return 'COMPLIANCE_OTP_SENT'
    if event_type == 'compliance_payment_confirmed':
        return 'COMPLIANCE_PAYMENT_CONFIRMED'
    return None


def build_in_app_notification(event_type: str, context: dict) -> tuple[str, str] | None:
    """
    Returns (subject, body) for the notification center, or None if this email should not
    create an in-app alert.
    """
    user = context.get('user')
    name = (context.get('full_name') or getattr(user, 'full_name', None) or '').strip()
    greeting = f'Hi {name}, ' if name else ''

    if event_type == 'transaction' and context.get('direction') == 'credit':
        currency = context.get('currency', '')
        amount = context.get('amount', '')
        ref = context.get('reference', '')
        return (
            'Deposit received',
            _two_sentences(
                f'{greeting}We credited {currency} {amount} to your account.',
                f'Reference: {ref}.' if ref else '',
            ),
        )

    if event_type == 'loan_approved':
        product = context.get('product_name') or context.get('loan_type') or 'loan'
        return (
            'Loan approved',
            _two_sentences(
                f'{greeting}Your {product} application was approved.',
                'Sign in to complete the next payout steps.',
            ),
        )

    if event_type == 'compliance_fee_otp':
        fee = context.get('fee_name') or 'compliance fee'
        return (
            'Verification code sent',
            _two_sentences(
                f'{greeting}We sent a verification code for {fee} to your email.',
                'Check your inbox — codes are never shown in the app for your security.',
            ),
        )

    if event_type == 'compliance_payment_confirmed':
        fee = context.get('fee_name') or 'compliance fee'
        return (
            'Payment confirmed',
            _two_sentences(
                f'{greeting}We confirmed your {fee} payment.',
                'You will receive a verification code by email when it is ready.',
            ),
        )

    return None


IN_APP_EVENT_TYPES = frozenset({
    'DEPOSIT',
    'LOAN_APPROVED',
    'COMPLIANCE_OTP_SENT',
    'COMPLIANCE_PAYMENT_CONFIRMED',
})
