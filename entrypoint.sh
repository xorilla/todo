#!/bin/sh
# Passos previs abans d'arrencar gunicorn:
#   1. collectstatic (whitenoise serveix els fitxers estàtics)
#   2. migrate       (esquema de la base de dades)
#   3. gunicorn      (servidor WSGI)
set -e

cd /app

python manage.py collectstatic --noinput
python manage.py migrate --noinput

exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 2 \
    --timeout 60
