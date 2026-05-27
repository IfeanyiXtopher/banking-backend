#!/usr/bin/env bash
#
# Native macOS/Linux stack (no Docker): Gunicorn (ASGI), Celery worker, Celery Beat.
#
# Prerequisites: venv with requirements/dev.txt, Postgres/Redis/RabbitMQ reachable
# (.env). Optional: Homebrew nginx using nginx/banking-backend.macos.sample.conf
#
# Usage:
#   ./scripts/manage_services.sh start|stop|restart|status|logs
#
# Environment (optional):
#   DJANGO_SETTINGS_MODULE   default: config.settings.dev
#

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PIDS="$ROOT/logs/pids"
GUNICORN_PID="$PIDS/gunicorn.pid"
CELERY_PID="$PIDS/celery_worker.pid"
BEAT_PID="$PIDS/celery_beat.pid"

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.dev}"

PYTHON="$ROOT/venv/bin/python"
GUNICORN="$ROOT/venv/bin/gunicorn"
CELERY="$ROOT/venv/bin/celery"

_ensure_venv() {
  if [[ ! -x "$GUNICORN" ]] || [[ ! -x "$CELERY" ]]; then
    echo "error: need venv with gunicorn & celery (e.g. pip install -r requirements/dev.txt)" >&2
    exit 1
  fi
}

_ensure_dirs() {
  mkdir -p "$PIDS" "$ROOT/logs"
}

_is_running() {
  local pid_file="$1"
  [[ -f "$pid_file" ]] || return 1
  local pid
  pid="$(cat "$pid_file")"
  kill -0 "$pid" 2>/dev/null
}

_stop_pidfile() {
  local name="$1" pid_file="$2"
  if [[ ! -f "$pid_file" ]]; then
    echo "$name: not running (no pid file)"
    return 0
  fi
  local pid
  pid="$(cat "$pid_file")"
  if kill -0 "$pid" 2>/dev/null; then
    echo "$name: stopping PID $pid"
    kill -TERM "$pid" 2>/dev/null || true
    local i=0
    while kill -0 "$pid" 2>/dev/null && [[ $i -lt 30 ]]; do
      sleep 1
      i=$((i + 1))
    done
    if kill -0 "$pid" 2>/dev/null; then
      echo "$name: force kill PID $pid"
      kill -KILL "$pid" 2>/dev/null || true
    fi
  else
    echo "$name: stale pid file (process gone)"
  fi
  rm -f "$pid_file"
}

cmd_start() {
  _ensure_venv
  _ensure_dirs

  if _is_running "$GUNICORN_PID"; then
    echo "gunicorn: already running"
  else
    echo "gunicorn: starting (127.0.0.1:8000, ASGI)"
    nohup "$GUNICORN" -c "$ROOT/gunicorn.conf.py" config.asgi:application \
      >>"$ROOT/logs/gunicorn_stdout.log" 2>>"$ROOT/logs/gunicorn_stderr.log" &
    echo $! >"$GUNICORN_PID"
  fi

  if _is_running "$CELERY_PID"; then
    echo "celery worker: already running"
  else
    echo "celery worker: starting (LC_ALL=C for macOS fork safety)"
    nohup env LC_ALL=C LANG=C "$CELERY" -A config.celery worker --loglevel=info \
      >>"$ROOT/logs/celery_worker.log" 2>>"$ROOT/logs/celery_worker_stderr.log" &
    echo $! >"$CELERY_PID"
  fi

  if _is_running "$BEAT_PID"; then
    echo "celery beat: already running"
  else
    echo "celery beat: starting"
    nohup "$CELERY" -A config.celery beat --loglevel=info \
      --scheduler django_celery_beat.schedulers:DatabaseScheduler \
      >>"$ROOT/logs/celery_beat.log" 2>>"$ROOT/logs/celery_beat_stderr.log" &
    echo $! >"$BEAT_PID"
  fi

  echo ""
  echo "Nginx is not started by this script. Example:"
  echo "  brew services start nginx"
  echo "  # Use nginx/banking-backend.macos.sample.conf (edit REPLACE_WITH_REPO_ROOT)"
}

cmd_stop() {
  _stop_pidfile "gunicorn" "$GUNICORN_PID"
  _stop_pidfile "celery worker" "$CELERY_PID"
  _stop_pidfile "celery beat" "$BEAT_PID"
}

cmd_status() {
  if _is_running "$GUNICORN_PID"; then echo "gunicorn: running (PID $(cat "$GUNICORN_PID"))"; else echo "gunicorn: stopped"; fi
  if _is_running "$CELERY_PID"; then echo "celery worker: running (PID $(cat "$CELERY_PID"))"; else echo "celery worker: stopped"; fi
  if _is_running "$BEAT_PID"; then echo "celery beat: running (PID $(cat "$BEAT_PID"))"; else echo "celery beat: stopped"; fi
}

cmd_logs() {
  echo "tail -f logs/gunicorn_stdout.log logs/gunicorn_stderr.log logs/celery_worker.log logs/celery_beat.log"
  tail -f "$ROOT/logs/gunicorn_stdout.log" "$ROOT/logs/gunicorn_stderr.log" \
    "$ROOT/logs/celery_worker.log" "$ROOT/logs/celery_beat.log" 2>/dev/null || true
}

case "${1:-}" in
  start) cmd_start ;;
  stop) cmd_stop ;;
  restart) cmd_stop; sleep 1; cmd_start ;;
  status) cmd_status ;;
  logs) cmd_logs ;;
  *)
    echo "usage: $0 start|stop|restart|status|logs" >&2
    exit 1
    ;;
esac
