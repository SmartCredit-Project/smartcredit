from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class FinancialInstitution(models.Model):
    """Institution financière cliente de la plateforme SmartCredit."""

    name = models.CharField(
        "nom",
        max_length=150,
        unique=True,
    )

    code = models.CharField(
        "code",
        max_length=30,
        unique=True,
        help_text="Identifiant court et stable de l'institution.",
    )

    email = models.EmailField(
        "adresse électronique",
        blank=True,
    )

    phone = models.CharField(
        "téléphone",
        max_length=30,
        blank=True,
    )

    address = models.TextField(
        "adresse",
        blank=True,
    )

    is_active = models.BooleanField(
        "institution active",
        default=True,
    )

    created_at = models.DateTimeField(
        "date de création",
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        "date de mise à jour",
        auto_now=True,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "institution financière"
        verbose_name_plural = "institutions financières"

    def __str__(self):
        return f"{self.name} ({self.code})"


class User(AbstractUser):
    """
    Utilisateur de la plateforme SmartCredit.

    Quatre rôles sont disponibles :
    - SUPERADMIN   : administrateur global de la plateforme.
    - ADMIN        : administrateur d'une institution financière.
    - CREDIT_AGENT : agent de crédit d'une institution.
    - APPLICANT    : demandeur de crédit.
    """

    class Role(models.TextChoices):
        SUPERADMIN = "SUPERADMIN", "Super administrateur"
        ADMIN = "ADMIN", "Administrateur d'institution"
        CREDIT_AGENT = "CREDIT_AGENT", "Agent de crédit"
        APPLICANT = "APPLICANT", "Demandeur de crédit"

    email = models.EmailField(
        "adresse électronique",
        unique=True,
    )

    role = models.CharField(
        "rôle",
        max_length=20,
        choices=Role.choices,
        default=Role.APPLICANT,
    )

    institution = models.ForeignKey(
        FinancialInstitution,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        verbose_name="institution",
        help_text=(
            "Institution de rattachement pour les administrateurs "
            "et les agents de crédit."
        ),
    )

    REQUIRED_FIELDS = ["email"]

    class Meta:
        ordering = ["-date_joined"]
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()

        if not self.username:
            self.username = self.email

        if self.is_superuser:
            self.role = self.Role.SUPERADMIN

        super().save(*args, **kwargs)

    @property
    def is_superadmin(self):
        return bool(self.is_superuser or self.role == self.Role.SUPERADMIN)

    @property
    def is_institution_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_credit_agent(self):
        return self.role == self.Role.CREDIT_AGENT

    @property
    def is_applicant(self):
        return self.role == self.Role.APPLICANT

    @property
    def is_staff_role(self):
        return bool(
            self.is_superadmin or self.is_institution_admin or self.is_credit_agent
        )


class ActivityLog(models.Model):
    """Journal des actions sensibles effectuées sur la plateforme."""

    class Action(models.TextChoices):
        LOGIN = "LOGIN", "Connexion"
        LOGOUT = "LOGOUT", "Déconnexion"
        REGISTERED = "REGISTERED", "Inscription"
        CREATED = "CREATED", "Création"
        UPDATED = "UPDATED", "Modification"
        DELETED = "DELETED", "Suppression"
        DEACTIVATED = "DEACTIVATED", "Désactivation"
        ASSIGNED = "ASSIGNED", "Affectation"
        STATUS_CHANGED = "STATUS_CHANGED", "Changement d'état"
        PREDICTION = "PREDICTION", "Prédiction"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_logs",
        verbose_name="utilisateur",
    )

    institution = models.ForeignKey(
        FinancialInstitution,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_logs",
        verbose_name="institution",
    )

    action = models.CharField(
        "action",
        max_length=30,
        choices=Action.choices,
        db_index=True,
    )

    entity_type = models.CharField(
        "type d'entité",
        max_length=60,
        blank=True,
    )

    entity_id = models.PositiveBigIntegerField(
        "identifiant de l'entité",
        null=True,
        blank=True,
    )

    description = models.TextField(
        "description",
        blank=True,
    )

    metadata = models.JSONField(
        "métadonnées",
        default=dict,
        blank=True,
    )

    ip_address = models.GenericIPAddressField(
        "adresse IP",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        "date de création",
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "journal d'activité"
        verbose_name_plural = "journaux d'activité"

    def __str__(self):
        return f"{self.get_action_display()} " f"({self.entity_type}#{self.entity_id})"


class FeatureFlag(models.Model):
    """Activation/désactivation d'une fonctionnalité de la plateforme."""

    key = models.CharField(
        "clé",
        max_length=60,
        unique=True,
    )

    name = models.CharField(
        "nom",
        max_length=150,
    )

    description = models.TextField(
        "description",
        blank=True,
    )

    is_enabled = models.BooleanField(
        "activée",
        default=True,
    )

    created_at = models.DateTimeField(
        "date de création",
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        "date de mise à jour",
        auto_now=True,
    )

    class Meta:
        ordering = ["key"]
        verbose_name = "drapeau de fonctionnalité"
        verbose_name_plural = "drapeaux de fonctionnalité"

    def __str__(self):
        return f"{self.key} ({'activée' if self.is_enabled else 'désactivée'})"
