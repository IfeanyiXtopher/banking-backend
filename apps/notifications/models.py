import uuid
from django.db import models
from django.conf import settings


class Notification(models.Model):
    class EventType(models.TextChoices):
        TRANSACTION = 'TRANSACTION', 'Transaction'
        LOW_BALANCE = 'LOW_BALANCE', 'Low Balance'
        LOAN_APPROVED = 'LOAN_APPROVED', 'Loan Approved'
        LOAN_REJECTED = 'LOAN_REJECTED', 'Loan Rejected'
        LOAN_PAYMENT_DUE = 'LOAN_PAYMENT_DUE', 'Loan Payment Due'
        PASSWORD_RESET = 'PASSWORD_RESET', 'Password Reset'
        MFA_OTP = 'MFA_OTP', 'MFA OTP'
        REGISTRATION = 'REGISTRATION', 'Registration'
        STATEMENT_READY = 'STATEMENT_READY', 'Statement Ready'
        SUPPORT_UPDATE = 'SUPPORT_UPDATE', 'Support Update'
        SECURITY_ALERT = 'SECURITY_ALERT', 'Security Alert'
        PROFILE_UPDATE_APPROVED = 'PROFILE_UPDATE_APPROVED', 'Profile update approved'
        GOAL_AUTOSAVE_SUCCESS = 'GOAL_AUTOSAVE_SUCCESS', 'Goal autosave contribution'
        GOAL_AUTOSAVE_INSUFFICIENT = 'GOAL_AUTOSAVE_INSUFFICIENT', 'Goal autosave insufficient funds'
        DEPOSIT = 'DEPOSIT', 'Deposit received'
        COMPLIANCE_OTP_SENT = 'COMPLIANCE_OTP_SENT', 'Compliance verification code sent'
        COMPLIANCE_PAYMENT_CONFIRMED = 'COMPLIANCE_PAYMENT_CONFIRMED', 'Compliance payment confirmed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications'
    )
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    subject = models.CharField(max_length=255)
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    sent_at = models.DateTimeField(auto_now_add=True)
    email_status = models.CharField(max_length=20, default='PENDING')

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        return f'{self.event_type} — {self.user.email}'


class NotificationPreference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_preference'
    )
    transaction_alerts = models.BooleanField(default=True)
    low_balance_alerts = models.BooleanField(default=True)
    low_balance_threshold = models.DecimalField(max_digits=10, decimal_places=2, default=100)
    loan_alerts = models.BooleanField(default=True)
    security_alerts = models.BooleanField(default=True)
    statement_alerts = models.BooleanField(default=True)

    def __str__(self):
        return f'Preferences for {self.user.email}'
