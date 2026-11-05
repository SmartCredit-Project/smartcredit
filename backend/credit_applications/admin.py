from django.contrib import admin

from .models import CreditApplication


@admin.register(CreditApplication)
class CreditApplicationAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "applicant",
        "loan_amnt",
        "loan_intent",
        "status",
        "institution",
        "assigned_agent",
        "created_at",
    ]

    list_filter = [
        "status",
        "institution",
        "loan_intent",
        "person_home_ownership",
        "created_at",
    ]

    search_fields = [
        "applicant__first_name",
        "applicant__last_name",
        "applicant__email",
    ]

    raw_id_fields = [
        "applicant",
        "created_by",
        "institution",
        "assigned_agent",
    ]

    readonly_fields = [
        "loan_percent_income",
        "created_at",
        "updated_at",
    ]
