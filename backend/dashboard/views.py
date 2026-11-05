from datetime import timedelta

from django.db.models import Avg, Count, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import IsStaffRole
from applicants.models import Applicant
from credit_applications.models import CreditApplication
from predictions.models import ModelVersion, Prediction


def group_counts(queryset, field):
    return {
        row[field]: row["count"]
        for row in queryset.values(field).annotate(
            count=Count("id")
        )
    }


def scope_queryset(queryset, user):
    """Limite un queryset à l'institution de l'utilisateur."""

    if user.is_superadmin:
        return queryset

    if not user.institution_id:
        return queryset.none()

    return queryset.filter(institution_id=user.institution_id)


class DashboardOverviewView(APIView):
    """GET /api/dashboard/ - Statistiques générales."""

    permission_classes = [IsStaffRole]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        user = request.user

        predictions = scope_queryset(
            Prediction.objects.all(),
            user,
        )
        users = scope_queryset(User.objects.all(), user)
        applicants = scope_queryset(
            Applicant.objects.all(),
            user,
        )
        applications = scope_queryset(
            CreditApplication.objects.all(),
            user,
        )

        active_model = ModelVersion.objects.filter(
            is_active=True
        ).first()

        return Response(
            {
                "users": {
                    "total": users.count(),
                    "active": users.filter(
                        is_active=True
                    ).count(),
                    "by_role": group_counts(users, "role"),
                },
                "applicants": {
                    "total": applicants.count(),
                },
                "applications": {
                    "total": applications.count(),
                    "by_status": group_counts(
                        applications,
                        "status",
                    ),
                },
                "predictions": {
                    "total": predictions.count(),
                    "by_risk_level": group_counts(
                        predictions,
                        "risk_level",
                    ),
                    "average_default_probability": (
                        predictions.aggregate(
                            value=Avg("default_probability")
                        )["value"]
                    ),
                },
                "active_model": (
                    {
                        "id": active_model.id,
                        "name": active_model.name,
                        "version": active_model.version,
                        "algorithm": active_model.algorithm,
                    }
                    if active_model
                    else None
                ),
            }
        )


class PredictionStatsView(APIView):
    """GET /api/dashboard/predictions/ - Statistiques des prédictions."""

    permission_classes = [IsStaffRole]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        queryset = scope_queryset(
            Prediction.objects.all(),
            request.user,
        )

        aggregates = queryset.aggregate(
            total=Count("id"),
            average_default_probability=Avg(
                "default_probability"
            ),
        )

        last_30_days = timezone.now() - timedelta(days=30)

        by_month = (
            queryset.filter(created_at__gte=last_30_days)
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )

        return Response(
            {
                "total": aggregates["total"],
                "predicted_default": queryset.filter(
                    predicted_class=1
                ).count(),
                "predicted_no_default": queryset.filter(
                    predicted_class=0
                ).count(),
                "high_risk": queryset.filter(
                    risk_level=Prediction.RiskLevel.HIGH
                ).count(),
                "average_default_probability": aggregates[
                    "average_default_probability"
                ],
                "by_risk_level": group_counts(
                    queryset,
                    "risk_level",
                ),
                "by_model_version": [
                    {
                        "model_version": row[
                            "model_version__version"
                        ],
                        "model_name": row[
                            "model_version__name"
                        ],
                        "count": row["count"],
                    }
                    for row in queryset.values(
                        "model_version__name",
                        "model_version__version",
                    )
                    .annotate(count=Count("id"))
                    .order_by("-count")
                ],
                "last_30_days_by_month": [
                    {
                        "month": row["month"],
                        "count": row["count"],
                    }
                    for row in by_month
                ],
            }
        )


class ApplicationStatsView(APIView):
    """GET /api/dashboard/applications/ - Statistiques des demandes."""

    permission_classes = [IsStaffRole]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        queryset = scope_queryset(
            CreditApplication.objects.all(),
            request.user,
        )

        aggregates = queryset.aggregate(
            total=Count("id"),
            total_amount=Sum("loan_amnt"),
            average_amount=Avg("loan_amnt"),
            average_income=Avg("person_income"),
        )

        by_month = (
            queryset.annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )

        return Response(
            {
                "total": aggregates["total"],
                "total_requested_amount": aggregates[
                    "total_amount"
                ],
                "average_requested_amount": aggregates[
                    "average_amount"
                ],
                "average_income": aggregates[
                    "average_income"
                ],
                "by_status": group_counts(
                    queryset,
                    "status",
                ),
                "by_loan_intent": group_counts(
                    queryset,
                    "loan_intent",
                ),
                "by_home_ownership": group_counts(
                    queryset,
                    "person_home_ownership",
                ),
                "by_month": [
                    {
                        "month": row["month"],
                        "count": row["count"],
                    }
                    for row in by_month
                ],
            }
        )
