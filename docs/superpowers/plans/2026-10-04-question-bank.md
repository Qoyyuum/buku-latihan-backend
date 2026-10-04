# Question Bank & Worksheet Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let teachers and parents upload lesson PDFs, build a reviewed question bank (AI via OpenRouter or hand-written), and generate typeset worksheets — with or without AI — that flow into the existing worksheet/grading pipeline unchanged.

**Architecture:** `curriculum` gains `YearLevel`. A new `apps/questionbank` Django app owns `Lesson`, `Question`, `GenerationJob`, `WorksheetQuestion` and `WorksheetBuild`, plus Celery tasks for lesson extraction, AI generation and WeasyPrint typesetting. Typesetting ends by calling the existing `rasterize_pdf`, so output is a plain `Worksheet` + `WorksheetPage`s + `AnswerSheet`. A new `bank/` route group in the Expo app drives it.

**Tech Stack:** Django 6.1 + DRF · Celery + Redis · OpenRouter (httpx) · WeasyPrint · pypdfium2 · pytest + pytest-django + factory-boy · uv · ruff · ty · Expo SDK 57 + TanStack Query

**Spec:** `docs/superpowers/specs/2026-10-04-question-bank-design.md`

## Global Constraints

- Backend paths are under `backend/`, frontend under `frontend/`; all paths below are repo-relative. Branch off `prod`, PR into `prod`.
- Backend checks after every task: `cd backend && uv run ruff check . && uv run ruff format --check . && uv run ty check && uv run pytest`.
- Frontend checks: `cd frontend && npx tsc --noEmit && npx expo lint && npx expo export --platform web`.
- Languages: `en` and `ms` only. No Arabic/Jawi, no mixed-language worksheets.
- Question types (and section order): `mcq`, `short_answer`, `long_answer`, `comprehension`, `composition`.
- Counts: each type 0–20; `comprehension`, `composition` 0–5; total 1–`QUESTIONBANK_MAX_QUESTIONS_PER_JOB` (50).
- Authors = roles `admin`, `teacher`, `parent`. Students get `403` on every questionbank endpoint. Non-owners get `404` on private objects (filter querysets, don't leak existence).
- File bodies never pass through Django — presigned PUT/GET only (`apps/common/storage.py`).
- New settings and defaults exactly: `OPENROUTER_GENERATE_MODEL="openrouter/free"`, `QUESTIONBANK_LESSON_MAX_PAGES=30`, `QUESTIONBANK_MAX_CONTEXT_CHARS=60000`, `QUESTIONBANK_MAX_QUESTIONS_PER_JOB=50`, `QUESTIONBANK_MAX_ACTIVE_AI_JOBS=2`.
- Extraction, generation and typeset tasks use `@shared_task(time_limit=1800)`.
- `weasyprint` is imported **inside** the render function, never at module top level — tests mock it and Windows dev machines lack Pango.
- New dependencies (`weasyprint`) must resolve to a release ≥7 days old; add with `uv add`.
- `ty` can't see reverse relations / `_id` magic — write explicit queries (`Question.objects.filter(generation_job=job)`), don't silence.
- Use `Worksheet`, `WorksheetPage`, `AnswerSheet` as they are; the only change to `apps/worksheets` is in Task 11.

## Review Focus

- **Re-typesetting a draft that already has pages**: old `WorksheetPage`s and the previously generated `AnswerSheet` must be replaced, not appended to (page orders restart at 0, exactly one generated answer sheet) — tested in Task 8 (`test_retypeset_replaces_pages_and_answer_sheet`).
- **Malay worksheet**: section headings and the header must use Malay copy, not English — tested in Task 8 (`test_ms_headings`).
- **Swap with a question already on the worksheet / of another type / another language / someone else's private question**: must `400`/`404`, worksheet unchanged — tested in Task 11.
- **Publishing a generated draft whose build is `stale`, `failed` or `rendering`**: must `400`; scanned worksheets (no build) publish as before — tested in Task 11.
- **Model returns more items of a type than requested, or wraps JSON in prose/code fences**: extras discarded; fenced JSON parsed; prose-only → retry then `failed` with `raw_model_output` kept — tested in Task 7.

---

### Task 1: YearLevel and Topic.year_level

**Files:**
- Modify: `backend/apps/curriculum/models.py`, `backend/apps/curriculum/admin.py`, `backend/apps/curriculum/api/serializers.py`, `backend/apps/curriculum/api/views.py`, `backend/config/api_router.py`
- Create: `backend/apps/curriculum/migrations/0002_yearlevel_topic_year_level.py` (via `makemigrations`)
- Test: `backend/apps/curriculum/tests/test_api.py`

**Interfaces:**
- Produces: `YearLevel(name: CharField(80, unique), order: PositiveIntegerField(default=0))`, `Meta.ordering = ["order", "name"]`; `Topic.year_level: FK(YearLevel, null=True, blank=True, on_delete=PROTECT, related_name="topics")`. Constraints on `Topic`: `UniqueConstraint(fields=["subject","year_level","name"], name="unique_topic_per_subject_year")` and `UniqueConstraint(fields=["subject","name"], condition=Q(year_level__isnull=True), name="unique_topic_per_subject_no_year")` (old `unique_topic_per_subject` removed). `Topic.ordering = ["subject", "year_level__order", "order", "name"]`.
- API: `/api/v1/year-levels/` (`YearLevelViewSet`, `IsTeacherOrReadOnly`); `TopicSerializer.fields` adds `year_level`, `year_level_name` (read-only); `TopicViewSet` filters `?subject=` and `?year_level=`.

- [ ] **Step 1: Write failing tests** in `apps/curriculum/tests/test_api.py`:

```python
def test_same_topic_name_in_two_year_levels(db):
    s = Subject.objects.create(name="Math")
    y4, y5 = YearLevel.objects.create(name="Year 4", order=4), YearLevel.objects.create(name="Year 5", order=5)
    Topic.objects.create(subject=s, year_level=y4, name="Fractions")
    Topic.objects.create(subject=s, year_level=y5, name="Fractions")
    assert Topic.objects.filter(name="Fractions").count() == 2

def test_duplicate_topic_without_year_level_rejected(db):
    s = Subject.objects.create(name="Math")
    Topic.objects.create(subject=s, name="Fractions")
    with pytest.raises(IntegrityError):
        Topic.objects.create(subject=s, name="Fractions")

def test_year_levels_read_only_for_students(db): ...  # GET 200, POST 403 (mirror test_subjects_read_only_for_students)

def test_topics_filter_by_year_level(db): ...  # GET /api/v1/topics/?year_level=<y4.id> returns only Year 4 topic, includes "year_level_name": "Year 4"
```

- [ ] **Step 2: Run** `cd backend && uv run pytest apps/curriculum -v` — expect FAIL (`YearLevel` import error).
- [ ] **Step 3: Implement** models/admin (`YearLevelAdmin` list_display `name, order`; `year_level` column in `TopicInline`), serializers, viewsets, router `router.register("year-levels", YearLevelViewSet, basename="year-level")`; run `uv run python manage.py makemigrations curriculum`.
- [ ] **Step 4: Run** `uv run pytest apps/curriculum -v` — expect PASS; then full backend checks.
- [ ] **Step 5: Commit** — `git commit -m "feat(curriculum): add YearLevel and per-year topics"`

---

### Task 2: questionbank app, models, IsAuthor, settings

**Files:**
- Create: `backend/apps/questionbank/{__init__,apps,models,admin}.py`, `backend/apps/questionbank/migrations/0001_initial.py` (via `makemigrations`), `backend/apps/questionbank/tests/{__init__,factories,test_models}.py`
- Modify: `backend/config/settings/base.py` (`LOCAL_APPS` += `"apps.questionbank"`, new settings), `backend/apps/common/permissions.py`, `backend/.env.example`

**Interfaces:**
- Produces (in `apps/questionbank/models.py`), field names/choices exactly as the spec's Data model tables:
  - TextChoices: `Language(EN="en","English"; MS="ms","Bahasa Melayu")`, `QuestionType(MCQ="mcq", SHORT_ANSWER="short_answer", LONG_ANSWER="long_answer", COMPREHENSION="comprehension", COMPOSITION="composition")`, `Difficulty(EASY, MEDIUM, HARD)`, `QuestionStatus(NEEDS_REVIEW="needs_review", ACCEPTED, REJECTED)`, `Visibility(PRIVATE, SHARED)`, `QuestionSource(GENERATED, MANUAL)`, `JobMode(AI="ai", BANK="bank")`, `JobStatus(QUEUED, RUNNING, DONE, FAILED)`, `LessonStatus(EXTRACTING, READY, FAILED)`, `BuildStatus(PENDING, RENDERING, DONE, FAILED, STALE)`.
  - `TYPE_ORDER: list[str] = [QuestionType.MCQ, …, QuestionType.COMPOSITION]` (section order).
  - Models `Lesson`, `Question`, `GenerationJob`, `WorksheetQuestion`, `WorksheetBuild` with the spec's fields, FKs and `on_delete`s. `WorksheetQuestion` constraints `unique_wsq_order` `(worksheet, order)` and `unique_wsq_question` `(worksheet, question)`; `ordering = ["worksheet", "order"]`.
  - `Question.objects.visible_to(user) -> QuerySet[Question]` (custom manager/queryset): admin → all; author → `Q(owner=user) | Q(visibility=SHARED, status=ACCEPTED)`; others → none.
- Produces (in `apps/common/permissions.py`): `IsAuthor(BasePermission)` — `role in {ADMIN, TEACHER, PARENT}`.
- Produces (in `tests/factories.py`): `UserFactory(role=...)`, `SubjectFactory`, `YearLevelFactory`, `TopicFactory`, `LessonFactory`, `QuestionFactory` (default: `mcq`, `en`, `accepted`, `shared`, valid MCQ body `{"prompt": "2+2?", "choices": ["1","2","3","4"]}`, `answer="D"`), `GenerationJobFactory`.

- [ ] **Step 1: Write failing tests** in `tests/test_models.py`:

```python
def test_visible_to_owner_sees_private(db):
    q = QuestionFactory(visibility=Visibility.PRIVATE)
    assert q in Question.objects.visible_to(q.owner)

def test_visible_to_other_author_sees_only_shared_accepted(db):
    other = UserFactory(role=UserRole.PARENT)
    shared = QuestionFactory()
    QuestionFactory(visibility=Visibility.PRIVATE)
    QuestionFactory(status=QuestionStatus.NEEDS_REVIEW)
    assert list(Question.objects.visible_to(other)) == [shared]

def test_visible_to_student_sees_nothing(db):
    QuestionFactory()
    assert not Question.objects.visible_to(UserFactory(role=UserRole.STUDENT)).exists()

def test_is_author_roles():
    # parent/teacher/admin True, student False, AnonymousUser False
```

- [ ] **Step 2: Run** `uv run pytest apps/questionbank -v` — expect FAIL (module missing).
- [ ] **Step 3: Implement** the app, models, `IsAuthor`, admin (`list_display` + `list_filter` on status/type/language for `Question`, `GenerationJob`, `Lesson`), settings read with `env.int(...)`/`env(...)` using the Global Constraints defaults, `.env.example` lines for `OPENROUTER_GENERATE_MODEL` and the four `QUESTIONBANK_*`; `uv run python manage.py makemigrations questionbank`.
- [ ] **Step 4: Run** `uv run pytest apps/questionbank -v` — expect PASS; full backend checks.
- [ ] **Step 5: Commit** — `git commit -m "feat(questionbank): add models, IsAuthor permission and settings"`

---

### Task 3: Question body validation

**Files:**
- Create: `backend/apps/questionbank/schemas.py`
- Test: `backend/apps/questionbank/tests/test_schemas.py`

**Interfaces:**
- Produces: `validate_question(type: str, body: dict, answer: str, marking_scheme: str) -> dict` returning normalized `{"body", "answer", "marking_scheme"}` (strings stripped; MCQ answer upper-cased) or raising `rest_framework.exceptions.ValidationError` with field-keyed messages. Rules exactly per the spec's `body` shapes table: MCQ = non-empty `prompt`, exactly 4 non-empty distinct `choices`, `answer` in `A`–`D`; `short_answer` needs `answer`; `long_answer` needs `answer` and `marking_scheme`; `comprehension` = non-empty `passage`, 2–6 `sub_questions` each with non-empty `prompt`/`answer`, `marking_scheme` required, `answer` forced to `""`; `composition` = non-empty `task`, ints `0 < min_words <= max_words <= 1000`, `marking_scheme` required, `answer` forced to `""`. Unknown keys in `body` are dropped.

- [ ] **Step 1: Write failing tests** — one parametrized valid case per type, plus:

```python
def test_mcq_needs_four_distinct_choices():
    with pytest.raises(ValidationError):
        validate_question("mcq", {"prompt": "x", "choices": ["a", "a", "b", "c"]}, "A", "")

def test_mcq_answer_normalized():
    assert validate_question("mcq", MCQ_BODY, " b ", "")["answer"] == "B"

def test_comprehension_sub_question_bounds():  # 1 and 7 sub-questions both rejected

def test_composition_word_range():  # min_words > max_words rejected

def test_unknown_type_rejected():

def test_unknown_body_keys_dropped():
    assert "evil" not in validate_question("short_answer", {"prompt": "p", "evil": 1}, "a", "")["body"]
```

- [ ] **Step 2: Run** `uv run pytest apps/questionbank/tests/test_schemas.py -v` — FAIL.
- [ ] **Step 3: Implement** `validate_question` in `schemas.py` (plain functions per type in a dict dispatch).
- [ ] **Step 4: Run** — PASS; full backend checks.
- [ ] **Step 5: Commit** — `git commit -m "feat(questionbank): validate question bodies per type"`

---

### Task 4: Lesson extraction pipeline

**Files:**
- Create: `backend/apps/common/pdf.py`, `backend/apps/questionbank/tasks.py`
- Modify: `backend/apps/worksheets/tasks.py` (use the helper), `backend/apps/common/openrouter.py`
- Test: `backend/apps/questionbank/tests/test_extract.py`, `backend/apps/worksheets/tests/test_tasks.py` (new)

**Interfaces:**
- Produces: `apps.common.pdf.page_count(pdf_bytes: bytes) -> int`; `apps.common.pdf.render_pages(pdf_bytes: bytes, scale: float = 2.0) -> Iterator[PIL.Image.Image]`. `rasterize_pdf` keeps its signature and behaviour, now iterating `render_pages`.
- Produces: `openrouter.transcribe_lesson_page(image_png: bytes, language: str) -> str` — `OPENROUTER_TRANSCRIBE_MODEL`, plain-text response (no `response_format`), prompt asks for a faithful transcription in English or Bahasa Melayu, keeping headings, numbered lists and tables as plain text, no commentary.
- Produces: `apps.questionbank.tasks.extract_lesson(lesson_id: int) -> None` (`@shared_task(time_limit=1800)`): sets `extracting`, checks `page_count` against `QUESTIONBANK_LESSON_MAX_PAGES` (over → `failed`, `error="Lesson PDF has N pages; the limit is 30."` with the real numbers), transcribes each page, joins as `"\n\n".join(f"--- Page {n} ---\n\n{text}" for n, text in enumerate(pages, 1))`, sets `ready` and clears `error`. Any exception → `failed`, `error=str(exc)`; no Celery retry.

- [ ] **Step 1: Write failing tests** (mock `storage.get_bytes`, `storage.put_bytes`, `openrouter.transcribe_lesson_page`; build a 2-page PDF in-test with `pypdfium2.PdfDocument.new()` + `new_page(595, 842)` + `save()` into `BytesIO`):

```python
def test_extract_lesson_joins_pages(db, two_page_pdf, mocker):
    lesson = LessonFactory(status=LessonStatus.EXTRACTING)
    mocker.patch("apps.common.storage.get_bytes", return_value=two_page_pdf)
    mocker.patch("apps.common.openrouter.transcribe_lesson_page", side_effect=["one", "two"])
    extract_lesson(lesson.id)
    lesson.refresh_from_db()
    assert lesson.status == LessonStatus.READY
    assert lesson.extracted_text == "--- Page 1 ---\n\none\n\n--- Page 2 ---\n\ntwo"

def test_extract_lesson_page_limit(db, two_page_pdf, mocker, settings):
    settings.QUESTIONBANK_LESSON_MAX_PAGES = 1  # → FAILED, error mentions "2 pages" and "limit is 1", transcriber never called

def test_extract_lesson_failure_recorded(db, two_page_pdf, mocker):  # transcriber raises httpx.HTTPError → FAILED, error set

def test_rasterize_pdf_still_creates_pages(db, two_page_pdf, mocker):  # worksheets regression: 2 WorksheetPages, orders 0 and 1
```

  `mocker` requires `pytest-mock` — add it to the dev group (`uv add --dev pytest-mock`) in this task.

- [ ] **Step 2: Run** `uv run pytest apps/questionbank/tests/test_extract.py apps/worksheets -v` — FAIL.
- [ ] **Step 3: Implement** `pdf.py`, refactor `rasterize_pdf`, add `transcribe_lesson_page`, add `extract_lesson`.
- [ ] **Step 4: Run** — PASS; full backend checks.
- [ ] **Step 5: Commit** — `git commit -m "feat(questionbank): extract lesson text from scanned PDFs"`

---

### Task 5: Lesson API

**Files:**
- Create: `backend/apps/questionbank/api/{__init__,serializers,views}.py`
- Modify: `backend/config/api_router.py`
- Test: `backend/apps/questionbank/tests/test_lessons_api.py`

**Interfaces:**
- Consumes: `extract_lesson` (Task 4), `IsAuthor` (Task 2), `storage.new_key/presign_put`.
- Produces: `LessonViewSet` at `/api/v1/lessons/` (`basename="lesson"`), permission `IsAuthor`, queryset = admin all / else `owner=request.user`. Fields: `id, topic, topic_name, title, language, source_file_key, extracted_text, status, error, created_at, updated_at`; read-only `status, error, created_at, updated_at`; `topic`, `language`, `source_file_key` read-only after create. Actions:
  - `POST upload-url/` (`detail=False`) `{filename, content_type}` → `{key, upload_url}`; key from `storage.new_key(f"lessons/{user.id}", filename)`; `content_type` must be `application/pdf` else `400`.
  - `create` → saves `owner`, `status=extracting`, then `transaction.on_commit(lambda: extract_lesson.delay(lesson.id))` → `201`. `source_file_key` must start with `lessons/{user.id}/` else `400`.
  - `POST {id}/extract/` → re-queue, `status=extracting`, `202`; `409` if already `extracting`.
  - `PATCH` (`title`, `extracted_text`), `DELETE`, list (`?topic=`), retrieve.

- [ ] **Step 1: Write failing tests:**

```python
def test_student_forbidden(db, api): ...                    # GET /api/v1/lessons/ as student → 403
def test_parent_creates_lesson_and_extraction_queued(db, api, mocker):
    delay = mocker.patch("apps.questionbank.tasks.extract_lesson.delay")
    # POST {topic, title, language: "ms", source_file_key: f"lessons/{parent.id}/x.pdf"} → 201, status "extracting"
    # with django_capture_on_commit_callbacks(execute=True): delay called once with lesson.id
def test_foreign_file_key_rejected(db, api): ...            # key under another user's prefix → 400
def test_other_author_gets_404(db, api): ...                # teacher B GET teacher A's lesson → 404
def test_upload_url_rejects_non_pdf(db, api, mocker): ...   # content_type image/png → 400
def test_extract_conflict_while_extracting(db, api): ...    # → 409
def test_owner_edits_extracted_text(db, api): ...           # PATCH → 200, persisted; PATCH topic ignored
```

- [ ] **Step 2: Run** `uv run pytest apps/questionbank/tests/test_lessons_api.py -v` — FAIL.
- [ ] **Step 3: Implement** serializers, `LessonViewSet`, register route.
- [ ] **Step 4: Run** — PASS; full backend checks.
- [ ] **Step 5: Commit** — `git commit -m "feat(questionbank): lesson upload and extraction API"`

---

### Task 6: Question API and review workflow

**Files:**
- Create: `backend/apps/questionbank/review.py`
- Modify: `backend/apps/questionbank/api/serializers.py`, `backend/apps/questionbank/api/views.py`, `backend/config/api_router.py`
- Test: `backend/apps/questionbank/tests/test_questions_api.py`, `backend/apps/questionbank/tests/test_review.py`

**Interfaces:**
- Consumes: `validate_question` (Task 3), `Question.objects.visible_to` (Task 2).
- Produces: `review.accept(question: Question, visibility: str = Visibility.SHARED) -> Question`, `review.reject(question: Question) -> Question` — enforce transitions `needs_review → accepted|rejected`, `accepted → rejected`; else raise `ValidationError({"status": "Cannot <action> a <status> question."})`; set `reviewed_at`.
- Produces: `QuestionViewSet` at `/api/v1/questions/` (`basename="question"`), `IsAuthor`; mixins list/retrieve/create/update (no destroy). Queryset `visible_to(user)`; default excludes `rejected` unless `?status=rejected`. Filters: `topic, type, language, difficulty, status, visibility, generation_job, mine=1` (owner only). Fields: `id, owner, topic, topic_name, type, language, difficulty, body, answer, marking_scheme, status, visibility, source, generation_job, created_at, updated_at, reviewed_at`; read-only `owner, status, source, generation_job, created_at, updated_at, reviewed_at`; `type` writable on create only. `validate()` runs `validate_question`. `create` → `owner=user, status=accepted, source=manual`. Update/accept/reject only by owner or admin (else `404` if invisible, `403` if visible-but-not-owner); update forbidden on `rejected` (`400`).
- Actions: `POST {id}/accept/` `{visibility?}`, `POST {id}/reject/`.

- [ ] **Step 1: Write failing tests:**

```python
def test_accept_defaults_to_shared(db): q = QuestionFactory(status=NEEDS_REVIEW, visibility=PRIVATE); assert review.accept(q).visibility == "shared"
def test_accept_keep_private(db): ...                 # accept(q, "private") → private
def test_cannot_accept_rejected(db): ...              # ValidationError
def test_manual_create_is_accepted(db, api): ...      # POST valid short_answer → 201, status accepted, source manual
def test_create_invalid_body_400(db, api): ...        # mcq with 3 choices → 400 with "choices" key
def test_other_author_cannot_edit_shared(db, api): ...# PATCH someone's shared question → 403
def test_other_author_cannot_see_private(db, api): ...# GET → 404
def test_rejected_hidden_by_default(db, api): ...     # list excludes; ?status=rejected&mine=1 includes
def test_type_immutable(db, api): ...                 # PATCH type → ignored (still mcq)
def test_student_forbidden(db, api): ...              # 403
```

- [ ] **Step 2: Run** — FAIL.
- [ ] **Step 3: Implement** `review.py`, serializer, viewset, route.
- [ ] **Step 4: Run** — PASS; full backend checks.
- [ ] **Step 5: Commit** — `git commit -m "feat(questionbank): question bank API with review workflow"`

---

### Task 7: AI generation task

**Files:**
- Create: `backend/apps/questionbank/prompts.py`, `backend/apps/questionbank/generation.py`
- Modify: `backend/apps/common/openrouter.py`, `backend/apps/questionbank/tasks.py`
- Test: `backend/apps/questionbank/tests/test_prompts.py`, `backend/apps/questionbank/tests/test_generation.py`

**Interfaces:**
- Consumes: `validate_question` (Task 3), models (Task 2).
- Produces: `prompts.LENGTH_RULES: dict[str, dict[str, str | tuple[int,int]]]` — `short/medium/long` → `long_answer` guidance (`"2–3 sentences"`, `"one paragraph"`, `"2–3 paragraphs"`) and `composition` word range (`(80,120)`, `(150,200)`, `(250,350)`).
- Produces: `prompts.build_generation_messages(*, topic: Topic, language: str, counts: dict[str,int], length: str, difficulty: str | None, lesson_text: str) -> list[dict[str, str]]` — system + user messages. Must include: "Brunei Darussalam", subject name, year level name (or "unspecified year level"), topic name, `"Write every question and answer in English."` / `"Write every question and answer in Bahasa Melayu."`, only non-zero counts, one line each as `- {type}: {n}`, the JSON shape per type from the spec, the length rule, and `lesson_text` truncated to `QUESTIONBANK_MAX_CONTEXT_CHARS` (append `"\n[truncated]"` when cut). Output contract: `{"questions": [{"type","difficulty","body","answer","marking_scheme"}]}`.
- Produces: `openrouter.chat_json(messages: list[dict], model: str) -> str` — returns raw `content` string (`response_format: json_object`); raises on HTTP error.
- Produces: `generation.parse_model_output(raw: str, counts: dict[str,int]) -> tuple[list[dict], int]` — strips ```` ``` ```` / ```` ```json ```` fences, `json.loads`, validates each item with `validate_question` (+ `difficulty` in `Difficulty`, default `medium`), keeps at most `counts[type]` per type in model order; returns `(valid_items, dropped_count)`. Raises `generation.MalformedOutput(str)` if not JSON / no `questions` list / zero valid items.
- Produces: `tasks.run_generation_job(job_id: int) -> None` (`@shared_task(time_limit=1800)`): `running`; gather lesson text (spec `lessons` or all owner's `ready` lessons under topic, joined with `"\n\n"`); call `chat_json`; on `MalformedOutput` retry once with an extra user message `"Your previous reply was invalid: <error>. Reply again with ONLY the JSON object."`; second failure or HTTP error → `failed`, `error`, `raw_model_output` = last raw. Success → bulk-create `Question(owner=job.owner, topic, language, status=needs_review, visibility=private, source=generated, generation_job=job, …)`; `result = {"question_ids": [...], "shortfall": {type: missing} (only >0), "dropped": n}`; `model`, `finished_at`, `done`.

- [ ] **Step 1: Write failing tests** (mock `apps.common.openrouter.chat_json`):

```python
def test_prompt_language_and_context(db):
    msgs = build_generation_messages(topic=topic_y4_fractions, language="ms", counts={"mcq": 2, "composition": 0}, length="medium", difficulty=None, lesson_text="Pecahan ialah ...")
    text = "\n".join(m["content"] for m in msgs)
    assert "Bahasa Melayu" in text and "Brunei Darussalam" in text and "Year 4" in text and "Fractions" in text
    assert "- mcq: 2" in text and "- composition:" not in text

def test_prompt_truncates_lesson_text(db, settings): settings.QUESTIONBANK_MAX_CONTEXT_CHARS = 10  # → "[truncated]" present, full text absent

def test_parse_discards_extras_and_counts_dropped():
    raw = json.dumps({"questions": [MCQ_ITEM, MCQ_ITEM, {"type": "mcq", "body": {}}]})
    items, dropped = parse_model_output(raw, {"mcq": 1})
    assert len(items) == 1 and dropped == 1

def test_parse_strips_code_fences(): parse_model_output("```json\n" + raw + "\n```", ...)  # ok

def test_job_creates_needs_review_questions_with_shortfall(db, mocker):  # counts mcq 3, model returns 2 valid → done, 2 questions needs_review/private, result.shortfall == {"mcq": 1}

def test_job_retries_once_then_fails(db, mocker):
    chat = mocker.patch("apps.common.openrouter.chat_json", side_effect=["not json", "still not json"])
    run_generation_job(job.id)
    job.refresh_from_db()
    assert chat.call_count == 2 and job.status == JobStatus.FAILED and job.raw_model_output == "still not json"

def test_job_recovers_on_retry(db, mocker):  # ["nope", valid] → done

def test_job_http_error_fails(db, mocker):   # httpx.HTTPStatusError → failed, error set, chat called once
```

- [ ] **Step 2: Run** — FAIL.
- [ ] **Step 3: Implement** `prompts.py`, `chat_json`, `generation.py`, `run_generation_job`.
- [ ] **Step 4: Run** — PASS; full backend checks.
- [ ] **Step 5: Commit** — `git commit -m "feat(questionbank): AI question generation via OpenRouter"`

---

### Task 8: Typesetting

**Files:**
- Create: `backend/apps/questionbank/typeset.py`, `backend/apps/questionbank/templates/questionbank/{worksheet,answer_key}.html`, `backend/apps/questionbank/templates/questionbank/print.css` (included inline via `{% include %}` inside `<style>`)
- Modify: `backend/apps/questionbank/tasks.py`, `backend/pyproject.toml` + `backend/uv.lock` (`uv add weasyprint`), `backend/Dockerfile`
- Test: `backend/apps/questionbank/tests/test_typeset.py`

**Interfaces:**
- Consumes: `WorksheetBuild`, `WorksheetQuestion` (Task 2); `apps.worksheets.tasks.rasterize_pdf` (called directly, synchronously).
- Produces: `typeset.SECTION_TITLES: dict[str, dict[str, str]]` — `en`: `Multiple choice`, `Short answers`, `Long answers`, `Comprehension`, `Composition`, prefix `Section`; `ms`: `Aneka pilihan`, `Jawapan pendek`, `Jawapan panjang`, `Kefahaman`, `Karangan`, prefix `Bahagian`. Header labels `en`: `Name`, `Date`; `ms`: `Nama`, `Tarikh`.
- Produces: `typeset.numbered_items(worksheet: Worksheet) -> list[dict]` — sections in `TYPE_ORDER`, each `{letter: "A", title, items: [{number: int, question, sub_labels: ["a","b",…]}]}`; numbering continuous across sections, letters assigned only to non-empty sections.
- Produces: `typeset.render_worksheet_html(build: WorksheetBuild) -> str`, `typeset.render_answer_key_html(build) -> str`, `typeset.compile_marking_notes(build) -> str` — lines like `Q1 [mcq] Answer: D`, `Q3(b) Answer: …`, followed by `Marking scheme: …` when non-empty.
- Produces: `typeset.html_to_pdf(html: str) -> bytes` — `from weasyprint import HTML` inside the function; `HTML(string=html).write_pdf()`.
- Produces: `tasks.typeset_worksheet(worksheet_id: int) -> None` (`@shared_task(time_limit=1800)`): build `rendering`; render both PDFs to `worksheets/{id}/generated/worksheet.pdf` and `.../answer-key.pdf` (`storage.put_bytes`, `application/pdf`); delete `WorksheetPage.objects.filter(worksheet=…)` and `AnswerSheet.objects.filter(worksheet=…, file_key=<answer-key.pdf key>)`; `rasterize_pdf(worksheet_id, pdf_key)`; create `AnswerSheet(file_key, notes=compile_marking_notes(build), uploaded_by=build.owner)`; save keys, `rendered_at`, `done`. Exception → `failed` + `error`.
- Answer-space rules exactly per spec §6 (long answer 4/8/14 lines by the job's `length`, default `medium` → 8; composition lines = `max_words // 10`).
- Dockerfile: before `uv sync`, `RUN apt-get update && apt-get install -y --no-install-recommends libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 fonts-dejavu-core && rm -rf /var/lib/apt/lists/*`. CSS `font-family: "DejaVu Sans", sans-serif; @page { size: A4; margin: 18mm; }`.

- [ ] **Step 1: Write failing tests** (mock `typeset.html_to_pdf` to return a real 1-page PDF built with pypdfium2; mock `storage.put_bytes` / `storage.get_bytes` with an in-memory dict):

```python
def test_numbering_continuous_across_sections(db): # 2 mcq + 1 comprehension(3 subs) → numbers 1,2,3; sections A,B; sub_labels ["a","b","c"]
def test_ms_headings(db):  # language ms → "Bahagian A — Aneka pilihan" and "Nama" in HTML; "Section" absent
def test_marking_notes_use_printed_numbers(db): # contains "Q1 [mcq] Answer: D" and "Q3(b) Answer:"
def test_typeset_creates_pages_and_answer_sheet(db, fake_storage, mocker): # build done, 1 WorksheetPage, 1 AnswerSheet with notes
def test_retypeset_replaces_pages_and_answer_sheet(db, fake_storage, mocker):
    typeset_worksheet(ws.id); typeset_worksheet(ws.id)
    assert list(WorksheetPage.objects.filter(worksheet=ws).values_list("order", flat=True)) == [0]
    assert AnswerSheet.objects.filter(worksheet=ws).count() == 1
def test_typeset_failure_recorded(db, mocker): # html_to_pdf raises → build failed, error set
```

- [ ] **Step 2: Run** — FAIL.
- [ ] **Step 3: Implement** templates, `typeset.py`, task, `uv add weasyprint` (check release age), Dockerfile.
- [ ] **Step 4: Run** — PASS; full backend checks. Then one real render on a machine with Pango (`docker build backend` and run `python -c` rendering a sample build, or Linux dev box) and eyeball the PDF for both `en` and `ms`.
- [ ] **Step 5: Commit** — `git commit -m "feat(questionbank): typeset generated worksheets with WeasyPrint"`

---

### Task 9: Bank sampling and draft assembly

**Files:**
- Create: `backend/apps/questionbank/sampling.py`, `backend/apps/questionbank/assembly.py`
- Test: `backend/apps/questionbank/tests/test_sampling.py`, `backend/apps/questionbank/tests/test_assembly.py`

**Interfaces:**
- Consumes: `Question.objects.visible_to` (Task 2), `typeset_worksheet` (Task 8).
- Produces: `sampling.InsufficientQuestions(Exception)` with `.shortfall: dict[str, int]`.
- Produces: `sampling.bank_pool(user, *, topic: Topic, language: str, type: str, difficulty: str | None) -> QuerySet[Question]` — `visible_to(user)` ∩ `status=accepted` ∩ filters.
- Produces: `sampling.sample_questions(user, *, topic, language, counts: dict[str,int], difficulty: str | None, rng: random.Random | None = None) -> list[Question]` — per type in `TYPE_ORDER`, `rng.sample(list_of_ids, k)`; collects all shortfalls before raising; result ordered by `TYPE_ORDER` then sample order.
- Produces: `assembly.create_worksheet_draft(*, owner: User, topic: Topic, language: str, questions: list[Question], title: str | None, job: GenerationJob | None) -> Worksheet` — atomic; `Worksheet(subject=topic.subject, topic=topic, title=title or default, source="Generated", status=draft, created_by=owner)`; default title `f"{topic.name} — {topic.year_level.name} practice"` or `f"{topic.name} practice"` when no year level; `WorksheetQuestion`s ordered by `TYPE_ORDER` (stable within type), `order` from 0; `WorksheetBuild(status=pending, owner, generation_job=job, language)`; `transaction.on_commit(lambda: typeset_worksheet.delay(ws.id))`.

- [ ] **Step 1: Write failing tests:**

```python
def test_sample_respects_pool(db):  # excludes rejected, needs_review, other language, other topic, other user's private; includes own private + others' shared
def test_sample_shortfall_lists_every_type(db):
    with pytest.raises(InsufficientQuestions) as e:
        sample_questions(u, topic=t, language="en", counts={"mcq": 5, "short_answer": 2}, difficulty=None)
    assert e.value.shortfall == {"mcq": 5, "short_answer": 2}  # given an empty bank
def test_sample_deterministic_with_seed(db):  # same random.Random(1) → same ids
def test_sample_difficulty_filter(db):
def test_draft_orders_by_type_and_queues_typeset(db, mocker, django_capture_on_commit_callbacks):
    # questions passed [composition, mcq] → WorksheetQuestion orders: mcq=0, composition=1; build pending; typeset delay called once
def test_default_title(db):  # "Fractions — Year 4 practice"
```

- [ ] **Step 2: Run** — FAIL.
- [ ] **Step 3: Implement** `sampling.py`, `assembly.py`.
- [ ] **Step 4: Run** — PASS; full backend checks.
- [ ] **Step 5: Commit** — `git commit -m "feat(questionbank): bank sampling and worksheet draft assembly"`

---

### Task 10: Generation job API

**Files:**
- Modify: `backend/apps/questionbank/api/serializers.py`, `backend/apps/questionbank/api/views.py`, `backend/config/api_router.py`
- Test: `backend/apps/questionbank/tests/test_jobs_api.py`

**Interfaces:**
- Consumes: `run_generation_job` (Task 7), `sample_questions`/`InsufficientQuestions` (Task 9), `create_worksheet_draft` (Task 9).
- Produces: `GenerationSpecSerializer` — fields `mode, topic, lessons (list[int], optional), language, counts (dict), length (default "medium"), difficulty (nullable), title (optional)`; validation exactly per spec "Generation request" and Global Constraints (count bounds; unknown count keys rejected; `lessons` only with `mode=ai`, each must be caller's `ready` lesson under `topic`). `validated_data` is stored as `job.spec` (IDs, not objects).
- Produces: `GenerationJobViewSet` at `/api/v1/generation-jobs/` (`basename="generation-job"`), `IsAuthor`, queryset admin all / else `owner=user`; list/retrieve/create only. Read fields: `id, mode, spec, status, model, result, error, created_at, finished_at` (`raw_model_output` only for admins).
  - `create`, `mode=ai`: if caller has ≥ `QUESTIONBANK_MAX_ACTIVE_AI_JOBS` jobs `queued|running` → `429 {"detail": "You already have 2 generation jobs running."}`; else job `queued`, on_commit `run_generation_job.delay`, `202`.
  - `create`, `mode=bank`: `sample_questions`; `InsufficientQuestions` → `400 {"detail": "Not enough questions in the bank.", "shortfall": {...}}` and no job/worksheet rows; else job `done` with `result={"question_ids", "worksheet_id"}` + `create_worksheet_draft` → `201`.
  - `POST {id}/retry/` — only `mode=ai` and `failed` (else `400`); same concurrency check; resets `error`, `queued`, re-enqueue → `202`.
  - `POST {id}/build-worksheet/` `{title?}` — `mode=ai`, `done`; uses `Question.objects.filter(generation_job=job, status=accepted)`; none → `400 {"detail": "Accept at least one question first."}`; else `create_worksheet_draft`, stores `result["worksheet_id"]` → `201 {"worksheet_id"}`.

- [ ] **Step 1: Write failing tests:**

```python
def test_ai_job_queued(db, api, mocker):  # 202, status queued, delay called on commit with job.id
def test_ai_job_concurrency_limit(db, api, mocker):  # 2 running jobs exist → 429
def test_counts_bounds(db, api):  # {"mcq": 21} → 400; all zero → 400; {"essay": 1} → 400; comprehension 6 → 400
def test_lessons_must_be_own_ready(db, api):  # other user's lesson → 400; own failed lesson → 400
def test_bank_mode_creates_draft(db, api, mocker):  # 201, worksheet draft with N WorksheetQuestions, no Celery generation call
def test_bank_mode_shortfall(db, api):
    res = api.post("/api/v1/generation-jobs/", {...,"mode": "bank","counts": {"mcq": 3}}, format="json")
    assert res.status_code == 400 and res.json()["shortfall"] == {"mcq": 3}
    assert not GenerationJob.objects.exists() and not Worksheet.objects.exists()
def test_build_worksheet_needs_accepted(db, api):  # → 400; after accepting one → 201
def test_retry_only_failed_ai(db, api, mocker):
def test_other_author_404_student_403(db, api):
```

- [ ] **Step 2: Run** — FAIL.
- [ ] **Step 3: Implement** serializer, viewset, route.
- [ ] **Step 4: Run** — PASS; full backend checks.
- [ ] **Step 5: Commit** — `git commit -m "feat(questionbank): generation job API for AI and bank modes"`

---

### Task 11: Worksheet builds (swap/typeset), parent worksheet access, publish guard

**Files:**
- Modify: `backend/apps/questionbank/api/serializers.py`, `backend/apps/questionbank/api/views.py`, `backend/config/api_router.py`, `backend/apps/worksheets/api/views.py`, `backend/apps/worksheets/api/serializers.py`
- Test: `backend/apps/questionbank/tests/test_builds_api.py`, `backend/apps/worksheets/tests/test_api.py`

**Interfaces:**
- Consumes: `bank_pool` (Task 9), `typeset_worksheet` (Task 8).
- Produces: `WorksheetBuildViewSet` at `/api/v1/worksheet-builds/` (`basename="worksheet-build"`), `lookup_field="worksheet"`, `IsAuthor`, queryset admin all / else `owner=user`. Retrieve/list fields: `worksheet, worksheet_title, worksheet_status, status, error, language, rendered_at, questions: [{order, question: <QuestionSerializer>}]`.
  - `POST {worksheet}/swap/` `{order: int, question: int}` → worksheet must be `draft` (`400`); `order` must exist (`400`); replacement must be in `bank_pool(user, topic=ws.topic, language=build.language, type=<current item's type>, difficulty=None)` (`400 "Replacement must be an accepted <type> question in <language> for this topic."`) and not already on the worksheet (`400`). Updates the row, build `stale` → `200` with the build.
  - `POST {worksheet}/typeset/` → worksheet `draft` (`400`) and build not `rendering` (`409`); build `rendering`, on_commit `typeset_worksheet.delay` → `202`.
- Modifies `WorksheetViewSet`:
  - `get_queryset`: teacher/admin unchanged; parent → `Q(status=published) | Q(created_by=user)`; student unchanged.
  - `get_permissions`: `update/partial_update/destroy` → `IsAuthor` + object check (teacher/admin any; parent only `created_by == user`, else `403`). All other teacher-only actions unchanged.
- Modifies `WorksheetSerializer.validate_status`: when moving to `published` and `WorksheetBuild.objects.filter(worksheet=instance).exclude(status=BuildStatus.DONE).exists()` → `ValidationError("Render the worksheet before publishing.")`.

- [ ] **Step 1: Write failing tests:**

```python
def test_swap_replaces_and_marks_stale(db, api):
def test_swap_rejects_duplicate(db, api):          # replacement already on worksheet → 400, unchanged
def test_swap_rejects_other_type(db, api):         # short_answer for an mcq slot → 400
def test_swap_rejects_other_language(db, api):     # → 400
def test_swap_rejects_foreign_private(db, api):    # → 400
def test_swap_on_published_400(db, api):
def test_typeset_conflict_while_rendering(db, api):# → 409
def test_publish_blocked_until_rendered(db, api):  # build stale/failed/rendering → 400; done → 200
def test_scanned_worksheet_publish_unchanged(db, api):  # no build → 200
def test_parent_sees_own_draft_not_others(db, api):
def test_parent_can_publish_own_not_others(db, api):  # own draft → 200; teacher's published → 403; teacher's draft → 404
def test_parent_cannot_rasterize(db, api):         # POST worksheets/{id}/rasterize/ → 403
# existing test_students_see_only_published / test_teachers_see_all keep passing
```

- [ ] **Step 2: Run** `uv run pytest apps/questionbank/tests/test_builds_api.py apps/worksheets -v` — FAIL.
- [ ] **Step 3: Implement** the viewset and the `apps/worksheets` changes.
- [ ] **Step 4: Run** — PASS; full backend checks; `uv run python manage.py spectacular --file /tmp/schema.yml` succeeds with no new errors.
- [ ] **Step 5: Commit** — `git commit -m "feat(questionbank): swap and render drafts; parents publish own worksheets"`

---

### Task 12: Frontend — plumbing, lessons and generate form

**Files:**
- Modify: `frontend/src/api/types.ts`, `frontend/src/api/client.ts`, `frontend/src/auth/store.tsx`, `frontend/src/app/(app)/dashboard.tsx`, `frontend/src/app/(app)/subjects.tsx`
- Create: `frontend/src/app/(app)/bank/_layout.tsx`, `frontend/src/app/(app)/bank/lessons.tsx`, `frontend/src/app/(app)/bank/generate.tsx`

**Interfaces:**
- Consumes: endpoints from Tasks 1, 5, 10.
- Produces (`types.ts`): `Language = 'en' | 'ms'`, `QuestionType`, `Difficulty`, `QuestionStatus`, `YearLevel`, `Lesson`, `Question`, `GenerationJob`, `GenerationSpec`, `WorksheetBuild` mirroring the serializers; `Topic` gains `year_level: number | null; year_level_name: string | null`.
- Produces (`client.ts` `api.*`): `yearLevels()`, `topics(params?: {subject?: number; year_level?: number})`, `lessons()`, `lesson(id)`, `lessonUploadUrl(filename)`, `createLesson(l)`, `updateLesson(id, patch)`, `extractLesson(id)`, `createGenerationJob(spec: GenerationSpec)`, `generationJob(id)`, `retryGenerationJob(id)`, `buildWorksheet(jobId, title?)`, `questions(filters)`, `createQuestion(q)`, `updateQuestion(id, patch)`, `acceptQuestion(id, visibility)`, `rejectQuestion(id)`, `worksheetBuild(worksheetId)`, `swapQuestion(worksheetId, order, questionId)`, `typesetWorksheet(worksheetId)`, `publishWorksheet(worksheetId)` (= `updateWorksheet(id, {status: 'published'})`). `ApiError` already carries the body — surface `shortfall` from it.
- Produces (`store.tsx`): `canAuthor: boolean` (`admin | teacher | parent`).
- `bank/_layout.tsx`: `if (!canAuthor) return <Redirect href="/(app)" />;` + `Stack` (mirror `admin/_layout.tsx`).
- `lessons.tsx`: list (title, topic, status, error) polling every 5 s while any lesson is `extracting` (TanStack `refetchInterval`); upload = `expo-document-picker` PDF → `lessonUploadUrl` → PUT (reuse the pattern in `admin/upload.tsx`) → `createLesson`; tap a lesson → editable `extracted_text` `TextInput` + Save + "Extract again".
- `generate.tsx` (the single simple form): `Use AI` switch; subject → year level → topic pickers; (AI only) multi-select of own `ready` lessons for the topic; language `English | Bahasa Melayu`; numeric inputs per type; length `short|medium|long`; difficulty `mixed|easy|medium|hard`; optional title. Submit → AI: navigate to `bank/review?job=<id>`; bank: navigate to `bank/compose?worksheet=<worksheet_id>`; bank `400` → show "Not enough questions: 3 multiple choice, 1 composition" from `shortfall`; `429` → show the API `detail`.
- Entry links: "Question bank" `Pressable` on `dashboard.tsx` (teachers) and on `subjects.tsx` when `isParent`, both → `/(app)/bank/generate`; plus links between bank screens in each screen header.

- [ ] **Step 1:** Read `https://docs.expo.dev/versions/v57.0.0/` pages for any Expo API touched (document picker, router) before coding (per `frontend/AGENTS.md`).
- [ ] **Step 2: Implement** types, client, store flag, layout, two screens, entry links.
- [ ] **Step 3: Verify** `cd frontend && npx tsc --noEmit && npx expo lint && npx expo export --platform web` — all succeed with no new warnings.
- [ ] **Step 4: Manual check** against a local backend: as a parent, upload a lesson PDF, see it go `extracting → ready`, submit the form once in each mode.
- [ ] **Step 5: Commit** — `git commit -m "feat(frontend): question bank lessons and generate form"`

---

### Task 13: Frontend — review, compose and bank browser

**Files:**
- Create: `frontend/src/app/(app)/bank/review.tsx`, `frontend/src/app/(app)/bank/compose.tsx`, `frontend/src/app/(app)/bank/questions.tsx`, `frontend/src/components/question-card.tsx`, `frontend/src/components/question-editor.tsx`

**Interfaces:**
- Consumes: `api.*` from Task 12.
- `question-card.tsx`: `QuestionCard({question, actions?: ReactNode})` — renders body per type (MCQ choices with the correct letter marked, comprehension passage + sub-questions, composition task + word range), answer, marking scheme, difficulty and status badges.
- `question-editor.tsx`: `QuestionEditor({value: Question | Draft, onSave(patch)})` — per-type fields matching the spec body shapes; shows API field errors inline.
- `review.tsx` (`?job=`): polls `generationJob` every 3 s while `queued|running`; `failed` → error + Retry; `done` → shortfall note + list of `needs_review` questions with Edit / Accept (Share) / Accept (Keep private) / Reject; "Build worksheet" button enabled when ≥1 accepted → navigate to `compose?worksheet=`.
- `compose.tsx` (`?worksheet=`): build status (poll every 3 s while `pending|rendering`); ordered questions; "Swap" opens the filtered list (`questions({topic, type, language, status: 'accepted'})`, excluding items already on the worksheet) → `swapQuestion`; "Render" (`typesetWorksheet`) when `stale|failed`; "Publish" enabled only when `done`; link to preview pages via the existing `worksheet` screen.
- `questions.tsx`: filter by topic/type/language/difficulty, toggle "mine only", "New question" opens `QuestionEditor` → `createQuestion`.

- [ ] **Step 1: Implement** components and screens.
- [ ] **Step 2: Verify** `npx tsc --noEmit && npx expo lint && npx expo export --platform web` — succeed.
- [ ] **Step 3: Manual check** end-to-end against a local backend with OpenRouter configured: AI job → review → accept 2 → build → render → publish; then as a student, open the published worksheet and see the typeset pages.
- [ ] **Step 4: Commit** — `git commit -m "feat(frontend): review, compose and browse the question bank"`

---

### Task 14: Docs

**Files:**
- Create: `docs/question-bank.md`
- Modify: `mkdocs.yml` (nav entry `Question bank: question-bank.md` after `Grading pipeline`), `docs/api.md` (new endpoints), `docs/deployment.md` (WeasyPrint system packages + new env vars), `docs/development.md` (note: typesetting needs Pango locally — on Windows use the container; tests don't need it)

- [ ] **Step 1: Write** `docs/question-bank.md` — flows (ingest, AI, bank, review, compose, typeset, publish), permissions table, settings table; copied from the spec, not re-invented.
- [ ] **Step 2: Verify** `pip install mkdocs && mkdocs build --strict` from repo root (or `uvx mkdocs build --strict`) — succeeds.
- [ ] **Step 3: Commit** — `git commit -m "docs: question bank and worksheet generation"`
