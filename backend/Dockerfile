# ═══════════════════════════════════════════════════════════════════
#  Voice Spark AI — Backend Dockerfile
#  Base: Python 3.12 slim + Playwright Chromium
# ═══════════════════════════════════════════════════════════════════
FROM python:3.12-slim AS backend

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=voice_spark.settings

WORKDIR /app

# Install system dependencies required for:
#  - psycopg2 (libpq-dev)
#  - Pillow (libjpeg, zlib)
#  - cryptography (libffi, libssl)
#  - General build tools
#  - curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (cached layer — only re-runs when requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium browser + required system dependencies
# --with-deps auto-installs all OS-level libraries Chromium needs
RUN playwright install --with-deps chromium

# Copy application code
COPY . .

# Create non-root user and prepare directories
RUN addgroup --system appgroup \
    && adduser --system --ingroup appgroup appuser \
    && mkdir -p /app/staticfiles /app/media \
    && chown -R appuser:appgroup /app

# Copy and set entrypoint
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["gunicorn"]
