# Architecture

## Overview

SafaPay Bank uses a **decoupled full-stack architecture**: the Django REST Framework backend runs on a self-managed VPS, while the React SPA is hosted on Vercel's CDN. All communication between them uses HTTPS.

---

## System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  Client (Browser)                                               │
│  ┌─────────────────────┐   ┌───────────────────────────────┐   │
│  │  Customer React SPA │   │  Admin React SPA               │   │
│  └────────┬────────────┘   └───────────────┬───────────────┘   │
└───────────┼────────────────────────────────┼───────────────────┘
            │ HTTPS                          │ HTTPS
            ▼                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Vercel CDN  (banking-frontend repo)                            │
│  Static assets · SPA routing · Preview deployments             │
└────────────────────────┬────────────────────────────────────────┘
                         │ REST / WebSocket (HTTPS)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  VPS  (banking-backend repo)                                    │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Nginx (Port 443)                                         │  │
│  │  · TLS termination (Let's Encrypt)                        │  │
│  │  · Rate limiting (auth: 5/min, api: 30/min)               │  │
│  │  · Security headers (HSTS, X-Frame-Options, CSP)          │  │
│  │  · Proxy /api/ and /ws/ → Django                          │  │
│  └──────────────────┬───────────────────────────────────────┘  │
│                     │                                            │
│  ┌──────────────────▼───────────────────────────────────────┐  │
│  │  Django (Gunicorn + Uvicorn workers, Port 8000)          │  │
│  │  ├── REST API (DRF)                                       │  │
│  │  └── WebSocket (Django Channels)                          │  │
│  └────┬──────────────────────┬──────────────────────────────┘  │
│       │                      │                                   │
│  ┌────▼──────┐   ┌──────────▼──────────┐   ┌──────────────┐   │
│  │ PostgreSQL│   │ Redis               │   │ RabbitMQ     │   │
│  │ (Port5432)│   │ Cache + Channels    │   │ Task Queue   │   │
│  └───────────┘   └─────────────────────┘   └──────┬───────┘   │
│                                                     │            │
│  ┌──────────────────────────────────────────────────▼───────┐  │
│  │  Celery Workers  ·  Celery Beat                           │  │
│  │  Email · PDF generation · FX polling · Loan reminders     │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Local Storage: /app/media/  (PDF statements, KYC docs)         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Technology Choices

| Concern | Technology | Reason |
|---|---|---|
| API framework | Django REST Framework | Batteries-included, serializers, permissions |
| Database | PostgreSQL 16 | ACID compliance, `DecimalField` for money |
| Cache & WS bus | Redis 7 | Channel layers for WebSocket, cache backend |
| Task queue | RabbitMQ + Celery | Reliable async task delivery |
| Auth tokens | djangorestframework-simplejwt | Stateless, short-lived access tokens |
| MFA | django-otp | TOTP (RFC 6238) + email OTP fallback |
| Password hashing | Argon2 | Recommended by OWASP, side-channel resistant |
| Brute force | django-axes | Automatic lockout after N failures |
| Object perms | django-guardian | Row-level permissions for admin roles |
| PDF generation | ReportLab | Programmatic, no browser dependency |
| API docs | drf-spectacular | Auto-generated OpenAPI 3.0 schema |
| Reverse proxy | Nginx | TLS, rate limiting, static file serving |
| Frontend | React 18 + Vite | Fast HMR, TypeScript, tree-shaking |
| Styling | Tailwind CSS | Utility-first, design tokens via config |
| State | Zustand | Lightweight, no boilerplate |
| Server state | TanStack Query | Caching, background refetch, mutations |

---

## Request Lifecycle

### Standard API Request

```
Browser → Vercel CDN → Nginx (TLS/rate-limit) → Django DRF view
  → JWT authentication
  → Permission check (IsAuthenticated / RBAC)
  → Serializer validation
  → Business logic / DB query
  → Response (JSON)
  → Audit log (async)
```

### Transaction Request (Critical Path)

```
POST /api/transactions/transfer/
  → JWT auth + ownership check
  → Idempotency key lookup (return cached if duplicate)
  → TransactionSerializer validation
  → services.transfer()
      → DB transaction (atomic)
      → select_for_update() on both accounts
      → Validate balances
      → Debit from_account
      → Credit to_account
      → Create Transaction record
      → Create fee record (if applicable)
      → Commit
  → send_transaction_notification.delay()  (Celery)
  → Return TransactionSerializer response
```

### WebSocket Flow

```
Browser connects → ws://api.domain.com/ws/updates/?token=<JWT>
  → Django Channels ASGI
  → JWT validated in connect()
  → User added to Redis channel group: user_{user_id}
  → Receives: { type: "notification", ... }
              { type: "balance_update", ... }

Server-side push (after transaction):
  channel_layer.group_send("user_{id}", { "type": "notification_message", ... })
```

---

## Data Flow: Double-Entry Accounting

Every transfer creates balanced debit/credit entries in a single atomic transaction:

```
Transfer $100 from Account A → Account B

  accounts table:
    Account A: balance  1000  → 900   (debit $100)
    Account B: balance   500  → 600   (credit $100)

  transactions table:
    Row 1: type=TRANSFER, amount=100, from=A, to=B, status=COMPLETED
    Row 2: type=FEE,       amount=0.5, from=A, to=null, status=COMPLETED (if fee)

All inside atomic() with select_for_update() — no race conditions.
```

---

## Security Layers

```
1. Transport    Nginx TLS (TLSv1.2+) · HSTS · No HTTP
2. Rate Limit   Nginx zones: auth 5/min, api 30/min
3. Auth         JWT Bearer tokens · 15-min access · 7-day rotating refresh
4. MFA          TOTP (authenticator app) or Email OTP fallback
5. Brute force  django-axes: 5 failures → 30-min lockout
6. CORS         Allowed origins: Vercel domain only
7. Headers      X-Frame-Options: DENY · X-Content-Type-Options · Referrer-Policy
8. Validation   DRF serializers · ORM parameterised queries (no raw SQL)
9. Audit        Every write action logged to AuditLog (append-only)
10. Encryption  Argon2 passwords · Encrypted volume at rest
```
