from django import forms
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import get_user_model


class EmailAdminAuthenticationForm(AdminAuthenticationForm):
    """Formulaire de connexion à l'admin Django par email."""

    username = forms.EmailField(
        label="Adresse électronique",
        widget=forms.EmailInput(
            attrs={
                "autofocus": True,
                "autocomplete": "email",
            }
        ),
    )

    error_messages = {
        **AdminAuthenticationForm.error_messages,
        "invalid_login": (
            "Saisissez une adresse électronique et un mot de passe "
            "valides. Les deux champs sont sensibles à la casse."
        ),
    }

    def clean(self):
        email = self.cleaned_data.get("username")

        if email:
            user = get_user_model().objects.filter(email__iexact=email).first()

            if user is not None:
                self.cleaned_data["username"] = user.username

        return super().clean()
