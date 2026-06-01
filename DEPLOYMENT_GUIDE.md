# VoiceSpark Deployment Guide

This repository is deployed as two services:

- Frontend: Vercel project `frontend`, production alias `https://frontend-xi-one-8hr5rqjb64.vercel.app`
- Backend: existing VPS app at `/opt/voice-spark-ai/backend`, public URL `https://134-209-146-170.sslip.io`

## Source Of Truth

Use this local checkout and GitHub branch as the source of truth for application code. Do not treat copied frontend source files on the VPS as production source; the live frontend is built and served by Vercel.

Before deploying, check for drift:

```bash
git status --short --branch
```

Backend files can be compared against the VPS with checksums or by redeploying the targeted changed files from this checkout.

## Environment Files

Real `.env` files contain secrets and must not be committed to GitHub.

Tracked templates:

- `backend/.env.example`
- `frontend/.env.example`

Production secrets should be set in:

- VPS backend environment / service config for Django, Celery, provider credentials, database, storage, and API keys.
- Vercel project environment variables for frontend public API URLs and frontend runtime config.

If a new variable is added, update the matching `.env.example` with the variable name and a redacted placeholder, then set the real value directly in VPS/Vercel.

## Backend Verification

Run from repository root or `backend` as shown:

```bash
python -m py_compile backend/content_engine/services/website.py backend/content_engine/services/intelligence.py backend/content_engine/views.py
cd backend
python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','voice_spark.settings'); import django; django.setup(); print('django imports ok')"
python manage.py check
```

## Frontend Verification

Run from `frontend`:

```bash
npm run build
```

Existing non-blocking warnings may appear for Lightning CSS `:export` and the calendar dynamic import. The build must still finish successfully.

## Backend Deploy

Upload only changed backend code files to:

```text
/opt/voice-spark-ai/backend
```

Then run on the VPS:

```bash
cd /opt/voice-spark-ai/backend
.venv/bin/python -m py_compile content_engine/services/website.py content_engine/services/intelligence.py content_engine/views.py
.venv/bin/python manage.py check
sudo systemctl restart voice-spark-backend
sudo systemctl restart voice-spark-celery
sudo systemctl status voice-spark-backend --no-pager
sudo systemctl status voice-spark-celery --no-pager
```

Restart Celery when backend task/generation/intelligence code changes.

## Frontend Deploy

Run from `frontend`:

```bash
npx vercel deploy --prod --yes
```

Confirm the deployment output includes:

```text
Aliased: https://frontend-xi-one-8hr5rqjb64.vercel.app
```

## Post-Deploy Smoke Checks

- Open `/business-profile-builder` and confirm onboarding/profile page loads.
- Create or re-analyze a website and confirm the saved business profile is written in English.
- Open `/content-plan`, click a week, and confirm the week detail UI loads with the updated layout.
- Confirm Save, Regenerate, Add Post, image picker, and Generate Campaign buttons still respond.

## GitHub Push

Stage only safe source files. Do not stage `.env`, local logs, local broker DBs, zip archives, or deployment tarballs unless intentionally releasing sanitized artifacts.

```bash
git add backend/content_engine/services/website.py backend/content_engine/services/intelligence.py frontend/src/views/content_plan/detail.jsx DEPLOYMENT_GUIDE.md
git commit -m "Enforce English profiles and improve planner detail UI"
git push
```
