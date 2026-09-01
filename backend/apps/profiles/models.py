"""Profil d'apprentissage : ce que l'utilisateur a déclaré, et où il en est."""

from django.conf import settings
from django.db import models

from common.models import BaseModel, TimeStampedModel


class Profile(TimeStampedModel):
    """Un profil pour un compte.

    `declared_level` est ce que l'utilisateur *dit* de lui à l'onboarding. Il
    ne détermine rien : c'est le diagnostic qui mesure, et le moteur adaptatif
    qui décide. On le conserve parce que l'écart entre le niveau déclaré et le
    niveau mesuré est un signal produit utile.
    """

    class DeclaredLevel(models.TextChoices):
        ZERO = "zero", "Je commence de zéro"
        KNOWS_LETTERS = "knows_letters", "Je connais déjà les lettres"
        IMPROVE = "improve_reading", "Je veux améliorer ma lecture"

    class DailyMinutes(models.IntegerChoices):
        M10 = 10, "10 minutes"
        M15 = 15, "15 minutes"
        M20 = 20, "20 minutes"
        M30 = 30, "30 minutes"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile",
        primary_key=True,
    )
    declared_level = models.CharField(
        max_length=20, choices=DeclaredLevel, default=DeclaredLevel.ZERO
    )
    daily_minutes = models.PositiveSmallIntegerField(
        choices=DailyMinutes, default=DailyMinutes.M15,
        help_text="Pilote la taille de la séance composée par le moteur.",
    )

    current_day = models.PositiveSmallIntegerField(default=0)
    streak_days = models.PositiveSmallIntegerField(default=0)
    last_session_date = models.DateField(null=True, blank=True)

    timezone = models.CharField(
        max_length=40, default="Africa/Dakar",
        help_text="Détermine l'heure locale des rappels.",
    )

    class Meta:
        verbose_name = "profil"
        verbose_name_plural = "profils"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(current_day__lte=30), name="profile_jour_max_30"
            ),
        ]

    def __str__(self):
        return f"{self.user} — jour {self.current_day}"


class Goal(BaseModel):
    """Objectif déclaré.

    Table séparée et non un simple champ : l'écran d'onboarding doit pouvoir
    passer en sélection multiple sans migration de schéma.
    """

    class Code(models.TextChoices):
        READ_ARABIC = "read_arabic", "Lire l'arabe"
        READ_FASTER = "read_faster", "Lire plus rapidement"
        READ_TEXTS = "read_texts", "Lire des textes"
        RESUME = "resume", "Reprendre après une pause"

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="goals")
    code = models.CharField(max_length=20, choices=Code)

    class Meta:
        verbose_name = "objectif"
        verbose_name_plural = "objectifs"
        constraints = [
            models.UniqueConstraint(fields=["profile", "code"], name="goal_unique_par_profil"),
        ]

    def __str__(self):
        return self.get_code_display()
