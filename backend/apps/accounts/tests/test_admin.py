"""L'admin Django doit être réellement utilisable.

Ce n'est pas cosmétique : c'est l'interface par laquelle la personne en charge
du contenu travaillera. Un `ModelAdmin` qui référence un champ inexistant ne
casse qu'au chargement de la page — jamais au `manage.py check`. Ces tests
chargent donc les pages pour de bon.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

User = get_user_model()

PAGES = [
    "/admin/",
    "/admin/accounts/user/",
    "/admin/accounts/user/add/",
    "/admin/accounts/consentrecord/",
    "/admin/profiles/profile/",
    # Goal n'est pas enregistré séparément : il s'édite dans le profil, en ligne.
]


@pytest.fixture
def admin_client(db):
    User.objects.create_superuser(email="admin@example.com", password="motdepasse-solide-1")
    c = Client()
    assert c.login(username="admin@example.com", password="motdepasse-solide-1")
    return c


@pytest.mark.django_db
@pytest.mark.parametrize("url", PAGES)
def test_page_admin_repond(admin_client, url):
    assert admin_client.get(url).status_code == 200, f"{url} ne se charge pas"


@pytest.mark.django_db
def test_liste_utilisateurs_affiche_email_et_telephone(admin_client):
    User.objects.create_user(phone="+221771234567", password="motdepasse-solide-1")
    body = admin_client.get("/admin/accounts/user/").content.decode()
    assert "admin@example.com" in body
    assert "+221771234567" in body, "la colonne téléphone doit être visible"


@pytest.mark.django_db
def test_creation_utilisateur_depuis_admin(admin_client):
    r = admin_client.post(
        "/admin/accounts/user/add/",
        {
            "email": "nouveau@example.com",
            "phone": "",
            "password1": "motdepasse-solide-1",
            "password2": "motdepasse-solide-1",
        },
    )
    # Un formulaire refusé renvoie 200 en réaffichant ses erreurs ; un
    # formulaire accepté redirige. Remonter les erreurs rend l'échec lisible
    # au lieu d'un simple « l'objet n'existe pas ».
    erreurs = {}
    if r.status_code == 200 and r.context and "adminform" in r.context:
        erreurs = dict(r.context["adminform"].form.errors)
    assert r.status_code == 302, f"formulaire refusé : {erreurs}"
    assert User.objects.filter(email="nouveau@example.com").exists(), (
        "le formulaire d'ajout de l'admin ne crée pas l'utilisateur"
    )


@pytest.mark.django_db
def test_consentement_non_modifiable_depuis_admin(admin_client):
    """Un consentement est une trace juridique : il se consulte, il ne se
    réécrit pas. L'inline doit être en lecture seule et sans ajout."""
    from apps.accounts.admin import ConsentInline

    assert ConsentInline.can_delete is False
    from django.contrib import admin as dj_admin
    inline = ConsentInline(User, dj_admin.site)
    assert inline.has_add_permission(None) is False
    assert set(ConsentInline.readonly_fields) == {
        "kind", "granted", "policy_version", "granted_at",
    }


@pytest.mark.django_db
def test_health_sans_authentification():
    """La sonde doit répondre sans jeton : un orchestrateur ne s'authentifie pas."""
    assert Client().get("/api/v1/health").json() == {"status": "ok"}


def test_sonde_repond_base_injoignable(settings):
    """La sonde ne doit toucher aucune base.

    `ATOMIC_REQUESTS = True` ouvre une transaction sur chaque requête : sans
    `non_atomic_requests` sur la vue, une brève indisponibilité de PostgreSQL
    ferait échouer la sonde, l'orchestrateur tuerait des conteneurs sains, et
    un hoquet de la base deviendrait une panne du service.
    """
    from django.db import connections

    from config.urls import health

    assert getattr(health, "_non_atomic_requests", None), (
        "la vue health doit porter @transaction.non_atomic_requests"
    )
    # Et la vue elle-même ne fait aucune requête.
    with connections["default"].execute_wrapper(
        lambda *a: pytest.fail("la sonde a interrogé la base")
    ):
        from django.test import RequestFactory
        r = health(RequestFactory().get("/api/v1/health"))
    assert r.status_code == 200
