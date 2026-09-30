# Buku Latihan

A low-cost worksheet-practice LMS: students answer past-year papers and
exercises by writing on the pages with a stylus (Android or web), teachers
upload worksheets + answer sheets, and AI-assisted grading produces
suggested marks for teacher review.

| Directory    | What |
|--------------|------|
| `backend/`   | Django 6.1 + DRF API (JWT, OpenAPI), Celery + Redis, S3/R2 storage. Managed with **uv**, checked with **ruff** + **ty**. |
| `frontend/`  | Expo SDK 57 app — one strict-TypeScript codebase for Android + static web SPA (Expo Router, TanStack Query, SVG ink canvas). |
| `deploy/`    | Podman/Docker Compose stack: Postgres 18, Redis, API, Celery worker, Caddy (HTTPS + SPA). |
| `docs/`      | MkDocs documentation (built on Read the Docs via `.readthedocs.yaml`). |

## Quick start

```bash
# deps (Postgres 18, Redis, MinIO)
podman compose -f deploy/compose.dev.yaml up -d

# API
cd backend && uv sync --dev && cp .env.example .env
uv run python manage.py migrate && uv run python manage.py runserver

# worker (PDF rasterize + auto-grading)
uv run celery -A config worker -l info

# app
cd frontend && npm install
EXPO_PUBLIC_API_URL=http://localhost:8000 npx expo start
```

Docs: <https://buku-latihan-backend.readthedocs.io/> (or `mkdocs serve`).
