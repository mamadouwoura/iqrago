"""Synchronisation d'une séance.

Pivot du mode hors ligne (D2). Le lot est **idempotent** : renvoyé trois fois
après une coupure, il n'écrit qu'une fois. Sans cette garantie, une coupure au
mauvais moment ferait progresser un utilisateur deux fois.
"""

from django.db import transaction
from django.utils import timezone

from apps.catalog.models import Exercise, Skill

from . import srs
from .models import ExerciseAttempt, MasteryState, SessionRun


@transaction.atomic
def synchroniser(user, *, day_number, attempts, session_id=None, lesson_id=None,
                 started_at=None, completed_at=None, abandoned_at_index=None,
                 source=SessionRun.Source.ONLINE, aujourdhui=None):
    """Enregistre un lot de tentatives et recalcule les maîtrises.

    Le serveur recalcule les niveaux **lui-même** à partir des tentatives
    brutes. Il n'accepte jamais un niveau calculé par le client : une
    application modifiée pourrait sinon s'attribuer la maîtrise complète.
    """
    aujourdhui = aujourdhui or timezone.localdate()

    seance = SessionRun.objects.filter(id=session_id, user=user).first() if session_id else None
    if seance is None:
        seance = SessionRun.objects.create(
            user=user, day_number=day_number, lesson_id=lesson_id,
            started_at=started_at or timezone.now(), source=source,
        )
    if completed_at:
        seance.completed_at = completed_at
    seance.abandoned_at_index = abandoned_at_index

    # Déduplication : les client_id déjà reçus sont ignorés en silence. Ce
    # n'est pas une erreur, c'est le comportement normal d'un lot rejoué.
    deja_vus = set(
        ExerciseAttempt.objects.filter(
            client_id__in=[a["client_id"] for a in attempts]
        ).values_list("client_id", flat=True)
    )

    seuils = dict(Skill.objects.values_list("id", "latency_threshold_ms"))
    exercices_valides = set(
        Exercise.objects.filter(
            id__in=[a["exercise_id"] for a in attempts if a.get("exercise_id")]
        ).values_list("id", flat=True)
    )

    maitrises = {
        m.skill_id: m
        for m in MasteryState.objects.select_for_update().filter(
            user=user, skill_id__in={a["skill_id"] for a in attempts}
        )
    }

    nouvelles, acceptees, doublons = [], 0, 0
    for a in attempts:
        if a["client_id"] in deja_vus:
            doublons += 1
            continue

        maitrise = maitrises.get(a["skill_id"])
        if maitrise is None:
            maitrise = MasteryState(user=user, skill_id=a["skill_id"])
            maitrises[a["skill_id"]] = maitrise

        avant, apres, hesitation = srs.appliquer(
            maitrise,
            juste=a["is_correct"],
            latence_ms=a["latency_ms"],
            seuil_ms=seuils.get(a["skill_id"], 1500),
            aujourdhui=aujourdhui,
        )

        nouvelles.append(
            ExerciseAttempt(
                client_id=a["client_id"],
                session_run=seance,
                exercise_id=a.get("exercise_id") if a.get("exercise_id") in exercices_valides
                else None,
                skill_id=a["skill_id"],
                is_correct=a["is_correct"],
                latency_ms=a["latency_ms"],
                is_hesitation=hesitation,
                level_before=avant,
                level_after=apres,
                answered_at=a["answered_at"],
            )
        )
        acceptees += 1

    ExerciseAttempt.objects.bulk_create(nouvelles)
    for maitrise in maitrises.values():
        maitrise.save()

    seance.completed_items = seance.attempts.count()
    seance.planned_items = max(seance.planned_items, seance.completed_items)
    seance.save()

    _mettre_a_jour_serie(user, aujourdhui, acceptees)

    return {
        "session_id": str(seance.id),
        "accepted": acceptees,
        "duplicates": doublons,
        "mastery_updates": [
            {"skill_id": m.skill_id, "level": m.level,
             "due_at": m.due_at.isoformat() if m.due_at else None}
            for m in maitrises.values()
        ],
    }


def _mettre_a_jour_serie(user, aujourdhui, acceptees):
    """La série compte les jours de pratique, pas les séances.

    Quatre séances dans la même soirée valent un jour, comme une seule. Sinon
    elle mesurerait l'empressement au lieu de la régularité.
    """
    if not acceptees:
        return
    profil = getattr(user, "profile", None)
    if profil is None:
        return

    dernier = profil.last_session_date
    if dernier == aujourdhui:
        return
    if dernier and (aujourdhui - dernier).days == 1:
        profil.streak_days += 1
    else:
        # Repart à 1, sans écran d'échec et sans notification culpabilisante.
        profil.streak_days = 1
    profil.last_session_date = aujourdhui
    profil.save(update_fields=["streak_days", "last_session_date", "updated_at"])


def apercu_progression(user):
    """Les chiffres de l'écran d'accueil, en une requête."""
    from django.db.models import Avg, Count, Q, Sum

    stats = MasteryState.objects.filter(user=user).aggregate(
        total=Count("id"),
        acquises=Count("id", filter=Q(level__gte=MasteryState.Level.SOLIDE)),
        fragiles=Count("id", filter=Q(level__lt=MasteryState.Level.SOLIDE, level__gt=0)),
        latence=Avg("avg_latency_ms"),
        vues=Sum("seen_count"),
        justes=Sum("correct_count"),
    )
    profil = getattr(user, "profile", None)
    total_catalogue = Skill.objects.filter(course_id="course.1").count()
    vues, justes = stats["vues"] or 0, stats["justes"] or 0

    return {
        "current_day": profil.current_day if profil else 0,
        "streak_days": profil.streak_days if profil else 0,
        "skills_total": total_catalogue,
        "skills_started": stats["total"] or 0,
        "skills_mastered": stats["acquises"] or 0,
        "skills_fragile": stats["fragiles"] or 0,
        "progression_pct": round(100 * (stats["acquises"] or 0) / total_catalogue)
        if total_catalogue else 0,
        "accuracy_pct": round(100 * justes / vues) if vues else None,
        "avg_latency_ms": round(stats["latence"]) if stats["latence"] else None,
        "due_today": MasteryState.objects.filter(
            user=user, due_at__lte=timezone.localdate()
        ).count(),
    }
