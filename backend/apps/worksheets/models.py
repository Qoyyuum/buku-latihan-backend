from django.conf import settings
from django.db import models


class WorksheetStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"


class Worksheet(models.Model):
    """
    A set of pages students can write on — a past-year paper, an exercise
    sheet, a Kumon-style drill. Pages are stored as images in object
    storage; PDFs are rasterized to one image per page by Celery.
    """

    subject = models.ForeignKey(
        "curriculum.Subject",
        on_delete=models.CASCADE,
        related_name="worksheets",
    )
    topic = models.ForeignKey(
        "curriculum.Topic",
        on_delete=models.SET_NULL,
        related_name="worksheets",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    exam_year = models.PositiveIntegerField(null=True, blank=True)
    source = models.CharField(
        max_length=200,
        blank=True,
        help_text="e.g. SPM 2023, UPSR trial, Kumon level D",
    )
    status = models.CharField(
        max_length=20,
        choices=WorksheetStatus.choices,
        default=WorksheetStatus.DRAFT,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="worksheets",
        null=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["subject", "topic", "title"]

    def __str__(self) -> str:
        return self.title


class WorksheetPage(models.Model):
    """One page of a worksheet, backed by an image object in S3/R2."""

    worksheet = models.ForeignKey(
        Worksheet,
        on_delete=models.CASCADE,
        related_name="pages",
    )
    order = models.PositiveIntegerField()
    image_key = models.CharField(
        max_length=500,
        help_text="Object-storage key of the rendered page image",
    )
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    answer_regions = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "Optional [{x, y, w, h, label}] boxes marking where answers go. "
            "Not required — students may write anywhere — but improves "
            "auto-grading when present."
        ),
    )

    class Meta:
        ordering = ["worksheet", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["worksheet", "order"],
                name="unique_page_order_per_worksheet",
            )
        ]

    def __str__(self) -> str:
        return f"{self.worksheet} p{self.order}"


class AnswerSheet(models.Model):
    """The teacher's marking key for a worksheet."""

    worksheet = models.ForeignKey(
        Worksheet,
        on_delete=models.CASCADE,
        related_name="answer_sheets",
    )
    file_key = models.CharField(max_length=500)
    notes = models.TextField(
        blank=True,
        help_text="Marking scheme notes fed to the auto-grader",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Answer sheet: {self.worksheet}"
