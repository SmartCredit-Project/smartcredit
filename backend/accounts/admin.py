from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .forms import EmailAdminAuthenticationForm
from .models import ActivityLog, FeatureFlag, FinancialInstitution, User

admin.site.login_form = EmailAdminAuthenticationForm


@admin.register(FinancialInstitution)
class FinancialInstitutionAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "name",
        "code",
        "email",
        "is_active",
        "created_at",
    ]

    list_filter = ["is_active", "created_at"]

    search_fields = ["name", "code", "email"]


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        "username",
        "email",
        "first_name",
        "last_name",
        "role",
        "institution",
        "is_active",
        "date_joined",
    ]

    list_filter = [
        "role",
        "institution",
        "is_active",
        "is_staff",
        "is_superuser",
    ]

    search_fields = [
        "username",
        "email",
        "first_name",
        "last_name",
    ]

    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "SmartCredit",
            {"fields": ("role", "institution")},
        ),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (
            "SmartCredit",
            {"fields": ("email", "role", "institution")},
        ),
    )


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "action",
        "user",
        "institution",
        "entity_type",
        "entity_id",
        "created_at",
    ]

    list_filter = [
        "action",
        "institution",
        "entity_type",
        "created_at",
    ]

    search_fields = [
        "user__email",
        "description",
    ]

    readonly_fields = [
        "user",
        "institution",
        "action",
        "entity_type",
        "entity_id",
        "description",
        "metadata",
        "ip_address",
        "created_at",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(FeatureFlag)
class FeatureFlagAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "key",
        "name",
        "is_enabled",
        "updated_at",
    ]

    list_filter = ["is_enabled"]

    search_fields = ["key", "name"]
