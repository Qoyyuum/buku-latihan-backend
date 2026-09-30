from typing import Any

from rest_framework import serializers

from apps.worksheets.models import AnswerSheet, Worksheet, WorksheetPage


class WorksheetPageSerializer(serializers.ModelSerializer[WorksheetPage]):
    class Meta:
        model = WorksheetPage
        fields = ["id", "order", "image_key", "width", "height", "answer_regions"]
        read_only_fields = ["id"]


class AnswerSheetSerializer(serializers.ModelSerializer[AnswerSheet]):
    class Meta:
        model = AnswerSheet
        fields = ["id", "file_key", "notes", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at"]


class WorksheetSerializer(serializers.ModelSerializer[Worksheet]):
    pages = WorksheetPageSerializer(many=True, read_only=True)
    answer_sheets = AnswerSheetSerializer(many=True, read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True)

    class Meta:
        model = Worksheet
        fields = [
            "id",
            "subject",
            "subject_name",
            "topic",
            "title",
            "description",
            "exam_year",
            "source",
            "status",
            "pages",
            "answer_sheets",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class UploadUrlRequestSerializer(serializers.Serializer[Any]):
    """Ask for a presigned PUT URL before uploading a file to S3."""

    filename = serializers.CharField(max_length=200)
    content_type = serializers.CharField(max_length=100, default="image/png")


class RegisterPageSerializer(serializers.Serializer[Any]):
    """Register a page after its image has been PUT to the presigned URL."""

    image_key = serializers.CharField(max_length=500)
    order = serializers.IntegerField(min_value=0)
    width = serializers.IntegerField(min_value=1, required=False)
    height = serializers.IntegerField(min_value=1, required=False)
    answer_regions = serializers.ListField(required=False, default=list)

    def create(self, validated_data: dict[str, Any]) -> WorksheetPage:
        worksheet = self.context["worksheet"]
        return WorksheetPage.objects.create(worksheet=worksheet, **validated_data)


class RegisterAnswerSheetSerializer(serializers.Serializer[Any]):
    file_key = serializers.CharField(max_length=500)
    notes = serializers.CharField(required=False, default="", allow_blank=True)

    def create(self, validated_data: dict[str, Any]) -> AnswerSheet:
        worksheet = self.context["worksheet"]
        user = self.context["request"].user
        return AnswerSheet.objects.create(
            worksheet=worksheet, uploaded_by=user, **validated_data
        )
