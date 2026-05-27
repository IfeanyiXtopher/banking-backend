# Database Models

## Overview

PostgreSQL is used as the primary database. All monetary amounts use `DecimalField(max_digits=18, decimal_places=2)` — never `FloatField`.

---

## Entity Relationship Summary

```
CustomUser
  ├── Account (owner FK, one-to-many)
  ├── LoanApplication (applicant FK, one-to-many)
  ├── SupportTicket (customer FK, one-to-many)
  ├── Notification (user FK, one-to-many)
  ├── NotificationPreference (user OneToOne)
  ├── PasswordResetToken (user FK, one-to-many)
  ├── EmailOTPToken (user FK, one-to-many)
  └── AuditLog (actor FK, one-to-many)

Account
  ├── Currency (FK)
  ├── Transaction (from_account FK → debits)
  ├── Transaction (to_account FK → credits)
  └── Statement (account FK)

Transaction
  ├── Account (from_account FK)
  ├── Account (to_account FK)
  └── Transaction (original_transaction FK → reversals)

LoanApplication
  ├── LoanProduct (FK)
  └── LoanAccount (OneToOne)

LoanAccount
  ├── Account (disbursement_account FK)
  └── RepaymentSchedule (loan_account FK, one-to-many)

SupportTicket
  └── TicketMessage (ticket FK, one-to-many)
```

---

## `apps.users`

### `CustomUser`

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | Primary key |
| `email` | EmailField | Unique, used as USERNAME_FIELD |
| `full_name` | CharField(255) | |
| `phone` | CharField(20) | Optional |
| `role` | CharField | CUSTOMER / SUPER_ADMIN / OPERATIONS_TELLER / COMPLIANCE_AUDITOR / LOAN_OFFICER / SUPPORT_STAFF |
| `kyc_status` | CharField | PENDING / SUBMITTED / APPROVED / REJECTED |
| `kyc_document` | FileField | Uploaded to `kyc/` |
| `profile_picture` | ImageField | Uploaded to `profiles/` |
| `is_active` | BooleanField | Default True |
| `is_staff` | BooleanField | Django admin access |
| `is_mfa_enabled` | BooleanField | Controls MFA enforcement on login |
| `is_locked` | BooleanField | Set by admin lock action |
| `date_joined` | DateTimeField | Auto-set on creation |
| `address` | TextField | Optional |
| `date_of_birth` | DateField | Optional |
| `nationality` | CharField(100) | Optional |

Password hashed with **Argon2** (configured in `PASSWORD_HASHERS`).

### `PasswordResetToken`

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | |
| `user` | FK → CustomUser | |
| `token` | CharField(64) | URL-safe random token |
| `expires_at` | DateTimeField | 1 hour from creation |
| `is_used` | BooleanField | Invalidated on use |

### `EmailOTPToken`

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | |
| `user` | FK → CustomUser | |
| `token` | CharField(6) | 6-digit numeric code |
| `purpose` | CharField(30) | `login_mfa`, `transaction_verify`, etc. |
| `expires_at` | DateTimeField | Configurable via `OTP_EMAIL_TOKEN_VALIDITY` |
| `is_used` | BooleanField | |

---

## `apps.accounts`

### `Currency`

| Field | Type | Notes |
|---|---|---|
| `code` | CharField(3) | Unique — ISO 4217 e.g. `USD` |
| `name` | CharField(50) | `US Dollar` |
| `symbol` | CharField(5) | `$` |
| `is_active` | BooleanField | Inactive currencies hidden from users |

### `Account`

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | |
| `owner` | FK → CustomUser | |
| `account_number` | CharField(20) | Auto-generated 10-digit number, unique |
| `account_type` | CharField | CHECKING / SAVINGS / CREDIT |
| `currency` | FK → Currency | |
| `balance` | DecimalField(18,2) | Ledger balance (may include pending) |
| `available_balance` | DecimalField(18,2) | Balance available for use |
| `status` | CharField | ACTIVE / FROZEN / CLOSED / PENDING |
| `nickname` | CharField(100) | User-defined label |
| `interest_rate` | DecimalField(5,4) | Annual rate for savings accounts |
| `credit_limit` | DecimalField(18,2) | For credit accounts only |
| `created_at` | DateTimeField | |
| `updated_at` | DateTimeField | Auto-updated |

**Rules:**
- `available_balance` is what gets checked before any debit
- A FROZEN or CLOSED account will reject all transactions
- `balance` and `available_balance` are always updated together

---

## `apps.transactions`

### `TransactionFee`

| Field | Type | Notes |
|---|---|---|
| `fee_type` | CharField | TRANSFER_LOCAL / TRANSFER_INTERNATIONAL / WITHDRAWAL / DEPOSIT |
| `flat_amount` | DecimalField | Fixed fee component |
| `percentage` | DecimalField(5,4) | `0.0150` = 1.5% |
| `min_amount` | DecimalField | Minimum fee |
| `max_amount` | DecimalField | Fee cap (0 = no cap) |
| `is_active` | BooleanField | |

`calculate(amount)` method: `fee = flat_amount + (amount × percentage)`, clamped by min/max.

### `ExchangeRate`

| Field | Type | Notes |
|---|---|---|
| `from_currency` | CharField(3) | |
| `to_currency` | CharField(3) | |
| `rate` | DecimalField(18,8) | E.g. `1.09000000` |
| `fetched_at` | DateTimeField | Updated hourly by Celery Beat |

Unique together: `(from_currency, to_currency)`.

### `Transaction`

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | |
| `reference_number` | CharField(20) | `TXN` + 10 digits, unique, auto-generated |
| `transaction_type` | CharField | DEPOSIT / WITHDRAWAL / TRANSFER_INTERNAL / TRANSFER_EXTERNAL / TRANSFER_INTERNATIONAL / LOAN_DISBURSEMENT / LOAN_PAYMENT / FEE / INTEREST / REVERSAL |
| `amount` | DecimalField(18,2) | Always positive |
| `currency` | CharField(3) | ISO code |
| `from_account` | FK → Account (nullable) | Null for deposits |
| `to_account` | FK → Account (nullable) | Null for withdrawals |
| `status` | CharField | PENDING / COMPLETED / FAILED / REVERSED / FLAGGED |
| `description` | CharField(255) | |
| `fee_amount` | DecimalField(10,2) | Fee charged for this tx |
| `exchange_rate` | DecimalField(18,8) | Rate applied for FX transfers |
| `idempotency_key` | CharField(128) | Unique, nullable — prevents duplicate submissions |
| `initiated_by` | FK → CustomUser | User who created the transaction |
| `reversed_by` | FK → CustomUser (nullable) | Admin who reversed it |
| `original_transaction` | FK → self (nullable) | Points to the tx being reversed |
| `created_at` | DateTimeField | |
| `completed_at` | DateTimeField | Null until completion |
| `metadata` | JSONField | Extensible payload |

**Indexes:** `(from_account, -created_at)`, `(to_account, -created_at)`, `status`, `transaction_type`

---

## `apps.loans`

### `LoanProduct`

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | |
| `name` | CharField(100) | |
| `loan_type` | CharField | PERSONAL / MORTGAGE / AUTO / BUSINESS / EDUCATION |
| `interest_rate` | DecimalField(5,4) | Annual rate, e.g. `0.1200` = 12% |
| `min_amount` / `max_amount` | DecimalField | Allowed range |
| `min_term_months` / `max_term_months` | PositiveIntegerField | |
| `description` | TextField | |
| `is_active` | BooleanField | |

### `LoanApplication`

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | |
| `applicant` | FK → CustomUser | |
| `product` | FK → LoanProduct | |
| `requested_amount` | DecimalField(18,2) | |
| `term_months` | PositiveIntegerField | |
| `purpose` | TextField | |
| `status` | CharField | DRAFT / SUBMITTED / UNDER_REVIEW / APPROVED / REJECTED / DISBURSED / CANCELLED |
| `reviewed_by` | FK → CustomUser (nullable) | Loan officer |
| `review_notes` | TextField | |

### `LoanAccount`

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | |
| `application` | OneToOne → LoanApplication | |
| `principal_amount` | DecimalField(18,2) | Original disbursed amount |
| `outstanding_balance` | DecimalField(18,2) | Decreases with payments |
| `interest_rate` | DecimalField(5,4) | Snapshot at disbursal time |
| `term_months` | PositiveIntegerField | |
| `monthly_payment` | DecimalField(18,2) | Calculated at disbursal |
| `disbursement_account` | FK → Account | Where money was sent |
| `status` | CharField | ACTIVE / PAID_OFF / DEFAULTED / WRITTEN_OFF |
| `disbursed_at` | DateTimeField | |
| `next_payment_due` | DateField | Updated after each payment |

### `RepaymentSchedule`

| Field | Type | Notes |
|---|---|---|
| `loan_account` | FK → LoanAccount | |
| `installment_number` | PositiveIntegerField | 1-based |
| `due_date` | DateField | |
| `principal_amount` | DecimalField(18,2) | Principal portion |
| `interest_amount` | DecimalField(18,2) | Interest portion |
| `total_amount` | DecimalField(18,2) | = principal + interest |
| `paid_amount` | DecimalField(18,2) | 0 until paid |
| `status` | CharField | PENDING / PAID / OVERDUE / WAIVED |

---

## `apps.statements`

### `Statement`

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | |
| `account` | FK → Account | |
| `period_start` | DateField | |
| `period_end` | DateField | |
| `pdf_file` | FileField | Stored in `MEDIA_ROOT/statements/` |
| `generated_at` | DateTimeField | |
| `is_paperless` | BooleanField | Default True |

Unique together: `(account, period_start, period_end)` — one PDF per period.

---

## `apps.notifications`

### `Notification`

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | |
| `user` | FK → CustomUser | |
| `event_type` | CharField | TRANSACTION / LOW_BALANCE / LOAN_APPROVED / LOAN_REJECTED / LOAN_PAYMENT_DUE / PASSWORD_RESET / MFA_OTP / REGISTRATION / STATEMENT_READY / SUPPORT_UPDATE / SECURITY_ALERT |
| `subject` | CharField(255) | Email subject line |
| `body` | TextField | Email body |
| `is_read` | BooleanField | In-app read status |
| `sent_at` | DateTimeField | |
| `email_status` | CharField | PENDING / SENT / FAILED |

---

## `apps.support`

### `SupportTicket`

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | |
| `ticket_number` | CharField(20) | `TKT` + 8 digits, unique, auto-generated |
| `customer` | FK → CustomUser | |
| `assigned_to` | FK → CustomUser (nullable) | Support staff |
| `subject` | CharField(255) | |
| `status` | CharField | OPEN / IN_PROGRESS / RESOLVED / CLOSED |
| `priority` | CharField | LOW / MEDIUM / HIGH / URGENT |
| `related_transaction` | FK → Transaction (nullable) | |
| `resolved_at` | DateTimeField | Nullable |

### `TicketMessage`

| Field | Type | Notes |
|---|---|---|
| `ticket` | FK → SupportTicket | |
| `author` | FK → CustomUser | |
| `body` | TextField | |
| `attachment` | FileField | Stored in `support/` |
| `is_internal_note` | BooleanField | Staff-only, hidden from customer |

---

## `apps.audit`

### `AuditLog`

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDField | |
| `actor` | FK → CustomUser (nullable) | Null = system action |
| `action` | CharField | CREATE / UPDATE / DELETE / LOGIN / LOGOUT / FAILED_LOGIN / TRANSACTION / REVERSAL / FREEZE_ACCOUNT / CLOSE_ACCOUNT / ROLE_CHANGE / KYC_UPDATE / LOAN_DECISION / CONFIG_CHANGE / VIEW_SENSITIVE |
| `target_model` | CharField(100) | Model name e.g. `Account` |
| `target_id` | CharField(100) | PK of the affected object |
| `old_value` | JSONField | Snapshot before change |
| `new_value` | JSONField | Snapshot after change |
| `description` | TextField | Human-readable note |
| `ip_address` | GenericIPAddressField | |
| `user_agent` | CharField(512) | |
| `timestamp` | DateTimeField | Auto-set, never changed |

**Immutability:** `save()` is overridden to block updates; `delete()` raises `PermissionError`. The Django admin also disables add/change/delete for this model.
