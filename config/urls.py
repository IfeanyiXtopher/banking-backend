from django.apps import apps
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path('django-admin/', admin.site.urls),

    # API schema
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # App APIs
    path('api/auth/', include('apps.users.urls')),
    path('api/accounts/', include('apps.accounts.urls')),
    path('api/cards/', include('apps.cards.urls')),
    path('api/payments/', include('apps.payments.urls')),
    path('api/', include('apps.savings.urls')),
    path('api/transactions/', include('apps.transactions.urls')),
    path('api/loans/', include('apps.loans.urls')),
    path('api/statements/', include('apps.statements.urls')),
    path('api/notifications/', include('apps.notifications.urls')),
    path('api/support/', include('apps.support.urls')),
    path('api/admin-portal/', include('apps.admin_portal.urls')),
]

if settings.DEBUG and apps.is_installed('debug_toolbar'):
    import debug_toolbar
    urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns

# runserver wires static automatically; Gunicorn/uvicorn do not — expose staticfiles URLs when DEBUG.
urlpatterns += staticfiles_urlpatterns()

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
