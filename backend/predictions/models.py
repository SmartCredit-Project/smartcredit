from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class ModelVersion(models.Model):
    """Version d'un modèle de Machine Learning utilisé."""

    name = models.CharField(
        "nom du modèle",
        max_length=150,
    )

    version = models.CharField(
        "version",
        max_length=50,
    )

    algorithm = models.CharField(
        "algorithme",
        max_length=150,
        blank=True,
    )

    accuracy = models.FloatField(
        "accuracy",
        null=True,
        blank=True,
    )

    precision = models.FloatField(
        "precision",
        null=True,
        blank=True,
    )

    recall = models.FloatField(
        "recall",
        null=True,
        blank=True,
    )

    roc_auc = models.FloatField(
        "ROC AUC",
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(
        "version active",
        default=False,
    )

    created_at = models.DateTimeField(
        "date de création",
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-is_active", "-created_at"]
        verbose_name = "version de modèle"
        verbose_name_plural = "versions de modèle"
        constraints = [
            models.UniqueConstraint(
                fields=["name", "version"],
                name="unique_model_name_version",
            )
        ]

    def __str__(self):
        return f"{self.name} v{self.version}"


class Prediction(models.Model):
    """Résultat d'une analyse de risque de crédit."""

    class RiskLevel(models.TextChoices):
        LOW = "LOW", "Risque faible"
        MEDIUM = "MEDIUM", "Risque modéré"
        HIGH = "HIGH", "Risque élevé"

    credit_application = models.ForeignKey(
        "credit_applications.CreditApplication",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="predictions",
        verbose_name="demande de crédit",
    )

    institution = models.ForeignKey(
        "accounts.FinancialInstitution",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="predictions",
        verbose_name="institution",
    )

    predicted_class = models.PositiveSmallIntegerField(
        "classe prédite",
    )

    default_probability = models.FloatField(
        "probabilité de défaut",
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1),
        ],
    )

    no_default_probability = models.FloatField(
        "probabilité d'absence de défaut",
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1),
        ],
    )

    risk_level = models.CharField(
        "niveau de risque",
        max_length=10,
        choices=RiskLevel.choices,
        db_index=True,
    )

    model_version = models.ForeignKey(
        ModelVersion,
        on_delete=models.PROTECT,
        related_name="predictions",
        verbose_name="version du modèle",
    )

    features = models.JSONField(
        "caractéristiques analysées",
        default=dict,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="predictions",
    )

    created_at = models.DateTimeField(
        "date de prédiction",
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "prédiction"
        verbose_name_plural = "prédictions"

    def __str__(self):
        return (
            f"Prédiction #{self.pk} - "
            f"{self.get_risk_level_display()}"
        )

    @property
    def message(self):
        messages = {
            self.RiskLevel.LOW: (
                "Risque faible de défaut de remboursement."
            ),
            self.RiskLevel.MEDIUM: (
                "Risque modéré de défaut de remboursement."
            ),
            self.RiskLevel.HIGH: (
                "Risque élevé de défaut de remboursement."
            ),
        }

        return messages.get(
            self.risk_level,
            "Risque non déterminé.",
        )
