import uuid
from django.db import models
from django.conf import settings


class AuditLog(models.Model):
    class Action(models.TextChoices):
        CREATE = 'CREATE', 'Create'
        UPDATE = 'UPDATE', 'Update'
        DELETE = 'DELETE', 'Delete'
        LOGIN = 'LOGIN', 'Login'
        LOGOUT = 'LOGOUT', 'Logout'
        FAILED_LOGIN = 'FAILED_LOGIN', 'Failed Login'
        TRANSACTION = 'TRANSACTION', 'Transaction'
        REVERSAL = 'REVERSAL', 'Reversal'
        FREEZE_ACCOUNT = 'FREEZE_ACCOUNT', 'Freeze Account'
        CLOSE_ACCOUNT = 'CLOSE_ACCOUNT', 'Close Account'
        ROLE_CHANGE = 'ROLE_CHANGE', 'Role Change'
        KYC_UPDATE = 'KYC_UPDATE', 'KYC Update'
        LOAN_DECISION = 'LOAN_DECISION', 'Loan Decision'
        CONFIG_CHANGE = 'CONFIG_CHANGE', 'Config Change'
        VIEW_SENSITIVE = 'VIEW_SENSITIVE', 'View Sensitive Data'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='audit_logs',
    )
    action = models.CharField(max_length=30, choices=Action.choices)
    target_model = models.CharField(max_length=100, blank=True)
    target_id = models.CharField(max_length=100, blank=True)
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['actor', '-timestamp']),
            models.Index(fields=['action']),
            models.Index(fields=['target_model', 'target_id']),
        ]

    def save(self, *args, **kwargs):
        # Append-only: prevent updates
        if self.pk and AuditLog.objects.filter(pk=self.pk).exists():
            return
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError('Audit logs cannot be deleted.')

    def __str__(self):
        return f'{self.action} by {self.actor} at {self.timestamp}'


def log_action(actor, action, target_model='', target_id='', old_value=None, new_value=None,
               description='', ip_address=None, user_agent=''):
    AuditLog.objects.create(
        actor=actor,
        action=action,
        target_model=target_model,
        target_id=str(target_id),
        old_value=old_value,
        new_value=new_value,
        description=description,
        ip_address=ip_address,
        user_agent=user_agent,
    )
