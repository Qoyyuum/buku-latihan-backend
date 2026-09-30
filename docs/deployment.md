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
