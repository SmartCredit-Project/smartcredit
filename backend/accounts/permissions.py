from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsSuperAdmin(BasePermission):
    """Réservé aux super administrateurs de la plateforme."""

    message = "Cette action est réservée au super administrateur."

    def has_permission(self, request, view):
        user = request.user

        return bool(
            user
            and user.is_authenticated
            and user.is_superadmin
        )


class IsAdminOrSuperAdmin(BasePermission):
    """Réservé aux administrateurs d'institution et au super admin."""

    message = (
        "Cette action est réservée aux administrateurs "
        "d'institution et au super administrateur."
    )

    def has_permission(self, request, view):
        user = request.user

        return bool(
            user
            and user.is_authenticated
            and (
                user.is_superadmin
                or user.is_institution_admin
            )
        )


class IsStaffRole(BasePermission):
    """Réservé aux super admins, admins et agents de crédit."""

    message = (
        "Cette action est réservée aux super administrateurs, "
        "aux administrateurs et aux agents de crédit."
    )

    def has_permission(self, request, view):
        user = request.user

        return bool(
            user
            and user.is_authenticated
            and user.is_staff_role
        )


class IsStaffRoleOrReadOnly(BasePermission):
    """Lecture pour tous les connectés, écriture pour le staff."""

    message = "La modification est réservée au personnel SmartCredit."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return True

        return user.is_staff_role


class IsSuperAdminOrReadOnly(BasePermission):
    """Lecture pour le staff, écriture réservée au super admin."""

    message = "La modification est réservée au super administrateur."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return user.is_staff_role

        return user.is_superadmin
