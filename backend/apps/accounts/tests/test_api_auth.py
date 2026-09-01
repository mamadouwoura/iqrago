"""API d'authentification.

Le point qui compte : un compte créé avec un numéro et sans e-mail doit
pouvoir se connecter. Le modèle l'autorise depuis l'étape 5, mais
`authenticate()` ne regardait que `USERNAME_FIELD`.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()
MDP = "motdepasse-solide-1"


@pytest.fixture
def api():
    return APIClient()


# ------------------------------------------------------------- inscription


@pytest.mark.django_db
def test_inscription_par_email(api):
    r = api.post("/api/v1/auth/register",
                 {"email": "Mamadou@Example.COM", "password": MDP}, format="json")
    assert r.status_code == 201, r.data
    assert r.data["user"]["email"] == "mamadou@example.com"
    assert r.data["tokens"]["access"] and r.data["tokens"]["refresh"]


@pytest.mark.django_db
def test_inscription_par_telephone(api):
    r = api.post("/api/v1/auth/register",
                 {"phone": "+221771234567", "password": MDP}, format="json")
    assert r.status_code == 201, r.data
    assert r.data["user"]["phone"] == "+221771234567"
    assert r.data["user"]["email"] is None


@pytest.mark.django_db
def test_inscription_sans_identifiant_refusee(api):
    r = api.post("/api/v1/auth/register", {"password": MDP}, format="json")
    assert r.status_code == 400
    assert "identifiant" in r.data


@pytest.mark.django_db
def test_inscription_mot_de_passe_faible_refusee(api):
    r = api.post("/api/v1/auth/register",
                 {"email": "a@example.com", "password": "12345678"}, format="json")
    assert r.status_code == 400
    assert "password" in r.data


@pytest.mark.django_db
def test_inscription_email_deja_pris(api):
    User.objects.create_user(email="a@example.com", password=MDP)
    r = api.post("/api/v1/auth/register",
                 {"email": "A@Example.com", "password": MDP}, format="json")
    assert r.status_code == 400, "la casse ne doit pas permettre un doublon"


# ---------------------------------------------------------------- connexion


@pytest.mark.django_db
def test_connexion_par_email(api):
    User.objects.create_user(email="a@example.com", password=MDP)
    r = api.post("/api/v1/auth/login", {"identifier": "a@example.com", "password": MDP},
                 format="json")
    assert r.status_code == 200, r.data


@pytest.mark.django_db
def test_connexion_par_telephone(api):
    """Le cas que `ModelBackend` seul rendait impossible."""
    User.objects.create_user(phone="+221771234567", password=MDP)
    r = api.post("/api/v1/auth/login",
                 {"identifier": "+221771234567", "password": MDP}, format="json")
    assert r.status_code == 200, r.data


@pytest.mark.django_db
def test_connexion_insensible_a_la_casse(api):
    User.objects.create_user(email="a@example.com", password=MDP)
    r = api.post("/api/v1/auth/login", {"identifier": "A@EXAMPLE.COM", "password": MDP},
                 format="json")
    assert r.status_code == 200


@pytest.mark.django_db
def test_message_identique_compte_inconnu_et_mot_de_passe_faux(api):
    """Deux messages différents permettraient de savoir qui a un compte."""
    User.objects.create_user(email="a@example.com", password=MDP)
    inconnu = api.post("/api/v1/auth/login",
                       {"identifier": "inconnu@example.com", "password": MDP}, format="json")
    faux = api.post("/api/v1/auth/login",
                    {"identifier": "a@example.com", "password": "mauvais-mot-de-passe"},
                    format="json")
    assert inconnu.status_code == faux.status_code == 400
    assert str(inconnu.data) == str(faux.data)


@pytest.mark.django_db
def test_compte_supprime_ne_peut_plus_se_connecter(api):
    u = User.objects.create_user(email="a@example.com", password=MDP)
    u.soft_delete()
    r = api.post("/api/v1/auth/login", {"identifier": "a@example.com", "password": MDP},
                 format="json")
    assert r.status_code == 400


# -------------------------------------------------------------------- /me


@pytest.fixture
def utilisateur_connecte(db, api):
    u = User.objects.create_user(email="a@example.com", password=MDP)
    r = api.post("/api/v1/auth/login", {"identifier": "a@example.com", "password": MDP},
                 format="json")
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['tokens']['access']}")
    return u, r.data["tokens"]


@pytest.mark.django_db
def test_me_exige_un_jeton(api):
    assert api.get("/api/v1/me").status_code == 401


@pytest.mark.django_db
def test_me_lecture_et_modification(api, utilisateur_connecte):
    assert api.get("/api/v1/me").data["email"] == "a@example.com"
    r = api.patch("/api/v1/me", {"interface_language": "en"}, format="json")
    assert r.status_code == 200 and r.data["interface_language"] == "en"


@pytest.mark.django_db
def test_suppression_de_compte(api, utilisateur_connecte):
    u, _ = utilisateur_connecte
    assert api.delete("/api/v1/me").status_code == 204
    u.refresh_from_db()
    assert u.is_deleted and not u.is_active


@pytest.mark.django_db
def test_deconnexion_met_le_jeton_en_liste_noire(api, utilisateur_connecte):
    _, tokens = utilisateur_connecte
    assert api.post("/api/v1/auth/logout", {"refresh": tokens["refresh"]},
                    format="json").status_code == 205

    # Le jeton ne doit plus permettre d'en obtenir un nouveau : sans cela,
    # « se déconnecter » ne ferait qu'oublier le jeton côté client.
    r = APIClient().post("/api/v1/auth/refresh", {"refresh": tokens["refresh"]}, format="json")
    assert r.status_code == 401


# ---------------------------------------------------------- consentements


@pytest.mark.django_db
def test_consentement_historise_sans_ecraser(api, utilisateur_connecte):
    for accorde in (True, False):
        r = api.post("/api/v1/me/consents",
                     {"kind": "voice", "granted": accorde, "policy_version": "1.0"},
                     format="json")
        assert r.status_code == 201, r.data

    lignes = api.get("/api/v1/me/consents").data["results"]
    assert len(lignes) == 2, "retirer un consentement ajoute une ligne, n'en modifie pas"


@pytest.mark.django_db
def test_consentements_isoles_par_utilisateur(api, utilisateur_connecte):
    autre = User.objects.create_user(email="b@example.com", password=MDP)
    from apps.accounts.models import ConsentRecord
    ConsentRecord.objects.create(user=autre, kind="voice", granted=True, policy_version="1.0")
    assert api.get("/api/v1/me/consents").data["results"] == []


@pytest.mark.django_db
def test_limitation_de_debit_sur_la_connexion(api):
    """Cinq essais par minute : au-delà, 429.

    C'est la seule protection contre l'essai systématique de mots de passe sur
    un compte connu.
    """
    User.objects.create_user(email="a@example.com", password=MDP)
    codes = [
        api.post("/api/v1/auth/login",
                 {"identifier": "a@example.com", "password": "mauvais"},
                 format="json").status_code
        for _ in range(7)
    ]
    assert 429 in codes, f"aucune limitation déclenchée : {codes}"
    assert codes.count(400) == 5, f"le quota devrait être de 5 : {codes}"
