"""Tests du modèle User.

Ils vérifient les quatre garanties qui, si elles cèdent, cassent le produit :
inscription par e-mail, inscription par téléphone, refus d'un compte sans
aucun identifiant, et hachage Argon2 effectif.
"""

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

User = get_user_model()


@pytest.mark.django_db
def test_creation_par_email():
    u = User.objects.create_user(email="Mamadou@Example.COM", password="motdepasse-solide-1")
    assert u.email == "mamadou@example.com", "l'e-mail doit être normalisé en minuscules"
    assert u.phone is None
    assert u.is_active is True
    assert u.is_staff is False


@pytest.mark.django_db
def test_creation_par_telephone_sans_email():
    """La cible principale n'a pas toujours d'e-mail actif. Exiger une adresse
    couperait le tunnel d'inscription."""
    u = User.objects.create_user(phone="+221771234567", password="motdepasse-solide-1")
    assert u.phone == "+221771234567"
    assert u.email is None


@pytest.mark.django_db
def test_refus_sans_aucun_identifiant():
    with pytest.raises(ValueError):
        User.objects.create_user(password="motdepasse-solide-1")


@pytest.mark.django_db
def test_contrainte_base_refuse_email_et_phone_nuls():
    """La règle doit tenir en base, pas seulement dans le gestionnaire : un
    compte créé par une autre voie ne doit pas pouvoir contourner le contrôle."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            User.objects.create(email=None, phone=None, password="x")


@pytest.mark.django_db
def test_mot_de_passe_hache_en_argon2():
    u = User.objects.create_user(email="a@example.com", password="motdepasse-solide-1")
    assert u.password.startswith("argon2$"), f"haché avec {u.password.split('$')[0]}"
    assert u.check_password("motdepasse-solide-1")
    assert not u.check_password("mauvais")


@pytest.mark.django_db
def test_email_unique():
    User.objects.create_user(email="a@example.com", password="motdepasse-solide-1")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            User.objects.create_user(email="a@example.com", password="motdepasse-solide-2")


@pytest.mark.django_db
def test_cle_primaire_est_un_uuid():
    u = User.objects.create_user(email="a@example.com", password="motdepasse-solide-1")
    assert not isinstance(u.pk, int), "un entier séquentiel révélerait le nombre d'inscrits"
    assert len(str(u.pk)) == 36


@pytest.mark.django_db
def test_superutilisateur():
    u = User.objects.create_superuser(email="admin@example.com", password="motdepasse-solide-1")
    assert u.is_staff and u.is_superuser


@pytest.mark.django_db
def test_suppression_logique():
    u = User.objects.create_user(email="a@example.com", password="motdepasse-solide-1")
    u.soft_delete()
    u.refresh_from_db()
    assert u.is_deleted and not u.is_active
