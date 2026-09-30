from django.conf import settings
from django.db import models


class AttemptStatus(models.TextChoices):
    IN_PROGRESS = "in_progress", "In progress"
    SUBMITTED = "submitted", "Submitted"
    GRADING = "grading", "Auto-grading"
    GRADED = "graded", "Graded — awaiting teacher review"
    RETURNED = "returned", "Returned to student"


class Attempt(models.Model):
    """One student's run at one worksheet."""

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="attempts",
        limit_choices_to={"role": "student"},
    )
    worksheet = models.ForeignKey(
        "worksheets.Worksheet",
        on_delete=models.CASCADE,
        related_name="attempts",
    )
    status = models.CharField(
        max_length=20,
        choices=AttemptStatus.choices,
        default=AttemptStatus.IN_PROGRESS,
    )

    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"{self.student} — {self.worksheet} ({self.status})"


class PageSubmission(models.Model):
    """
    A student's ink on one worksheet page.

    ``strokes_key`` holds the vector stroke JSON (replayable, tiny);
    ``image_key`` holds the composited PNG (page + ink) rendered by Celery
    for teacher review and OCR transcription.
    """

    attempt = models.ForeignKey(
        Attempt,
        on_delete=models.CASCADE,
        related_name="pages",
    )
    worksheet_page = models.ForeignKey(
        "worksheets.WorksheetPage",
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    strokes_key = models.CharField(max_length=500, blank=True)
    image_key = models.CharField(max_length=500, blank=True)
    uploaded_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "worksheet_page"],
                name="unique_page_submission",
            )
        ]

    def __str__(self) -> str:
        return f"{self.attempt} — {self.worksheet_page}"


class GradeJobStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    DONE = "done", "Done"
    FAILED = "failed", "Failed"


class GradeJob(models.Model):
    """
    One auto-grading run over an attempt: composite → transcribe → decide.

    Keeps the full provider trace so suggested marks can be audited.
    """

    attempt = models.ForeignKey(
        Attempt,
        on_delete=models.CASCADE,
        related_name="grade_jobs",
    )
    status = models.CharField(
        max_length=20,
        choices=GradeJobStatus.choices,
        default=GradeJobStatus.PENDING,
    )
    transcribe_model = models.CharField(max_length=200, blank=True)
    grade_model = models.CharField(max_length=200, blank=True)
    transcript = models.JSONField(default=dict, blank=True)
    decisions = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"GradeJob #{self.pk} — {self.attempt} ({self.status})"


class Mark(models.Model):
    """The (possibly AI-suggested, teacher-confirmed) marks for an attempt."""

    attempt = models.OneToOneField(
        Attempt,
        on_delete=models.CASCADE,
        related_name="mark",
    )
    score = models.FloatField(default=0)
    max_score = models.FloatField(default=0)
    per_page = models.JSONField(
        default=dict,
        blank=True,
        help_text="Optional per-page/per-region breakdown of marks",
    )
    feedback = models.TextField(blank=True)
    auto_suggested = models.BooleanField(
        default=False,
        help_text="True while marks are unconfirmed AI suggestions",
    )
    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="marks_given",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.attempt}: {self.score}/{self.max_score}"
