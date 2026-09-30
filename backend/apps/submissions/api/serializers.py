from typing import Any

from rest_framework import serializers

from apps.accounts.api.serializers import UserSerializer
from apps.common import storage
from apps.submissions.models import (
    Attempt,
    AttemptStatus,
    GradeJob,
    Mark,
    PageSubmission,
)
from apps.worksheets.api.serializers import WorksheetSerializer
from apps.worksheets.models import Worksheet, WorksheetPage, WorksheetStatus


class PageSubmissionSerializer(serializers.ModelSerializer[PageSubmission]):
    url = serializers.SerializerMethodField()

    class Meta:
        model = PageSubmission
        fields = [
            "id",
            "worksheet_page",
            "strokes_key",
            "image_key",
            "url",
            "uploaded_at",
        ]
        read_only_fields = ["id", "strokes_key", "image_key", "url", "uploaded_at"]

    def get_url(self, obj: PageSubmission) -> str | None:
        """Signed GET for the composited page image, once grading renders it."""
        if not obj.image_key:
            return None
        return storage.presign_get(obj.image_key)


class StrokeUploadSerializer(serializers.Serializer[Any]):
    """Inline stroke JSON upload — the vector ink for one page."""

    worksheet_page = serializers.PrimaryKeyRelatedField(
        queryset=WorksheetPage.objects.all()
    )
    strokes = serializers.ListField(
        child=serializers.DictField(),
        help_text="[{points: [{x,y,t,pressure}], color, width}, ...]",
    )


class GradeJobSerializer(serializers.ModelSerializer[GradeJob]):
    class Meta:
        model = GradeJob
        fields = [
            "id",
            "status",
            "transcribe_model",
            "grade_model",
            "transcript",
            "decisions",
            "error",
            "created_at",
            "finished_at",
        ]
        read_only_fields = fields


class MarkSerializer(serializers.ModelSerializer[Mark]):
    class Meta:
        model = Mark
        fields = [
            "id",
            "attempt",
            "score",
            "max_score",
            "per_page",
            "feedback",
            "auto_suggested",
            "marked_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "auto_suggested", "created_at", "updated_at"]


class AttemptSerializer(serializers.ModelSerializer[Attempt]):
    student = UserSerializer(read_only=True)
    worksheet = WorksheetSerializer(read_only=True)
    worksheet_id = serializers.PrimaryKeyRelatedField(
        queryset=Worksheet.objects.filter(status=WorksheetStatus.PUBLISHED),
        source="worksheet",
        write_only=True,
    )
    pages = PageSubmissionSerializer(many=True, read_only=True)
    mark = MarkSerializer(read_only=True)
    grade_jobs = GradeJobSerializer(many=True, read_only=True)

    class Meta:
        model = Attempt
        fields = [
            "id",
            "student",
            "worksheet",
            "worksheet_id",
            "status",
            "started_at",
            "submitted_at",
            "returned_at",
            "pages",
            "mark",
            "grade_jobs",
        ]
        read_only_fields = [
            "id",
            "status",
            "started_at",
            "submitted_at",
            "returned_at",
        ]

    def create(self, validated_data: dict[str, Any]) -> Attempt:
        attempt, _ = Attempt.objects.get_or_create(
            student=self.context["request"].user,
            worksheet=validated_data["worksheet"],
            status=AttemptStatus.IN_PROGRESS,
        )
        return attempt

    def to_representation(self, instance: Attempt) -> dict[str, Any]:
        """Hide marks until returned, unless the viewer marked it."""
        data = super().to_representation(instance)
        request = self.context.get("request")
        if (
            request
            and instance.student == request.user
            and instance.status != AttemptStatus.RETURNED
        ):
            data["mark"] = None
        return data
