"""Shared helpers for email (or MFA) OTP tokens."""
import random
import uuid
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import EmailOTPToken

# Purposes stored on EmailOTPToken — mirrored in admin portal filters.
PURPOSE_LOGIN_MFA = 'login_mfa'
PURPOSE_TRANSFER_AUTH = 'transfer_auth'
PURPOSE_REGULATED_FEE = 'regulated_fee'

OTP_PURPOSE_LABELS = {
    PURPOSE_LOGIN_MFA: 'Login MFA',
    PURPOSE_TRANSFER_AUTH: 'Transfer verification',
    PURPOSE_REGULATED_FEE: 'Compliance fee verification',
}


def otp_purpose_label(purpose: str) -> str:
    return OTP_PURPOSE_LABELS.get(purpose, purpose.replace('_', ' ').title())


def create_email_otp(user, purpose: str, context_id: uuid.UUID | None = None) -> str:
    """Create a 6-digit OTP for this user and purpose. Returns the plaintext code."""
    token = f'{random.randint(0, 999_999):06d}'
    validity = getattr(settings, 'OTP_EMAIL_TOKEN_VALIDITY', 300)
    EmailOTPToken.objects.create(
        user=user,
        token=token,
        purpose=purpose,
        context_id=context_id,
        expires_at=timezone.now() + timedelta(seconds=validity),
    )
    return token


def invalidate_unused_email_otps(user, purpose: str, context_id: uuid.UUID | None = None) -> None:
    """Mark outstanding OTPs for this purpose (and optional context) as used."""
    qs = EmailOTPToken.objects.filter(user=user, purpose=purpose, is_used=False)
    if context_id is not None:
        qs = qs.filter(context_id=context_id)
    qs.update(is_used=True)