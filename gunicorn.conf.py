# Gunicorn + Uvicorn worker for ASGI (Channels). Used by scripts/manage_services.sh.
# Run from repo root: gunicorn -c gunicorn.conf.py config.asgi:application

import multiprocessing
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

bind = "127.0.0.1:8000"
worker_class = "uvicorn.workers.UvicornWorker"
workers = max(2, multiprocessing.cpu_count())
timeout = 120
graceful_timeout = 30
keepalive = 5
accesslog = str(BASE_DIR / "logs" / "gunicorn_access.log")
errorlog = str(BASE_DIR / "logs" / "gunicorn_error.log")
capture_output = True
chdir = str(BASE_DIR)
