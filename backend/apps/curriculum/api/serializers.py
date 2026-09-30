from rest_framework import serializers

from apps.curriculum.models import Subject, Topic


class TopicSerializer(serializers.ModelSerializer[Topic]):
    class Meta:
        model = Topic
        fields = ["id", "subject", "name", "order"]
        read_only_fields = ["id"]


class SubjectSerializer(serializers.ModelSerializer[Subject]):
    topics = TopicSerializer(many=True, read_only=True)

    class Meta:
        model = Subject
        fields = ["id", "name", "slug", "description", "topics"]
        read_only_fields = ["id", "slug"]
