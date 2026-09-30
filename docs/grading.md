# Grading pipeline

Two-stage OpenRouter pipeline, run asynchronously by Celery when an
attempt is submitted (`apps.submissions.tasks.grade_attempt`):

```text
PageSubmission strokes ──► composite ink onto page PNG (PIL)
        │                        │
        │                        ▼
        │              stage 1: VISION transcription
        │              model: openrouter/free (env-configurable)
        │              prompt: extract answers, optional answer_regions
        │              output: {answers: [{label, value, bbox?}]}
        │                        │
        │                        ▼
        └──────────────► stage 2: JEV decision grading
                       model: typesafe/jev-1.13 (text-only, ~200 ms)
                       input: worksheet title + answer-sheet notes +
                              transcribed answers
                       output: typed decisions {score, probability}
                               per question + summary
                               │
                               ▼
                   Mark(auto_suggested=True) + GradeJob(done)
                   attempt.status = "graded" ──► teacher confirms
                   ──► return to student
```

## Why two stages

`typesafe/jev-1.13` is a *decision* model: cheap, fast, returns typed
scores/probabilities — but **text-only**. It cannot see images, so a
vision model first transcribes handwriting to text. Keeping the stages
separate means each is independently swappable (env vars
`OPENROUTER_TRANSCRIBE_MODEL` / `OPENROUTER_GRADE_MODEL`).

## Improving accuracy

- **Answer regions**: `WorksheetPage.answer_regions` holds normalised
  `{x, y, w, h, label}` rects per question. When present, the transcription
  prompt asks for per-region answers — much better alignment to the
  answer key than whole-page transcription.
- **Answer-sheet notes**: `AnswerSheet.notes` is free-text marking scheme
  ("Q1: b, Q2: x=3, accept 0.5 or 1/2 …") passed verbatim to Jev.
- **Review is mandatory**: marks stay `auto_suggested` and invisible to the
  student until a teacher confirms and returns. Teacher corrections
  overwrite the suggestion.

## State & failures

Each run writes a `GradeJob` (`pending → running → done|failed`) keeping
the full transcript + decisions JSON for audit/debugging. Failures log
the error, roll the attempt back to `submitted`, and Celery retries
(`max_retries=2`, 60 s backoff). `submit` is idempotent — resubmission is
rejected once an attempt has left `in_progress`.

## Cost notes

- `openrouter/free` vision is free-tier (rate-limited) — fine for
  low-volume grading; pin a cheap paid vision model for reliability.
- Jev input is small (transcript + answer key); ~$0.04/M input tokens,
  free output — grading a worksheet costs fractions of a cent.
