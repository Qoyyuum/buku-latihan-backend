from django.db.models import QuerySet
from rest_framework import viewsets

from apps.common.permissions import IsTeacherOrReadOnly
from apps.curriculum.api.serializers import SubjectSerializer, TopicSerializer
from apps.curriculum.models import Subject, Topic


class SubjectViewSet(viewsets.ModelViewSet):
    """Everyone can browse; only teachers/admins can edit."""

    serializer_class = SubjectSerializer
    permission_classes = [IsTeacherOrReadOnly]
    lookup_field = "slug"

    def get_queryset(self) -> QuerySet[Subject]:
        return Subject.objects.prefetch_related("topics")


class TopicViewSet(viewsets.ModelViewSet):
    serializer_class = TopicSerializer
    permission_classes = [IsTeacherOrReadOnly]

    def get_queryset(self) -> QuerySet[Topic]:
        return Topic.objects.select_related("subject")
