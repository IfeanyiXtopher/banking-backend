# Async Tasks (Celery)

## Setup

- **Broker:** RabbitMQ (`amqp://USER:PASS@RABBIT_HOST:5672/`)
- **Result backend:** Redis (`redis://REDIS_HOST:6379/1`)
- **Worker process:** `celery -A config worker -l INFO`
- **Beat scheduler:** `celery -A config beat -l INFO`

In production, start both via the systemd units in `deploy/systemd/`.
Locally you can also start them with `./scripts/manage_services.sh start`.

---

## Task Index

### `apps/notifications/tasks.py`

| Task | Trigger | Description |
|---|---|---|
| `send_transaction_notification` | After every transaction | Creates Notification record, sends email, pushes WebSocket event |
| `send_low_balance_alert` | After debit, if balance < threshold | Sends email alert to account owner |
| `send_loan_email` | Loan status change | Sends approval/rejection/disbursement email |
| `send_statement_ready_notification` | After PDF generation | Notifies user their statement is ready to download |

### `apps/statements/tasks.py`

| Task | Trigger | Description |
|---|---|---|
| `generate_statement_pdf_task` | On-demand (user request) | Runs `services.create_or_regenerate_statement()` |
| `generate_monthly_statements` | Celery Beat — 1st of each month | Generates PDFs for all active accounts for the prior month |

### `utils/tasks.py`

| Task | Trigger | Description |
|---|---|---|
| `update_exchange_rates` | Celery Beat — every hour | Fetches latest rates from FX API and upserts `ExchangeRate` rows |
| `check_low_balances` | Celery Beat — every 6 hours | Scans accounts below their alert threshold, queues notifications |
| `send_loan_payment_reminders` | Celery Beat — every day at 9 AM | Checks `RepaymentSchedule` for due dates within 3 days, sends reminders |
| `accrue_interest` | Celery Beat — 1st of each month | Calculates and applies monthly interest to SAVINGS accounts |

---

## Periodic Task Schedule

Configured via `utils/celery_schedules.py` and loaded with:
```bash
python manage.py shell -c "from utils.celery_schedules import setup_periodic_tasks; setup_periodic_tasks()"
```

| Task | Schedule |
|---|---|
| `update_exchange_rates` | Every 60 minutes |
| `check_low_balances` | Every 6 hours |
| `send_loan_payment_reminders` | Daily at 09:00 UTC |
| `accrue_interest` | Monthly, 1st at 00:00 UTC |
| `generate_monthly_statements` | Monthly, 1st at 01:00 UTC |

---

## Monitoring Celery

```bash
# Watch worker logs in real-time
tail -f logs/celery_worker.log

# Watch beat scheduler
tail -f logs/celery_beat.log

# Open RabbitMQ management UI
open http://localhost:15672
# Credentials: guest / guest
```

Use the RabbitMQ management UI to:
- View queue lengths and message rates
- Inspect stuck or unacknowledged messages
- Manually purge queues during development

---

## Retries

All tasks use the default Celery retry policy. For tasks that send external requests (email, FX API):

```python
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_transaction_notification(self, transaction_id):
    try:
        ...
    except Exception as exc:
        raise self.retry(exc=exc)
```

Failed tasks after max retries are stored in the Dead Letter queue in RabbitMQ for manual review.
