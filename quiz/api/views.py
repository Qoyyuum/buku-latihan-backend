from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, CreateModelMixin
from quiz.models import Quiz, Question, Category, SubCategory, Progress, Sitting
from quiz.api.serializers import QuizSerializer, QuestionSerializer, CategorySerializer, SubCategorySerializer, ProgressSerializer, SittingSerializer
# from rest_framework.response import Response
# from rest_framework import status

class QuizViewSet(RetrieveModelMixin, ListModelMixin, GenericViewSet):
	queryset = Quiz.objects.all()
	serializer_class = QuizSerializer

	def get(self, request, *args, **kwargs):
		return self.list(request, *args, **kwargs)


class CategoryViewSet(RetrieveModelMixin, ListModelMixin, GenericViewSet):
	queryset = Category.objects.all()
	serializer_class = CategorySerializer

	def get(self, request, *args, **kwargs):
		return self.list(request, *args, **kwargs)

class SubCategoryViewSet(RetrieveModelMixin, ListModelMixin, GenericViewSet):
	queryset = SubCategory.objects.all()
	serializer_class = SubCategorySerializer

	def get(self, request, *args, **kwargs):
		return self.list(request, *args, **kwargs)


class QuestionViewSet(RetrieveModelMixin, ListModelMixin, GenericViewSet):
	queryset = Question.objects.all()
	serializer_class = QuestionSerializer

	def get(self, request, *args, **kwargs):
		return self.list(request, *args, **kwargs)

class ProgressViewSet(RetrieveModelMixin, CreateModelMixin, ListModelMixin, GenericViewSet):
	queryset = Progress.objects.all()
	serializer_class = ProgressSerializer

	def get(self, request, *args, **kwargs):
		return self.list(request, *args, **kwargs)

	def post(self, request, *args, **kwargs):
		return self.create(request, *args, **kwargs)

class SittingViewSet(RetrieveModelMixin, CreateModelMixin, ListModelMixin, GenericViewSet):
	queryset = Sitting.objects.all()
	serializer_class = SittingSerializer

	def get(self, request, *args, **kwargs):
		return self.list(request, *args, **kwargs)

	def post(self, request, *args, **kwargs):
		return self.create(request, *args, **kwargs)