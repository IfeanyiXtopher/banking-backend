from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.users'
    verbose_name = 'Users'

    def ready(self):
        # Bind Celery after Django settings are final (eager mode, broker URL, etc.).
        # asgi/wsgi also import config.celery; this covers manage.py commands that never load ASGI.
        import config.celery  # noqa: F401
