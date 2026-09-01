"""API du catalogue.

Deux garanties : jamais de contenu non publié, jamais de leçon payante servie
à un compte gratuit.
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.catalog.models import ContentVersion, Lesson

User = get_user_model()
MDP = "motdepasse-solide-1"


@pytest.fixture
def socle(db):
    call_command("importer_contenu", verbosity=0)


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def api_connectee(db, api):
    User.objects.create_user(email="a@example.com", password=MDP)
    r = api.post("/api/v1/auth/login", {"identifier": "a@example.com", "password": MDP},
                 format="json")
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['tokens']['access']}")
    return api


# ----------------------------------------------------------------- publics


@pytest.mark.django_db
def test_parcours_accessible_sans_compte(api, socle):
    r = api.get("/api/v1/courses")
    assert r.status_code == 200
    assert r.data[0]["code"] == "course.1"
    assert len(r.data[0]["modules"]) == 8


@pytest.mark.django_db
def test_programme_visible_sans_compte(api, socle):
    """La page de vente montre les trente jours ; l'API n'en sert que trois."""
    r = api.get("/api/v1/courses/course.1/programme")
    assert r.status_code == 200
    assert len(r.data) == 30
    assert sum(1 for j in r.data if j["is_free"]) == 3


# ------------------------------------------------------------------ leçons


@pytest.mark.django_db
def test_lecon_exige_un_compte(api, socle):
    assert api.get("/api/v1/courses/course.1/lessons/1").status_code == 401


@pytest.mark.django_db
def test_lecon_gratuite_servie(api_connectee, socle):
    r = api_connectee.get("/api/v1/courses/course.1/lessons/3")
    assert r.status_code == 200, r.data
    assert r.data["day_number"] == 3
    assert r.data["skills"], "la leçon doit porter ses nouveautés"


@pytest.mark.django_db
def test_lecon_payante_refusee(api_connectee, socle):
    r = api_connectee.get("/api/v1/courses/course.1/lessons/8")
    assert r.status_code == 403
    assert r.data["error"]["code"] == "entitlement_required"
    assert r.data["error"]["details"]["day"] == 8


@pytest.mark.django_db
def test_equipe_accede_a_tout(api, socle):
    User.objects.create_superuser(email="staff@example.com", password=MDP)
    r = api.post("/api/v1/auth/login", {"identifier": "staff@example.com", "password": MDP},
                 format="json")
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['tokens']['access']}")
    assert api.get("/api/v1/courses/course.1/lessons/8").status_code == 200


@pytest.mark.django_db
def test_lecon_hors_ligne_introuvable(api_connectee, socle):
    """Une leçon retirée de la ligne ne doit plus être servie, même si elle
    existe encore en base."""
    Lesson.objects.filter(course_id="course.1", day_number=1).update(is_live=False)
    assert api_connectee.get("/api/v1/courses/course.1/lessons/1").status_code == 404


@pytest.mark.django_db
def test_brouillon_jamais_servi(api_connectee, socle):
    """Le test qui compte : un contenu en cours d'écriture ne doit pas fuiter
    vers les apprenants."""
    auteur = User.objects.create_user(email="auteur@example.com", password=MDP)
    version = ContentVersion.objects.create(label="Jour 3 — brouillon", author=auteur)
    socle_j3 = Lesson.objects.get(course_id="course.1", day_number=3, content_version=None)
    Lesson.objects.create(
        course=socle_j3.course, module=socle_j3.module, day_number=3,
        title_fr="TITRE EN COURS D'ECRITURE", content_version=version, is_free=True,
    )
    r = api_connectee.get("/api/v1/courses/course.1/lessons/3")
    assert r.status_code == 200
    assert r.data["title_fr"] != "TITRE EN COURS D'ECRITURE"


# ------------------------------------------------------- compétences, médias


@pytest.mark.django_db
def test_graphe_des_competences(api_connectee, socle):
    r = api_connectee.get("/api/v1/skills")
    assert r.status_code == 200
    assert len(r.data) == 283
    syllabe = next(c for c in r.data if c["id"] == "syllable.dal.fatha")
    assert set(syllabe["prerequisites"]) == {"letter.dal.sound", "haraka.fatha"}


@pytest.mark.django_db
def test_competences_filtrables_par_jour(api_connectee, socle):
    r = api_connectee.get("/api/v1/skills?jusqu_au_jour=3")
    assert all(c["introduced_on_day"] <= 3 for c in r.data)
    assert len(r.data) < 283


@pytest.mark.django_db
def test_manifeste_des_medias(api_connectee, socle):
    r = api_connectee.get("/api/v1/media/manifest")
    assert r.status_code == 200
    assert len(r.data) == 158
    assert all(m["bundled"] for m in r.data)


# ---------------------------------------------------------------- onboarding


@pytest.mark.django_db
def test_onboarding_puis_profil(api_connectee):
    r = api_connectee.post(
        "/api/v1/onboarding",
        {"declared_level": "zero", "daily_minutes": 15,
         "goals": ["read_arabic", "read_texts"]},
        format="json",
    )
    assert r.status_code == 201, r.data
    assert set(r.data["goals"]) == {"read_arabic", "read_texts"}

    profil = api_connectee.get("/api/v1/profile")
    assert profil.status_code == 200
    assert profil.data["daily_minutes"] == 15
    assert profil.data["current_day"] == 0


@pytest.mark.django_db
def test_repasser_l_onboarding_remplace_les_objectifs(api_connectee):
    for objectifs in (["read_arabic", "read_texts"], ["read_faster"]):
        api_connectee.post(
            "/api/v1/onboarding",
            {"declared_level": "zero", "daily_minutes": 20, "goals": objectifs},
            format="json",
        )
    r = api_connectee.get("/api/v1/profile")
    assert r.data["goals"] == ["read_faster"], "les objectifs se remplacent, ne se cumulent pas"


@pytest.mark.django_db
def test_profil_absent_avant_onboarding(api_connectee):
    r = api_connectee.get("/api/v1/profile")
    assert r.status_code == 404
    assert r.data["error"]["code"] == "onboarding_requis"
