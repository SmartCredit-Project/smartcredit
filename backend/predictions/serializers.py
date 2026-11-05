from rest_framework import serializers

from credit_applications.models import CreditApplication

from .models import ModelVersion, Prediction


class ModelVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelVersion
        fields = [
            "id",
            "name",
            "version",
            "algorithm",
            "accuracy",
            "precision",
            "recall",
            "roc_auc",
            "is_active",
            "created_at",
        ]
        read_only_fields = fields


class PredictionSerializer(serializers.ModelSerializer):
    model_version = ModelVersionSerializer(read_only=True)

    model_name = serializers.CharField(
        source="model_version.name",
        read_only=True,
    )

    prediction = serializers.IntegerField(
        source="predicted_class",
        read_only=True,
    )

    risk_level_display = serializers.CharField(
        source="get_risk_level_display",
        read_only=True,
    )

    message = serializers.CharField(read_only=True)

    institution_name = serializers.CharField(
        source="institution.name",
        read_only=True,
        default=None,
    )

    class Meta:
        model = Prediction
        fields = [
            "id",
            "credit_application",
            "institution",
            "institution_name",
            "prediction",
            "predicted_class",
            "default_probability",
            "no_default_probability",
            "risk_level",
            "risk_level_display",
            "message",
            "model_name",
            "model_version",
            "features",
            "created_by",
            "created_at",
        ]
        read_only_fields = fields


class PredictionRequestSerializer(serializers.Serializer):
    """
    Requête de prédiction.

    Deux modes sont supportés :
    - `credit_application` : utilise les caractéristiques enregistrées.
    - caractéristiques brutes : analyse ponctuelle sans demande.
    """

    credit_application = serializers.PrimaryKeyRelatedField(
        queryset=CreditApplication.objects.all(),
        required=False,
        allow_null=True,
    )

    person_age = serializers.IntegerField(
        min_value=18,
        max_value=100,
        required=False,
    )

    person_income = serializers.FloatField(
        min_value=0.000001,
        required=False,
    )

    person_home_ownership = serializers.ChoiceField(
        choices=CreditApplication.HomeOwnership.values,
        required=False,
    )

    person_emp_length = serializers.FloatField(
        min_value=0,
        allow_null=True,
        required=False,
        default=None,
    )

    loan_intent = serializers.ChoiceField(
        choices=CreditApplication.LoanIntent.values,
        required=False,
    )

    loan_amnt = serializers.FloatField(
        min_value=0.000001,
        required=False,
    )

    def validate(self, attrs):
        application = attrs.get("credit_application")

        if application is not None:
            return attrs

        required_features = [
            "person_age",
            "person_income",
            "person_home_ownership",
            "loan_intent",
            "loan_amnt",
        ]

        missing = [
            feature
            for feature in required_features
            if feature not in attrs
        ]

        if missing:
            raise serializers.ValidationError(
                {
                    "detail": (
                        "Fournissez une demande de crédit ou "
                        "les caractéristiques suivantes : "
                        f"{', '.join(missing)}."
                    )
                }
            )

        return attrs

    def get_features(self):
        application = self.validated_data.get(
            "credit_application"
        )

        if application is not None:
            return application.get_model_features()

        return {
            "person_age": self.validated_data["person_age"],
            "person_income": self.validated_data["person_income"],
            "person_home_ownership": (
                self.validated_data["person_home_ownership"]
            ),
            "person_emp_length": (
                self.validated_data.get("person_emp_length")
            ),
            "loan_intent": self.validated_data["loan_intent"],
            "loan_amnt": self.validated_data["loan_amnt"],
        }
