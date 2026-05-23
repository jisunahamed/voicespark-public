#!/usr/bin/env bash
set -euo pipefail

APP_DIR=${APP_DIR:-/opt/voice-spark-ai}
REPO_URL=${REPO_URL:-https://github.com/jisunahamed/Voice-Spark-AI-.git}
APP_USER=${APP_USER:-voice_spark}
BACKEND_PORT=${BACKEND_PORT:-8000}

if [[ $EUID -ne 0 ]]; then
  echo "Run as root." >&2
  exit 1
fi

apt-get update
apt-get install -y python3 python3-venv python3-pip nginx postgresql postgresql-contrib redis-server git curl

if ! id "$APP_USER" >/dev/null 2>&1; then
  useradd --system --create-home --shell /bin/bash "$APP_USER"
fi

mkdir -p "$APP_DIR"
if [[ ! -d "$APP_DIR/.git" ]]; then
  git clone "$REPO_URL" "$APP_DIR"
else
  git -C "$APP_DIR" fetch origin main
  git -C "$APP_DIR" reset --hard origin/main
fi

chown -R "$APP_USER":"$APP_USER" "$APP_DIR"
cd "$APP_DIR/backend"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created $APP_DIR/backend/.env. Edit it with production secrets, then rerun this script." >&2
  exit 2
fi

sudo -u "$APP_USER" python3 -m venv .venv
sudo -u "$APP_USER" .venv/bin/python -m pip install --upgrade pip
sudo -u "$APP_USER" .venv/bin/pip install -r requirements.txt
sudo -u "$APP_USER" .venv/bin/python -m playwright install chromium

set -a
source .env
set +a

sudo -u postgres psql <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${DB_USER}') THEN
    CREATE ROLE ${DB_USER} LOGIN PASSWORD '${DB_PASSWORD}';
  END IF;
END
\$\$;
SELECT 'CREATE DATABASE ${DB_NAME} OWNER ${DB_USER}'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${DB_NAME}')\\gexec
GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};
SQL

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
ExecStart=$APP_DIR/backend/.venv/bin/celery -A blaze worker -l info
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
