# Authentication, MFA, JWT & RBAC

## Authentication Flow

```
1. POST /api/auth/login/ → credentials validated
   ├── MFA disabled → return { access, refresh }
   └── MFA enabled  → return { mfa_required: true }
       └── POST /api/auth/login/mfa/ with OTP
           └── return { access, refresh }
```

---

## JWT Tokens

Implemented with `djangorestframework-simplejwt`.

| Token | Lifetime | Rotation |
|---|---|---|
| Access | 15 minutes | Not rotated |
| Refresh | 7 days | Rotated on use (blacklisting enabled) |

**How it works:**
- The React frontend stores the access token in memory (Zustand) and the refresh token in an `HttpOnly` cookie (or `localStorage` behind a flag).
- An Axios interceptor automatically calls `/api/auth/token/refresh/` when a request returns `401` and retries the original request with the new token.
- When a refresh token is used, a new refresh token is issued and the old one is blacklisted — this limits the attack window if a refresh token is leaked.

**Security settings in `base.py`:**
```python
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
}
```

---

## Multi-Factor Authentication (MFA)

### TOTP (Authenticator App)

Users can enable TOTP (RFC 6238, 30-second window) via an authenticator app such as Google Authenticator or Authy. On enable:

1. Backend generates a TOTP secret and returns the QR code URI.
2. User scans with their app.
3. User confirms with a valid 6-digit code to activate.

### Email OTP Fallback

For users without a TOTP device, or as a fallback:

1. Login response includes `{ mfa_required: true }`.
2. Backend sends a 6-digit OTP to the user's registered email (TTL: configurable, default 10 minutes).
3. User submits OTP to `/api/auth/login/mfa/`.

### MFA Enforcement

Setting `REQUIRE_MFA_FOR_ADMINS = True` in settings forces all non-CUSTOMER roles to have MFA enabled — their login always triggers the MFA step.

---

## Brute Force Protection

Implemented with `django-axes`.

| Setting | Default |
|---|---|
| Max failures | 5 |
| Cooldown period | 30 minutes |
| Tracks | IP address + username |
| Unlock | Auto after cooldown, or manual by admin |

Failed attempt is also logged to `AuditLog` with `action=FAILED_LOGIN`.

---

## Password Policy

Passwords must satisfy all built-in Django validators plus:
- Minimum 8 characters
- Not too similar to the user's personal information
- Not a common password

Hashing: **Argon2id** (recommended by OWASP — resistant to GPU brute-force, side-channel attacks).

---

## Session / Auto-Logout

There is no server-side session. Instead, the React frontend uses an **inactivity timer** (`useInactivityLogout` hook):
- Default inactivity timeout: 15 minutes.
- On timeout, the store is cleared and the user is redirected to `/auth/login`.
- On every user interaction (mouse move, key press, click, scroll), the timer is reset.

---

## Role-Based Access Control (RBAC)

### User Roles

| Role | Description |
|---|---|
| `CUSTOMER` | Default role for all registered users. Customer-facing features only. |
| `SUPER_ADMIN` | Full admin access, can change roles, configure fees and exchange rates. |
| `OPERATIONS_TELLER` | Can review and reverse transactions, adjust account balances/status. |
| `COMPLIANCE_AUDITOR` | Read-only access to audit logs and transaction history. |
| `LOAN_OFFICER` | Reviews loan applications, approves/rejects, initiates disbursal. |
| `SUPPORT_STAFF` | Views and responds to support tickets, can view customer profiles. |

### Admin Portal Access

Permissions are enforced on both the frontend (route guards) and backend (view-level permission classes):

```python
# Example permission class used in admin_portal views
class IsAdminUser(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role != "CUSTOMER"

class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "SUPER_ADMIN"
```

### Admin Actions are Audited

Every create/update/delete through the admin portal uses `AuditMixin` on the view, which automatically writes an `AuditLog` entry after each mutating operation.

---

## KYC Flow

```
1. User submits document → POST /api/auth/kyc/upload/ (multipart)
2. Document stored in media/kyc/{user_id}/
3. User's kyc_status set to SUBMITTED
4. Admin reviews via /api/admin-portal/users/{id}/kyc/
   ├── APPROVED → kyc_status=APPROVED, notification sent
   └── REJECTED → kyc_status=REJECTED, notification sent with reason
```

Certain features (e.g., high-value transfers) require `kyc_status=APPROVED` before proceeding.
