"""
Branded wrapper for all outgoing SafaPay Bank emails (header + footer).
"""
from __future__ import annotations

import re
from datetime import datetime

from django.conf import settings
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.utils.html import escape, linebreaks

from .email_assets import logo_image_src, public_assets_base

BANK_NAME = 'SafaPay Bank'
BANK_TAGLINE = 'Purity, clarity, and trust'
SUPPORT_EMAIL = getattr(settings, 'SUPPORT_EMAIL', 'support@safapay.bank')


def get_from_email() -> str:
    """From header for outgoing mail; ensures a display name when .env is bare address."""
    raw = (getattr(settings, 'DEFAULT_FROM_EMAIL', '') or '').strip()
    if not raw:
        user = (getattr(settings, 'EMAIL_HOST_USER', '') or '').strip()
        return f'{BANK_NAME} <{user}>' if user else BANK_NAME
    if '@' in raw and '<' not in raw and '>' not in raw:
        return f'{BANK_NAME} <{raw}>'
    return raw


EMAIL_SUBJECTS = {
    'registration': 'Welcome to SafaPay Bank — Account Created',
    'password_reset': 'Reset Your Password',
    'mfa_otp': 'Your Verification Code',
    'transaction': 'Transaction Alert',
    'low_balance': 'Low Balance Alert',
    'loan_approved': 'Loan Application Approved',
    'loan_rejected': 'Loan Application Update',
    'loan_payment_due': 'Loan Payment Reminder',
    'statement_ready': 'Your Statement is Ready',
    'support_update': 'Support Ticket Update',
    'security_alert': 'Security Alert — Action Required',
    'profile_update_approved': 'Your profile update was approved',
    'goal_autosave_success': 'Money moved to your savings goal',
    'goal_autosave_insufficient': 'Savings goal — add funds to your account',
}


def fallback_body(event_type: str, context: dict) -> str:
    if event_type == 'mfa_otp':
        extra = context.get('fee_name')
        base = f"Your verification code is: {context.get('otp')}. Valid for 5 minutes."
        if extra:
            return f"{extra}: {base}"
        return base
    if event_type == 'password_reset':
        return f"Click the link to reset your password: {context.get('token')}"
    if event_type == 'transaction':
        return (
            f"Transaction alert: {context.get('tx_type')} of "
            f"{context.get('currency')} {context.get('amount')} "
            f"(Ref: {context.get('reference')})"
        )
    if event_type == 'profile_update_approved':
        return (
            f"Hello {context.get('full_name') or context.get('user')}, "
            'your profile change request was approved and your details are updated.'
        )
    if event_type == 'goal_autosave_success':
        return (
            f"We moved {context.get('amount')} to your goal “{context.get('goal_title')}” "
            f"({context.get('plan_label')}). Saved so far: {context.get('new_saved_balance')}."
        )
    if event_type == 'goal_autosave_insufficient':
        return (
            f"We couldn’t move {context.get('amount')} to “{context.get('goal_title')}” "
            f"({context.get('plan_label')}) — available in your primary account is only "
            f"{context.get('available_balance')}. Add funds to your primary account to keep "
            'this goal on track.'
        )
    if event_type == 'support_update':
        return (
            f"Hello {context.get('full_name') or 'there'},\n\n"
            f"We replied to your support ticket #{context.get('ticket_number')} "
            f"({context.get('subject')}).\n\n"
            f"Current status: {context.get('status')}\n\n"
            f"{context.get('staff_reply', '').strip()}\n\n"
            '— SafaPay Bank Support'
        )
    return f"You have a new notification: {event_type}"


def get_frontend_base_url() -> str:
    origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', None) or []
    if isinstance(origins, str):
        origins = [origins]
    if origins:
        return origins[0].strip().rstrip('/')
    return ''


def get_sign_in_url() -> str:
    base = get_frontend_base_url()
    return f'{base}/auth/signin' if base else ''


def get_email_brand_context() -> dict:
    year = datetime.now().year
    # Header logo: HTTPS only when EMAIL_ASSETS_BASE_URL is public; else HTML wordmark (Gmail-safe).
    custom_logo = (getattr(settings, 'EMAIL_LOGO_URL', '') or '').strip()
    logo_src = logo_image_src(custom_logo)
    use_logo_image = bool(logo_src) and (
        custom_logo.startswith('https://') or bool(public_assets_base())
    )

    def _social_url(key: str) -> str:
        return (getattr(settings, key, '') or '').strip() or '#'

    # HTML icon boxes (Gmail-safe) — X, Facebook, LinkedIn only.
    social_icons = [
        {'label': 'X (Twitter)', 'glyph': '𝕏', 'url': _social_url('EMAIL_SOCIAL_TWITTER')},
        {'label': 'Facebook', 'glyph': 'f', 'url': _social_url('EMAIL_SOCIAL_FACEBOOK')},
        {'label': 'LinkedIn', 'glyph': 'in', 'url': _social_url('EMAIL_SOCIAL_LINKEDIN')},
    ]

    return {
        'bank_name': BANK_NAME,
        'bank_tagline': BANK_TAGLINE,
        'support_email': SUPPORT_EMAIL,
        'copyright_year': year,
        'logo_src': logo_src if use_logo_image else '',
        'has_logo': use_logo_image,
        'primary_color': '#152a1e',
        'accent_color': '#c8f000',
        'social_icons': social_icons,
        'sign_in_url': get_sign_in_url(),
    }


def plain_text_to_html(text: str) -> str:
    """Turn plain-text email bodies into simple HTML paragraphs."""
    cleaned = text.strip()
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    # Drop legacy per-template sign-offs; global footer is in base.html.
    cleaned = re.sub(
        r'\n*Best regards,?\s*\n*SafaPay Bank Team\s*$',
        '',
        cleaned,
        flags=re.IGNORECASE,
    )
    return linebreaks(escape(cleaned))


def wrap_text_body(inner_text: str, extra_context: dict | None = None) -> str:
    ctx = {**get_email_brand_context(), **(extra_context or {})}
    ctx['email_body'] = inner_text.strip()
    return render_to_string('emails/base.txt', ctx)


def wrap_html_body(inner_html: str, extra_context: dict | None = None) -> str:
    ctx = {**get_email_brand_context(), **(extra_context or {})}
    ctx['email_body'] = inner_html
    return render_to_string('emails/base.html', ctx)


def render_event_email(event_type: str, context: dict) -> tuple[str, str, str]:
    """
    Returns (subject, plain_text_body, html_body) with branded header and footer.
    """
    subject = EMAIL_SUBJECTS.get(event_type, 'SafaPay Bank Notification')
    ctx = {**get_email_brand_context(), **context, 'email_subject': subject}

    try:
        inner_text = render_to_string(f'emails/{event_type}.txt', ctx)
    except TemplateDoesNotExist:
        inner_text = fallback_body(event_type, context)

    text_body = wrap_text_body(inner_text, ctx)

    try:
        inner_html = render_to_string(f'emails/{event_type}.html', ctx)
    except TemplateDoesNotExist:
        inner_html = plain_text_to_html(inner_text)

    html_body = wrap_html_body(inner_html, ctx)
    return subject, text_body, html_body


def render_custom_email(
    *,
    subject: str,
    text_body: str,
    html_body: str | None = None,
    extra_context: dict | None = None,
) -> tuple[str, str, str]:
    """Wrap arbitrary subject/body (e.g. samples, one-off sends)."""
    ctx = {**get_email_brand_context(), **(extra_context or {}), 'email_subject': subject}
    wrapped_text = wrap_text_body(text_body, ctx)
    inner_html = html_body if html_body is not None else plain_text_to_html(text_body)
    wrapped_html = wrap_html_body(inner_html, ctx)
    return subject, wrapped_text, wrapped_html
