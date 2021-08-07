from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from multichoice.api.serializers import AnswerSerializer, MCQuestionSerializer
from multichoice.models import Answer, MCQuestion


class MCQuestionViewSet(RetrieveModelMixin, ListModelMixin, GenericViewSet):
    queryset = MCQuestion.objects.all()
    serializer_class = MCQuestionSerializer

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class AnswerViewSet(
    CreateModelMixin, RetrieveModelMixin, ListModelMixin, GenericViewSet
):
    queryset = Answer.objects.all()
    serializer_class = AnswerSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)
