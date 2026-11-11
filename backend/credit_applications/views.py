from accounts.audit import log_activity
from accounts.models import ActivityLog
from accounts.permissions import IsAdminOrSuperAdmin, IsStaffRole
from accounts.scoping import scope_applicants, scope_credit_applications
from applicants.models import Applicant
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status as http_status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import CreditApplication
from .serializers import (
    CreditApplicationAssignSerializer,
    CreditApplicationSerializer,
    CreditApplicationStatusSerializer,
)


class CreditApplicationViewSet(viewsets.ModelViewSet):
    """
    Gestion des demandes de crédit.

    - SUPERADMIN : toutes les demandes.
    - ADMIN : demandes de son institution.
    - CREDIT_AGENT : demandes qu'il a créées ou qui lui sont assignées.
    - APPLICANT : ses propres demandes.
    """

    queryset = CreditApplication.objects.all()
    serializer_class = CreditApplicationSerializer

    def get_permissions(self):
        if self.action in ["status", "destroy"]:
            permission_classes = [IsStaffRole]
        elif self.action == "assign":
            permission_classes = [IsAdminOrSuperAdmin]
        else:
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]

    def get_queryset(self):
        queryset = CreditApplication.objects.select_related(
            "applicant",
            "applicant__user",
            "created_by",
            "assigned_agent",
            "institution",
        ).all()

        queryset = scope_credit_applications(queryset, self.request.user)

        application_status = self.request.query_params.get("status")
        if application_status:
            queryset = queryset.filter(status=application_status)

        applicant_id = self.request.query_params.get("applicant")
        if applicant_id:
            queryset = queryset.filter(applicant_id=applicant_id)

        loan_intent = self.request.query_params.get("loan_intent")
        if loan_intent:
            queryset = queryset.filter(loan_intent=loan_intent)

        assigned_agent = self.request.query_params.get("assigned_agent")
        if assigned_agent:
            queryset = queryset.filter(assigned_agent_id=assigned_agent)

        return queryset.order_by("-created_at")

    def perform_create(self, serializer):
        requester = self.request.user
        applicant = serializer.validated_data["applicant"]

        if requester.is_applicant:
            if applicant.user_id != requester.id:
                raise PermissionDenied(
                    "Vous ne pouvez créer une demande que pour " "votre propre profil."
                )

            institution = applicant.institution

            if institution is None:
                raise ValidationError(
                    {
                        "institution": (
                            "Associez une institution à votre profil "
                            "avant de créer une demande."
                        )
                    }
                )

        elif requester.is_superadmin:
            institution = applicant.institution or requester.institution

        else:
            if not requester.institution_id:
                raise PermissionDenied(
                    "Votre compte n'est rattaché à aucune institution."
                )

            if applicant.institution_id != requester.institution_id:
                raise PermissionDenied(
                    "Ce demandeur n'appartient pas à votre institution."
                )

            if (
                requester.is_credit_agent
                and not scope_applicants(
                    Applicant.objects.filter(pk=applicant.pk),
                    requester,
                ).exists()
            ):
                raise PermissionDenied(
                    "Ce demandeur ne fait pas partie de vos dossiers."
                )

            institution = requester.institution

        application = serializer.save(
            created_by=requester,
            institution=institution,
        )

        log_activity(
            action=ActivityLog.Action.CREATED,
            user=requester,
            institution=institution,
            entity_type="CreditApplication",
            entity_id=application.id,
            description=(f"Création de la demande #{application.id}."),
            request=self.request,
        )

    def perform_update(self, serializer):
        requester = self.request.user
        instance = serializer.instance
        applicant = serializer.validated_data.get(
            "applicant",
            instance.applicant,
        )

        if requester.is_applicant:
            if instance.status != CreditApplication.Status.PENDING:
                raise PermissionDenied(
                    "Une demande en cours de traitement ne peut " "plus être modifiée."
                )

            if applicant.user_id != requester.id:
                raise PermissionDenied(
                    "Vous ne pouvez modifier que vos propres demandes."
                )

        elif not requester.is_superadmin:
            if (
                not requester.institution_id
                or applicant.institution_id != requester.institution_id
            ):
                raise PermissionDenied(
                    "Ce demandeur n'appartient pas à votre institution."
                )

            if (
                requester.is_credit_agent
                and not scope_applicants(
                    Applicant.objects.filter(pk=applicant.pk),
                    requester,
                ).exists()
            ):
                raise PermissionDenied(
                    "Ce demandeur ne fait pas partie de vos dossiers."
                )

        application = serializer.save()

        if (
            requester.is_superadmin
            and application.applicant.institution_id != application.institution_id
        ):
            application.institution = application.applicant.institution
            application.save(update_fields=["institution", "updated_at"])

        log_activity(
            action=ActivityLog.Action.UPDATED,
            user=requester,
            institution=application.institution,
            entity_type="CreditApplication",
            entity_id=application.id,
            description=(f"Mise à jour de la demande #{application.id}."),
            request=self.request,
        )

    def perform_destroy(self, instance):
        log_activity(
            action=ActivityLog.Action.DELETED,
            user=self.request.user,
            institution=instance.institution,
            entity_type="CreditApplication",
            entity_id=instance.id,
            description=(f"Suppression de la demande #{instance.id}."),
            request=self.request,
        )

        instance.delete()

    @extend_schema(
        request=CreditApplicationStatusSerializer,
        responses=CreditApplicationSerializer,
    )
    @action(
        detail=True,
        methods=["patch"],
        url_path="status",
        permission_classes=[IsStaffRole],
    )
    def status(self, request, pk=None):
        """PATCH /api/credit-applications/{id}/status/"""

        application = self.get_object()

        serializer = CreditApplicationStatusSerializer(
            data=request.data,
            context={"application": application},
        )

        serializer.is_valid(raise_exception=True)

        previous_status = application.status

        application.status = serializer.validated_data["status"]
        application.save(update_fields=["status", "updated_at"])

        log_activity(
            action=ActivityLog.Action.STATUS_CHANGED,
            user=request.user,
            institution=application.institution,
            entity_type="CreditApplication",
            entity_id=application.id,
            description=(
                f"Demande #{application.id} : "
                f"{previous_status} -> {application.status}."
            ),
            metadata={
                "previous_status": previous_status,
                "status": application.status,
            },
            request=request,
        )

        return Response(
            CreditApplicationSerializer(application).data,
            status=http_status.HTTP_200_OK,
        )

    @extend_schema(
        request=CreditApplicationAssignSerializer,
        responses=CreditApplicationSerializer,
    )
    @action(
        detail=True,
        methods=["patch"],
        url_path="assign",
        permission_classes=[IsAdminOrSuperAdmin],
    )
    def assign(self, request, pk=None):
        """PATCH /api/credit-applications/{id}/assign/"""

        application = self.get_object()

        serializer = CreditApplicationAssignSerializer(
            data=request.data,
            context={"application": application},
        )

        serializer.is_valid(raise_exception=True)

        agent = serializer.validated_data.get("assigned_agent")

        application.assigned_agent = agent
        application.assigned_at = timezone.now() if agent is not None else None
        application.save(
            update_fields=[
                "assigned_agent",
                "assigned_at",
                "updated_at",
            ]
        )

        log_activity(
            action=ActivityLog.Action.ASSIGNED,
            user=request.user,
            institution=application.institution,
            entity_type="CreditApplication",
            entity_id=application.id,
            description=(
                f"Demande #{application.id} affectée à "
                f"{agent.email if agent else 'personne'}."
            ),
            metadata={"assigned_agent": (agent.id if agent is not None else None)},
            request=request,
        )

        return Response(
            CreditApplicationSerializer(application).data,
            status=http_status.HTTP_200_OK,
        )

    @extend_schema(responses={200: dict})
    @action(
        detail=True,
        methods=["get"],
        url_path="prediction",
        permission_classes=[IsAuthenticated],
    )
    def prediction(self, request, pk=None):
        """GET /api/credit-applications/{id}/prediction/"""

        from predictions.serializers import PredictionSerializer

        application = self.get_object()

        latest_prediction = (
            application.predictions.select_related("model_version", "created_by")
            .order_by("-created_at")
            .first()
        )

        if latest_prediction is None:
            return Response(
                {
                    "detail": (
                        "Aucune prédiction n'a encore été "
                        "effectuée pour cette demande."
                    )
                },
                status=http_status.HTTP_404_NOT_FOUND,
            )

        return Response(PredictionSerializer(latest_prediction).data)
