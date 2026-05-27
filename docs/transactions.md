# Transaction Engine

## Overview

All monetary operations (deposit, withdrawal, transfer) are handled in `apps/transactions/services.py`. The core guarantee is **atomicity** — a transfer either fully completes or fully rolls back. There is no partial state.

---

## Double-Entry Accounting

Every transfer debits one account and credits another in a single DB transaction:

```
Transfer $100 from Account A → Account B:

  Account A: balance 1000 → 900  (debit)
  Account B: balance  500 → 600  (credit)

  Transaction record: {
    type: TRANSFER_INTERNAL,
    from_account: A,
    to_account: B,
    amount: 100,
    status: COMPLETED
  }

  Fee Transaction (if applicable): {
    type: FEE,
    from_account: A,
    to_account: null,
    amount: 0.50,
    status: COMPLETED
  }
```

All four writes (Account A, Account B, Transaction, Fee) happen in one `atomic()` block.

---

## Race Condition Prevention

High concurrency on shared accounts is handled with **row-level locking**:

```python
with transaction.atomic():
    from_acc = Account.objects.select_for_update().get(pk=from_account_id)
    to_acc   = Account.objects.select_for_update().get(pk=to_account_id)
    # PostgreSQL now holds a row-level lock on both rows.
    # Any concurrent transaction touching either account will queue behind this one.
    ...
```

This ensures two simultaneous transfers from the same account cannot race and both succeed with stale balance data.

---

## Idempotency

Clients should generate a **UUID v4 idempotency key** per transaction attempt and include it in the request:

```json
{
  "from_account_id": "...",
  "to_account_id": "...",
  "amount": "100.00",
  "idempotency_key": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
}
```

If the backend already has a `Transaction` with that key:
- Returns the existing `Transaction` with HTTP 200 (not 201).
- Never processes the request twice.

If the first request is in-flight when the duplicate arrives:
- The duplicate waits briefly and then returns a `409 Conflict` (retry after).

This protects against network retries causing duplicate debits.

---

## Fee Calculation

Fees are configured in `TransactionFee` records and applied at service time:

```python
fee = TransactionFee.objects.filter(fee_type=..., is_active=True).first()
if fee:
    fee_amount = fee.calculate(amount)
    # Debit fee_amount from from_account (separate FEE transaction)
```

`calculate(amount)`:
```
fee = flat_amount + (amount × percentage)
fee = max(fee, min_amount)
if max_amount > 0:
    fee = min(fee, max_amount)
```

---

## Foreign Exchange (FX)

For `TRANSFER_INTERNATIONAL`:

1. Look up `ExchangeRate` for `(from_currency, to_currency)`.
2. Convert: `to_amount = from_amount × rate`.
3. Debit `from_amount` from `from_account` in its currency.
4. Credit `to_amount` to `to_account` in its currency.
5. Record the rate snapshot in `Transaction.exchange_rate`.

Rates are refreshed hourly by the Celery Beat task `update_exchange_rates`.

---

## Transaction States

```
PENDING → COMPLETED   (normal flow)
PENDING → FAILED      (validation failed, insufficient funds, DB error)
COMPLETED → REVERSED  (admin reversal)
COMPLETED → FLAGGED   (admin flagged for review)
```

A `REVERSED` transaction creates a mirror `REVERSAL` transaction record crediting the debited account(s) back.

---

## Reversal

Admin endpoint: `POST /api/admin-portal/transactions/{id}/reverse/`

```python
def reverse_transaction(transaction_id, reversed_by):
    with atomic():
        tx = Transaction.objects.select_for_update().get(pk=transaction_id)
        assert tx.status == "COMPLETED"

        # Undo the balance changes
        if tx.from_account:
            tx.from_account.balance += tx.amount
        if tx.to_account:
            tx.to_account.balance -= tx.amount

        # Create REVERSAL record
        Transaction.objects.create(
            transaction_type="REVERSAL",
            amount=tx.amount,
            from_account=tx.to_account,
            to_account=tx.from_account,
            original_transaction=tx,
            reversed_by=reversed_by,
            status="COMPLETED",
        )

        tx.status = "REVERSED"
        tx.save()
```

---

## Notification Hook

After every successful transaction, the service dispatches an async Celery task:

```python
send_transaction_notification.delay(transaction_id)
```

This task:
1. Creates a `Notification` record.
2. Sends an email via Django's email backend.
3. Pushes a real-time message to the user's WebSocket channel via Redis.
