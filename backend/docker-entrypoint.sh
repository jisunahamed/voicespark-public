#!/bin/bash
set -e

echo "══════════════════════════════════════════════════"
echo "  Voice Spark AI — Backend Starting"
echo "══════════════════════════════════════════════════"

# Wait for PostgreSQL to be ready
if [ -n "$DB_HOST" ] && [ "$DB_HOST" != "localhost" ]; then
    echo "⏳ Waiting for PostgreSQL at $DB_HOST:${DB_PORT:-5432}..."
    for i in $(seq 1 30); do
        if python -c "
import socket
s = socket.socket()
s.settimeout(2)
s.connect(('$DB_HOST', ${DB_PORT:-5432}))
s.close()
" 2>/dev/null; then
            echo "✅ PostgreSQL is ready"
            break
        fi
        if [ "$i" -eq 30 ]; then
            echo "❌ PostgreSQL not available after 30 attempts"
            exit 1
        fi
        echo "   Attempt $i/30 — waiting 2s..."
        sleep 2
    done
fi

# Run database migrations
echo "🔄 Running database migrations..."
python manage.py migrate --noinput

# Create cache table (required for Django DB cache backend used by Celery)
echo "🔄 Creating cache table..."
python manage.py createcachetable 2>/dev/null || true

# Collect static files
echo "📦 Collecting static files..."
python manage.py collectstatic --noinput

echo "══════════════════════════════════════════════════"

# Determine what to run based on CMD argument
if [ "$1" = "gunicorn" ] || [ -z "$1" ]; then
    echo "🚀 Starting Gunicorn on port 8000..."
    exec gunicorn blaze.wsgi:application \
        --bind 0.0.0.0:8000 \
        --workers "${GUNICORN_WORKERS:-3}" \
        --timeout "${GUNICORN_TIMEOUT:-120}" \
        --access-logfile - \
        --error-logfile -
elif [ "$1" = "celery" ]; then
    echo "🚀 Starting Celery worker (queues: celery, make_posts)..."
    exec celery -A blaze worker \
        -l info \
        -Q celery,make_posts \
        -c "${CELERY_CONCURRENCY:-2}" \
        --without-heartbeat \
        --without-mingle
else
    exec "$@"
fi
