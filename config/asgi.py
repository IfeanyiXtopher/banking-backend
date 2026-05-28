import os

from decouple import config
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE',
    config('DJANGO_SETTINGS_MODULE', default='config.settings.dev'),
)

django_asgi_app = get_asgi_application()

# Import after setup so Celery reads CELERY_* from Django (e.g. task_always_eager).
from config.celery import app as celery_app  # noqa: E402, F401

from apps.notifications.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
