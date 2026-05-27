"""
Celery Beat periodic task schedule.
Run: python manage.py shell then execute this once to populate the DB,
or include via a data migration.
"""
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
import json


def setup_periodic_tasks():
    # Exchange rate update — every hour
    hourly, _ = IntervalSchedule.objects.get_or_create(every=1, period=IntervalSchedule.HOURS)
    PeriodicTask.objects.update_or_create(
        name='Update Exchange Rates',
        defaults=dict(interval=hourly, task='utils.tasks.update_exchange_rates', args=json.dumps([])),
    )

    # Low balance check — every 4 hours
    four_hourly, _ = IntervalSchedule.objects.get_or_create(every=4, period=IntervalSchedule.HOURS)
    PeriodicTask.objects.update_or_create(
        name='Check Low Balances',
        defaults=dict(interval=four_hourly, task='utils.tasks.check_low_balances', args=json.dumps([])),
    )

    # Monthly statement generation — 1st of every month at 2am
    monthly, _ = CrontabSchedule.objects.get_or_create(minute='0', hour='2', day_of_month='1', month_of_year='*', day_of_week='*')
    PeriodicTask.objects.update_or_create(
        name='Generate Monthly Statements',
        defaults=dict(crontab=monthly, task='apps.statements.tasks.generate_monthly_statements', args=json.dumps([])),
    )

    # Loan payment reminders — daily at 9am
    daily_9am, _ = CrontabSchedule.objects.get_or_create(minute='0', hour='9', day_of_month='*', month_of_year='*', day_of_week='*')
    PeriodicTask.objects.update_or_create(
        name='Loan Payment Reminders',
        defaults=dict(crontab=daily_9am, task='utils.tasks.send_loan_payment_reminders', args=json.dumps([])),
    )

    # Savings goal autosave (weekly / round-up / smart) — daily at 6am UTC
    daily_6am, _ = CrontabSchedule.objects.get_or_create(
        minute='0', hour='6', day_of_month='*', month_of_year='*', day_of_week='*'
    )
    PeriodicTask.objects.update_or_create(
        name='Savings Goal Autosave',
        defaults=dict(
            crontab=daily_6am,
            task='apps.savings.tasks.run_savings_goal_autosave',
            args=json.dumps([]),
        ),
    )

    print('Periodic tasks configured.')
