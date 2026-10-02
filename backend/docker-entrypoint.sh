#!/bin/sh
# Apply migrations, then hand off to the container command
# (gunicorn for api, celery for worker). Idempotent — a no-op when the
# schema is already current.
set -e

python manage.py migrate --noinput

exec "$@"
