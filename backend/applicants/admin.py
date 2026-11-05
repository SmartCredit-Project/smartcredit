from django.contrib import admin

from .models import Applicant


@admin.register(Applicant)
class ApplicantAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "first_name",
        "last_name",
        "email",
        "phone",
        "institution",
        "annual_income",
        "created_at",
    ]

    list_filter = ["institution", "created_at"]

    search_fields = [
        "first_name",
        "last_name",
        "email",
        "phone",
    ]

    raw_id_fields = ["user", "institution"]
