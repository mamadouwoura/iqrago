"""Le cycle éditorial doit tenir, pas décorer.

Une machine à états qui accepte n'importe quelle transition n'en est pas une :
elle donne l'illusion d'un processus de validation là où il n'y en a aucun.
Ces tests vérifient qu'elle refuse.
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.catalog.models import ContentVersion, Course, Exercise, Skill

User = get_user_model()
S = ContentVersion.State


@pytest.fixture
def auteur(db):
    return User.objects.create_user(email="auteur@example.com", password="motdepasse-solide-1")


@pytest.fixture
def relecteur(db):
    return User.objects.create_user(email="relecteur@example.com", password="motdepasse-solide-1")


@pytest.fixture
def version(auteur):
    return ContentVersion.objects.create(label="Jour 8 — famille ٮ", author=auteur)


@pytest.fixture
def competence(db):
    course = Course.objects.create(code="course.1", title_fr="Lire l'arabe")
    return Skill.objects.create(
        id="letter.ba.sound", course=course, type=Skill.Type.LETTER_SOUND, arabic="ب"
    )


# ------------------------------------------------------------- transitions


def test_cycle_nominal(version, relecteur):
    assert version.state == S.DRAFT
    version.soumettre(reviewer=relecteur)
    assert version.state == S.REVIEW and version.submitted_at

    version.valider(par=relecteur)
    assert version.state == S.APPROVED and version.approved_by == relecteur

    version.publier()
    assert version.state == S.PUBLISHED and version.published_at


@pytest.mark.parametrize(
    "depuis,methode",
    [
        (S.DRAFT, "valider"),      # valider sans relecture
        (S.DRAFT, "publier"),      # publier un brouillon
        (S.REVIEW, "publier"),     # publier sans validation
        (S.PUBLISHED, "soumettre"),
        (S.APPROVED, "depublier"),
    ],
)
def test_transition_interdite(version, relecteur, depuis, methode):
    ContentVersion.objects.filter(pk=version.pk).update(state=depuis)
    version.refresh_from_db()
    kwargs = {"par": relecteur} if methode == "valider" else {}
    with pytest.raises(ValidationError):
        getattr(version, methode)(**kwargs)


def test_publier_saute_la_relecture_est_impossible(version):
    """Le raccourci que tout le monde prend quand il est pressé."""
    with pytest.raises(ValidationError):
        version.publier()
    version.refresh_from_db()
    assert version.state == S.DRAFT


# ------------------------------------------------- séparation auteur / valideur


def test_auteur_ne_valide_pas_son_contenu(version, auteur):
    version.soumettre()
    with pytest.raises(ValidationError, match="propre contenu"):
        version.valider(par=auteur)


@pytest.mark.django_db
def test_contrainte_base_refuse_auteur_valideur(auteur):
    """La règle tient aussi hors du code applicatif : un import ou un script
    ne doit pas pouvoir la contourner."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            ContentVersion.objects.create(
                label="x", author=auteur, approved_by=auteur, state=S.APPROVED
            )


# ------------------------------------------------------------- immuabilité


def test_contenu_publie_est_immuable(version, competence, relecteur):
    exercice = Exercise.objects.create(
        skill=competence, type=Exercise.Type.LETTER_TO_SOUND,
        payload={"options": []}, content_version=version,
    )
    version.soumettre()
    version.valider(par=relecteur)
    version.publier()

    exercice.refresh_from_db()
    exercice.difficulty = 5
    with pytest.raises(ValidationError, match="immuable"):
        exercice.save()


def test_contenu_en_brouillon_reste_modifiable(version, competence):
    exercice = Exercise.objects.create(
        skill=competence, type=Exercise.Type.LETTER_TO_SOUND,
        payload={}, content_version=version,
    )
    exercice.difficulty = 3
    exercice.save()
    exercice.refresh_from_db()
    assert exercice.difficulty == 3


def test_revision_duplique_dans_un_brouillon(version, competence, relecteur):
    Exercise.objects.create(
        skill=competence, type=Exercise.Type.LETTER_TO_SOUND,
        payload={"n": 1}, content_version=version,
    )
    version.soumettre()
    version.valider(par=relecteur)
    version.publier()

    revision = version.creer_revision(author=relecteur)
    assert revision.state == S.DRAFT
    assert revision.remplace == version
    assert revision.exercises.count() == 1

    # L'original n'a pas bougé : c'est tout l'intérêt.
    version.refresh_from_db()
    assert version.state == S.PUBLISHED
    assert version.exercises.count() == 1

    # Et la copie, elle, se modifie.
    copie = revision.exercises.first()
    copie.difficulty = 4
    copie.save()


def test_revision_impossible_sur_un_brouillon(version, relecteur):
    with pytest.raises(ValidationError):
        version.creer_revision(author=relecteur)


def test_renvoyer_en_brouillon_efface_la_validation(version, relecteur):
    version.soumettre()
    version.valider(par=relecteur)
    version.renvoyer_en_brouillon(motif="mot du jour 8 à revoir")
    assert version.state == S.DRAFT
    assert version.approved_by is None
    assert "jour 8" in version.notes


# ------------------------------------------------- révision d'une leçon publiée


@pytest.fixture
def parcours_min(db):
    from apps.catalog.models import Module

    course = Course.objects.create(code="course.1", title_fr="Lire l'arabe")
    module = Module.objects.create(
        code="m1", course=course, title_fr="Noyau", day_start=1, day_end=7
    )
    return course, module


def test_reviser_une_lecon_publiee(version, relecteur, parcours_min):
    """Le cas que la contrainte d'unicité (parcours, jour) interdisait :
    dupliquer une leçon pour la corriger."""
    from apps.catalog.models import Lesson

    course, module = parcours_min
    socle = Lesson.objects.create(
        course=course, module=module, day_number=3, title_fr="Le premier mot", is_live=True
    )
    lecon = Lesson.objects.create(
        course=course, module=module, day_number=3, title_fr="Le premier mot",
        content_version=version,
    )
    version.soumettre()
    version.valider(par=relecteur)
    version.publier()

    # La bascule a eu lieu : une seule leçon en ligne pour le jour 3.
    socle.refresh_from_db()
    lecon.refresh_from_db()
    assert lecon.is_live and not socle.is_live
    assert Lesson.objects.filter(course=course, day_number=3, is_live=True).count() == 1

    revision = version.creer_revision(author=relecteur)
    copie = revision.lessons.get()
    assert copie.day_number == 3
    assert not copie.is_live, "une révision non publiée ne doit pas être servie"

    # Trois leçons pour le jour 3, une seule en ligne : c'est l'objectif.
    assert Lesson.objects.filter(course=course, day_number=3).count() == 3
    assert Lesson.objects.filter(course=course, day_number=3, is_live=True).count() == 1


def test_depublier_retire_de_la_ligne(version, relecteur, parcours_min):
    from apps.catalog.models import Lesson

    course, module = parcours_min
    lecon = Lesson.objects.create(
        course=course, module=module, day_number=3, title_fr="x", content_version=version
    )
    version.soumettre()
    version.valider(par=relecteur)
    version.publier()
    version.depublier()

    lecon.refresh_from_db()
    assert not lecon.is_live
    assert Lesson.objects.filter(pk=lecon.pk).exists(), "dépublier ne supprime rien"
