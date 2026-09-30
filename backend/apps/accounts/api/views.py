from typing import Any

from django.db.models import QuerySet
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer

from apps.accounts.api.serializers import (
    ClassroomSerializer,
    CreateUserSerializer,
    EnrollmentSerializer,
    ParentChildSerializer,
    UserSerializer,
)
from apps.accounts.models import Classroom, Enrollment, ParentChild, User, UserRole
from apps.common.permissions import IsTeacher


class UserViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """Teachers see/manage their students; admins see everyone."""

    def get_queryset(self) -> QuerySet[User]:
        user = self.request.user
        if not isinstance(user, User):
            return User.objects.none()
        if user.role == UserRole.ADMIN:
            return User.objects.all()
        if user.role == UserRole.TEACHER:
            student_ids = Enrollment.objects.filter(classroom__teacher=user).values(
                "student_id"
            )
            return User.objects.filter(id__in=student_ids)
        return User.objects.filter(pk=user.pk)

    def get_serializer_class(self) -> type[BaseSerializer[Any]]:
        if self.action == "create":
            return CreateUserSerializer
        return UserSerializer

    def get_permissions(self) -> list[Any]:
        if self.action == "create":
            return [IsTeacher()]
        return [IsAuthenticated()]

    @action(detail=False, methods=["get"])
    def me(self, request: Request) -> Response:
        if not isinstance(request.user, User):
            return Response(status=401)
        return Response(UserSerializer(request.user).data)


class ClassroomViewSet(viewsets.ModelViewSet):
    serializer_class = ClassroomSerializer
    permission_classes = [IsTeacher]

    def get_queryset(self) -> QuerySet[Classroom]:
        user = self.request.user
        qs = Classroom.objects.select_related("teacher").prefetch_related(
            "enrollments__student"
        )
        if not isinstance(user, User):
            return qs.none()
        if user.role == UserRole.ADMIN:
            return qs
        return qs.filter(teacher=user)

    def perform_create(self, serializer: Any) -> None:
        serializer.save(teacher=self.request.user)


class EnrollmentViewSet(
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = EnrollmentSerializer
    permission_classes = [IsTeacher]

    def get_queryset(self) -> QuerySet[Enrollment]:
        user = self.request.user
        qs = Enrollment.objects.select_related("student", "classroom")
        if not isinstance(user, User):
            return qs.none()
        if user.role == UserRole.ADMIN:
            return qs
        return qs.filter(classroom__teacher=user)


class ParentChildViewSet(viewsets.ModelViewSet):
    serializer_class = ParentChildSerializer
    permission_classes = [IsTeacher]

    def get_queryset(self) -> QuerySet[ParentChild]:
        user = self.request.user
        qs = ParentChild.objects.select_related("parent", "child")
        if not isinstance(user, User):
            return qs.none()
        if user.role == UserRole.ADMIN:
            return qs
        return qs.filter(child__enrollments__classroom__teacher=user).distinct()
