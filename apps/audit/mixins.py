from .models import log_action, AuditLog
from .middleware import AuditMiddleware


class AuditMixin:
    """Mixin for DRF views to auto-log create/update actions."""

    audit_action_map = {
        'POST': AuditLog.Action.CREATE,
        'PUT': AuditLog.Action.UPDATE,
        'PATCH': AuditLog.Action.UPDATE,
        'DELETE': AuditLog.Action.DELETE,
    }

    def perform_create(self, serializer):
        instance = serializer.save()
        log_action(
            actor=self.request.user,
            action=AuditLog.Action.CREATE,
            target_model=instance.__class__.__name__,
            target_id=instance.pk,
            new_value=serializer.data,
            ip_address=AuditMiddleware.get_client_ip(self.request),
            user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
        )
        return instance

    def perform_update(self, serializer):
        old_value = self.get_serializer(self.get_object()).data if hasattr(self, 'get_object') else {}
        instance = serializer.save()
        log_action(
            actor=self.request.user,
            action=AuditLog.Action.UPDATE,
            target_model=instance.__class__.__name__,
            target_id=instance.pk,
            old_value=dict(old_value),
            new_value=serializer.data,
            ip_address=AuditMiddleware.get_client_ip(self.request),
            user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
        )
        return instance
