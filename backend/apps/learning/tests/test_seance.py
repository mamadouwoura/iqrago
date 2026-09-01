"""Composition de séance et synchronisation.

Les cas limites comptent plus que le cas nominal : jour 1 sans historique,
retour après quinze jours d'absence, lot rejoué après une coupure.
"""

import uuid
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog.models import Exercise, Skill
from apps.learning import composition, services
from apps.learning.models import ExerciseAttempt, MasteryState, SessionRun
from apps.profiles.models import Profile

User = get_user_model()
MDP = "motdepasse-solide-1"
N = MasteryState.Level


@pytest.fixture
def socle(db):
    call_command("importer_contenu", verbosity=0)


@pytest.fixture
def apprenant(db):
    u = User.objects.create_user(email="apprenant@example.com", password=MDP)
    Profile.objects.create(user=u, daily_minutes=15, current_day=1)
    return u


def _maitriser(user, ids, niveau=N.SOLIDE, due=None):
    for sid in ids:
        MasteryState.objects.update_or_create(
            user=user, skill_id=sid, defaults={"level": niveau, "due_at": due}
        )


# ------------------------------------------------------------- composition


@pytest.mark.django_db
def test_jour_1_ne_propose_que_des_nouveautes(socle, apprenant):
    s = composition.composer(apprenant, jour=1, minutes=15)
    blocs = {b["kind"]: b for b in s["blocks"]}
    assert blocs["review"]["skills"] == [], "aucun historique au jour 1"
    assert blocs["new"]["skills"], "le jour 1 doit introduire quelque chose"


@pytest.mark.django_db
def test_verrou_de_prerequis(socle, apprenant):
    """Une syllabe n'est jamais introduite avant que sa lettre soit solide."""
    ouvrables = composition.competences_ouvrables(apprenant, jour=30)
    ids = {s.id for s in ouvrables}
    assert "letter.dal.recognize" in ids
    assert "syllable.dal.fatha" not in ids, (
        "la syllabe exige letter.dal.sound au niveau 3"
    )

    _maitriser(apprenant, ["letter.dal.recognize", "letter.dal.sound", "haraka.fatha"])
    ids = {s.id for s in composition.competences_ouvrables(apprenant, jour=30)}
    assert "syllable.dal.fatha" in ids, "prérequis acquis : la syllabe s'ouvre"


@pytest.mark.django_db
def test_prerequis_fragile_ne_suffit_pas(socle, apprenant):
    _maitriser(apprenant, ["letter.dal.recognize", "letter.dal.sound", "haraka.fatha"],
               niveau=N.FRAGILE)
    ids = {s.id for s in composition.competences_ouvrables(apprenant, jour=30)}
    assert "syllable.dal.fatha" not in ids, "niveau 2 n'ouvre pas, il faut 3"


@pytest.mark.django_db
def test_plafond_protege_apres_une_longue_absence(socle, apprenant):
    """Quinze jours d'absence ne doivent pas produire une séance de 40 minutes.

    Les cartes en retard attendent leur tour — jamais affichées comme une
    dette, qui est la première cause d'abandon des applications à répétition
    espacée.
    """
    hier = timezone.localdate() - timedelta(days=1)
    _maitriser(apprenant, [s.id for s in Skill.objects.all()[:80]], N.FRAGILE, due=hier)

    s = composition.composer(apprenant, jour=10, minutes=15)
    assert s["planned_items"] <= composition.CRENEAUX[15]
    revisions = next(b for b in s["blocks"] if b["kind"] == "review")["skills"]
    assert len(revisions) <= int(composition.CRENEAUX[15] * composition.PART_REVISION_MAX)


@pytest.mark.django_db
def test_plancher_reserve_des_places_aux_revisions(socle, apprenant):
    """Une journée chargée en nouveautés ne doit pas faire taire la mémoire."""
    hier = timezone.localdate() - timedelta(days=1)
    _maitriser(apprenant, ["letter.dal.recognize", "letter.dhal.recognize"],
               N.FRAGILE, due=hier)

    s = composition.composer(apprenant, jour=20, minutes=10)
    revisions = next(b for b in s["blocks"] if b["kind"] == "review")["skills"]
    assert len(revisions) >= composition.RESERVE_MINIMALE


@pytest.mark.django_db
def test_taille_suit_le_temps_declare(socle, apprenant):
    tailles = {
        m: composition.composer(apprenant, jour=15, minutes=m)["planned_items"]
        for m in (10, 30)
    }
    assert tailles[10] < tailles[30]
    assert tailles[30] <= composition.CRENEAUX[30]


@pytest.mark.django_db
def test_lecture_composee_uniquement_de_lacquis(socle, apprenant):
    """Zéro surprise : un mot ne s'affiche pas si l'une de ses lettres n'a
    jamais été montrée."""
    s = composition.composer(apprenant, jour=3, minutes=15)
    lecture = next(b for b in s["blocks"] if b["kind"] == "reading")["skills"]
    assert lecture == [], "au jour 1 rien n'est acquis : aucune lecture possible"

    mot = Skill.objects.get(id="word.warad")
    _maitriser(apprenant, [p.id for p in mot.prerequisites.all()], N.FRAGILE)
    s = composition.composer(apprenant, jour=3, minutes=15)
    lecture = next(b for b in s["blocks"] if b["kind"] == "reading")["skills"]
    assert lecture, "tous les atomes connus : le mot devient lisible"


@pytest.mark.django_db
def test_seance_sans_exercice_reste_valide(socle, apprenant):
    """La base ne contient aucun exercice : la séance doit se composer
    quand même. Le moteur travaille sur des compétences ; les exercices ne
    sont que leur habillage."""
    s = composition.composer(apprenant, jour=1, minutes=15)
    items = [i for b in s["blocks"] for i in b["items"]]
    assert items, "des compétences sont proposées"
    assert all(i["exercise"] is None for i in items)


@pytest.mark.django_db
def test_exercice_rattache_quand_il_existe(socle, apprenant):
    skill = Skill.objects.get(id="letter.dal.recognize")
    Exercise.objects.create(
        skill=skill, type=Exercise.Type.FAMILY_ODD_ONE_OUT, payload={"options": ["د", "ذ"]}
    )
    s = composition.composer(apprenant, jour=1, minutes=15)
    item = next(
        i for b in s["blocks"] for i in b["items"] if i["skill_id"] == "letter.dal.recognize"
    )
    assert item["exercise"]["type"] == "family_odd_one_out"


# ---------------------------------------------------------- synchronisation


def _tentative(skill_id, juste=True, latence=900, client_id=None):
    return {
        "client_id": client_id or uuid.uuid4(),
        "skill_id": skill_id,
        "is_correct": juste,
        "latency_ms": latence,
        "answered_at": timezone.now(),
    }


@pytest.mark.django_db
def test_synchro_cree_les_maitrises(socle, apprenant):
    r = services.synchroniser(
        apprenant, day_number=1,
        attempts=[_tentative("letter.dal.recognize"), _tentative("letter.dhal.recognize")],
    )
    assert r["accepted"] == 2 and r["duplicates"] == 0
    assert MasteryState.objects.filter(user=apprenant).count() == 2
    assert MasteryState.objects.get(
        user=apprenant, skill_id="letter.dal.recognize"
    ).level == N.DECOUVERTE


@pytest.mark.django_db
def test_lot_rejoue_nest_ecrit_quune_fois(socle, apprenant):
    """Le pivot du mode hors ligne : un lot renvoyé après une coupure ne doit
    pas faire progresser deux fois."""
    lot = [_tentative("letter.dal.recognize"), _tentative("letter.dhal.recognize")]

    premier = services.synchroniser(apprenant, day_number=1, attempts=lot)
    second = services.synchroniser(apprenant, day_number=1, attempts=lot)

    assert premier["accepted"] == 2
    assert second["accepted"] == 0 and second["duplicates"] == 2
    assert ExerciseAttempt.objects.count() == 2
    assert MasteryState.objects.get(
        user=apprenant, skill_id="letter.dal.recognize"
    ).level == N.DECOUVERTE, "le niveau n'a pas monté deux fois"


@pytest.mark.django_db
def test_hesitation_detectee_par_le_serveur(socle, apprenant):
    seuil = Skill.objects.get(id="letter.dal.recognize").latency_threshold_ms
    services.synchroniser(
        apprenant, day_number=1,
        attempts=[_tentative("letter.dal.recognize", latence=seuil + 1000)],
    )
    a = ExerciseAttempt.objects.get()
    assert a.is_hesitation and a.level_before == a.level_after


@pytest.mark.django_db
def test_serveur_recalcule_et_ignore_le_niveau_du_client(socle, apprenant):
    """Une application modifiée ne doit pas pouvoir s'attribuer la maîtrise."""
    t = _tentative("letter.dal.recognize", juste=False)
    t["level_after"] = 4  # tentative de triche
    services.synchroniser(apprenant, day_number=1, attempts=[t])
    assert MasteryState.objects.get(user=apprenant).level == N.DECOUVERTE


@pytest.mark.django_db
def test_serie_compte_les_jours_pas_les_seances(socle, apprenant):
    for _ in range(3):
        services.synchroniser(
            apprenant, day_number=1, attempts=[_tentative("letter.dal.recognize")]
        )
    apprenant.profile.refresh_from_db()
    assert apprenant.profile.streak_days == 1, "trois séances le même jour valent un jour"


@pytest.mark.django_db
def test_abandon_enregistre_son_index(socle, apprenant):
    services.synchroniser(
        apprenant, day_number=1, attempts=[_tentative("letter.dal.recognize")],
        abandoned_at_index=3,
    )
    assert SessionRun.objects.get().abandoned_at_index == 3


# ---------------------------------------------------------------------- API


@pytest.fixture
def api(db, apprenant):
    c = APIClient()
    r = c.post("/api/v1/auth/login",
               {"identifier": "apprenant@example.com", "password": MDP}, format="json")
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['tokens']['access']}")
    return c


@pytest.mark.django_db
def test_api_seance_du_jour(socle, api):
    r = api.get("/api/v1/session/today")
    assert r.status_code == 200, r.data
    assert r.data["day_number"] == 1
    assert [b["kind"] for b in r.data["blocks"]] == ["review", "new", "practice", "reading"]


@pytest.mark.django_db
def test_api_seance_refusee_au_dela_du_gratuit(socle, api, apprenant):
    Profile.objects.filter(user=apprenant).update(current_day=8)
    r = api.get("/api/v1/session/today")
    assert r.status_code == 403
    assert r.data["error"]["code"] == "entitlement_required"


@pytest.mark.django_db
def test_api_synchro_puis_apercu(socle, api):
    cid = str(uuid.uuid4())
    lot = {
        "day_number": 1,
        "attempts": [{
            "client_id": cid, "skill_id": "letter.dal.recognize",
            "is_correct": True, "latency_ms": 800,
            "answered_at": timezone.now().isoformat(),
        }],
    }
    r = api.post("/api/v1/session/sync", lot, format="json")
    assert r.status_code == 200, r.data
    assert r.data["accepted"] == 1 and r.data["streak_days"] == 1

    # Rejeu du même lot : accepté, mais rien n'est réécrit.
    r2 = api.post("/api/v1/session/sync", lot, format="json")
    assert r2.data["accepted"] == 0 and r2.data["duplicates"] == 1

    apercu = api.get("/api/v1/progress/overview")
    assert apercu.data["skills_started"] == 1
    assert apercu.data["accuracy_pct"] == 100
    assert apercu.data["skills_total"] == 283


@pytest.mark.django_db
def test_api_refuse_un_client_id_repete_dans_le_lot(socle, api):
    cid = str(uuid.uuid4())
    t = {"client_id": cid, "skill_id": "letter.dal.recognize", "is_correct": True,
         "latency_ms": 800, "answered_at": timezone.now().isoformat()}
    r = api.post("/api/v1/session/sync", {"day_number": 1, "attempts": [t, t]}, format="json")
    assert r.status_code == 400
