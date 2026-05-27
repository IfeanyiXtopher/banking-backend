## Native VPS Deployment (Nginx + Gunicorn + Celery)

This folder contains systemd unit templates for running the backend without Docker.

### 1) Adjust paths

Edit the unit files to match:
- your deploy path (recommended: `/opt/banking-backend`)
- the Linux user that should run the services (recommended: `ubuntu`)
- the venv path (recommended: `/opt/banking-backend/venv`)

### 2) Environment file

systemd loads `/opt/banking-backend/.env` via `EnvironmentFile=`.
Make sure it is present and readable by the service user.

### 3) Static + DB setup

On each deploy (or after pulling new code):
- `python manage.py migrate --noinput`
- `python manage.py seed_data`
- `python manage.py collectstatic --noinput`

Then restart services:
- `systemctl restart banking-backend-gunicorn`
- `systemctl restart banking-backend-celery`
- `systemctl restart banking-backend-celery-beat`

