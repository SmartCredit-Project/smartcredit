#!/bin/sh
# ============================================================
# SMARTCREDIT - POINT D'ENTREE DU CONTENEUR BACKEND
# ============================================================

set -e

echo "Collecte des fichiers statiques..."

python manage.py collectstatic --noinput

echo "Application des migrations de la base de données..."

python manage.py migrate --noinput

if [ -n "${DJANGO_SUPERUSER_EMAIL:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
    echo "Vérification du super administrateur..."

    python manage.py ensure_superuser
else
    echo "Création automatique du super administrateur ignorée (variables absentes)."
fi

PORT="${PORT:-8000}"
GUNICORN_WORKERS="${GUNICORN_WORKERS:-1}"
GUNICORN_THREADS="${GUNICORN_THREADS:-4}"

echo "Démarrage de Gunicorn sur le port ${PORT}..."

exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT}" \
    --workers "${GUNICORN_WORKERS}" \
    --threads "${GUNICORN_THREADS}" \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
