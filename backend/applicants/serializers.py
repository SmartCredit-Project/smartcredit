from rest_framework import serializers

from .models import Applicant


class ApplicantSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(
        read_only=True,
    )

    user = serializers.PrimaryKeyRelatedField(
        read_only=True,
    )

    institution_name = serializers.CharField(
        source="institution.name",
        read_only=True,
        default=None,
    )

    class Meta:
        model = Applicant
        fields = [
            "id",
            "user",
            "institution",
            "institution_name",
            "first_name",
            "last_name",
            "full_name",
            "email",
            "phone",
            "date_of_birth",
            "occupation",
            "employer",
            "financial_situation",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "created_at",
            "updated_at",
        ]

    def validate_email(self, value):
        query = Applicant.objects.filter(email__iexact=value)

        if self.instance:
            query = query.exclude(pk=self.instance.pk)

        if query.exists():
            raise serializers.ValidationError(
                "Un demandeur possède déjà cette adresse."
            )

        return value

    def validate_date_of_birth(self, value):
        from django.utils import timezone

        if value and value > timezone.localdate():
            raise serializers.ValidationError(
                "La date de naissance ne peut pas être future."
            )

        return value
