from __future__ import annotations

from celery import shared_task
from datetime import date


@shared_task(bind=True, max_retries=3)
def generate_statement_task(
    self,
    account_id: str,
    period_start_str: str,
    period_end_str: str,
    to_email: str | None = None,
    e_signed: bool = False,
):
    try:
        from .services import create_or_regenerate_statement, email_statement_pdf

        period_start = date.fromisoformat(period_start_str)
        period_end = date.fromisoformat(period_end_str)
        statement = create_or_regenerate_statement(account_id, period_start, period_end)
        if to_email:
            email_statement_pdf(statement, to_email.strip(), e_signed=bool(e_signed))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@shared_task
def generate_monthly_statements():
    """Scheduled task: generate statements for all active accounts at month end."""
    from datetime import date
    from dateutil.relativedelta import relativedelta
    from apps.accounts.models import Account

    today = date.today()
    period_end = today.replace(day=1) - relativedelta(days=1)
    period_start = period_end.replace(day=1)

    for account in Account.objects.filter(status='ACTIVE'):
        generate_statement_task.delay(str(account.id), period_start.isoformat(), period_end.isoformat())
