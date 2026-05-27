# Deployment Guide (VPS) — Nginx + Gunicorn + Celery

This guide assumes you are running the backend on a VPS using:
- Gunicorn (ASGI) on `127.0.0.1:8000`
- Nginx as the reverse proxy (TLS termination)
- Celery worker + Celery beat in systemd

## Prerequisites

- Ubuntu 22.04 VPS (2 vCPU / 4 GB RAM minimum)
- Domain pointing to the VPS (example: `api.yourdomain.com`)
- Postgres, Redis, RabbitMQ reachable (installed on the VPS, or managed services)
- Nginx + Certbot for TLS

## 1) System packages

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y nginx certbot python3-venv python3-pip build-essential
```

## 2) Clone & configure

```bash
git clone <your-backend-repo> /opt/banking-backend
cd /opt/banking-backend

cp .env.example .env
nano .env   # set DB_HOST/REDIS_URL/RABBITMQ_URL, DJANGO_SETTINGS_MODULE=config.settings.prod, ALLOWED_HOSTS, etc.
```

Expected key values for production:
- `DJANGO_SETTINGS_MODULE=config.settings.prod`
- `DEBUG=False`
- `ALLOWED_HOSTS=api.yourdomain.com,...`
- `CORS_ALLOWED_ORIGINS=https://app.yourdomain.com` (if you have a separate frontend origin)

## 3) TLS with Let's Encrypt

Stop anything that uses port 80, then:

```bash
sudo certbot certonly --standalone -d api.yourdomain.com
```

You will have:
- `/etc/letsencrypt/live/api.yourdomain.com/fullchain.pem`
- `/etc/letsencrypt/live/api.yourdomain.com/privkey.pem`

Update `/opt/banking-backend/nginx/nginx.conf` to point to those paths:
- `ssl_certificate`
- `ssl_certificate_key`

## 4) Nginx configuration

1. Edit `/opt/banking-backend/nginx/nginx.conf`:
   - `server_name api.yourdomain.com;`
   - TLS cert paths (step 3)
   - Static/media paths if your deploy folder differs (defaults assume `/opt/banking-backend`)
2. Enable config:

```bash
sudo ln -sf /opt/banking-backend/nginx/nginx.conf /etc/nginx/sites-available/banking-backend.conf
sudo ln -sf /etc/nginx/sites-available/banking-backend.conf /etc/nginx/sites-enabled/banking-backend.conf

sudo nginx -t
sudo systemctl reload nginx
```

## 5) Python environment + Django setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements/prod.txt

python manage.py migrate --noinput
python manage.py seed_data
python manage.py collectstatic --noinput
```

## 6) systemd services (Gunicorn + Celery)

Unit templates live in:
`/opt/banking-backend/deploy/systemd/`

1. Copy them into systemd:

```bash
sudo cp /opt/banking-backend/deploy/systemd/*.service /etc/systemd/system/
```

2. Edit the files to match your server:
- `User` / `Group` (recommended: the deploy user that owns `/opt/banking-backend`)
- `EnvironmentFile=/opt/banking-backend/.env`
- `ExecStart` paths if your venv is elsewhere

3. Start and enable:

```bash
sudo systemctl daemon-reload
sudo systemctl enable banking-backend-gunicorn
sudo systemctl enable banking-backend-celery
sudo systemctl enable banking-backend-celery-beat

sudo systemctl start banking-backend-gunicorn
sudo systemctl start banking-backend-celery
sudo systemctl start banking-backend-celery-beat
```

## 7) Verify

- Swagger UI: `https://api.yourdomain.com/api/docs/`
- API health: `https://api.yourdomain.com/api/` (or any known endpoint)

Check logs:
- `journalctl -u banking-backend-gunicorn -f`
- `journalctl -u banking-backend-celery -f`
- `journalctl -u banking-backend-celery-beat -f`

## Backup notes

- Back up Postgres using `pg_dump`
- Back up `/opt/banking-backend/media/` for uploaded files

