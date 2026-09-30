# Local setup

## Prerequisites

- Python 3.14 (managed by [uv](https://docs.astral.sh/uv/))
- Node.js 20+ and npm (for the Expo app)
- PostgreSQL 18+ (or use the Compose stack, which provides it)
- Redis 7 (or Compose)
- An S3-compatible bucket — Cloudflare R2 is recommended (10 GB free,
  zero egress). For local development any MinIO/localstack works too.

## Backend

```bash
cd backend
uv sync --dev
cp .env.example .env      # fill in DB, Redis, S3 and OpenRouter values
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

API is then at `http://localhost:8000/api/v1/`, OpenAPI docs at
`/api/schema/swagger-ui/`.

### Environment variables

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | e.g. `postgres://buku:buku@localhost:5432/buku` |
| `REDIS_URL` / `CELERY_BROKER_URL` | e.g. `redis://localhost:6379/0` |
| `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` | standard Django |
| `CORS_ALLOWED_ORIGINS` | frontend origin(s) for the SPA |
| `AWS_S3_ENDPOINT_URL`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_REGION_NAME` | S3/R2 storage |
| `OPENROUTER_API_KEY`, `OPENROUTER_TRANSCRIBE_MODEL` (default `openrouter/free`), `OPENROUTER_GRADE_MODEL` (default `typesafe/jev-1.13`) | auto-grading |

### Celery worker

```bash
cd backend
uv run celery -A config worker -l info
```

Required for PDF rasterisation and auto-grading.

## Frontend

```bash
cd frontend
npm install
echo 'EXPO_PUBLIC_API_URL=http://localhost:8000' > .env
npx expo start          # press 'w' for web, scan QR for Android (Expo Go*)
npx expo start --web    # web only
```

\* Libraries with native code (SecureStore, SVG) require a **development
build** rather than Expo Go: `npx expo run:android` or an EAS development
build. The web target needs no native build.

## Compose alternative

Instead of installing Postgres/Redis locally, run
`podman compose -f deploy/compose.yaml up` from the repo root — see
[Deployment](deployment.md).
