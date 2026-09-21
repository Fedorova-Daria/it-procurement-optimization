from rest_framework.routers import DefaultRouter

from django.urls import include, path

from .views import DocumentViewSet, health_check

router = DefaultRouter()
router.register("documents", DocumentViewSet, basename="document")

urlpatterns = [
    path("health/", health_check, name="health-check"),
    path("", include(router.urls)),
]
