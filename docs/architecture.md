# Architecture

```text
┌─────────────┐  HTTPS   ┌──────────────────┐      ┌──────────────┐
│  Expo app    │─────────▶│  Django + DRF     │─────▶│ PostgreSQL 18 │
│  (Android +  │  JWT    │  API              │      └──────────────┘
│   web SPA)   │         │                   │      ┌──────────────┐
└─────────────┘         │                   │─────▶│ Redis        │
       │                └──────┬────────────┘      │ (Celery)     │
       │ presigned URLs        │ enqueue           └──────┬───────┘
       ▼                       │                          │
┌─────────────┐                │                 ┌────────▼───────┐
│ S3 / R2      │               │                 │ Celery worker   │
│ page images, │               │                 │ - PDF rasterize │
│ ink strokes  │               │                 │ - auto-grading  │
└─────────────┘                │                 └───────┬────────┘
                               │                         │ HTTPS
                               ▼                 ┌────────▼───────┐
                        OpenAPI schema           │ OpenRouter      │
                        /api/schema/             │ vision + Jev    │
                                                 └────────────────┘
```

## Data model

- **accounts**: `User` (role: admin/teacher/student/parent), `Classroom`,
  `Enrollment`, `ParentChild` links.
- **curriculum**: `Subject` → `Topic`.
- **worksheets**: `Worksheet` → `WorksheetPage` (image key + optional
  `answer_regions` rects), `AnswerSheet` (key file + free-text marking
  notes used by the auto-grader).
- **submissions**: `Attempt` (student × worksheet) → `PageSubmission`
  (stroke vector JSON + composited image), `Mark` (score/feedback,
  `auto_suggested` flag), `GradeJob` (pipeline state + raw model output).

## Flow

1. Teacher uploads a PDF or page images via presigned PUT URLs straight to
   object storage, then registers pages/answer sheets through the API.
2. PDFs are rasterised to PNG pages by a Celery task (`pypdfium2`).
3. Student opens a worksheet → app fetches the `bundle` manifest (metadata
   + signed GET URLs) → caches pages for offline use.
4. Student writes on top of each page image; strokes are stored as
   normalised vectors (x, y in 0–1) and uploaded per page.
5. Submit → attempt enters the grading pipeline; a teacher reviews the
   suggested mark and returns it to the student.

## Why these choices

- **S3 presigned URLs**: media never passes through Django — cheap R2
  storage, zero-egress-cost downloads.
- **Vector strokes**, not photos: resolution-independent, editable,
  composited server-side for review and transcription.
- **Two-stage grading** (vision → Jev): Jev is text-only and very cheap;
  the vision model only transcribes. See [Grading](grading.md).
- **One Expo codebase**: Android APK + static web SPA from the same
  TypeScript source.
