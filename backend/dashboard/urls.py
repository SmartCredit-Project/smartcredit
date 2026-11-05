from django.urls import path

from .views import (
    ApplicationStatsView,
    DashboardOverviewView,
    PredictionStatsView,
)


urlpatterns = [
    path(
        "",
        DashboardOverviewView.as_view(),
        name="dashboard-overview",
    ),

    path(
        "predictions/",
        PredictionStatsView.as_view(),
        name="dashboard-predictions",
    ),

    path(
        "applications/",
        ApplicationStatsView.as_view(),
        name="dashboard-applications",
    ),
]
