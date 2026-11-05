from django.conf import settings
from django.db import models


class CreditApplication(models.Model):
    """Demande de crédit soumise par un demandeur."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "En attente"
        IN_ANALYSIS = "IN_ANALYSIS", "En cours d'analyse"
        ANALYZED = "ANALYZED", "Analysée"
        ACCEPTED = "ACCEPTED", "Acceptée"
        REJECTED = "REJECTED", "Refusée"

    class HomeOwnership(models.TextChoices):
        RENT = "RENT", "Locataire"
        OWN = "OWN", "Propriétaire"
        MORTGAGE = "MORTGAGE", "Prêt hypothécaire"
        OTHER = "OTHER", "Autre"

    class LoanIntent(models.TextChoices):
        PERSONAL = "PERSONAL", "Personnel"
        EDUCATION = "EDUCATION", "Éducation"
        MEDICAL = "MEDICAL", "Médical"
        VENTURE = "VENTURE", "Création d'entreprise"
        HOMEIMPROVEMENT = "HOMEIMPROVEMENT", "Amélioration de l'habitat"
        DEBTCONSOLIDATION = "DEBTCONSOLIDATION", "Consolidation de dettes"

    class LoanGrade(models.TextChoices):
        A = "A", "A"
        B = "B", "B"
        C = "C", "C"
        D = "D", "D"
        E = "E", "E"
        F = "F", "F"
        G = "G", "G"

    class YesNo(models.TextChoices):
        YES = "Y", "Oui"
        NO = "N", "Non"

    applicant = models.ForeignKey(
        "applicants.Applicant",
        on_delete=models.PROTECT,
        related_name="credit_applications",
        verbose_name="demandeur",
    )

    institution = models.ForeignKey(
        "accounts.FinancialInstitution",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="credit_applications",
        verbose_name="institution",
    )

    # --------------------------------------------------------
    # Caractéristiques utilisées par le pipeline final
    # --------------------------------------------------------

    person_age = models.PositiveSmallIntegerField(
        "âge du demandeur",
    )

    person_income = models.FloatField(
        "revenu annuel",
    )

    person_home_ownership = models.CharField(
        "type de logement",
        max_length=20,
        choices=HomeOwnership.choices,
    )

    person_emp_length = models.FloatField(
        "ancienneté professionnelle (années)",
        null=True,
        blank=True,
    )

    loan_intent = models.CharField(
        "objet du crédit",
        max_length=30,
        choices=LoanIntent.choices,
    )

    loan_amnt = models.FloatField(
        "montant demandé",
    )

    loan_percent_income = models.FloatField(
        "ratio crédit / revenu",
        editable=False,
        default=0,
    )

    # --------------------------------------------------------
    # Informations complémentaires (non utilisées par le
    # modèle actuel, conservées pour l'évolution du système)
    # --------------------------------------------------------

    loan_grade = models.CharField(
        "note du crédit",
        max_length=1,
        choices=LoanGrade.choices,
        blank=True,
    )

    loan_int_rate = models.FloatField(
        "taux d'intérêt",
        null=True,
        blank=True,
    )

    cb_person_default_on_file = models.CharField(
        "défaut enregistré au bureau de crédit",
        max_length=1,
        choices=YesNo.choices,
        blank=True,
    )

    cb_person_cred_hist_length = models.FloatField(
        "ancienneté historique de crédit (années)",
        null=True,
        blank=True,
    )

    # --------------------------------------------------------
    # Suivi de la demande
    # --------------------------------------------------------

    status = models.CharField(
        "état de la demande",
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_credit_applications",
    )

    assigned_agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_credit_applications",
        verbose_name="agent assigné",
    )

    assigned_at = models.DateTimeField(
        "date d'affectation",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        "date de soumission",
        auto_now_add=True,
        db_index=True,
    )

    updated_at = models.DateTimeField(
        "date de mise à jour",
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "demande de crédit"
        verbose_name_plural = "demandes de crédit"

    def __str__(self):
        return (
            f"Demande #{self.pk} - {self.applicant} "
            f"({self.get_status_display()})"
        )

    def save(self, *args, **kwargs):
        if self.person_income and self.person_income > 0:
            self.loan_percent_income = (
                self.loan_amnt / self.person_income
            )
        else:
            self.loan_percent_income = 0

        super().save(*args, **kwargs)

    def get_model_features(self):
        """Retourne les caractéristiques attendues par le modèle."""

        return {
            "person_age": self.person_age,
            "person_income": self.person_income,
            "person_home_ownership": self.person_home_ownership,
            "person_emp_length": self.person_emp_length,
            "loan_intent": self.loan_intent,
            "loan_amnt": self.loan_amnt,
            "loan_percent_income": self.loan_percent_income,
        }
