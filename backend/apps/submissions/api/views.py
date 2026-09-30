import json
from typing import Any

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.db.models import Count, QuerySet
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User, UserRole
from apps.common import storage
from apps.common.permissions import IsStudent, IsTeacher
from apps.submissions.api.serializers import (
    AttemptSerializer,
    MarkSerializer,
    PageSubmissionSerializer,
    StrokeUploadSerializer,
)
from apps.submissions.models import Attempt, AttemptStatus, Mark, PageSubmission


def _visible_attempts(
    user: AbstractBaseUser | AnonymousUser,
) -> QuerySet[Attempt]:
    base = Attempt.objects.select_related(
        "student", "worksheet__subject", "worksheet__topic"
    ).prefetch_related("pages", "grade_jobs")
    if not isinstance(user, User):
        return base.none()
    if user.role == UserRole.ADMIN:
        return base
    if user.role == UserRole.TEACHER:
        return base.filter(student__enrollments__classroom__teacher=user)
    if user.role == UserRole.PARENT:
        return base.filter(student__parents__parent=user)
    return base.filter(student=user)


class AttemptViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """
    Students create attempts, upload ink per page, and submit.
    Teachers see submissions of students in their classrooms; parents see
    their children's.
    """

    serializer_class = AttemptSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self) -> QuerySet[Attempt]:
        qs = _visible_attempts(self.request.user)
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    def get_permissions(self) -> list[Any]:
        if self.action in {"create", "upload_page", "submit"}:
            return [IsStudent()]
        if self.action == "return_marks":
            return [IsTeacher()]
        return [IsAuthenticated()]

    @extend_schema(request=StrokeUploadSerializer)
    @action(detail=True, methods=["post"], url_path="pages")
    def upload_page(self, request: Request, pk: int | None = None) -> Response:
        """Save the vector strokes for one worksheet page to object storage."""
        attempt = self.get_object()
        if attempt.status != AttemptStatus.IN_PROGRESS:
            return Response(
                {"detail": "Attempt is no longer editable."},
                status=status.HTTP_409_CONFLICT,
            )
        serializer = StrokeUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        page = serializer.validated_data["worksheet_page"]
        strokes = serializer.validated_data["strokes"]

        key = f"attempts/{attempt.id}/pages/{page.id}/strokes.json"
        storage.put_bytes(key, json.dumps(strokes).encode(), "application/json")

        page_sub, _ = PageSubmission.objects.update_or_create(
            attempt=attempt,
            worksheet_page=page,
            defaults={"strokes_key": key},
        )
        return Response(
            PageSubmissionSerializer(page_sub).data, status=status.HTTP_200_OK
        )

    @action(detail=True, methods=["post"])
    def submit(self, request: Request, pk: int | None = None) -> Response:
        """Finish the attempt and queue auto-grading."""
        attempt = self.get_object()
        if attempt.status != AttemptStatus.IN_PROGRESS:
            return Response(
                {"detail": "Attempt already submitted."},
                status=status.HTTP_409_CONFLICT,
            )
        attempt.status = AttemptStatus.SUBMITTED
        attempt.submitted_at = timezone.now()
        attempt.save(update_fields=["status", "submitted_at"])

        from apps.submissions.tasks import grade_attempt

        grade_attempt.delay(attempt.id)
        return Response(AttemptSerializer(attempt).data)

    @action(detail=True, methods=["post"], url_path="return")
    def return_marks(self, request: Request, pk: int | None = None) -> Response:
        """Teacher confirms the marks (possibly AI-suggested) and returns them."""
        attempt = self.get_object()
        if attempt.status not in {AttemptStatus.SUBMITTED, AttemptStatus.GRADED}:
            return Response(
                {"detail": "Nothing to return yet."},
                status=status.HTTP_409_CONFLICT,
            )
        attempt.status = AttemptStatus.RETURNED
        attempt.returned_at = timezone.now()
        attempt.save(update_fields=["status", "returned_at"])

        if hasattr(attempt, "mark"):
            attempt.mark.auto_suggested = False
            attempt.mark.marked_by = request.user
            attempt.mark.save(update_fields=["auto_suggested", "marked_by"])
        return Response(AttemptSerializer(attempt).data)


class MarkViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Teachers write marks; students/parents read returned ones."""

    serializer_class = MarkSerializer

    def get_queryset(self) -> QuerySet[Mark]:
        user = self.request.user
        base = Mark.objects.select_related("attempt__student", "attempt__worksheet")
        if not isinstance(user, User):
            return base.none()
        if user.role == UserRole.ADMIN:
            return base
        if user.role == UserRole.TEACHER:
            return base.filter(attempt__student__enrollments__classroom__teacher=user)
        if user.role == UserRole.PARENT:
            return base.filter(
                attempt__student__parents__parent=user,
                attempt__status=AttemptStatus.RETURNED,
            )
        return base.filter(
            attempt__student=user, attempt__status=AttemptStatus.RETURNED
        )

    def get_permissions(self) -> list[Any]:
        if self.action in {"create", "update", "partial_update"}:
            return [IsTeacher()]
        return [IsAuthenticated()]

    def perform_create(self, serializer: Any) -> None:
        serializer.save(marked_by=self.request.user, auto_suggested=False)

    def perform_update(self, serializer: Any) -> None:
        serializer.save(marked_by=self.request.user, auto_suggested=False)


class DashboardView(APIView):
    """
    Role-scoped summary stats for the web dashboard.

      students → their own attempts/marks
      parents  → their children
      teachers → students in their classrooms
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        user = request.user
        attempts = _visible_attempts(user)

        by_status = dict(
            attempts.values_list("status")
            .annotate(n=Count("id"))
            .values_list("status", "n")
        )
        marks = Mark.objects.filter(
            attempt__in=attempts, attempt__status=AttemptStatus.RETURNED
        )
        avg = None
        scores = [(m.score / m.max_score) * 100 for m in marks if m.max_score > 0]
        if scores:
            avg = round(sum(scores) / len(scores), 1)

        return Response(
            {
                "attempts_total": attempts.count(),
                "attempts_by_status": by_status,
                "returned_avg_percent": avg,
                "submitted_pending_review": by_status.get("submitted", 0)
                + by_status.get("graded", 0),
            }
        )
