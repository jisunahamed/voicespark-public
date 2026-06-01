<p align="center">
  <img src="https://img.shields.io/badge/Django-6.0-092E20?style=for-the-badge&logo=django&logoColor=white" />
  <img src="https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black" />
  <img src="https://img.shields.io/badge/Celery-5.x-37814A?style=for-the-badge&logo=celery&logoColor=white" />
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white" />
  <img src="https://img.shields.io/badge/Playwright-Chromium-2EAD33?style=for-the-badge&logo=playwright&logoColor=white" />
  <img src="https://img.shields.io/badge/PostgreSQL-16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" />
</p>

<h1 align="center">⚡ Voice Spark AI</h1>

<p align="center">
  <strong>AI-powered social media content engine</strong><br/>
  Website intelligence · Brand analysis · Campaign planning · Multi-platform publishing
</p>

<p align="center">
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-features">Features</a> •
  <a href="#️-architecture">Architecture</a> •
  <a href="#-environment-variables">Config</a> •
  <a href="#-development">Development</a> •
  <a href="#-api-reference">API</a> •
  <a href="#-troubleshooting">Troubleshooting</a>
</p>

---

## 🚀 Quick Start

> **Prerequisites:** [Docker Desktop](https://docs.docker.com/get-docker/) (includes Docker Compose v2). That's it — no Node, Python, or database setup required.

```bash
# 1️⃣  Clone
git clone https://github.com/jisunahamed/voicespark-public.git
cd voicespark-public

# 2️⃣  Configure
cp .env.example .env
#    Edit .env → set SECRET_KEY, DB passwords, GEMINI_API_KEY

# 3️⃣  Launch
docker compose up -d --build
```

🎉 **Open [http://localhost](http://localhost)** — the entire stack is running.

<details>
<summary><b>🪟 Windows users — click here</b></summary>

```cmd
git clone https://github.com/jisunahamed/voicespark-public.git
cd voicespark-public
copy .env.example .env
notepad .env
start.bat
```

Or just double-click `start.bat`.

</details>

<details>
<summary><b>🍎 macOS / 🐧 Linux users — click here</b></summary>

```bash
git clone https://github.com/jisunahamed/voicespark-public.git
cd voicespark-public
cp .env.example .env
nano .env          # or vim, or your preferred editor
chmod +x start.sh && ./start.sh
```

</details>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🤖 **AI Content Generation** | Gemini-powered captions, image prompts, blog content, and hashtag suggestions |
| 🌐 **Website Intelligence** | Playwright-driven crawling + AI brand analysis — extracts colors, fonts, tone, audiences |
| 📊 **Campaign Planner** | Multi-week campaign strategy with funnel-aware content calendar generation |
| 📱 **Multi-Platform Publish** | Direct publishing to **Facebook**, **Instagram**, **LinkedIn**, **X/Twitter**, **WordPress** |
| 🎨 **Brand Kit** | Manages brand colors, typography, visual style, logo, and voice guidelines |
| 🕵️ **Competitor Tracking** | Auto-discovers and analyzes competitor websites and social presence |
| 📅 **Scheduling** | Queue and auto-publish posts at optimal times with Celery |
| 🏢 **Multi-Workspace** | Manage multiple brands/clients from a single account |
| 🖼️ **AI Image Generation** | NanoBanana integration for on-brand social media visuals |
| 🔐 **OAuth Flows** | Full OAuth2/OAuth1 for Meta, LinkedIn, X, and WordPress |

---

## 🏗️ Architecture

```
                    ┌─────────────────────────────────┐
                    │          Nginx (:80)             │
                    │      reverse proxy + gzip        │
                    └──────────┬──────────┬────────────┘
                               │          │
              ┌────────────────┘          └────────────────┐
              ▼                                            ▼
  ┌───────────────────────┐                 ┌──────────────────────────┐
  │   Frontend (React)    │                 │   Backend (Django)       │
  │   Vite + MUI + nginx  │                 │   Gunicorn + Playwright  │
  │   port 80 (internal)  │                 │   port 8000 (internal)   │
  └───────────────────────┘                 └─────────────┬────────────┘
                                                          │
                                            ┌─────────────┴────────────┐
                                            ▼                          ▼
                                 ┌──────────────────┐      ┌──────────────────┐
                                 │   Celery Worker   │      │   Celery Beat     │
                                 │  queues: celery,  │      │   (optional)      │
                                 │  make_posts       │      │                   │
                                 └────────┬──────────┘      └──────────────────┘
                                          │
                           ┌──────────────┴──────────────┐
                           ▼                              ▼
                ┌───────────────────┐          ┌───────────────────┐
                │  PostgreSQL 16    │          │     Redis 7       │
                │  primary data     │          │   task broker     │
                └───────────────────┘          └───────────────────┘
```

### Service Map

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `nginx` | `nginx:alpine` | **80** (only public port) | Reverse proxy, gzip, security headers |
| `frontend` | `node:22` → `nginx:alpine` | internal | Vite React SPA (multi-stage build) |
| `backend` | `python:3.12-slim` + Playwright | internal | Django REST API + Gunicorn |
| `celery` | same as backend | — | Async task processing (content gen, publishing) |
| `postgres` | `postgres:16-alpine` | internal | Primary database |
| `redis` | `redis:7-alpine` | internal | Celery message broker |

### Request Flow

```
Browser → :80 nginx
  ├── /admin/*, /auth/*, /content-engine/*, /nano-banana/*, /workspace/*
  │     └→ backend:8000 (Django — no prefix stripping)
  ├── /static/*, /media/*
  │     └→ backend:8000 (Gunicorn serves collected static + media)
  └── /* (everything else)
        └→ frontend:80 (React SPA with try_files → index.html)
```

---

## 📁 Project Structure

```
voicespark-public/
├── docker-compose.yml          # 🐳 6-service orchestration
├── .env.example                # 📋 All configurable variables
├── start.sh / start.bat        # 🚀 One-click start scripts
├── nginx/
│   └── nginx.conf              # Reverse proxy config
├── backend/                    # 🐍 Django 6.0 API
│   ├── Dockerfile
│   ├── docker-entrypoint.sh    # Migrate → cache → static → start
│   ├── voice_spark/                  # Django project settings + WSGI
│   ├── auth_user/              # JWT authentication
│   ├── content_engine/         # Website crawling + AI analysis
│   ├── nano_banana/            # Image generation + content posts
│   ├── fb_auth/                # Facebook/Instagram OAuth
│   ├── linkedin_auth/          # LinkedIn OAuth
│   ├── x_auth/                 # X/Twitter OAuth (1.0a + 2.0)
│   ├── wordpress_auth/         # WordPress publishing
│   ├── workspace/              # Multi-workspace management
│   └── utils/                  # Shared utilities
└── frontend/                   # ⚛️ React 19 + Vite + MUI
    ├── Dockerfile              # Multi-stage: build → nginx
    ├── nginx.conf              # SPA routing
    └── src/
```

---

## 🔐 Environment Variables

### Required (app won't work without these)

| Variable | What it does | How to get it |
|----------|-------------|---------------|
| `SECRET_KEY` | Django cryptographic signing | Run: `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `POSTGRES_PASSWORD` | Database password | Choose a strong password |
| `DB_PASSWORD` | Same as above (Django side) | Must match `POSTGRES_PASSWORD` |
| `GEMINI_API_KEY` | Powers all AI features | [Google AI Studio](https://aistudio.google.com/apikey) |
| `ENCRYPTION_KEY` | Encrypts stored OAuth tokens | Run: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |

### Required for image generation

| Variable | What it does |
|----------|-------------|
| `NANOBANANA_API_KEY` | AI image generation for social posts |

### Social Media OAuth (optional — enable per platform)

<details>
<summary><b>📘 Facebook / Instagram</b></summary>

Create a Meta App at [developers.facebook.com](https://developers.facebook.com):

```env
META_APP_ID=your-meta-app-id
META_APP_SECRET=your-meta-app-secret
META_REDIRECT_URI=http://localhost/auth/fb/callback
INSTAGRAM_REDIRECT_URI=http://localhost/auth/fb/callback
FACEBOOK_CONFIG_ID=your-facebook-login-config-id
INSTAGRAM_CONFIG_ID=your-instagram-login-config-id
```

Required Meta App permissions: `email`, `public_profile`, `pages_manage_posts`, `pages_read_engagement`, `pages_show_list`, `instagram_content_publish`, `instagram_manage_insights`

</details>

<details>
<summary><b>💼 LinkedIn</b></summary>

Create an app at [linkedin.com/developers](https://www.linkedin.com/developers/):

```env
LINKEDIN_CLIENT_ID=your-linkedin-client-id
LINKEDIN_CLIENT_SECRET=your-linkedin-client-secret
LINKEDIN_REDIRECT_URI=http://localhost/auth/linkedin/callback/
```

Required products: Sign In with LinkedIn, Share on LinkedIn, Marketing Developer Platform (for org posts)

</details>

<details>
<summary><b>🐦 X / Twitter</b></summary>

Create a project at [developer.x.com](https://developer.x.com):

```env
# OAuth 2.0
X_CLIENT_ID=your-x-client-id
X_CLIENT_SECRET=your-x-client-secret
X_REDIRECT_URI=http://localhost/auth/x/callback/

# OAuth 1.0a (required for media uploads)
X_CONSUMER_KEY=your-consumer-key
X_CONSUMER_SECRET=your-consumer-secret
X_OAUTH1_CALLBACK=http://localhost/auth/x/callback/
```

App permissions required: Read and Write

</details>

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `false` | Django debug mode |
| `PORT` | `80` | Host port for the app |
| `BACKEND_URL` | `http://localhost` | Public URL for media links |
| `GUNICORN_WORKERS` | `3` | Gunicorn process count |
| `CELERY_CONCURRENCY` | `2` | Parallel Celery tasks (keep low — Playwright is memory-heavy) |
| `CONTENT_ENGINE_USE_CELERY` | `true` | Use Celery for content tasks (recommended) |
| `ADVANCED_PIPELINE_ENABLED` | `false` | Enable advanced AI pipeline |
| `DB_SSL_MODE` | `disable` | PostgreSQL SSL mode (`require` for cloud DBs) |

See [`.env.example`](.env.example) for the complete list.

---

## 🛠️ Development

### Option A: Full Docker (recommended for most devs)

Everything runs inside Docker. Create `docker-compose.override.yml` for live reload:

```yaml
# docker-compose.override.yml (gitignored — create it yourself)
services:
  backend:
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - ./backend:/app
    environment:
      - DEBUG=true

  frontend:
    build:
      target: build
    command: npm run dev -- --host 0.0.0.0 --port 80
    volumes:
      - ./frontend:/app
      - /app/node_modules
```

Then `docker compose up --build`.

### Option B: Hybrid (Docker for infra, local for code)

Best for fast iteration. You need Python 3.12 and Node 22 installed.

```bash
# Terminal 1 — Infrastructure
docker compose up postgres redis -d

# Terminal 2 — Backend
cd backend
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
playwright install chromium
python manage.py migrate
python manage.py runserver

# Terminal 3 — Frontend
cd frontend
npm install
npm run dev
```

### Useful Commands

```bash
# 📋 Logs
docker compose logs -f                    # All services
docker compose logs backend celery -f     # Backend + worker only

# 🔧 Django management
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py shell
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py migrate

# 🔄 Rebuild after code changes
docker compose up -d --build

# 🗑️ Full reset (WARNING: destroys database)
docker compose down -v
docker compose up -d --build

# 📊 Check health
curl http://localhost/health/
docker compose ps
```

---

## 🔌 API Reference

### Authentication

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/user/register/` | POST | Create new account |
| `/auth/user/login/` | POST | Login → JWT tokens |
| `/auth/user/token/refresh/` | POST | Refresh access token |

### Content Engine

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/content-engine/analyse-brand/` | POST | Crawl website + AI brand analysis |
| `/content-engine/campaign-plans/` | POST | Generate multi-week campaign |
| `/content-engine/generate/` | POST | Generate individual content pieces |
| `/content-engine/source-matrix/` | POST | Manage content sources |

### Publishing

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/nano-banana/generate/` | POST | Generate post image + captions |
| `/auth/fb/post/` | POST | Publish to Facebook |
| `/auth/fb/instagram/post/` | POST | Publish to Instagram |
| `/auth/linkedin/post/` | POST | Publish to LinkedIn |
| `/auth/x/post/` | POST | Publish to X/Twitter |

### Workspace

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/workspace/` | GET/POST | List / create workspaces |
| `/workspace/<id>/` | GET/PATCH | Workspace details |

---

## 🐛 Troubleshooting

<details>
<summary><b>Port 80 already in use</b></summary>

Change it in `.env`:
```env
PORT=8080
```
Restart: `docker compose up -d`
Access at `http://localhost:8080`

</details>

<details>
<summary><b>Database connection refused</b></summary>

Make sure your `.env` has:
```env
DB_HOST=postgres          # NOT localhost
DB_SSL_MODE=disable       # Docker doesn't use SSL
```
Then: `docker compose restart backend`

</details>

<details>
<summary><b>Playwright / Chromium crashes (OOM)</b></summary>

Increase shared memory in `docker-compose.yml`:
```yaml
backend:
  shm_size: '512m'    # default is 256m
celery:
  shm_size: '512m'
```

Also make sure Docker Desktop has at least **4 GB RAM** allocated.

</details>

<details>
<summary><b>Windows: "bash\r: No such file or directory"</b></summary>

Line ending issue. The `.gitattributes` file prevents this, but if you cloned before it existed:
```bash
git rm --cached -r .
git reset --hard
```

</details>

<details>
<summary><b>Frontend shows blank page</b></summary>

Check if `VITE_BACKEND_SERVER` in `.env` matches your setup:
```env
VITE_BACKEND_SERVER=http://localhost/        # Docker
VITE_BACKEND_SERVER=http://localhost:8000/   # Local dev
```
Frontend must be rebuilt after changing Vite env vars:
```bash
docker compose up -d --build frontend
```

</details>

<details>
<summary><b>Social media OAuth callback fails</b></summary>

Redirect URIs in `.env` must **exactly match** what's configured in each platform's developer console:
```env
META_REDIRECT_URI=http://localhost/auth/fb/callback
LINKEDIN_REDIRECT_URI=http://localhost/auth/linkedin/callback/
X_REDIRECT_URI=http://localhost/auth/x/callback/
```
For production, replace `http://localhost` with your domain.

</details>

<details>
<summary><b>Create admin/superuser account</b></summary>

```bash
docker compose exec backend python manage.py createsuperuser
```
Then login at `http://localhost/admin/`

</details>

---

## 🌍 Production Deployment

For deploying on a VPS (DigitalOcean, Hetzner, AWS EC2, etc.):

```bash
# 1. SSH into your server
ssh user@your-server

# 2. Clone + configure
git clone https://github.com/jisunahamed/voicespark-public.git
cd voicespark-public
cp .env.example .env

# 3. Update .env for production
nano .env
```

Key production `.env` changes:

```env
DEBUG=false
SECRET_KEY=<generate-a-real-key>
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CORS_ALLOWED_ORIGINS=https://yourdomain.com
BACKEND_URL=https://yourdomain.com
VITE_BACKEND_SERVER=https://yourdomain.com/
VITE_SCRAPER_BACKEND_SERVER=https://yourdomain.com/

# Update all OAuth redirect URIs to use your domain
META_REDIRECT_URI=https://yourdomain.com/auth/fb/callback
LINKEDIN_REDIRECT_URI=https://yourdomain.com/auth/linkedin/callback/
X_REDIRECT_URI=https://yourdomain.com/auth/x/callback/
X_OAUTH1_CALLBACK=https://yourdomain.com/auth/x/callback/
```

```bash
# 4. Launch
docker compose up -d --build

# 5. Add SSL (recommended: use Caddy or Certbot in front of nginx)
```

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## 📄 License

This project is open source. See [LICENSE](LICENSE) for details.

---

<p align="center">
  Built with ❤️ by <a href="https://github.com/jisunahamed">Jisun Ahamed</a>
</p>
