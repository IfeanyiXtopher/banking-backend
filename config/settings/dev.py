from .base import *

DEBUG = True

INSTALLED_APPS += ['debug_toolbar']

MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE

INTERNAL_IPS = ['127.0.0.1']

# Email in dev: use real SMTP when EMAIL_HOST_PASSWORD is set; console only when SMTP is not configured
# or USE_CONSOLE_EMAIL_IN_DEV=true (offline / no broker).
_has_smtp_credentials = bool(config('EMAIL_HOST_PASSWORD', default='').strip())
if config('USE_CONSOLE_EMAIL_IN_DEV', default=not _has_smtp_credentials, cast=bool):
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

CORS_ALLOW_ALL_ORIGINS = True

# With manage_services / runserver, RabbitMQ is often off. Eager runs .delay() in-process
# (no broker). Set CELERY_TASK_ALWAYS_EAGER=False in .env when RabbitMQ + workers are up.
CELERY_TASK_ALWAYS_EAGER = config('CELERY_TASK_ALWAYS_EAGER', default=True, cast=bool)
CELERY_TASK_EAGER_PROPAGATES = True
