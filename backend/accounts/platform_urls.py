from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ActivityLogViewSet, FeatureFlagViewSet, FinancialInstitutionViewSet

router = DefaultRouter()

router.register(
    "institutions",
    FinancialInstitutionViewSet,
    basename="institution",
)

router.register(
    "activity-logs",
    ActivityLogViewSet,
    basename="activity-log",
)

router.register(
    "feature-flags",
    FeatureFlagViewSet,
    basename="feature-flag",
)

urlpatterns = [
    path("", include(router.urls)),
]
