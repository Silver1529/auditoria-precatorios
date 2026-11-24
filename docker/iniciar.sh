#!/bin/sh
# Início do container: migrações, usuário inicial opcional e gunicorn.
# As migrações rodam aqui porque o preDeployCommand do Render não existe no plano gratuito.
set -e
cd /app/web
python manage.py migrate --noinput
if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
  python manage.py createsuperuser --noinput --email "${DJANGO_SUPERUSER_EMAIL:-admin@example.com}" \
    >/dev/null 2>&1 && echo "usuário ${DJANGO_SUPERUSER_USERNAME} criado" || echo "usuário ${DJANGO_SUPERUSER_USERNAME} já existe"
fi
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-10000}" \
  --workers "${WEB_CONCURRENCY:-2}" --access-logfile - --error-logfile -
