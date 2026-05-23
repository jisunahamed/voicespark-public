@echo off
REM ═══════════════════════════════════════════════════════════════════
REM  Voice Spark AI — Quick Start Script (Windows)
REM ═══════════════════════════════════════════════════════════════════

echo.
echo ╔══════════════════════════════════════════════════╗
echo ║        Voice Spark AI — Docker Setup             ║
echo ╚══════════════════════════════════════════════════╝
echo.

REM Check Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not installed.
    echo    Install from: https://docs.docker.com/desktop/install/windows-install/
    pause
    exit /b 1
)
echo ✅ Docker found

REM Check Docker Compose
docker compose version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker Compose is not available.
    echo    Make sure Docker Desktop is installed and running.
    pause
    exit /b 1
)
echo ✅ Docker Compose found

REM Check .env exists
if not exist .env (
    echo.
    echo 📋 No .env file found. Creating from .env.example...
    copy .env.example .env >nul
    echo ⚠️  Please edit .env with your actual values (API keys, passwords)
    echo    At minimum, update:
    echo      - SECRET_KEY
    echo      - POSTGRES_PASSWORD / DB_PASSWORD
    echo      - GEMINI_API_KEY
    echo.
    pause
)

echo.
echo 🐳 Building and starting containers...
echo.

docker compose up -d --build

echo.
echo ══════════════════════════════════════════════════
echo ✅ Voice Spark AI is starting!
echo.
echo 📊 Container status:
docker compose ps
echo.
echo 🌐 Access the app at: http://localhost
echo 🔧 Admin panel at:    http://localhost/admin/
echo ❤️  Health check at:   http://localhost/health/
echo.
echo 📋 Useful commands:
echo    docker compose logs -f          View all logs
echo    docker compose logs backend -f  View backend logs
echo    docker compose logs celery -f   View Celery logs
echo    docker compose down             Stop all services
echo    docker compose down -v          Stop and remove volumes
echo ══════════════════════════════════════════════════
echo.
pause
