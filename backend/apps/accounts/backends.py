"""Connexion par e-mail ou par téléphone.

`ModelBackend` n'interroge que `USERNAME_FIELD`. Comme il vaut `email`, un
compte créé avec un numéro et sans adresse serait impossible à ouvrir — alors
même que le modèle l'autorise depuis l'étape 5. Ce backend comble l'écart.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

User = get_user_model()


class EmailOuTelephoneBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        identifiant = username or kwargs.get("email") or kwargs.get("identifier")
        if not identifiant or not password:
            return None

        identifiant = identifiant.strip()
        try:
            user = User.objects.get(
                Q(email__iexact=identifiant) | Q(phone=identifiant), deleted_at__isnull=True
            )
        except User.DoesNotExist:
            # Hacher quand même : sans cela, un identifiant inexistant répond
            # plus vite qu'un mot de passe faux, ce qui permet d'énumérer les
            # comptes au chronomètre.
            User().set_password(password)
            return None
        except User.MultipleObjectsReturned:
            # Ne devrait pas arriver — email et phone sont uniques — mais une
            # ambiguïté ne doit jamais ouvrir une session.
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
