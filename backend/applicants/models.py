from django.conf import settings
from django.db import models


class Applicant(models.Model):
    """Demandeur de crédit."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applicant_profile",
        help_text=(
            "Compte utilisateur associé au demandeur, "
            "lorsque celui-ci consulte ses propres demandes."
        ),
    )

    institution = models.ForeignKey(
        "accounts.FinancialInstitution",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applicants",
        verbose_name="institution",
    )

    first_name = models.CharField(
        "prénom",
        max_length=100,
    )

    last_name = models.CharField(
        "nom",
        max_length=100,
    )

    email = models.EmailField(
        "adresse électronique",
        unique=True,
    )

    phone = models.CharField(
        "téléphone",
        max_length=30,
        blank=True,
    )

    date_of_birth = models.DateField(
        "date de naissance",
        null=True,
        blank=True,
    )

    occupation = models.CharField(
        "profession",
        max_length=150,
        blank=True,
    )

    employer = models.CharField(
        "employeur",
        max_length=150,
        blank=True,
    )

    financial_situation = models.TextField(
        "situation financière",
        blank=True,
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
        ordering = ["-created_at"]
        verbose_name = "demandeur"
        verbose_name_plural = "demandeurs"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
