from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task
def update_exchange_rates():
    from utils.fx_service import fetch_and_update_rates
    fetch_and_update_rates()


@shared_task
def check_low_balances():
    from apps.accounts.models import Account
    from apps.notifications.models import NotificationPreference
    from apps.notifications.services import send_email_notification

    for pref in NotificationPreference.objects.filter(low_balance_alerts=True).select_related('user'):
        accounts = Account.objects.filter(owner=pref.user, status='ACTIVE')
        for account in accounts:
            if account.available_balance <= pref.low_balance_threshold:
                send_email_notification.delay(
                    str(pref.user.id),
                    'low_balance',
                    {
                        'account_number': account.account_number,
                        'balance': str(account.available_balance),
                        'currency': account.currency.code,
                        'threshold': str(pref.low_balance_threshold),
                    },
                )


@shared_task
def send_loan_payment_reminders():
    from datetime import date, timedelta
    from apps.loans.models import LoanAccount, RepaymentSchedule
    from apps.notifications.services import send_email_notification

    reminder_date = date.today() + timedelta(days=3)
    due_schedules = RepaymentSchedule.objects.filter(
        due_date=reminder_date,
        status=RepaymentSchedule.Status.PENDING,
    ).select_related('loan_account__application__applicant')

    for schedule in due_schedules:
        user = schedule.loan_account.application.applicant
        send_email_notification.delay(
            str(user.id),
            'loan_payment_due',
            {
                'amount': str(schedule.total_amount),
                'due_date': str(schedule.due_date),
                'installment': schedule.installment_number,
            },
        )
