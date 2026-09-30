from typing import Any

from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.accounts.models import User, UserRole
from apps.common import storage
from apps.common.permissions import IsTeacher
from apps.worksheets.api.serializers import (
    AnswerSheetSerializer,
    RegisterAnswerSheetSerializer,
    RegisterPageSerializer,
    UploadUrlRequestSerializer,
    WorksheetPageSerializer,
    WorksheetSerializer,
)
from apps.worksheets.models import Worksheet, WorksheetStatus


class WorksheetViewSet(viewsets.ModelViewSet):
    """
    Students see published worksheets; teachers/admins see all and can edit.

    Extra actions:
      POST {id}/upload-url/      — presigned PUT for a page image or PDF
      POST {id}/pages/           — register an uploaded image as a page
      POST {id}/answer-sheets/   — register an uploaded answer-key file
      GET  {id}/bundle/          — manifest + signed GET URLs (offline download)
    """

    serializer_class = WorksheetSerializer

    def get_queryset(self) -> QuerySet[Worksheet]:
        qs = Worksheet.objects.select_related(
            "subject", "topic", "created_by"
        ).prefetch_related("pages", "answer_sheets")
        subject_id = self.request.query_params.get("subject")
        if subject_id:
            qs = qs.filter(subject_id=subject_id)
        user = self.request.user
        if isinstance(user, User) and user.role in {
            UserRole.ADMIN,
            UserRole.TEACHER,
        }:
            return qs
        return qs.filter(status=WorksheetStatus.PUBLISHED)

    def get_permissions(self) -> list[Any]:
        if self.action in {
            "create",
            "update",
            "partial_update",
            "destroy",
            "upload_url",
            "pages",
            "rasterize",
            "answer_sheets",
        }:
            return [IsTeacher()]
        return [IsAuthenticated()]

    def perform_create(self, serializer: Any) -> None:
        serializer.save(created_by=self.request.user)

    @extend_schema(request=UploadUrlRequestSerializer)
    @action(detail=True, methods=["post"], url_path="upload-url")
    def upload_url(self, request: Request, pk: int | None = None) -> Response:
        """Return a presigned PUT URL + object key for direct-to-S3 upload."""
        serializer = UploadUrlRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        filename = serializer.validated_data["filename"]
        content_type = serializer.validated_data["content_type"]

        prefix = "pdfs" if content_type == "application/pdf" else "worksheet-pages"
        key = storage.new_key(f"worksheets/{pk}/{prefix}", filename)
        return Response(
            {"key": key, "upload_url": storage.presign_put(key, content_type)}
        )

    @extend_schema(request=RegisterPageSerializer, responses=WorksheetPageSerializer)
    @action(detail=True, methods=["post"], url_path="pages")
    def pages(self, request: Request, pk: int | None = None) -> Response:
        """Register an already-uploaded image as a worksheet page."""
        worksheet = self.get_object()
        serializer = RegisterPageSerializer(
            data=request.data, context={"worksheet": worksheet}
        )
        serializer.is_valid(raise_exception=True)
        page = serializer.save()
        return Response(
            WorksheetPageSerializer(page).data, status=status.HTTP_201_CREATED
        )

    @extend_schema(
        request=RegisterAnswerSheetSerializer, responses=AnswerSheetSerializer
    )
    @extend_schema(request=None)
    @action(detail=True, methods=["post"], url_path="rasterize")
    def rasterize(self, request: Request, pk: int | None = None) -> Response:
        """
        Queue Celery rasterization of an uploaded PDF into worksheet pages.
        Body: {"pdf_key": "<object key returned by upload-url>"}
        """
        if not isinstance(request.data, dict):
            return Response(status=status.HTTP_400_BAD_REQUEST)
        pdf_key = request.data.get("pdf_key")
        if not pdf_key:
            return Response(
                {"detail": "pdf_key is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from apps.worksheets.tasks import rasterize_pdf

        worksheet = self.get_object()
        result = rasterize_pdf.delay(worksheet.pk, pdf_key)
        return Response({"task_id": result.id}, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["post"], url_path="answer-sheets")
    def answer_sheets(self, request: Request, pk: int | None = None) -> Response:
        """Register an already-uploaded file as the worksheet's answer sheet."""
        worksheet = self.get_object()
        serializer = RegisterAnswerSheetSerializer(
            data=request.data, context={"worksheet": worksheet, "request": request}
        )
        serializer.is_valid(raise_exception=True)
        sheet = serializer.save()
        return Response(
            AnswerSheetSerializer(sheet).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["get"])
    def bundle(self, request: Request, pk: int | None = None) -> Response:
        """
        Offline-download manifest: worksheet metadata plus every page with a
        short-lived signed GET URL. The app caches these files locally.
        """
        worksheet = self.get_object()
        data = WorksheetSerializer(worksheet).data
        data["page_downloads"] = [
            {
                "page_id": page.id,
                "order": page.order,
                "url": storage.presign_get(page.image_key),
                "width": page.width,
                "height": page.height,
                "answer_regions": page.answer_regions,
            }
            for page in worksheet.pages.all()
        ]
        return Response(data)
