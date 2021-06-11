from django.conf import settings
from django.urls import path, include
from rest_framework.routers import DefaultRouter, SimpleRouter
from quiz.api import views
from quiz.api.views import QuizViewSet, QuestionViewSet, ProgressViewSet, CategoryViewSet, SubCategoryViewSet, SittingViewSet

if settings.DEBUG:
	router = DefaultRouter()
else:
	router = SimpleRouter()

router.register("quizzes", QuizViewSet)
router.register("questions", QuestionViewSet)
router.register("progress", ProgressViewSet)
router.register("sittings", SittingViewSet)
router.register("categories", CategoryViewSet)
router.register("subcategories", SubCategoryViewSet)

urlpatterns = [
	path("", include(router.urls)),
]
