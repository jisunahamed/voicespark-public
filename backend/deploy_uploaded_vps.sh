#!/usr/bin/env bash
set -euo pipefail

APP_DIR=${APP_DIR:-/opt/voice-spark-ai}
APP_USER=${APP_USER:-voice_spark}
BACKEND_PORT=${BACKEND_PORT:-8000}

if [[ $EUID -ne 0 ]]; then
  echo "Run as root." >&2
  exit 1
fi

if [[ ! -d "$APP_DIR/backend" ]]; then
  echo "$APP_DIR/backend does not exist. Upload and extract the app first." >&2
  exit 1
fi

if [[ ! -f "$APP_DIR/backend/.env" ]]; then
  echo "$APP_DIR/backend/.env does not exist. Upload production env first." >&2
  exit 2
fi

apt-get update
apt-get install -y python3 python3-venv python3-pip nginx postgresql postgresql-contrib redis-server git curl

if ! id "$APP_USER" >/dev/null 2>&1; then
  useradd --system --create-home --shell /bin/bash "$APP_USER"
fi

chown -R "$APP_USER":"$APP_USER" "$APP_DIR"
cd "$APP_DIR/backend"

sudo -u "$APP_USER" python3 -m venv .venv
sudo -u "$APP_USER" .venv/bin/python -m pip install --upgrade pip
sudo -u "$APP_USER" .venv/bin/pip install -r requirements.txt
./.venv/bin/python -m playwright install-deps chromium
sudo -u "$APP_USER" .venv/bin/python -m playwright install chromium

mapfile -t DB_ENV < <(sudo -u "$APP_USER" .venv/bin/python - <<'PY'
from dotenv import dotenv_values

env = dotenv_values(".env")
for key in ("DB_NAME", "DB_USER", "DB_PASSWORD"):
    value = env.get(key)
    if not value:
        raise SystemExit(f"Missing {key} in .env")
    print(value)
PY
)
DB_NAME=${DB_ENV[0]}
DB_USER=${DB_ENV[1]}
DB_PASSWORD=${DB_ENV[2]}

sudo -u postgres psql <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${DB_USER}') THEN
    CREATE ROLE ${DB_USER} LOGIN PASSWORD '${DB_PASSWORD}';
  END IF;
  ALTER ROLE ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';
END
\$\$;
SELECT 'CREATE DATABASE ${DB_NAME} OWNER ${DB_USER}'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${DB_NAME}')\gexec
GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};
SQL

sudo -u "$APP_USER" .venv/bin/python manage.py migrate
sudo -u "$APP_USER" .venv/bin/python manage.py migrate --run-syncdb
sudo -u "$APP_USER" .venv/bin/python manage.py collectstatic --noinput

cat >/etc/systemd/system/voice-spark-backend.service <<EOF
[Unit]
Description=Voice Spark AI Django backend
After=network.target postgresql.service redis-server.service

[Service]
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR/backend
EnvironmentFile=$APP_DIR/backend/.env
ExecStart=$APP_DIR/backend/.venv/bin/gunicorn blaze.wsgi:application --bind 127.0.0.1:$BACKEND_PORT --workers 3 --timeout 120
Restart=always

[Install]
WantedBy=multi-user.target
EOF

cat >/etc/systemd/system/voice-spark-celery.service <<EOF
[Unit]
Description=Voice Spark AI Celery worker
After=network.target redis-server.service postgresql.service

[Service]
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR/backend
EnvironmentFile=$APP_DIR/backend/.env
ExecStart=$APP_DIR/backend/.venv/bin/celery -A blaze worker -l info -Q celery,make_posts
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now voice-spark-backend voice-spark-celery redis-server
systemctl restart voice-spark-backend voice-spark-celery

cat >/etc/nginx/sites-available/voice-spark-backend <<EOF
server {
    listen 80;
    server_name _;

    client_max_body_size 25m;

    location /media/ {
        alias $APP_DIR/backend/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:$BACKEND_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

ln -sf /etc/nginx/sites-available/voice-spark-backend /etc/nginx/sites-enabled/voice-spark-backend
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx

echo "Backend deployed. Check: http://$(curl -s ifconfig.me)/"
