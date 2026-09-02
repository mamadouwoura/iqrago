"""Cohérence du graphe pédagogique et de l'admin de contenu."""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import Client

from apps.catalog.models import Course, Lesson, Module, Skill, SkillPrerequisite

User = get_user_model()


@pytest.fixture
def parcours(db):
    course = Course.objects.create(code="course.1", title_fr="Lire l'arabe")
    module = Module.objects.create(
        code="m1", course=course, title_fr="Le noyau libre", day_start=1, day_end=7
    )
    return course, module


# ---------------------------------------------------------------- prérequis


@pytest.mark.django_db
def test_prerequis_ne_peut_pas_boucler_sur_lui_meme(parcours):
    course, _ = parcours
    s = Skill.objects.create(id="letter.ba.sound", course=course, type=Skill.Type.LETTER_SOUND)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            SkillPrerequisite.objects.create(skill=s, requires=s)


@pytest.mark.django_db
def test_prerequis_unique(parcours):
    course, _ = parcours
    a = Skill.objects.create(id="a", course=course, type=Skill.Type.LETTER_SOUND)
    b = Skill.objects.create(id="b", course=course, type=Skill.Type.LETTER_RECOGNIZE)
    SkillPrerequisite.objects.create(skill=a, requires=b)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            SkillPrerequisite.objects.create(skill=a, requires=b)


# ------------------------------------------------------------------- leçons


@pytest.mark.django_db
def test_lecon_refuse_un_module_d_un_autre_parcours(parcours):
    course, module = parcours
    autre = Course.objects.create(code="course.2", title_fr="Textes")
    lecon = Lesson(course=autre, module=module, day_number=1, title_fr="x")
    with pytest.raises(ValidationError, match="n'appartient pas"):
        lecon.full_clean()


@pytest.mark.django_db
def test_lecon_refuse_un_jour_hors_plage_du_module(parcours):
    course, module = parcours  # module J1-7
    lecon = Lesson(course=course, module=module, day_number=12, title_fr="x")
    with pytest.raises(ValidationError, match="hors de la plage"):
        lecon.full_clean()


@pytest.mark.django_db
def test_un_seul_jour_par_parcours(parcours):
    course, module = parcours
    Lesson.objects.create(course=course, module=module, day_number=1, title_fr="a")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Lesson.objects.create(course=course, module=module, day_number=1, title_fr="b")


# ------------------------------------------------------------------- import


@pytest.mark.django_db
def test_import_du_socle_est_idempotent(volumes):
    """Réimporter ne doit pas dupliquer : c'est ce qui permet de retravailler
    les fichiers source sans repartir d'une base vide."""
    call_command("importer_contenu", verbosity=0)
    compte = (Skill.objects.count(), SkillPrerequisite.objects.count(), Lesson.objects.count())

    call_command("importer_contenu", verbosity=0)
    assert (
        Skill.objects.count(), SkillPrerequisite.objects.count(), Lesson.objects.count()
    ) == compte

    assert compte[0] == volumes['nb_competences'], (
        "la base doit refléter content/competences.json"
    )
    assert Lesson.objects.filter(is_free=True).count() == 3, "jours 1 à 3 gratuits"


@pytest.mark.django_db
def test_import_respecte_zero_surprise():
    """Aucun prérequis ne doit être introduit APRÈS la compétence qui en
    dépend. C'est la règle « zéro surprise », vérifiée ici sur les données
    réellement en base et non sur le fichier."""
    call_command("importer_contenu", verbosity=0)
    fautifs = [
        f"{lien.skill_id} (J{lien.skill.introduced_on_day}) "
        f"← {lien.requires_id} (J{lien.requires.introduced_on_day})"
        for lien in SkillPrerequisite.objects.select_related("skill", "requires")
        if lien.skill.introduced_on_day is not None
        and lien.requires.introduced_on_day is not None
        and lien.requires.introduced_on_day > lien.skill.introduced_on_day
    ]
    assert not fautifs, "prérequis introduits trop tard : " + "; ".join(fautifs[:5])


# -------------------------------------------------------------------- admin


PAGES = [
    "/admin/catalog/course/",
    "/admin/catalog/module/",
    "/admin/catalog/skill/",
    "/admin/catalog/lesson/",
    "/admin/catalog/exercise/",
    "/admin/catalog/media/",
    "/admin/catalog/contentversion/",
    "/admin/catalog/contentversion/add/",
]


@pytest.fixture
def admin_client(db):
    User.objects.create_superuser(email="admin@example.com", password="motdepasse-solide-1")
    c = Client()
    assert c.login(username="admin@example.com", password="motdepasse-solide-1")
    return c


@pytest.mark.django_db
@pytest.mark.parametrize("url", PAGES)
def test_page_admin_catalogue_repond(admin_client, url):
    assert admin_client.get(url).status_code == 200, f"{url} ne se charge pas"


@pytest.mark.django_db
def test_admin_liste_les_competences_importees(admin_client):
    call_command("importer_contenu", verbosity=0)
    body = admin_client.get("/admin/catalog/skill/").content.decode()
    assert "letter.ba.sound" in body
