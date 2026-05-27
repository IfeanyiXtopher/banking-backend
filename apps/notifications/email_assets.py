"""
Email images: local Lucide PNGs (same as landing footer), NOT Font Awesome or remote CDNs.

Gmail SMTP often breaks cid: inline images. We therefore:
  1. Prefer HTTPS URLs when EMAIL_ASSETS_BASE_URL (or a public FRONTEND_URL) is set.
  2. Otherwise embed PNGs via MIME Content-ID with a Gmail-safe multipart/related layout.
"""
from __future__ import annotations

import re
from email.mime.image import MIMEImage
from pathlib import Path

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

_ASSETS_DIR = Path(__file__).resolve().parent / 'static' / 'email'

# Content-ID → filename (Lucide icons from landing SOCIAL_LINKS)
INLINE_IMAGE_CIDS = (
    ('sp-logo', 'logo-white.png'),
    ('sp-icon-twitter', 'icon-twitter.png'),
    ('sp-icon-facebook', 'icon-facebook.png'),
    ('sp-icon-instagram', 'icon-instagram.png'),
    ('sp-icon-linkedin', 'icon-linkedin.png'),
    ('sp-icon-youtube', 'icon-youtube.png'),
)

_CID_PATTERN = re.compile(r'\bcid:([a-z0-9-]+)\b', re.I)


def cid_src(content_id: str) -> str:
    return f'cid:{content_id}'


def public_assets_base() -> str:
    """HTTPS origin for /email/*.png (must be publicly reachable — not localhost)."""
    explicit = (getattr(settings, 'EMAIL_ASSETS_BASE_URL', '') or '').strip().rstrip('/')
    if explicit:
        return explicit
    origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', None) or []
    if isinstance(origins, str):
        origins = [origins]
    for origin in origins:
        base = origin.strip().rstrip('/')
        if not base.startswith('https://'):
            continue
        if 'localhost' in base or '127.0.0.1' in base:
            continue
        return base
    return ''


def image_src(content_id: str, filename: str) -> str:
    base = public_assets_base()
    if base:
        return f'{base}/email/{filename}'
    return cid_src(content_id)


def logo_image_src(custom_url: str = '') -> str:
    if custom_url:
        return custom_url
    return image_src('sp-logo', 'logo-white.png')


def html_uses_cid_images(html_body: str) -> bool:
    return bool(_CID_PATTERN.search(html_body))


def attach_inline_images(message: EmailMultiAlternatives) -> None:
    for content_id, filename in INLINE_IMAGE_CIDS:
        path = _ASSETS_DIR / filename
        if not path.is_file():
            continue
        mime_image = MIMEImage(path.read_bytes(), _subtype='png')
        mime_image.add_header('Content-ID', f'<{content_id}>')
        mime_image.add_header('Content-Disposition', 'inline')
        message.attach(mime_image)


def send_branded_email(
    *,
    subject: str,
    text_body: str,
    html_body: str,
    from_email: str,
    recipient_list: list[str],
    fail_silently: bool = False,
    attachments: list[tuple[str, bytes, str]] | None = None,
) -> int:
    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=from_email,
        to=recipient_list,
    )
    message.attach_alternative(html_body, 'text/html')
    if attachments:
        for filename, content, mimetype in attachments:
            message.attach(filename, content, mimetype)
    # Only attach inline PNGs when HTML still references cid: (public HTTPS logo URL avoids this).
    if html_uses_cid_images(html_body):
        message.mixed_subtype = 'related'
        attach_inline_images(message)
    return message.send(fail_silently=fail_silently)
