from django.db.models import Q


def scope_users(queryset, user):
    """Portée des utilisateurs selon le rôle."""

    if user.is_superadmin:
        return queryset

    if user.is_institution_admin:
        if not user.institution_id:
            return queryset.none()

        return queryset.filter(institution_id=user.institution_id)

    return queryset.filter(pk=user.pk)


def scope_applicants(queryset, user):
    """Portée des demandeurs selon le rôle."""

    if user.is_superadmin:
        return queryset

    if user.is_institution_admin:
        if not user.institution_id:
            return queryset.none()

        return queryset.filter(institution_id=user.institution_id)

    if user.is_credit_agent:
        if not user.institution_id:
            return queryset.none()

        return queryset.filter(
            Q(institution_id=user.institution_id)
            & (
                Q(created_by=user)
                | Q(credit_applications__created_by=user)
                | Q(credit_applications__assigned_agent=user)
            )
        ).distinct()

    return queryset.filter(user=user)


def scope_credit_applications(queryset, user):
    """Portée des demandes de crédit selon le rôle."""

    if user.is_superadmin:
        return queryset

    if user.is_institution_admin:
        if not user.institution_id:
            return queryset.none()

        return queryset.filter(institution_id=user.institution_id)

    if user.is_credit_agent:
        if not user.institution_id:
            return queryset.none()

        return queryset.filter(
            Q(institution_id=user.institution_id)
            & (Q(created_by=user) | Q(assigned_agent=user))
        )

    return queryset.filter(applicant__user=user)


def scope_predictions(queryset, user):
    """Portée des prédictions selon le rôle."""

    if user.is_superadmin:
        return queryset

    if user.is_institution_admin:
        if not user.institution_id:
            return queryset.none()

        return queryset.filter(institution_id=user.institution_id)

    if user.is_credit_agent:
        if not user.institution_id:
            return queryset.none()

        return queryset.filter(
            Q(institution_id=user.institution_id)
            & (
                Q(credit_application__created_by=user)
                | Q(credit_application__assigned_agent=user)
            )
        )

    return queryset.filter(credit_application__applicant__user=user)
