from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import ActivityLog, FeatureFlag, FinancialInstitution, User


class FinancialInstitutionSerializer(serializers.ModelSerializer):
    """Représentation d'une institution financière."""

    user_count = serializers.SerializerMethodField()

    def get_user_count(self, obj) -> int:
        return obj.users.count()

    class Meta:
        model = FinancialInstitution
        fields = [
            "id",
            "name",
            "code",
            "email",
            "phone",
            "address",
            "is_active",
            "user_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user_count",
            "created_at",
            "updated_at",
        ]

    def validate_code(self, value):
        return value.strip().upper()


class UserSerializer(serializers.ModelSerializer):
    """Représentation publique d'un utilisateur."""

    role_display = serializers.CharField(
        source="get_role_display",
        read_only=True,
    )

    institution_name = serializers.CharField(
        source="institution.name",
        read_only=True,
        default=None,
    )

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "role_display",
            "institution",
            "institution_name",
            "is_active",
            "date_joined",
        ]
        read_only_fields = fields


class UserAdminSerializer(serializers.ModelSerializer):
    """Création et modification d'un utilisateur par le staff."""

    password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        style={"input_type": "password"},
    )

    institution_name = serializers.CharField(
        source="institution.name",
        read_only=True,
        default=None,
    )

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "institution",
            "institution_name",
            "is_active",
            "password",
            "date_joined",
        ]
        read_only_fields = [
            "id",
            "username",
            "date_joined",
        ]

    def validate_email(self, value):
        query = User.objects.filter(email__iexact=value)

        if self.instance:
            query = query.exclude(pk=self.instance.pk)

        if query.exists():
            raise serializers.ValidationError(
                "Un utilisateur possède déjà cette adresse."
            )

        return value

    def validate_password(self, value):
        if value:
            validate_password(value)

        return value

    def _requester(self):
        request = self.context.get("request")

        if request and request.user.is_authenticated:
            return request.user

        return None

    def validate(self, attrs):
        requester = self._requester()

        if requester is None:
            raise serializers.ValidationError("Un utilisateur authentifié est requis.")

        role = attrs.get(
            "role",
            getattr(self.instance, "role", User.Role.APPLICANT),
        )

        institution = attrs.get(
            "institution",
            getattr(self.instance, "institution", None),
        )

        if not requester.is_superadmin:
            if role != User.Role.CREDIT_AGENT:
                raise serializers.ValidationError(
                    {
                        "role": (
                            "Un administrateur d'institution ne peut "
                            "gérer que des agents de crédit."
                        )
                    }
                )

            if self.instance and self.instance.role not in [
                User.Role.CREDIT_AGENT,
                User.Role.APPLICANT,
            ]:
                raise serializers.ValidationError(
                    {"role": ("Vous ne pouvez pas modifier cet " "utilisateur.")}
                )

            attrs["institution"] = requester.institution

            if requester.institution_id is None:
                raise serializers.ValidationError(
                    {
                        "institution": (
                            "Votre compte n'est rattaché à aucune " "institution."
                        )
                    }
                )

        else:
            if role == User.Role.SUPERADMIN:
                attrs["institution"] = None

            elif (
                role
                in [
                    User.Role.ADMIN,
                    User.Role.CREDIT_AGENT,
                ]
                and institution is None
            ):
                raise serializers.ValidationError(
                    {"institution": ("Une institution est requise pour ce rôle.")}
                )

        if (
            self.instance
            and self.instance.is_superadmin
            and not requester.is_superadmin
        ):
            raise serializers.ValidationError(
                "Vous ne pouvez pas modifier un super administrateur."
            )

        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password", None)

        user = User(**validated_data)

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save()

        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)

        for field, value in validated_data.items():
            setattr(instance, field, value)

        if "email" in validated_data:
            instance.username = instance.email

        if password:
            instance.set_password(password)

        instance.save()

        return instance


class RegisterSerializer(serializers.ModelSerializer):
    """Inscription publique d'un demandeur de crédit."""

    password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )

    password_confirm = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "password",
            "password_confirm",
        ]
        read_only_fields = ["id"]

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "Un utilisateur possède déjà cette adresse."
            )

        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": ("Les deux mots de passe ne correspondent pas.")}
            )

        validate_password(attrs["password"])

        attrs.pop("password_confirm")

        return attrs

    def create(self, validated_data):
        from applicants.models import Applicant

        password = validated_data.pop("password")

        user = User(
            **validated_data,
            role=User.Role.APPLICANT,
        )
        user.set_password(password)
        user.save()

        existing_profile = Applicant.objects.filter(
            email__iexact=user.email,
            user__isnull=True,
        ).first()

        if existing_profile is not None:
            existing_profile.user = user
            existing_profile.save(update_fields=["user", "updated_at"])

            if existing_profile.institution_id:
                user.institution_id = existing_profile.institution_id
                user.save(update_fields=["institution"])

        return user


class LogoutSerializer(serializers.Serializer):
    """Données requises pour la déconnexion."""

    refresh = serializers.CharField()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Authentification par adresse électronique."""

    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop("username", None)

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        token["role"] = user.role
        token["email"] = user.email
        token["institution_id"] = user.institution_id

        return token

    def validate(self, attrs):
        email = attrs.get("email", "").strip().lower()
        password = attrs.get("password")

        user = User.objects.filter(email__iexact=email).first()

        authenticated = None

        if user is not None:
            authenticated = authenticate(
                request=self.context.get("request"),
                username=user.username,
                password=password,
            )

        if authenticated is None:
            raise AuthenticationFailed(
                "Adresse électronique ou mot de passe incorrect.",
                code="authorization",
            )

        attrs["username"] = authenticated.username

        data = super().validate(attrs)

        data["user"] = UserSerializer(self.user).data

        return data


class ActivityLogSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(
        source="user.email",
        read_only=True,
        default=None,
    )

    action_display = serializers.CharField(
        source="get_action_display",
        read_only=True,
    )

    institution_name = serializers.CharField(
        source="institution.name",
        read_only=True,
        default=None,
    )

    class Meta:
        model = ActivityLog
        fields = [
            "id",
            "user",
            "user_email",
            "institution",
            "institution_name",
            "action",
            "action_display",
            "entity_type",
            "entity_id",
            "description",
            "metadata",
            "ip_address",
            "created_at",
        ]
        read_only_fields = fields


class FeatureFlagSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeatureFlag
        fields = [
            "id",
            "key",
            "name",
            "description",
            "is_enabled",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]
