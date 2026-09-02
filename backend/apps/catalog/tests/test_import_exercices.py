"""Import des brouillons d'exercices.

Deux garanties : l'import n'écrit jamais de doublon, et il ne publie jamais
rien. La publication reste une décision éditoriale, pas un effet de bord.
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.catalog.models import ContentVersion, Exercise

User = get_user_model()
MDP = "motdepasse-solide-1"


@pytest.fixture
def socle(db):
    call_command("importer_contenu", verbosity=0)


@pytest.fixture
def equipe(db):
    return User.objects.create_superuser(email="equipe@example.com", password=MDP)


@pytest.mark.django_db
def test_import_cree_des_brouillons(socle, equipe):
    call_command("importer_exercices", verbosity=0)

    assert Exercise.objects.exists(), "aucun exercice importé"
    assert ContentVersion.objects.exists(), "aucun lot créé"
    assert not ContentVersion.objects.exclude(
        state=ContentVersion.State.DRAFT
    ).exists(), "l'import ne doit RIEN publier"
    assert not Exercise.objects.filter(content_version__isnull=True).exists(), (
        "tout exercice importé doit appartenir à un lot relisible"
    )


@pytest.mark.django_db
def test_import_est_idempotent(socle, equipe):
    call_command("importer_exercices", verbosity=0)
    n, lots = Exercise.objects.count(), ContentVersion.objects.count()

    call_command("importer_exercices", verbosity=0)
    assert Exercise.objects.count() == n, "réimporter a créé des doublons"
    assert ContentVersion.objects.count() == lots


@pytest.mark.django_db
def test_import_ne_touche_pas_un_lot_publie(socle, equipe):
    """Un lot publié est immuable. L'import doit le contourner, pas échouer :
    sinon un seul lot publié bloquerait toute la production suivante."""
    relecteur = User.objects.create_user(email="relecteur@example.com", password=MDP)
    call_command("importer_exercices", verbosity=0)

    version = ContentVersion.objects.filter(exercises__isnull=False).distinct().first()
    titre_avant = version.label
    version.soumettre()
    version.valider(par=relecteur)
    version.publier()
    n_avant = version.exercises.count()

    call_command("importer_exercices", verbosity=0)

    version.refresh_from_db()
    assert version.state == ContentVersion.State.PUBLISHED
    assert version.label == titre_avant
    assert version.exercises.count() == n_avant


@pytest.mark.django_db
def test_import_exige_un_compte_dequipe(socle):
    """Un lot doit avoir un auteur : sans lui, la règle « l'auteur ne valide
    pas son propre contenu » n'a plus de sens."""
    with pytest.raises(CommandError, match="compte d'équipe"):
        call_command("importer_exercices", verbosity=0)


@pytest.mark.django_db
def test_import_refuse_un_auteur_inconnu(socle, equipe):
    with pytest.raises(CommandError, match="Aucun compte"):
        call_command("importer_exercices", auteur="fantome@example.com", verbosity=0)


@pytest.mark.django_db
def test_lot_par_jour_et_non_par_exercice(socle, equipe):
    """L'unité de relecture est le lot : relire 888 exercices un par un est
    impraticable, et un relecteur qui ne peut pas finir valide sans lire."""
    call_command("importer_exercices", verbosity=0)
    lots = ContentVersion.objects.count()
    assert lots <= 30, f"{lots} lots — un par jour de parcours au plus"
    assert Exercise.objects.count() > lots * 5, "un lot doit grouper plusieurs exercices"
