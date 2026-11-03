#!/usr/bin/env bash
# Render build command for the Ruvia backend.
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate --no-input

# Optional: create the admin account from DJANGO_SUPERUSER_EMAIL and DJANGO_SUPERUSER_PASSWORD.
if [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  python manage.py createsuperuser --no-input || true
fi

# Optional: SEED_DEMO=true creates Jane and Joe once. SEED_DEMO=refresh rebuilds them on every deploy.
if [ "$SEED_DEMO" = "true" ]; then
  python manage.py seed_demo --if-missing
elif [ "$SEED_DEMO" = "refresh" ]; then
  python manage.py seed_demo
fi
