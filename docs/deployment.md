# Deployment

Everything runs on one small VPS (≥1 GB RAM — no local LLM needed) via
`deploy/compose.yaml`, which works with both `podman compose` and
`docker compose`.

```text
           ┌──────────────────────────────────────────┐
  :80/:443 │  Caddy — automatic HTTPS + SPA + proxy    │
           └──────┬───────────────┬───────────────────┘
                  │ /api /admin /static   │ everything else
                  ▼                       ▼
          ┌──────────────┐        ┌──────────────┐
          │ api (gunicorn│        │ frontend/dist│
          │  +whitenoise)│        │ static SPA   │
          └──────┬───────┘        └──────────────┘
      ┌──────────┼───────────┐
      ▼          ▼           ▼
┌──────────┐┌──────────┐┌──────────┐
│ postgres ││ redis    ││ worker   │
│ 18       ││ (celery) ││ (celery) │
└──────────┘└──────────┘└──────────┘
```

## Steps

1. **Build the SPA** on your dev machine or in CI:

    ```bash
    cd frontend
    EXPO_PUBLIC_API_URL=https://api.example.com npx expo export --platform web
    ```

    `EXPO_PUBLIC_API_URL` is baked into the bundle at export time. Or let a
    container do it:

    ```bash
    podman compose -f deploy/compose.yaml --profile frontend-build run --rm web-build
    ```

2. **Configure**:

    ```bash
    cp deploy/.env.example deploy/.env   # fill in DOMAIN, secrets, R2 keys
    ```

    - `DOMAIN=your-domain` → Caddy gets a Let's Encrypt cert automatically.
      Use `DOMAIN=localhost` for HTTP-only testing.
    - Point the R2/S3 variables at your bucket.

3. **Launch**:

    ```bash
    podman compose -f deploy/compose.yaml up -d --build
    podman compose -f deploy/compose.yaml exec api python manage.py createsuperuser
    ```

    The `migrate` service runs `manage.py migrate` before `api`/`worker`
    start; `api` runs `collectstatic` on boot and serves `/static` through
    whitenoise.

4. **Verify**: `https://<domain>/` (SPA login), `/admin/`,
   `/api/schema/swagger-ui/`.

## Coolify

`deploy/compose.coolify.yaml` deploys **backend only** — Postgres, Redis,
MinIO, migrate, api (gunicorn+whitenoise) and the Celery worker. Coolify's
own proxy terminates TLS, so there is no Caddy and no `DOMAIN` variable.

1. In Coolify: **New Resource → Docker Compose → this repository**, branch
   `prod`, compose file `deploy/compose.coolify.yaml`.
2. Assign domains in the Coolify UI:
   - `api` → e.g. `api.example.com` (port 8000 — serves `/api`, `/admin`,
     `/static`)
   - `minio` → e.g. `s3.example.com` (port 9000 — **required public**:
     presigned URLs go straight to clients)
3. Set the environment variables in the Coolify dashboard — see
   `deploy/.env.coolify.example` for the full list. Every variable has a
   default in the compose file; secrets ship as `change-me` placeholders
   you must replace (`DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD`,
   `MINIO_ROOT_PASSWORD`, `OPENROUTER_API_KEY`) and the domain variables
   (`DJANGO_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`,
   `CORS_ALLOWED_ORIGINS`, `AWS_S3_ENDPOINT_URL`) must match the FQDNs
   you assigned.
4. Deploy. `migrate` runs migrations and `minio-init` creates the media
   bucket before `api`/`worker` start. Then:
   `python manage.py createsuperuser` from the `api` container's terminal
   in Coolify.

Postgres and Redis are compose-internal — never expose their ports.
MinIO's API (`:9000`) is public for presigned URLs, but its console
(`:9001`) stays inside the stack.

## Scaling notes

- The whole stack fits a 1–2 GB VPS comfortably; the grader's heavy
  lifting is OpenRouter, not the box.
- To scale writes, raise `worker --concurrency` or add another worker
  service — grading jobs are idempotent per attempt.
- Postgres and Redis are single containers; for managed DB just point
  `DATABASE_URL` elsewhere and remove the `db` service.

## Android app

Distribute via EAS (free builds): `npx eas-cli build -p android
--profile production`. The APK talks to the same API; set
`EXPO_PUBLIC_API_URL` in `eas.json` or EAS env vars.
