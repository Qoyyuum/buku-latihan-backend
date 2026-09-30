# Buku Latihan

A low-cost Learning Management System for **handwritten worksheet practice**,
inspired by Kumon Connect and LiveWorksheets.

Students practise past-year papers and exercises by writing directly on the
worksheet pages with a stylus on their phone/tablet (Android app or the web
app). Teachers (or parents) upload worksheets with answer sheets, students
download worksheets for offline use, submit their ink for marking, and track
their progress per subject/topic. Automatic grading via OpenRouter vision +
Jev decision models produces *suggested* marks that teachers confirm.

## Roles

| Role    | Capabilities |
|---------|--------------|
| Admin   | Everything: users, classrooms, subjects, worksheets, marking |
| Teacher | Upload worksheets/answer sheets, manage classrooms, mark student work, dashboards |
| Student | Browse subjects/worksheets, download offline, write answers, submit, view returned marks |
| Parent  | Read-only view of their children's attempts, marks, and progress |

## Components

- **`backend/`** — Django 6.1 + DRF API, JWT auth, PostgreSQL 18, Celery +
  Redis, S3-compatible object storage (Cloudflare R2 recommended).
- **`frontend/`** — Expo (React Native + React Native Web) single codebase:
  Android app and static web SPA, strict TypeScript.
- **`deploy/`** — Podman Compose stack for a small VPS: API, worker,
  Postgres, Redis, Caddy reverse proxy, static frontend.

## Quick links

- [Local setup](setup.md) — get everything running on your machine
- [API reference](api.md) — endpoints, auth, upload flow
- [Grading pipeline](grading.md) — how auto-grading works
- [Deployment](deployment.md) — production Compose stack
