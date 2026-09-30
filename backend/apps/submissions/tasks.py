import io
import json
import logging

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

        scores = [
            d.get("score", 0)
            for d in (decisions.get("decisions") or {}).values()
            if isinstance(d, dict) and d.get("score") is not None
        ]
        total = sum(float(s) for s in scores)
        max_total = 10.0 * len(scores) if scores else 0.0

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
                "per_page": {str(i): s for i, s in enumerate(scores)},
                "feedback": decisions.get("summary", ""),
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
