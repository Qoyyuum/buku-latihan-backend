# API

Base URL: `/api/v1/`. OpenAPI schema at `/api/schema/` (drf-spectacular),
interactive docs at `/api/schema/swagger-ui/`.

## Authentication

JWT via `djangorestframework-simplejwt`:

```bash
POST /api/v1/auth/token/          # {username, password} -> {access, refresh}
POST /api/v1/auth/token/refresh/  # {refresh} -> {access}
```

Send `Authorization: Bearer <access>` on all other requests.

## Resources

| Endpoint | Notes |
|---|---|
| `GET/POST /users/` | admin/teacher manage users (roles) |
| `GET /users/me/` | current user incl. `role` |
| `GET/POST /classrooms/`, `/enrollments/` | teacher ↔ students |
| `GET/POST /parent-links/` | parent ↔ children |
| `GET/POST /subjects/`, `/topics/` | curriculum |
| `GET /worksheets/` | students see `status=published` only; `?subject=<id>` filter |
| `GET/POST /attempts/` | students start attempts; `?status=` filter |
| `GET/POST /marks/` | teachers write/confirm marks |
| `GET /dashboard/` | role-scoped stats |

## Worksheet upload flow (teacher/admin)

All file bodies go **directly to S3** via presigned PUT — the API only sees
object keys:

1. `POST /worksheets/` — create a `draft` worksheet (subject, title,
   exam_year, source).
2. `POST /worksheets/{id}/upload-url/` `{filename, content_type}` →
   `{key, upload_url}`. PUT the bytes to `upload_url`.
3. Either:
   - PDF: `POST /worksheets/{id}/rasterize/` `{pdf_key}` → Celery turns each
     page into a `WorksheetPage` PNG; or
   - Images: `POST /worksheets/{id}/pages/` `{image_key, order, width?,
     height?}` per page.
4. `POST /worksheets/{id}/answer-sheets/` `{file_key, notes}` — the notes
   (marking scheme text) feed the auto-grader.
5. `PATCH /worksheets/{id}/` `{status: "published"}`.

## Student flow

1. `GET /worksheets/{id}/bundle/` → worksheet metadata +
   `page_downloads[]` with short-lived signed GET URLs. The app downloads
   the PNGs for offline use.
2. `POST /attempts/` `{worksheet_id}` → attempt (idempotent per
   student+worksheet while `in_progress`).
3. `POST /attempts/{id}/pages/` `{worksheet_page, strokes}` — stroke
   vectors per page; repeatable (upsert).
4. `POST /attempts/{id}/submit/` → queues auto-grading.

## Marking (teacher/admin)

- `GET /attempts/?status=submitted` (queue) — `graded` means the AI
  suggestion is ready to review.
- `GET /attempts/{id}/` → `pages[]` signed URLs of the composited inked
  pages, `mark` (with `auto_suggested`), `grade_jobs[]` raw output.
- `POST /marks/` or `PATCH /marks/{id}/` to set the final score.
- `POST /attempts/{id}/return/` — locks and returns to the student.

Students only see `mark` after `return`; parents see their children's
returned attempts read-only.
