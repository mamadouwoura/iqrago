"""Composition de la séance du jour.

Le principe du §10 du cahier des charges, traduit en une contrainte de code :

    Aucun écran ne demande « quelle est la leçon suivante ? ».
    Il demande « quelles compétences sont dues, et laquelle est prête ? ».

Le serveur compose ; le client n'implémente aucune pédagogie. C'est ce qui
permet d'ajuster le moteur sans publier une nouvelle version de l'application.
"""

from django.db.models import Q
from django.utils import timezone

from apps.catalog.models import ContentVersion, Exercise, Lesson, Skill

from .models import MasteryState

# Nombre d'items par séance, selon le temps déclaré à l'onboarding.
CRENEAUX = {10: 10, 15: 14, 20: 18, 30: 26}

PART_REVISION_MAX = 0.50   # plafond : une longue absence ne fait pas une séance de 40 min
PART_REVISION_MIN = 0.30   # plancher : les révisions ne sont jamais totalement évincées
RESERVE_MINIMALE = 2       # places gardées tant qu'une carte est due

NIVEAU_PREREQUIS = MasteryState.Level.SOLIDE   # 3 — pour introduire une nouveauté
NIVEAU_ATOME = MasteryState.Level.FRAGILE      # 2 — pour composer un item


def _niveaux(user):
    return dict(
        MasteryState.objects.filter(user=user).values_list("skill_id", "level")
    )


def competences_dues(user, aujourdhui=None):
    """Les cartes à revoir, les plus fragiles d'abord."""
    aujourdhui = aujourdhui or timezone.localdate()
    return list(
        MasteryState.objects.filter(user=user, due_at__lte=aujourdhui)
        .select_related("skill")
        .order_by("level", "due_at")
    )


def competences_ouvrables(user, jour, course_id="course.1", niveaux=None):
    """Les nouveautés dont tous les prérequis sont acquis.

    Le verrou de prérequis est appliqué ici, pas dans le contenu : une
    compétence n'est jamais introduite si un de ses prérequis est sous le
    niveau 3.
    """
    niveaux = _niveaux(user) if niveaux is None else niveaux
    candidates = (
        Skill.objects.filter(course_id=course_id, introduced_on_day__lte=jour)
        .exclude(id__in=[s for s, n in niveaux.items() if n > 0])
        .prefetch_related("prerequisites")
        .order_by("introduced_on_day", "difficulty", "id")
    )
    return [
        s for s in candidates
        if all(niveaux.get(p.id, 0) >= NIVEAU_PREREQUIS for p in s.prerequisites.all())
    ]


def _atomes_connus(skill, niveaux):
    """Zéro surprise : tous les atomes d'un item composé doivent être au moins
    fragiles. Un mot ne s'affiche pas si l'une de ses lettres n'a jamais été
    montrée — c'est l'expérience la plus décourageante du débutant."""
    return all(niveaux.get(p.id, 0) >= NIVEAU_ATOME for p in skill.prerequisites.all())


def _exercices_pour(skills, exclure_ids=()):
    """Un exercice **publié** par compétence, le plus facile d'abord.

    Le filtre sur l'état de la version est la moitié qui compte : sans lui, un
    exercice en cours d'écriture atteint un apprenant. C'est précisément ce que
    le cycle éditorial existe pour empêcher, et un exercice sans version n'a
    jamais été relu du tout.
    """
    if not skills:
        return {}
    qs = (
        Exercise.objects.filter(
            skill_id__in=[s.id for s in skills],
            content_version__state=ContentVersion.State.PUBLISHED,
        )
        .exclude(id__in=exclure_ids)
        .select_related("skill")
        .order_by("skill_id", "difficulty")
    )
    par_skill = {}
    for ex in qs:
        par_skill.setdefault(ex.skill_id, []).append(ex)
    return par_skill


def composer(user, jour, minutes=15, course_id="course.1", aujourdhui=None):
    """Compose la séance du jour.

    Renvoie un dictionnaire de blocs. Les exercices peuvent manquer — la base
    n'en contient pas encore — sans que la composition en souffre : le moteur
    travaille sur des compétences, les exercices ne sont que leur habillage.
    """
    aujourdhui = aujourdhui or timezone.localdate()
    creneaux = CRENEAUX.get(minutes, 14)
    niveaux = _niveaux(user)

    # 1. Révisions dues — plancher et plafond.
    dues = competences_dues(user, aujourdhui)
    reserve = min(len(dues), max(RESERVE_MINIMALE, int(creneaux * PART_REVISION_MIN)))
    n_revision = max(min(len(dues), int(creneaux * PART_REVISION_MAX)), reserve)
    revisions = [m.skill for m in dues[:n_revision]]

    # 2. Nouveautés du jour, prérequis vérifiés.
    restant = max(0, creneaux - len(revisions) - 1)  # -1 : la lecture finale
    nouveautes = competences_ouvrables(user, jour, course_id, niveaux)[:restant]

    # 3. Renforcement : les plus fragiles déjà vues, si la séance n'est pas pleine.
    restant = max(0, creneaux - len(revisions) - len(nouveautes) - 1)
    deja = {s.id for s in revisions + nouveautes}
    renforcement = [
        m.skill for m in MasteryState.objects.filter(
            user=user, level__lt=NIVEAU_PREREQUIS
        ).exclude(skill_id__in=deja).select_related("skill").order_by("level")[:restant]
    ]

    # 4. Toute séance se termine par une lecture réelle, composée uniquement
    #    de l'acquis. C'est le moment où l'apprenant constate qu'il lit.
    lecture = _lecture(user, jour, course_id, niveaux)

    lecon = Lesson.objects.filter(
        course_id=course_id, day_number=jour, is_live=True
    ).first()

    blocs = [
        ("review", revisions),
        ("new", nouveautes),
        ("practice", renforcement),
        ("reading", lecture),
    ]
    toutes = [s for _, groupe in blocs for s in groupe]
    exercices = _exercices_pour(toutes)

    return {
        "day_number": jour,
        "lesson_id": str(lecon.id) if lecon else None,
        "estimated_minutes": minutes,
        "blocks": [
            {
                "kind": nom,
                "skills": [s.id for s in groupe],
                "items": [
                    _item(s, exercices.get(s.id, [])) for s in groupe
                ],
            }
            for nom, groupe in blocs
        ],
        "planned_items": len(toutes),
    }


def _lecture(user, jour, course_id, niveaux):
    """Un item de lecture — mot ou phrase — entièrement composé d'acquis."""
    candidats = (
        Skill.objects.filter(
            Q(type=Skill.Type.WORD) | Q(type=Skill.Type.FLUENCY),
            course_id=course_id, introduced_on_day__lte=jour,
        )
        .prefetch_related("prerequisites")
        .order_by("-introduced_on_day")
    )
    for skill in candidats:
        if _atomes_connus(skill, niveaux):
            return [skill]
    return []


def _item(skill, exercices):
    return {
        "skill_id": skill.id,
        "arabic": skill.arabic,
        "type": skill.type,
        "latency_threshold_ms": skill.latency_threshold_ms,
        "exercise": (
            {
                "id": str(exercices[0].id),
                "type": exercices[0].type,
                "payload": exercices[0].payload,
            }
            if exercices
            else None
        ),
    }
