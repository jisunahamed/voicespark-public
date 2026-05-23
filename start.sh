#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
#  Voice Spark AI — Quick Start Script (Linux / macOS)
# ═══════════════════════════════════════════════════════════════════
set -e

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║        Voice Spark AI — Docker Setup             ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# Check Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed."
    echo "   Install from: https://docs.docker.com/get-docker/"
    exit 1
fi
echo "✅ Docker found: $(docker --version)"

# Check Docker Compose
if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose (v2) is not available."
    echo "   Install from: https://docs.docker.com/compose/install/"
    exit 1
fi
echo "✅ Docker Compose found: $(docker compose version --short)"

# Check .env exists
if [ ! -f .env ]; then
    echo ""
    echo "📋 No .env file found. Creating from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your actual values (API keys, passwords)"
    echo "   At minimum, update:"
    echo "     - SECRET_KEY"
    echo "     - POSTGRES_PASSWORD / DB_PASSWORD"
    echo "     - GEMINI_API_KEY"
    echo ""
    read -p "   Press Enter to continue after editing .env, or Ctrl+C to abort..."
fi

echo ""
echo "🐳 Building and starting containers..."
echo ""

docker compose up -d --build

echo ""
echo "══════════════════════════════════════════════════"
echo "✅ Voice Spark AI is starting!"
echo ""
echo "📊 Container status:"
docker compose ps
echo ""
echo "🌐 Access the app at: http://localhost"
echo "🔧 Admin panel at:    http://localhost/admin/"
echo "❤️  Health check at:   http://localhost/health/"
echo ""
echo "📋 Useful commands:"
echo "   docker compose logs -f          # View all logs"
echo "   docker compose logs backend -f  # View backend logs"
echo "   docker compose logs celery -f   # View Celery logs"
echo "   docker compose down             # Stop all services"
echo "   docker compose down -v          # Stop and remove volumes"
echo "══════════════════════════════════════════════════"
