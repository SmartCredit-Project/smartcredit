from .models import ActivityLog, FeatureFlag


def get_client_ip(request):
    if request is None:
        return None

    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")

    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    return request.META.get("REMOTE_ADDR")


def log_activity(
    *,
    action,
    user=None,
    institution=None,
    entity_type="",
    entity_id=None,
    description="",
    metadata=None,
    request=None,
):
    """Enregistre une action dans le journal d'activité."""

    if institution is None and user is not None:
        institution = getattr(user, "institution", None)

    return ActivityLog.objects.create(
        user=user,
        institution=institution,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
        metadata=metadata or {},
        ip_address=get_client_ip(request),
    )


def is_feature_enabled(key, default=True):
    """Retourne l'état d'un drapeau, avec une valeur par défaut."""

    flag = FeatureFlag.objects.filter(key=key).first()

    if flag is None:
        return default

    return flag.is_enabled
