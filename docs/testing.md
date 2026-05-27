# Testing

## Test Stack

| Tool | Purpose |
|---|---|
| `pytest` + `pytest-django` | Unit and integration tests |
| `factory_boy` | Test data fixtures |
| `bandit` | Static Application Security Testing (SAST) |
| `safety` | Dependency vulnerability scanning |

---

## Running Tests

```bash
# Activate your venv (install with requirements/dev.txt)
# source venv/bin/activate

# Full test suite with coverage report
pytest --cov=apps --cov-report=term-missing -v

# Fast run (no coverage, parallel)
pytest -n auto

# Only one app
pytest apps/transactions/ -v

# Specific test file
pytest apps/users/tests/test_auth.py -v

# Only tests marked as unit
pytest -m unit

# Only tests marked as integration
pytest -m integration

# Stop on first failure
pytest -x
```

---

## Test File Structure

Each app follows this pattern:

```
apps/{app}/
└── tests/
    ├── __init__.py
    ├── test_models.py       # Model validation, methods, constraints
    ├── test_serializers.py  # Serializer validation, field rendering
    ├── test_views.py        # API endpoint integration tests
    └── test_services.py     # Service function unit tests
```

---

## Writing Tests

### Model Test Example

```python
# apps/accounts/tests/test_models.py
import pytest
from apps.accounts.models import Account

@pytest.mark.django_db
def test_account_balance_cannot_go_negative():
    account = AccountFactory(balance="100.00")
    account.balance = "-1.00"
    with pytest.raises(Exception):
        account.full_clean()   # triggers validators
```

### API Test Example

```python
# apps/transactions/tests/test_views.py
import pytest
from rest_framework.test import APIClient
from apps.users.tests.factories import UserFactory
from apps.accounts.tests.factories import AccountFactory

@pytest.mark.django_db
class TestTransferEndpoint:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)

    def test_internal_transfer_success(self):
        from_acc = AccountFactory(owner=self.user, balance="1000.00")
        to_acc   = AccountFactory(owner=self.user, balance="0.00")

        resp = self.client.post("/api/transactions/transfer/", {
            "from_account_id": str(from_acc.id),
            "to_account_id":   str(to_acc.id),
            "amount": "100.00",
            "transfer_type": "TRANSFER_INTERNAL",
            "idempotency_key": "test-key-001",
        })

        assert resp.status_code == 201
        from_acc.refresh_from_db()
        to_acc.refresh_from_db()
        assert from_acc.balance == Decimal("900.00")
        assert to_acc.balance == Decimal("100.00")

    def test_transfer_insufficient_funds(self):
        from_acc = AccountFactory(owner=self.user, balance="50.00")
        to_acc   = AccountFactory(owner=self.user)

        resp = self.client.post("/api/transactions/transfer/", {
            "from_account_id": str(from_acc.id),
            "to_account_id":   str(to_acc.id),
            "amount": "100.00",
            "transfer_type": "TRANSFER_INTERNAL",
        })

        assert resp.status_code == 400
```

### Service Test Example

```python
# apps/transactions/tests/test_services.py
import pytest
from decimal import Decimal
from apps.transactions.services import transfer

@pytest.mark.django_db
def test_idempotency_returns_same_result():
    user = UserFactory()
    from_acc = AccountFactory(owner=user, balance="500.00")
    to_acc   = AccountFactory(owner=user)

    key = "unique-idem-key-abc"
    result1 = transfer(from_acc.id, to_acc.id, Decimal("50.00"), user.id, idempotency_key=key)
    result2 = transfer(from_acc.id, to_acc.id, Decimal("50.00"), user.id, idempotency_key=key)

    assert result1.id == result2.id          # same transaction returned
    from_acc.refresh_from_db()
    assert from_acc.balance == Decimal("450.00")  # only debited once
```

---

## Security Scanning

```bash
# SAST — checks for hardcoded passwords, SQL injection, etc.
bandit -r apps/ config/ utils/ -ll

# Dependency CVE check
safety check

# Both run automatically in CI before tests
```

---

## pytest.ini

```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings.dev
python_files = tests.py test_*.py *_tests.py
python_classes = Test*
python_functions = test_*
addopts = --reuse-db
markers =
    unit: marks tests as unit tests (fast, no external calls)
    integration: marks tests as integration tests (uses real DB)
```

---

## Coverage Targets

| Module | Target |
|---|---|
| `apps/transactions/services.py` | 95%+ |
| `apps/users/views.py` | 90%+ |
| `apps/loans/services.py` | 90%+ |
| `apps/admin_portal/views.py` | 85%+ |
| Overall | 80%+ |
