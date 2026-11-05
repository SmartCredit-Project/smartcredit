from django.db.models import Q
from rest_framework import serializers, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from accounts.audit import log_activity
from accounts.models import ActivityLog
from accounts.permissions import IsStaffRole

from .models import Applicant
from .serializers import ApplicantSerializer


class ApplicantViewSet(viewsets.ModelViewSet):
    """
    Gestion des demandeurs de crédit.

    - SUPERADMIN : tous les demandeurs.
    - ADMIN / CREDIT_AGENT : demandeurs de leur institution.
    - APPLICANT : complète et consulte son propre profil.
    """

    queryset = Applicant.objects.all()
    serializer_class = ApplicantSerializer

    def get_permissions(self):
        if self.action == "destroy":
            permission_classes = [IsStaffRole]
        else:
            permission_classes = [IsAuthenticated]

        return [
            permission()
            for permission in permission_classes
        ]

    def get_queryset(self):
        queryset = Applicant.objects.select_related(
            "user",
            "institution",
        ).all()

        user = self.request.user

        if user.is_superadmin:
            pass

        elif user.is_institution_admin or user.is_credit_agent:
            if not user.institution_id:
                return queryset.none()

            queryset = queryset.filter(
                institution_id=user.institution_id
            )

        else:
            queryset = queryset.filter(user=user)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
            )

        return queryset.order_by("-created_at")

    def perform_create(self, serializer):
        requester = self.request.user
        extra = {}

        if requester.is_applicant:
            if Applicant.objects.filter(user=requester).exists():
                raise serializers.ValidationError(
                    {
                        "detail": (
                            "Un profil demandeur est déjà associé "
                            "à ce compte."
                        )
                    }
                )

            extra["user"] = requester

            if (
                serializer.validated_data.get("institution")
                is None
                and requester.institution_id
            ):
                extra["institution"] = requester.institution

        elif not requester.is_superadmin:
            if not requester.institution_id:
                raise PermissionDenied(
                    "Votre compte n'est rattaché à aucune institution."
                )

            extra["institution"] = requester.institution

        applicant = serializer.save(**extra)

        if (
            requester.is_applicant
            and applicant.institution_id
            and requester.institution_id != applicant.institution_id
        ):
            requester.institution = applicant.institution
            requester.save(update_fields=["institution"])

        log_activity(
            action=ActivityLog.Action.CREATED,
            user=requester,
            institution=applicant.institution,
            entity_type="Applicant",
            entity_id=applicant.id,
            description=(
                f"Création du demandeur {applicant.full_name}."
            ),
            request=self.request,
        )

    def perform_update(self, serializer):
        requester = self.request.user
        extra = {}

        if (
            not requester.is_superadmin
            and (
                requester.is_institution_admin
                or requester.is_credit_agent
            )
        ):
            extra["institution"] = requester.institution

        applicant = serializer.save(**extra)

        if (
            requester.is_applicant
            and applicant.institution_id
            and requester.institution_id != applicant.institution_id
        ):
            requester.institution = applicant.institution
            requester.save(update_fields=["institution"])

        log_activity(
            action=ActivityLog.Action.UPDATED,
            user=requester,
            institution=applicant.institution,
            entity_type="Applicant",
            entity_id=applicant.id,
            description=(
                f"Mise à jour du demandeur {applicant.full_name}."
            ),
            request=self.request,
        )

    def perform_destroy(self, instance):
        log_activity(
            action=ActivityLog.Action.DELETED,
            user=self.request.user,
            institution=instance.institution,
            entity_type="Applicant",
            entity_id=instance.id,
            description=(
                f"Suppression du demandeur {instance.full_name}."
            ),
            request=self.request,
        )

        instance.delete()
