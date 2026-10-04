# Question Bank & Worksheet Generation — Design Spec

Date: 2026-10-04
Status: Draft — awaiting review

## Intent

Teachers and parents can turn their own lesson material into practice
worksheets without scanning a ready-made paper. They upload a scanned lesson
PDF, and either:

- **AI mode** — have an OpenRouter model write new questions from the lesson,
  review them, and build a worksheet from the accepted ones; or
- **Bank mode** — skip AI entirely and assemble a worksheet by sampling
  questions that are already in the bank (written by AI earlier, or by
  teachers/parents by hand), then swap individual items.

Either way the result is an ordinary `Worksheet` with rasterized
`WorksheetPage`s and an `AnswerSheet`, so the student app, ink capture and
auto-grading pipeline work unchanged. Students see no difference between a
generated worksheet and a scanned one.

Success criteria:

- A teacher or parent can upload a lesson PDF under a topic and year level and
  get editable extracted text.
- One simple form drives both modes: pick a topic (and optionally lessons),
  language, question counts per type, and a length; toggle **Use AI** on/off.
- AI-generated questions land in a review queue; nothing reaches the shared
  bank unless a human accepts it.
- Bank mode produces a draft worksheet immediately; the author can swap any
  question for another one of the same type from the filtered bank.
- A typeset worksheet PDF and a matching answer-key PDF are produced, and the
  answer key's marking scheme feeds the existing auto-grader.

## Decisions

| Question | Decision |
|---|---|
| Curriculum hierarchy | Add `YearLevel`; `Topic` gains a nullable `year_level` FK. Hierarchy: `Subject → Topic (per year level)` |
| Languages (v1) | English (`en`) and Malay (`ms`) only. Arabic/Jawi (Ugama, Jawi lessons) out of scope for v1; no mixed-language worksheets |
| Lesson input | Scanned PDF via the existing presigned-PUT flow; vision model transcribes each page |
| Question types | `mcq`, `short_answer`, `long_answer`, `comprehension`, `composition` |
| Difficulty | `easy` / `medium` / `hard` — AI-assigned, author-editable |
| Generation toggle | `GenerationJob.mode` = `ai` (OpenRouter) or `bank` (no AI, sample existing questions) |
| Bank mode UX | Auto-sample, then browse and swap individual questions |
| Review gate | AI questions start `needs_review`; accept / edit / reject. Accepting shares to the bank by default, with a "keep private" option |
| Manual questions | Authors can write questions directly; they are created `accepted` |
| Typesetting | WeasyPrint HTML/CSS → PDF → existing pypdfium2 rasterizer |
| Who can author | Admins, teachers **and parents** (same rights in the question bank). Students have no access |
| Visibility | Lessons, jobs, private questions: owner (+ admins). Shared questions: all authors |
| Frontend | New `bank/` route group in the Expo app, gated to authors |

## Data model

### `curriculum` (extended)

- **`YearLevel`** — `name` (unique, e.g. "Year 4"), `order` (int, default 0).
  Ordered by `order, name`. Teacher-editable, read-only for others (same as
  `Subject`).
- **`Topic.year_level`** — FK → `YearLevel`, `null=True`, `on_delete=PROTECT`.
  Existing topics keep `NULL`. Uniqueness changes from `(subject, name)` to:
  - `(subject, year_level, name)` — so "Fractions" can exist at Year 4 and Year 5;
  - plus `(subject, name)` **where `year_level IS NULL`** — so null year levels
    cannot be used to duplicate names (NULLs are distinct in a plain
    unique constraint).

### New app: `questionbank`

Shared choices: `Language` (`en` English, `ms` Bahasa Melayu),
`QuestionType`, `Difficulty`, `QuestionStatus`, `Visibility`, `JobMode`,
`JobStatus`, `LessonStatus`, `BuildStatus`.

**`Lesson`** — personal to the uploader.

| Field | Notes |
|---|---|
| `owner` | FK user, CASCADE |
| `topic` | FK `curriculum.Topic`, PROTECT |
| `title` | ≤200 chars |
| `language` | `Language` |
| `source_file_key` | object key of the uploaded PDF |
| `extracted_text` | text, editable by owner |
| `status` | `extracting` → `ready` / `failed` (set to `extracting` on registration — the file is already in storage) |
| `error` | text, set on failure |
| `created_at`, `updated_at` | |

**`Question`**

| Field | Notes |
|---|---|
| `owner` | FK user, SET_NULL (questions outlive their author in the shared bank) |
| `topic` | FK `Topic`, PROTECT |
| `type` | `QuestionType` |
| `language` | `Language` |
| `difficulty` | `Difficulty`, default `medium` |
| `body` | JSON, shape depends on `type` (below) |
| `answer` | text (MCQ: the correct letter `A`–`D`) |
| `marking_scheme` | text |
| `status` | `needs_review` / `accepted` / `rejected` |
| `visibility` | `private` / `shared` |
| `source` | `generated` / `manual` |
| `generation_job` | FK `GenerationJob`, null, SET_NULL |
| `created_at`, `updated_at`, `reviewed_at` | |

`body` shapes (validated on every write, AI or human):

| Type | `body` | `answer` | `marking_scheme` |
|---|---|---|---|
| `mcq` | `{prompt, choices: [4 strings]}` | `A`/`B`/`C`/`D` | optional |
| `short_answer` | `{prompt}` | required | optional |
| `long_answer` | `{prompt}` | model answer, required | required |
| `comprehension` | `{passage, sub_questions: [{prompt, answer}] (2–6)}` | blank | required |
| `composition` | `{task, min_words, max_words}` | blank | rubric, required |

A `comprehension` question is one passage with its sub-questions; a
`composition` is one writing task. Counts for those types are passages / tasks.

**`GenerationJob`** — mirrors `submissions.GradeJob`.

| Field | Notes |
|---|---|
| `owner` | FK user, CASCADE |
| `mode` | `ai` / `bank` |
| `spec` | JSON — validated request (below) |
| `status` | `queued` → `running` → `done` / `failed` |
| `model` | OpenRouter model used (AI mode) |
| `result` | JSON — `{question_ids, shortfall, dropped, worksheet_id}` |
| `raw_model_output` | text — last raw model response, for debugging |
| `error` | text |
| `created_at`, `finished_at` | |

**`WorksheetQuestion`** — ordered join: `worksheet` FK (CASCADE), `question`
FK (PROTECT), `order`. Unique `(worksheet, order)` and `(worksheet, question)`.

**`WorksheetBuild`** — one per generated worksheet; keeps the existing
`Worksheet` model untouched.

| Field | Notes |
|---|---|
| `worksheet` | OneToOne `Worksheet`, CASCADE |
| `owner` | FK user |
| `generation_job` | FK `GenerationJob`, null |
| `language` | `Language` |
| `status` | `pending` / `rendering` / `done` / `failed` / `stale` |
| `error` | text |
| `pdf_key`, `answer_key_pdf_key` | object keys of the rendered PDFs |
| `rendered_at` | |

## Generation request (one form, both modes)

```json
{
  "mode": "ai",
  "topic": 12,
  "lessons": [3, 4],
  "language": "ms",
  "counts": {"mcq": 10, "short_answer": 5, "long_answer": 0,
             "comprehension": 1, "composition": 0},
  "length": "medium",
  "difficulty": null,
  "title": "Pecahan — Latihan 1"
}
```

- `topic` — required in both modes.
- `lessons` — AI mode only, optional. Must be the caller's own `ready`
  lessons under `topic`. Omitted → all of the caller's `ready` lessons under
  the topic; none → the prompt uses curriculum context only (subject, year
  level, topic name).
- `counts` — each type 0–20, `comprehension` and `composition` 0–5, total
  1–50 (`QUESTIONBANK_MAX_QUESTIONS_PER_JOB`).
- `length` — `short` / `medium` / `long`, default `medium`. Sets expected
  answer length for long-form types: `long_answer` = 2–3 sentences / one
  paragraph / 2–3 paragraphs (also scales answer space when typeset);
  `composition` word range = 80–120 / 150–200 / 250–350.
- `difficulty` — optional filter (bank mode) or target (AI mode); `null` = mixed.
- `title` — optional; default `"<Topic> — <Year level> practice"`.

## Flows

### 1. Lesson ingestion

1. `POST /api/v1/lessons/upload-url/` `{filename, content_type: application/pdf}`
   → `{key, upload_url}` (key prefix `lessons/<user_id>/`).
2. Client PUTs the PDF straight to R2.
3. `POST /api/v1/lessons/` `{topic, title, language, source_file_key}` →
   lesson `extracting`; Celery `extract_lesson` queued.
4. Task: download PDF, rasterize pages (shared helper with `rasterize_pdf`),
   send each page to the vision model (`OPENROUTER_TRANSCRIBE_MODEL`) asking
   for a faithful transcription in the lesson language, join pages with a
   page marker, save `extracted_text`, status `ready`.
5. PDFs over `QUESTIONBANK_LESSON_MAX_PAGES` (default 30) fail fast with a
   clear error. Any exception → `failed` + `error`.
6. Owner can `PATCH` `extracted_text`/`title` and `POST lessons/{id}/extract/`
   to retry a failed or bad extraction.

### 2. AI mode

1. `POST /api/v1/generation-jobs/` with `mode: "ai"` → job `queued`, `202`.
2. Celery `run_generation_job`: assemble the prompt — curriculum context
   (Brunei Darussalam school, subject, year level, topic), language
   instruction, lesson text (truncated to `QUESTIONBANK_MAX_CONTEXT_CHARS`,
   default 60 000), counts, length rules, and the exact JSON shape per type.
3. OpenRouter chat completion (`OPENROUTER_GENERATE_MODEL`,
   `response_format: json_object`).
4. Validate each item with the same body validator used for manual edits.
   Invalid items are dropped (counted in `result.dropped`); extra items beyond
   the requested count per type are discarded.
5. If the response is not JSON or yields zero valid questions, retry once with
   the validation errors appended; still bad → job `failed`, raw output kept.
6. Valid items → `Question(status=needs_review, visibility=private,
   source=generated)`. Fewer than requested → job `done` with
   `result.shortfall` per type.
7. Each user may have at most 2 AI jobs `queued`/`running`; a third → `429`.
8. After review, `POST generation-jobs/{id}/build-worksheet/` `{title?}`
   creates the draft worksheet from the job's **accepted** questions (400 if
   none).

### 3. Bank mode

1. `POST /api/v1/generation-jobs/` with `mode: "bank"` — handled
   synchronously, no Celery, no AI.
2. Pool per type: `status=accepted`, matching topic + language (+ difficulty
   if given), and (`visibility=shared` or `owner=caller`).
3. Randomly sample the requested count per type without replacement.
4. Any type short → `400 {"detail": "Not enough questions in the bank.",
   "shortfall": {"mcq": 3}}`; nothing is created.
5. Otherwise create the job (`done`) and a draft worksheet → `201` with the
   job and `worksheet_id`.

### 4. Review

- `GET /api/v1/questions/?generation_job=<id>&status=needs_review`.
- Owner can `PATCH` any content field (`type` is immutable after creation)
  while the question is `needs_review` or `accepted`.
- `POST questions/{id}/accept/` `{visibility: "shared" | "private"}`
  (default `shared`) → `accepted`, `reviewed_at` set.
- `POST questions/{id}/reject/` → `rejected`. Rejected questions are hidden
  from default listings and from sampling, never deleted (audit). No `DELETE`.
- Allowed transitions: `needs_review → accepted | rejected`,
  `accepted → rejected`. Anything else → `400`.
- `POST /api/v1/questions/` creates a manual question directly as `accepted`.

### 5. Assembly & swapping

- Draft creation (both modes): `Worksheet(status=draft, subject=topic.subject,
  topic, title, source="Generated", created_by=caller)`, `WorksheetQuestion`s
  ordered by type (`mcq, short_answer, long_answer, comprehension,
  composition`) then pick order, and a `WorksheetBuild(status=pending)`; the
  typeset task is queued on commit.
- `GET /api/v1/worksheet-builds/{worksheet_id}/` → build status + ordered
  questions (full bodies).
- `POST worksheet-builds/{worksheet_id}/swap/` `{order, question}` → replaces
  the question at `order`. The replacement must be visible to the caller,
  `accepted`, same type, same language, and not already on the worksheet.
  Build becomes `stale`.
- `GET /api/v1/questions/?topic=&type=&language=&difficulty=&status=accepted`
  is the browse view for picking replacements.
- `POST worksheet-builds/{worksheet_id}/typeset/` → `rendering`, re-queues the
  typeset task.
- Swaps and typesetting are only allowed while the worksheet is `draft`.

### 6. Typesetting

Celery `typeset_worksheet(worksheet_id)`:

1. Render `questionbank/worksheet.html` (A4, Django template + print CSS):
   header (title, subject, year level, name/date lines), sections per type with
   localized headings (`en`: "Section A — Multiple choice"; `ms`: "Bahagian A
   — Aneka pilihan", etc.), continuous question numbering, answer space per
   type (MCQ lettered choices; short answer 2 lines; long answer 4/8/14 lines
   by `length`; comprehension passage box + 3 lines per sub-question;
   composition lines ≈ `max_words / 10`).
2. WeasyPrint → `worksheets/<id>/generated/worksheet.pdf`.
3. Render `questionbank/answer_key.html` (same numbering, answers + marking
   schemes) → `worksheets/<id>/generated/answer-key.pdf`.
4. Delete the worksheet's existing pages and the previously generated
   `AnswerSheet`, then call the existing `rasterize_pdf` logic synchronously
   to create fresh `WorksheetPage`s.
5. Create `AnswerSheet(file_key=answer-key key, notes=compiled marking
   scheme)`; notes use the printed numbering (`Q3(b) …`) so the transcriber's
   labels line up with the grader.
6. Build `done` + `rendered_at`; any exception → `failed` + `error`.

WeasyPrint is imported inside the task module function, so the rest of the
app (and the test suite, which mocks it) runs on machines without Pango
installed. The API image installs Pango + DejaVu fonts.

### 7. Publishing

- Publishing uses the existing `PATCH /api/v1/worksheets/{id}/`
  `{status: "published"}`. If the worksheet has a `WorksheetBuild` that is
  not `done`, publishing is rejected with `400`.
- "Assign" in v1 means publish — there is no per-class assignment model;
  published worksheets are visible to all students (existing behaviour).

## Permissions

New `IsAuthor` permission: role in `admin`, `teacher`, `parent`.

| Resource | Student | Author (non-owner) | Owner | Admin |
|---|---|---|---|---|
| Lessons | 403 | 404 | full | full |
| Generation jobs | 403 | 404 | create/read/build | full |
| Private question | 403 | 404 | read/edit/review | full |
| Shared accepted question | 403 | read, sample, swap in | read/edit/review | full |
| Worksheet build | 403 | 404 | read/swap/typeset | full |

Existing `WorksheetViewSet` changes, needed so parents can see and publish
what they generate:

- Parents see published worksheets **plus their own drafts**.
- Parents may `update` / `partial_update` / `destroy` worksheets they created.
- Upload/pages/rasterize/answer-sheet actions stay teacher-only.
- Teachers' and students' behaviour is unchanged.

## Configuration

New settings (env-overridable, documented in `backend/.env.example`):

| Setting | Default |
|---|---|
| `OPENROUTER_GENERATE_MODEL` | `openrouter/free` |
| `QUESTIONBANK_LESSON_MAX_PAGES` | `30` |
| `QUESTIONBANK_MAX_CONTEXT_CHARS` | `60000` |
| `QUESTIONBANK_MAX_QUESTIONS_PER_JOB` | `50` |
| `QUESTIONBANK_MAX_ACTIVE_AI_JOBS` | `2` |

Extraction, generation and typesetting tasks set `time_limit=1800` (the
global `CELERY_TASK_TIME_LIMIT` is 300 s, too short for a 30-page lesson).

New dependency: `weasyprint` (pinned to a release ≥7 days old). Dockerfile
adds `libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 fonts-dejavu-core`.

## Frontend (Expo app)

New route group `src/app/(app)/bank/`, gated by a new `canAuthor` flag in the
auth store (admin/teacher/parent). Entry links from the teacher dashboard and
from the parent's subjects screen.

| Screen | Purpose |
|---|---|
| `bank/lessons` | List own lessons with status; upload PDF (topic, title, language); view/edit extracted text; retry extraction |
| `bank/generate` | The simple form: Use AI toggle, topic, (AI) lesson picker, language, counts per type, length, difficulty, title. Shows shortfall errors |
| `bank/review` | A job's questions: edit, accept (shared / private), reject; "Build worksheet" |
| `bank/compose` | A draft's questions in order with build status; swap from filtered bank; Render; Publish |
| `bank/questions` | Browse the bank + write a manual question |

## Errors

- Extraction failure → lesson `failed` + `error`, retry via `extract/`.
- Generation failure (HTTP error, bad JSON twice, zero valid items) → job
  `failed` + `error` + `raw_model_output`, retry via
  `POST generation-jobs/{id}/retry/` (AI jobs only).
- Bank shortfall → `400` with per-type `shortfall`.
- Typeset failure → build `failed` + `error`, retry via `typeset/`.

## Testing

pytest + factory-boy (`apps/questionbank/tests/factories.py`):

- Unit: body validation per type, sampling (pool filters, shortfall, seeded
  RNG), review transitions, prompt assembly (language, context truncation,
  counts), marking-scheme compilation, typeset HTML (numbering, localized
  headings).
- Task: `extract_lesson`, `run_generation_job` (valid, partial, malformed →
  retry → fail) and `typeset_worksheet` with OpenRouter, storage and
  WeasyPrint mocked.
- API: permission matrix above (owner vs other author vs student vs parent),
  publish guard, swap rules, AI-job concurrency limit.
- Regression: existing worksheet tests for teachers/students still pass.

## Out of scope (v1)

- Arabic / Jawi lessons and right-to-left typesetting.
- Mixed-language worksheets.
- Per-classroom assignment of worksheets.
- Image/diagram questions (text-only questions in v1).
- Auto-populating `WorksheetPage.answer_regions` from the typeset layout.
- Non-PDF lesson inputs (photos, DOCX), and lesson sharing between users.

## Known risks

- Any parent can publish a worksheet that every student can see (follows
  existing global-visibility behaviour). Revisit with a class-assignment model.
- Free OpenRouter models may produce weak or malformed JSON; the review gate
  and retry/failed states contain this, but quality depends on the chosen
  model.
- Shared questions are editable only by their owner; edits do not change
  already-typeset worksheets (PDFs are snapshots).
