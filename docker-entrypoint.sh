#!/bin/sh
# ============================================================
# SMARTCREDIT - POINT D'ENTREE DU CONTENEUR BACKEND
# ============================================================

set -e

echo "Application des migrations de la base de données..."

python manage.py migrate --noinput

echo "Démarrage de Gunicorn..."

exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 1 \
    --threads 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
