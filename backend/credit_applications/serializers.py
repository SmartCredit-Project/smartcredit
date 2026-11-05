from rest_framework import serializers

from accounts.models import User

from .models import CreditApplication


class CreditApplicationSerializer(serializers.ModelSerializer):
    applicant_name = serializers.CharField(
        source="applicant.full_name",
        read_only=True,
    )

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    institution_name = serializers.CharField(
        source="institution.name",
        read_only=True,
        default=None,
    )

    assigned_agent_email = serializers.CharField(
        source="assigned_agent.email",
        read_only=True,
        default=None,
    )

    class Meta:
        model = CreditApplication
        fields = [
            "id",
            "applicant",
            "applicant_name",
            "institution",
            "institution_name",
            "person_age",
            "person_income",
            "person_home_ownership",
            "person_emp_length",
            "loan_intent",
            "loan_amnt",
            "loan_percent_income",
            "loan_grade",
            "loan_int_rate",
            "cb_person_default_on_file",
            "cb_person_cred_hist_length",
            "status",
            "status_display",
            "created_by",
            "assigned_agent",
            "assigned_agent_email",
            "assigned_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "institution",
            "loan_percent_income",
            "status",
            "created_by",
            "assigned_agent",
            "assigned_at",
            "created_at",
            "updated_at",
        ]

    def validate_applicant(self, value):
        requester = self.context.get("request")
        user = requester.user if requester else None

        if user and user.is_applicant:
            if value.user_id != user.id:
                raise serializers.ValidationError(
                    "Vous ne pouvez créer une demande que pour "
                    "votre propre profil."
                )

        return value

    def validate_person_age(self, value):
        if value < 18 or value > 100:
            raise serializers.ValidationError(
                "L'âge doit être compris entre 18 et 100 ans."
            )

        return value

    def validate_person_income(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Le revenu annuel doit être strictement positif."
            )

        return value

    def validate_loan_amnt(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Le montant du crédit doit être strictement positif."
            )

        return value

    def validate_person_emp_length(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError(
                "L'ancienneté professionnelle ne peut pas être négative."
            )

        return value

    def validate(self, attrs):
        age = attrs.get(
            "person_age",
            getattr(self.instance, "person_age", None),
        )

        employment_length = attrs.get(
            "person_emp_length",
            getattr(self.instance, "person_emp_length", None),
        )

        if (
            age is not None
            and employment_length is not None
            and employment_length > (age - 14)
        ):
            raise serializers.ValidationError(
                {
                    "person_emp_length": (
                        "L'ancienneté professionnelle est "
                        "incohérente avec l'âge indiqué."
                    )
                }
            )

        return attrs


class CreditApplicationStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=CreditApplication.Status.choices,
    )

    def validate_status(self, value):
        allowed_transitions = {
            CreditApplication.Status.PENDING: {
                CreditApplication.Status.IN_ANALYSIS,
                CreditApplication.Status.REJECTED,
            },
            CreditApplication.Status.IN_ANALYSIS: {
                CreditApplication.Status.ANALYZED,
                CreditApplication.Status.ACCEPTED,
                CreditApplication.Status.REJECTED,
            },
            CreditApplication.Status.ANALYZED: {
                CreditApplication.Status.ACCEPTED,
                CreditApplication.Status.REJECTED,
            },
            CreditApplication.Status.ACCEPTED: set(),
            CreditApplication.Status.REJECTED: set(),
        }

        current_status = self.context["application"].status

        if value == current_status:
            return value

        if value not in allowed_transitions[current_status]:
            raise serializers.ValidationError(
                (
                    f"Transition impossible de "
                    f"'{current_status}' vers '{value}'."
                )
            )

        return value


class CreditApplicationAssignSerializer(serializers.Serializer):
    assigned_agent = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(
            role=User.Role.CREDIT_AGENT,
            is_active=True,
        ),
        required=False,
        allow_null=True,
    )

    def validate_assigned_agent(self, value):
        if value is None:
            return value

        application = self.context["application"]

        if application.institution_id is None:
            raise serializers.ValidationError(
                "La demande n'est rattachée à aucune institution."
            )

        if value.institution_id != application.institution_id:
            raise serializers.ValidationError(
                "L'agent doit appartenir à l'institution de la demande."
            )

        return value
