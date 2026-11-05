from django.db.models import Q
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .audit import log_activity
from .models import ActivityLog, FeatureFlag, FinancialInstitution, User
from .permissions import IsAdminOrSuperAdmin, IsSuperAdmin
from .serializers import (
    ActivityLogSerializer,
    CustomTokenObtainPairSerializer,
    FeatureFlagSerializer,
    FinancialInstitutionSerializer,
    LogoutSerializer,
    RegisterSerializer,
    UserAdminSerializer,
    UserSerializer,
)


class RegisterView(APIView):
    """POST /api/auth/register/ - Inscription d'un demandeur."""

    permission_classes = [AllowAny]

    @extend_schema(
        request=RegisterSerializer,
        responses={201: UserSerializer},
    )
    def post(self, request):
        serializer = RegisterSerializer(
            data=request.data,
            context={"request": request},
        )

        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        log_activity(
            action=ActivityLog.Action.REGISTERED,
            user=user,
            institution=user.institution,
            entity_type="User",
            entity_id=user.id,
            description="Inscription d'un demandeur de crédit.",
            request=request,
        )

        return Response(
            UserSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    """POST /api/auth/login/ - Connexion par email."""

    permission_classes = [AllowAny]

    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == status.HTTP_200_OK:
            email = request.data.get("email", "")
            user = User.objects.filter(
                email__iexact=email
            ).first()

            if user is not None:
                log_activity(
                    action=ActivityLog.Action.LOGIN,
                    user=user,
                    entity_type="User",
                    entity_id=user.id,
                    description="Connexion réussie.",
                    request=request,
                )

        return response


class LogoutView(APIView):
    """POST /api/auth/logout/ - Déconnexion (blacklist du refresh)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=LogoutSerializer,
        responses={200: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response(
                {
                    "detail": (
                        "Le token de rafraîchissement est requis."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            RefreshToken(refresh_token).blacklist()

        except TokenError:
            return Response(
                {"detail": "Token invalide ou expiré."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        log_activity(
            action=ActivityLog.Action.LOGOUT,
            user=request.user,
            entity_type="User",
            entity_id=request.user.id,
            description="Déconnexion.",
            request=request,
        )

        return Response(
            {"detail": "Déconnexion réussie."},
            status=status.HTTP_200_OK,
        )


class MeView(APIView):
    """GET /api/auth/me/ - Informations de l'utilisateur courant."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses=UserSerializer)
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class UserViewSet(viewsets.ModelViewSet):
    """
    Gestion des utilisateurs.

    - SUPERADMIN : tous les utilisateurs, tous rôles.
    - ADMIN      : agents de son institution uniquement.
    """

    queryset = User.objects.all()
    permission_classes = [IsAdminOrSuperAdmin]

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return UserSerializer

        return UserAdminSerializer

    def get_queryset(self):
        queryset = User.objects.select_related(
            "institution"
        ).order_by("-date_joined")

        user = self.request.user

        if not user.is_superadmin:
            if not user.institution_id:
                return queryset.none()

            queryset = queryset.filter(
                institution_id=user.institution_id
            )

        role = self.request.query_params.get("role")
        if role:
            queryset = queryset.filter(role=role)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )

        return queryset

    def perform_create(self, serializer):
        user = serializer.save()

        log_activity(
            action=ActivityLog.Action.CREATED,
            user=self.request.user,
            institution=user.institution,
            entity_type="User",
            entity_id=user.id,
            description=f"Création de l'utilisateur {user.email}.",
            request=self.request,
        )

    def perform_update(self, serializer):
        user = serializer.save()

        was_deactivated = not user.is_active

        log_activity(
            action=(
                ActivityLog.Action.DEACTIVATED
                if was_deactivated
                else ActivityLog.Action.UPDATED
            ),
            user=self.request.user,
            institution=user.institution,
            entity_type="User",
            entity_id=user.id,
            description=f"Mise à jour de l'utilisateur {user.email}.",
            request=self.request,
        )

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()

        if user.is_superadmin:
            return Response(
                {
                    "detail": (
                        "Un super administrateur ne peut pas être "
                        "désactivé."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            not request.user.is_superadmin
            and user.role != User.Role.CREDIT_AGENT
        ):
            return Response(
                {
                    "detail": (
                        "Un administrateur ne peut désactiver que "
                        "des agents de crédit."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        user.is_active = False
        user.save(update_fields=["is_active"])

        log_activity(
            action=ActivityLog.Action.DEACTIVATED,
            user=request.user,
            institution=user.institution,
            entity_type="User",
            entity_id=user.id,
            description=f"Désactivation de l'utilisateur {user.email}.",
            request=request,
        )

        return Response(status=status.HTTP_204_NO_CONTENT)


class FinancialInstitutionViewSet(viewsets.ModelViewSet):
    """
    Gestion des institutions financières.

    - SUPERADMIN : accès complet.
    - Autres     : lecture seule, limitée à leur institution.
    """

    queryset = FinancialInstitution.objects.all()
    serializer_class = FinancialInstitutionSerializer

    def get_permissions(self):
        if self.request.method in ["GET", "HEAD", "OPTIONS"]:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsSuperAdmin]

        return [
            permission()
            for permission in permission_classes
        ]

    def get_queryset(self):
        queryset = FinancialInstitution.objects.all()

        user = self.request.user

        if user.is_superadmin:
            return queryset

        if user.institution_id:
            return queryset.filter(pk=user.institution_id)

        return queryset.filter(is_active=True)

    def perform_create(self, serializer):
        institution = serializer.save()

        log_activity(
            action=ActivityLog.Action.CREATED,
            user=self.request.user,
            institution=institution,
            entity_type="FinancialInstitution",
            entity_id=institution.id,
            description=f"Création de l'institution {institution.name}.",
            request=self.request,
        )

    def perform_update(self, serializer):
        institution = serializer.save()

        log_activity(
            action=ActivityLog.Action.UPDATED,
            user=self.request.user,
            institution=institution,
            entity_type="FinancialInstitution",
            entity_id=institution.id,
            description=(
                f"Mise à jour de l'institution {institution.name}."
            ),
            request=self.request,
        )

    def perform_destroy(self, instance):
        log_activity(
            action=ActivityLog.Action.DELETED,
            user=self.request.user,
            institution=instance,
            entity_type="FinancialInstitution",
            entity_id=instance.id,
            description=(
                f"Suppression de l'institution {instance.name}."
            ),
            request=self.request,
        )

        instance.delete()


class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Consultation du journal d'activité.

    - SUPERADMIN : tous les journaux.
    - ADMIN      : journaux de son institution uniquement.
    """

    queryset = ActivityLog.objects.all()
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAdminOrSuperAdmin]

    def get_queryset(self):
        queryset = ActivityLog.objects.select_related(
            "user",
            "institution",
        ).all()

        user = self.request.user

        if not user.is_superadmin:
            if not user.institution_id:
                return queryset.none()

            queryset = queryset.filter(
                institution_id=user.institution_id
            )

        action = self.request.query_params.get("action")
        if action:
            queryset = queryset.filter(action=action)

        entity_type = self.request.query_params.get(
            "entity_type"
        )
        if entity_type:
            queryset = queryset.filter(
                entity_type=entity_type
            )

        user_id = self.request.query_params.get("user")
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        return queryset


class FeatureFlagViewSet(viewsets.ModelViewSet):
    """
    Gestion des drapeaux de fonctionnalité.

    - SUPERADMIN : accès complet.
    - ADMIN      : lecture seule.
    """

    queryset = FeatureFlag.objects.all()
    serializer_class = FeatureFlagSerializer

    def get_permissions(self):
        if self.request.method in ["GET", "HEAD", "OPTIONS"]:
            permission_classes = [IsAdminOrSuperAdmin]
        else:
            permission_classes = [IsSuperAdmin]

        return [
            permission()
            for permission in permission_classes
        ]

    def perform_create(self, serializer):
        flag = serializer.save()

        log_activity(
            action=ActivityLog.Action.CREATED,
            user=self.request.user,
            entity_type="FeatureFlag",
            entity_id=flag.id,
            description=f"Création du drapeau {flag.key}.",
            request=self.request,
        )

    def perform_update(self, serializer):
        flag = serializer.save()

        log_activity(
            action=ActivityLog.Action.UPDATED,
            user=self.request.user,
            entity_type="FeatureFlag",
            entity_id=flag.id,
            description=f"Mise à jour du drapeau {flag.key}.",
            metadata={"is_enabled": flag.is_enabled},
            request=self.request,
        )

    def perform_destroy(self, instance):
        log_activity(
            action=ActivityLog.Action.DELETED,
            user=self.request.user,
            entity_type="FeatureFlag",
            entity_id=instance.id,
            description=f"Suppression du drapeau {instance.key}.",
            request=self.request,
        )

        instance.delete()
