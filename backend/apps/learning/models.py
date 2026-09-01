"""Progression : ce que l'utilisateur maîtrise, et ce qu'il doit revoir.

Le catalogue décrit le savoir ; cette application décrit un apprenant face à ce
savoir. La séparation permet de republier du contenu sans toucher à la
progression de qui que ce soit.
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.catalog.models import Exercise, Lesson, Skill
from common.models import BaseModel, TimeStampedModel


class MasteryState(TimeStampedModel):
    """Une ligne par (utilisateur × compétence). ~283 par apprenant.

    Table la plus chaude du produit : lue à chaque composition de séance,
    écrite à chaque réponse.
    """

    class Level(models.IntegerChoices):
        INCONNUE = 0, "Inconnue"
        DECOUVERTE = 1, "Découverte"
        FRAGILE = 2, "Fragile"
        SOLIDE = 3, "Solide"
        ACQUISE = 4, "Acquise"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="maitrises"
    )
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="maitrises")

    level = models.PositiveSmallIntegerField(choices=Level, default=Level.INCONNUE)
    due_at = models.DateField(null=True, blank=True)

    seen_count = models.PositiveIntegerField(default=0)
    correct_count = models.PositiveIntegerField(default=0)
    hesitation_count = models.PositiveIntegerField(default=0)
    avg_latency_ms = models.PositiveIntegerField(default=0)
    last_seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "maîtrise"
        verbose_name_plural = "maîtrises"
        constraints = [
            models.UniqueConstraint(fields=["user", "skill"], name="maitrise_unique"),
        ]
        indexes = [
            # Index partiel : seules les cartes programmées sont interrogées.
            models.Index(
                fields=["user", "due_at"],
                condition=models.Q(due_at__isnull=False),
                name="maitrise_due_idx",
            ),
        ]

    def __str__(self):
        return f"{self.user} · {self.skill_id} · niveau {self.level}"

    @property
    def est_acquise(self):
        return self.level >= self.Level.SOLIDE


class SessionRun(BaseModel):
    """Une séance jouée."""

    class Source(models.TextChoices):
        ONLINE = "online", "En ligne"
        OFFLINE_SYNC = "offline_sync", "Synchronisée hors ligne"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="seances"
    )
    lesson = models.ForeignKey(
        Lesson, on_delete=models.SET_NULL, null=True, blank=True, related_name="seances"
    )
    day_number = models.PositiveSmallIntegerField()

    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

    planned_items = models.PositiveSmallIntegerField(default=0)
    completed_items = models.PositiveSmallIntegerField(default=0)

    # Le champ le plus utile de la table : il dit à quel exercice précis la
    # séance meurt. Sans lui, on optimise la rétention à l'aveugle.
    abandoned_at_index = models.PositiveSmallIntegerField(null=True, blank=True)

    source = models.CharField(max_length=20, choices=Source, default=Source.ONLINE)

    class Meta:
        verbose_name = "séance"
        verbose_name_plural = "séances"
        ordering = ["-started_at"]
        indexes = [models.Index(fields=["user", "-started_at"])]

    def __str__(self):
        return f"{self.user} · jour {self.day_number}"


class ExerciseAttempt(TimeStampedModel):
    """Une réponse. Conservée brute, avec sa latence.

    C'est la matière première du futur moteur adaptatif (D11) : sans
    l'historique des tentatives, il n'y aura rien à ajuster le jour venu.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Généré par le téléphone. Clé de déduplication du mode hors ligne : un lot
    # renvoyé trois fois après une coupure n'écrit qu'une fois.
    client_id = models.UUIDField(unique=True)

    session_run = models.ForeignKey(
        SessionRun, on_delete=models.CASCADE, related_name="attempts"
    )
    exercise = models.ForeignKey(
        Exercise, on_delete=models.SET_NULL, null=True, blank=True, related_name="attempts"
    )
    # Dénormalisé : évite une jointure sur toutes les requêtes d'analyse, et
    # survit à la suppression d'un exercice.
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="attempts")

    is_correct = models.BooleanField()
    latency_ms = models.PositiveIntegerField()
    is_hesitation = models.BooleanField(default=False)

    level_before = models.PositiveSmallIntegerField()
    level_after = models.PositiveSmallIntegerField()

    # Deux horodatages : l'horloge d'un téléphone n'est pas fiable.
    # `answered_at` sert à la pédagogie, `received_at` à l'audit.
    answered_at = models.DateTimeField()
    received_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "tentative"
        verbose_name_plural = "tentatives"
        ordering = ["answered_at"]
        indexes = [
            models.Index(fields=["skill", "answered_at"]),
            models.Index(fields=["session_run"]),
        ]

    def __str__(self):
        return f"{self.skill_id} · {'juste' if self.is_correct else 'faux'}"
