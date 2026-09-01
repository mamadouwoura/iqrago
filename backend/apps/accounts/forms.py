"""Formulaires d'administration du compte.

Les formulaires par défaut de Django reposent sur un champ `username` que notre
modèle n'a pas : l'identifiant est un e-mail **ou** un téléphone. Sans ces deux
sous-classes, le formulaire d'ajout de l'admin échoue silencieusement — il
affiche la page et ne crée rien.
"""

from django import forms
from django.contrib.auth.forms import BaseUserCreationForm
from django.contrib.auth.forms import UserChangeForm as DjangoUserChangeForm

from .models import User


class IdentifiantMixin(forms.ModelForm):
    """Normalise les identifiants et impose qu'il y en ait au moins un."""

    def clean_email(self):
        # Une chaîne vide n'est pas « pas d'e-mail » : deux comptes sans
        # e-mail se heurteraient à la contrainte d'unicité sur ''.
        return (self.cleaned_data.get("email") or "").strip().lower() or None

    def clean_phone(self):
        return (self.cleaned_data.get("phone") or "").strip() or None

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("email") and not cleaned.get("phone"):
            raise forms.ValidationError(
                "Renseigne au moins une adresse e-mail ou un numéro de téléphone : "
                "un compte sans identifiant est irrécupérable."
            )
        return cleaned


class UserCreationForm(IdentifiantMixin, BaseUserCreationForm):
    class Meta(BaseUserCreationForm.Meta):
        model = User
        fields = ("email", "phone")


class UserChangeForm(IdentifiantMixin, DjangoUserChangeForm):
    class Meta(DjangoUserChangeForm.Meta):
        model = User
        fields = (
            "email", "phone", "interface_language", "is_active", "is_staff",
            "is_superuser", "groups", "user_permissions", "deleted_at",
        )
