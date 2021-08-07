from rest_framework import serializers

from multichoice.models import Answer, MCQuestion


class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = "__all__"


class MCQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MCQuestion
        fields = "__all__"
