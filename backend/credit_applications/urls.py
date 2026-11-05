from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CreditApplicationViewSet

router = DefaultRouter()

router.register(
    "credit-applications",
    CreditApplicationViewSet,
    basename="credit-application",
)

urlpatterns = [
    path("", include(router.urls)),
]
