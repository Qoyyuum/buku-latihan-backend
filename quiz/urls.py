from django.conf import settings
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework.routers import DefaultRouter, SimpleRouter

from quiz.api.views import (
    CategoryViewSet,
    ProgressViewSet,
    QuestionViewSet,
    QuizViewSet,
    SittingViewSet,
    SubCategoryViewSet,
)

router = DefaultRouter() if settings.DEBUG else SimpleRouter()
router.register("quizzes", QuizViewSet)
router.register("questions", QuestionViewSet)
router.register("progress", ProgressViewSet)
router.register("sittings", SittingViewSet)
router.register("categories", CategoryViewSet)
router.register("subcategories", SubCategoryViewSet)

schema_view = get_schema_view(
    openapi.Info(
        title="Quiz API",
        default_version="v1",
        description="Quiz API to get a list of questions and submit answers against",
        terms_of_service="https://buku-latihan.herokuapp.com/",
        contact=openapi.Contact(email="abdul.qoyyuum@gmail.com"),
        license=openapi.License(name="GPLv3 License"),
    ),
    public=True,
    permission_classes=(permissions.IsAuthenticatedOrReadOnly,),
)

urlpatterns = [
    path("", include(router.urls)),
    # path(r'swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    # path(r'swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path(r"doc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
]
