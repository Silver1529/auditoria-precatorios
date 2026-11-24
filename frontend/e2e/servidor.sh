#!/usr/bin/env bash
# Servidor do teste ponta a ponta: banco SQLite novo a cada execução, usuário e2e, porta 8001.
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/../.." && pwd)"
BANCO="$RAIZ/web/e2e.sqlite3"
PY="$RAIZ/.venv/bin/python"
export DEBUG=1 DATABASE_URL="sqlite:///$BANCO"
rm -f "$BANCO"
cd "$RAIZ/web"
"$PY" manage.py migrate -v0
DJANGO_SUPERUSER_PASSWORD=e2e-senha-123 "$PY" manage.py createsuperuser --noinput --username e2e --email e2e@example.com >/dev/null
exec "$PY" manage.py runserver 127.0.0.1:8001 --noreload
