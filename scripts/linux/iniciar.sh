#!/usr/bin/env sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
if [ "${1:-}" = "--producao" ]; then
    export DJANGO_SETTINGS_MODULE=config.settings.production
    exec .venv/bin/gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 3 --timeout 90
fi
export DJANGO_SETTINGS_MODULE=config.settings.development
exec .venv/bin/python manage.py runserver 127.0.0.1:8000
