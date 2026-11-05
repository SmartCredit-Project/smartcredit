from django.contrib import admin

from .models import ModelVersion, Prediction


@admin.register(ModelVersion)
class ModelVersionAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "name",
        "version",
        "algorithm",
        "is_active",
        "created_at",
    ]

    list_filter = ["is_active", "created_at"]

    search_fields = ["name", "version", "algorithm"]


@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "credit_application",
        "predicted_class",
        "default_probability",
        "risk_level",
        "institution",
        "model_version",
        "created_at",
    ]

    list_filter = [
        "risk_level",
        "institution",
        "predicted_class",
        "model_version",
        "created_at",
    ]

    search_fields = [
        "credit_application__applicant__first_name",
        "credit_application__applicant__last_name",
    ]

    raw_id_fields = [
        "credit_application",
        "model_version",
        "created_by",
        "institution",
    ]

    readonly_fields = [
        "features",
        "created_at",
    ]
