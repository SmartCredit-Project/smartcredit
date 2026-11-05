from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ModelVersionViewSet,
    PredictionViewSet,
    health_check,
    home,
    model_info,
)


router = DefaultRouter()

router.register(
    "predictions",
    PredictionViewSet,
    basename="prediction",
)

router.register(
    "model-versions",
    ModelVersionViewSet,
    basename="model-version",
)

urlpatterns = [
    path("", home, name="api-home"),

    path("health/", health_check, name="health-check"),

    path("model-info/", model_info, name="model-info"),

    path("", include(router.urls)),
]
