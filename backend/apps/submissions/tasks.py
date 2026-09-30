import io
import json
import logging
from typing import Any

from celery import shared_task
from django.utils import timezone
from PIL import Image, ImageDraw

from apps.common import openrouter, storage
from apps.submissions.models import (
    Attempt,
    AttemptStatus,
    GradeJob,
    GradeJobStatus,
    Mark,
    PageSubmission,
)
from apps.worksheets.models import AnswerSheet

logger = logging.getLogger(__name__)


def _render_strokes(page_png: bytes, strokes: list[dict]) -> bytes:
    """Draw the student's vector ink onto the worksheet page image."""
    image = Image.open(io.BytesIO(page_png)).convert("RGB")
    draw = ImageDraw.Draw(image)
    for stroke in strokes:
        points = [
            (float(p["x"]) * image.width, float(p["y"]) * image.height)
            for p in stroke.get("points", [])
        ]
        if len(points) == 1:
            points.append(points[0])
        if len(points) < 2:
            continue
        draw.line(
            points,
            fill=stroke.get("color", "#1a1aff"),
            width=int(stroke.get("width", 4)),
            joint="curve",
        )
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def grade_attempt(self, attempt_id: int) -> None:
    """
    Composite → transcribe (vision) → decide (Jev) → suggested Mark.

    Leaves the attempt in GRADED state for the teacher to confirm/return.
    """
    attempt = Attempt.objects.select_related("worksheet", "student").get(id=attempt_id)
    job = GradeJob.objects.create(
        attempt=attempt,
        status=GradeJobStatus.RUNNING,
    )
    attempt.status = AttemptStatus.GRADING
    attempt.save(update_fields=["status"])

    try:
        all_answers: list[dict] = []
        transcripts: dict[str, dict] = {}

        page_subs = PageSubmission.objects.filter(attempt=attempt).select_related(
            "worksheet_page"
        )
        for page_sub in page_subs:
            page = page_sub.worksheet_page
            page_png = storage.get_bytes(page.image_key)
            strokes = json.loads(storage.get_bytes(page_sub.strokes_key) or b"[]")

            composited = _render_strokes(page_png, strokes)
            comp_key = f"attempts/{attempt_id}/pages/{page.order}/composite.png"
            storage.put_bytes(comp_key, composited, "image/png")
            page_sub.image_key = comp_key
            page_sub.save(update_fields=["image_key"])

            transcript = openrouter.transcribe_page(
                composited, regions=page.answer_regions or None
            )
            transcripts[str(page.id)] = transcript
            for a in transcript.get("answers", []):
                a["page"] = page.order
            all_answers.extend(transcript.get("answers", []))

        answer_notes = "\n\n".join(
            s.notes
            for s in AnswerSheet.objects.filter(worksheet=attempt.worksheet)
            if s.notes
        )
        decisions = openrouter.grade_answers(
            attempt.worksheet.title, answer_notes, all_answers
        )

        # Jev score answers: probability-weighted position 0..SCORE_LEVEL_MAX,
        # normalised to a 0-10 mark per question.
        per_q: dict[str, dict[str, Any]] = {}
        scores: list[float] = []
        confidences: list[float] = []
        for qid, d in (decisions.get("answers") or {}).items():
            if not isinstance(d, dict) or d.get("score") is None:
                continue
            norm = float(d["score"]) * 10.0 / openrouter.SCORE_LEVEL_MAX
            scores.append(norm)
            per_q[qid] = {
                "score": round(norm, 2),
                "confidence": d.get("confidence"),
            }
            if d.get("confidence") is not None:
                confidences.append(float(d["confidence"]))
        total = sum(scores)
        max_total = 10.0 * len(scores) if scores else 0.0
        mean_conf = (
            round(sum(confidences) / len(confidences), 2) if confidences else None
        )
        feedback = (
            f"AI-suggested marks — mean confidence {mean_conf:.0%}. "
            "Please review before returning."
            if mean_conf is not None
            else "AI-suggested marks. Please review before returning."
        )

        job.transcript = transcripts
        job.decisions = decisions
        job.status = GradeJobStatus.DONE
        job.finished_at = timezone.now()
        job.save()

        Mark.objects.update_or_create(
            attempt=attempt,
            defaults={
                "score": total,
                "max_score": max_total,
                "per_page": per_q,
                "feedback": feedback,
                "auto_suggested": True,
            },
        )
        attempt.status = AttemptStatus.GRADED
        attempt.save(update_fields=["status"])
    except Exception as exc:
        logger.exception("grade_attempt failed for attempt %s", attempt_id)
        job.status = GradeJobStatus.FAILED
        job.error = str(exc)
        job.finished_at = timezone.now()
        job.save()
        attempt.status = AttemptStatus.SUBMITTED
        attempt.save(update_fields=["status"])
        raise self.retry(exc=exc) from exc
