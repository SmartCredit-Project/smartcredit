from credit_applications.models import CreditApplication
from rest_framework import serializers

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

    result = serializers.SerializerMethodField()

    default_probability_percentage = serializers.SerializerMethodField()

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
            "result",
            "default_probability",
            "default_probability_percentage",
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

    def get_result(self, obj) -> str:
        if obj.predicted_class == 1:
            return "DEFAULT_RISK_DETECTED"

        return "NO_DEFAULT_RISK"

    def get_default_probability_percentage(self, obj) -> float:
        return round(obj.default_probability * 100, 2)


class PredictionRequestSerializer(serializers.Serializer):
    """Requête de prédiction basée sur une demande enregistrée."""

    credit_application = serializers.PrimaryKeyRelatedField(
        queryset=CreditApplication.objects.all(),
    )

    def validate_credit_application(self, application):
        if application.person_income is None or application.person_income <= 0:
            raise serializers.ValidationError(
                "Le revenu annuel doit être strictement positif."
            )

        if application.loan_amnt is None or application.loan_amnt <= 0:
            raise serializers.ValidationError(
                "Le montant du crédit doit être strictement positif."
            )

        return application
