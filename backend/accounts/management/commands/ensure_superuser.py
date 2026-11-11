import os

from accounts.models import User
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = (
        "Crée le super administrateur défini par DJANGO_SUPERUSER_EMAIL et "
        "DJANGO_SUPERUSER_PASSWORD s'il n'existe pas. Commande idempotente."
    )

    def handle(self, *args, **options):
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "").strip().lower()
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")

        if not email or not password:
            self.stdout.write(
                "Super administrateur ignoré : "
                "DJANGO_SUPERUSER_EMAIL et DJANGO_SUPERUSER_PASSWORD "
                "doivent être définis."
            )
            return

        first_name = os.environ.get("DJANGO_SUPERUSER_FIRST_NAME", "").strip()
        last_name = os.environ.get("DJANGO_SUPERUSER_LAST_NAME", "").strip()
        reset_password = os.environ.get(
            "DJANGO_SUPERUSER_RESET_PASSWORD",
            "",
        ).lower() in {"1", "true", "yes"}
        password_updated = False

        with transaction.atomic():
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "username": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "role": User.Role.SUPERADMIN,
                    "is_staff": True,
                    "is_superuser": True,
                    "is_active": True,
                },
            )

            if created:
                user.set_password(password)
                user.save()
                password_updated = True
            else:
                was_superadmin = user.is_superadmin
                changed_fields = []

                for field, value in {
                    "role": User.Role.SUPERADMIN,
                    "is_staff": True,
                    "is_superuser": True,
                    "is_active": True,
                }.items():
                    if getattr(user, field) != value:
                        setattr(user, field, value)
                        changed_fields.append(field)

                if not was_superadmin or reset_password:
                    user.set_password(password)
                    changed_fields.append("password")
                    password_updated = True

                if changed_fields:
                    user.save(update_fields=changed_fields)

        if created:
            self.stdout.write(
                self.style.SUCCESS(f"Super administrateur {email} créé avec succès.")
            )
        elif password_updated:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Compte {email} promu super administrateur "
                    "avec le mot de passe fourni."
                )
            )
        else:
            self.stdout.write(
                f"Super administrateur {email} déjà présent. "
                "Le mot de passe n'a pas été modifié."
            )
