import logging

from accounts.audit import is_feature_enabled, log_activity
from accounts.models import ActivityLog
from accounts.permissions import IsAdminOrSuperAdmin
from accounts.scoping import scope_predictions
from credit_applications.models import CreditApplication
from django.db import transaction
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import ModelVersion, Prediction
from .serializers import (
    ModelVersionSerializer,
    PredictionRequestSerializer,
    PredictionSerializer,
)
from .services.prediction_service import (
    get_model_health,
    get_model_info,
    predict_and_save,
)

logger = logging.getLogger(__name__)


@extend_schema(responses=OpenApiTypes.OBJECT)
@api_view(["GET"])
@permission_classes([AllowAny])
def home(request):
    """GET /api/ - Présentation de l'API SmartCredit."""

    return Response(
        {
            "message": "Bienvenue dans SmartCredit API",
            "version": "1.0.0",
            "documentation": "/api/docs/",
            "schema": "/api/schema/",
        }
    )


@extend_schema(responses=OpenApiTypes.OBJECT)
@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """GET /api/health/ - Vérification de l'état du service."""

    try:
        return Response(get_model_health())

    except Exception as error:
        return Response(
            {
                "status": "unhealthy",
                "model_loaded": False,
                "error": str(error),
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


@extend_schema(responses=OpenApiTypes.OBJECT)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def model_info(request):
    """GET /api/model-info/ - Informations sur le modèle actif."""

    try:
        return Response(get_model_info())

    except Exception as error:
        return Response(
            {"error": str(error)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class PredictionViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    Prédiction et historique des analyses de risque.

    POST /api/predictions/ : effectue une prédiction.
    GET  /api/predictions/ : liste l'historique.
    GET  /api/predictions/{id}/ : détail d'une prédiction.
    """

    queryset = Prediction.objects.all()
    serializer_class = PredictionSerializer

    def get_permissions(self):
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = Prediction.objects.select_related(
            "credit_application",
            "credit_application__applicant",
            "model_version",
            "created_by",
            "institution",
        ).all()

        queryset = scope_predictions(queryset, self.request.user)

        risk_level = self.request.query_params.get("risk_level")
        if risk_level:
            queryset = queryset.filter(risk_level=risk_level)

        application_id = self.request.query_params.get("credit_application")
        if application_id:
            queryset = queryset.filter(credit_application_id=application_id)

        return queryset.order_by("-created_at")

    @extend_schema(
        request=PredictionRequestSerializer,
        responses={201: PredictionSerializer},
    )
    def create(self, request, *args, **kwargs):
        if not is_feature_enabled("predictions", default=True):
            return Response(
                {"detail": ("La fonctionnalité de prédiction est " "désactivée.")},
                status=status.HTTP_403_FORBIDDEN,
            )

        request_serializer = PredictionRequestSerializer(data=request.data)

        request_serializer.is_valid(raise_exception=True)

        credit_application = request_serializer.validated_data["credit_application"]

        user = request.user

        if user.is_superadmin:
            allowed = True

        elif user.is_institution_admin:
            allowed = bool(
                user.institution_id
                and credit_application.institution_id == user.institution_id
            )

        elif user.is_credit_agent:
            allowed = bool(
                user.institution_id
                and credit_application.institution_id == user.institution_id
                and (
                    credit_application.created_by_id == user.id
                    or credit_application.assigned_agent_id == user.id
                )
            )

        else:
            allowed = credit_application.applicant.user_id == user.id

        if not allowed:
            raise PermissionDenied("Vous ne pouvez pas analyser cette demande.")

        try:
            with transaction.atomic():
                credit_application = CreditApplication.objects.select_for_update().get(
                    pk=credit_application.pk
                )

                existing_prediction = credit_application.predictions.first()

                if existing_prediction is not None:
                    return Response(
                        {
                            "detail": (
                                "Une prédiction existe déjà pour cette "
                                "demande de crédit."
                            ),
                            "prediction": existing_prediction.id,
                        },
                        status=status.HTTP_409_CONFLICT,
                    )

                features = credit_application.get_model_features()

                prediction, result = predict_and_save(
                    features,
                    credit_application=credit_application,
                    created_by=user,
                )

        except FileNotFoundError as error:
            logger.exception("Modèle indisponible.")

            return Response(
                {
                    "detail": ("Le modèle de prédiction est indisponible."),
                    "error": str(error),
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        except ValueError as error:
            return Response(
                {
                    "detail": ("Les données de prédiction sont invalides."),
                    "error": str(error),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as error:
            logger.exception("Erreur pendant la prédiction.")

            return Response(
                {
                    "detail": "Erreur pendant la prédiction.",
                    "error": str(error),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        log_activity(
            action=ActivityLog.Action.PREDICTION,
            user=user,
            institution=prediction.institution,
            entity_type="Prediction",
            entity_id=prediction.id,
            description=(
                f"Prédiction #{prediction.id} : "
                f"{prediction.get_risk_level_display()}."
            ),
            metadata={
                "risk_level": prediction.risk_level,
                "default_probability": (prediction.default_probability),
            },
            request=request,
        )

        response_data = PredictionSerializer(prediction).data
        response_data["decision_threshold"] = result["decision_threshold"]
        response_data["disclaimer"] = result["disclaimer"]

        return Response(
            response_data,
            status=status.HTTP_201_CREATED,
        )


class ModelVersionViewSet(viewsets.ReadOnlyModelViewSet):
    """Consultation des versions de modèle (administrateurs)."""

    queryset = ModelVersion.objects.all()
    serializer_class = ModelVersionSerializer
    permission_classes = [IsAdminOrSuperAdmin]
