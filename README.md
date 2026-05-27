# SafaPay Bank — Backend

> Django REST Framework API server for the SafaPay Bank banking platform.  
> Deployed on a VPS via Nginx + Gunicorn (native processes; no Docker). Frontend lives in `banking-frontend`.

## Table of Contents

- [Quick Start](#quick-start)
- [Environment Variables](#environment-variables)
- [Project Structure](#project-structure)
- [Documentation](#documentation)
- [Running Tests](#running-tests)
- [Local development](#local-development)
- [Useful Commands](#useful-commands)

---

## Quick Start

**Requirements:** Git, Python 3.12, Postgres, Redis, RabbitMQ, Nginx

```bash
# 1. Clone and enter the repo
git clone <your-repo-url> banking-backend
cd banking-backend

# 2. Configure environment
cp .env.example .env
# Edit .env with your secrets (see docs/environment.md for details)

# 3. Create venv + install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements/prod.txt

# 4. Run migrations + seed data
python manage.py migrate
python manage.py seed_data

# 5. Collect static files
python manage.py collectstatic --noinput

# 6. (Optional) Create your first superuser
python manage.py createsuperuser

# 7. Start Gunicorn + Celery worker + Celery Beat
./scripts/manage_services.sh start
```

| Service | URL |
|---|---|
| REST API | http://localhost:8000/api/ |
| Swagger UI | http://localhost:8000/api/docs/ |
| ReDoc | http://localhost:8000/api/redoc/ |
| Django Admin | http://localhost:8000/django-admin/ |
| RabbitMQ Dashboard | http://localhost:15672/ (guest / guest) |

---

## Environment Variables

See [docs/environment.md](docs/environment.md) for a full reference of every variable.

---

## Project Structure

```
banking-backend/
├── config/                  # Django project configuration
│   ├── settings/
│   │   ├── base.py          # Shared settings
│   │   ├── dev.py           # Development overrides
│   │   └── prod.py          # Production overrides (Sentry, HTTPS)
│   ├── urls.py              # Root URL configuration
│   ├── asgi.py              # ASGI entry point (HTTP + WebSocket)
│   ├── wsgi.py              # WSGI entry point
│   └── celery.py            # Celery application
│
├── apps/                    # Django applications
│   ├── users/               # Auth, MFA, KYC, profiles
│   ├── accounts/            # Bank accounts, currencies
│   ├── transactions/        # Double-entry transactions, fees, FX
│   ├── loans/               # Loan products, applications, repayments
│   ├── statements/          # PDF statement generation
│   ├── notifications/       # Email notifications, WebSocket consumer
│   ├── support/             # Support tickets
│   ├── audit/               # Immutable audit logs
│   └── admin_portal/        # RBAC-protected admin APIs
│
├── utils/                   # Shared utilities
│   ├── fx_service.py        # Open Exchange Rates integration
│   ├── tasks.py             # Celery Beat tasks
│   └── celery_schedules.py  # Periodic task registration
│
├── templates/
│   └── emails/              # Plain-text email templates
│
├── docs/                    # Developer documentation
├── nginx/nginx.conf         # Nginx reverse proxy config
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
└── pytest.ini
```

---

## Documentation

| Document | Description |
|---|---|
| [docs/architecture.md](docs/architecture.md) | System architecture, data flow diagrams |
| [docs/api-reference.md](docs/api-reference.md) | All REST endpoints with request/response examples |
| [docs/models.md](docs/models.md) | Database schema and model relationships |
| [docs/auth.md](docs/auth.md) | Authentication, MFA, JWT, and RBAC |
| [docs/transactions.md](docs/transactions.md) | Double-entry engine, idempotency, FX |
| [docs/async-tasks.md](docs/async-tasks.md) | Celery workers and scheduled jobs |
| [docs/environment.md](docs/environment.md) | All environment variables |
| [docs/deployment.md](docs/deployment.md) | VPS deployment guide (Nginx, TLS, CI/CD) |
| [docs/testing.md](docs/testing.md) | Running tests, coverage, security scanning |

---

## Running Tests

```bash
# Install dev deps (in venv)
pip install -r requirements/dev.txt

# Run full test suite with coverage
pytest --cov=apps --cov-report=term-missing -v

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Security scan (SAST)
bandit -r apps/ config/ utils/ -ll

# Dependency vulnerability check
safety check
```

---

## Local development

Native processes (venv + Gunicorn/Celery).

### Native services (`manage_services.sh`)

Typical day-to-day flow when Postgres, Redis, and RabbitMQ are reachable (local installs or separate containers) and you run Django on the host.

**Requirements:** Python venv at `./venv` with `pip install -r requirements/dev.txt`, `.env` configured (see [docs/environment.md](docs/environment.md)).

From the repo root:

```bash
./scripts/manage_services.sh start     # Gunicorn (ASGI on 127.0.0.1:8000) + Celery worker + Celery Beat
./scripts/manage_services.sh restart   # stop, then start (handy after pulling code)
./scripts/manage_services.sh stop
./scripts/manage_services.sh status
./scripts/manage_services.sh logs      # tail Gunicorn + Celery logs under logs/
```

- **REST API:** http://127.0.0.1:8000/api/ (and `/api/docs/`, `/django-admin/`, etc.)
- **Nginx is not started** by this script. For a reverse proxy on macOS you can use Homebrew nginx and `nginx/banking-backend.macos.sample.conf` (replace `REPLACE_WITH_REPO_ROOT` with this repo’s path). The script prints the same hint on start.
- **`DJANGO_SETTINGS_MODULE`** defaults to `config.settings.dev` (override if needed).

---

## Useful Commands

```bash
# Create and apply new migrations
python manage.py makemigrations
python manage.py migrate

# Open Django shell
python manage.py shell

# Collect static files
python manage.py collectstatic --noinput

# View Celery worker logs
tail -f logs/celery_worker.log

# Restart services
./scripts/manage_services.sh restart
```
