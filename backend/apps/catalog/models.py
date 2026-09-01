"""Catalogue : la structure pédagogique et son cycle éditorial.

Deux natures d'objets, à ne pas confondre :

* **Structurels** — `Course`, `Module`, `Skill`. Ils décrivent le graphe
  d'apprentissage. Ils sont édités par l'équipe et ne passent pas par un
  cycle de relecture : les modifier ne change pas ce qu'un apprenant lit.
* **Éditoriaux** — `Lesson`, `Exercise`. C'est ce que l'apprenant voit. Ils
  sont rattachés à une `ContentVersion` et suivent
  `draft → review → approved → published`.

Le catalogue ne connaît **aucun utilisateur apprenant** : la progression vit
ailleurs. C'est cette séparation qui permet de republier du contenu sans
toucher aux données de progression.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from common.models import BaseModel, TimeStampedModel

# --------------------------------------------------------------- cycle éditorial


class ContentVersion(BaseModel):
    """Un lot éditorial : ce qui est relu et publié d'un seul tenant.

    Le lot, et non l'exercice isolé, est l'unité de relecture. Faire valider
    285 exercices un par un est impraticable ; « Jour 8 — famille ٮ », qui
    contient la leçon et ses exercices, se relit d'une traite et se publie
    sans état intermédiaire visible par l'apprenant.
    """

    class State(models.TextChoices):
        DRAFT = "draft", "Brouillon"
        REVIEW = "review", "En relecture"
        APPROVED = "approved", "Validé"
        PUBLISHED = "published", "Publié"
        UNPUBLISHED = "unpublished", "Dépublié"

    label = models.CharField("intitulé", max_length=120)
    state = models.CharField(max_length=20, choices=State, default=State.DRAFT, db_index=True)

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="versions_ecrites"
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="versions_relues",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="versions_validees",
    )

    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    unpublished_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)
    remplace = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="revisions"
    )

    class Meta:
        verbose_name = "version de contenu"
        verbose_name_plural = "versions de contenu"
        ordering = ["-created_at"]
        constraints = [
            # Un auteur ne valide pas son propre contenu. La règle est en base
            # parce qu'elle protège d'un raccourci qu'on prend toujours quand
            # on est pressé.
            models.CheckConstraint(
                condition=~models.Q(approved_by=models.F("author")),
                name="version_validation_par_un_tiers",
            ),
        ]

    def __str__(self):
        return f"{self.label} [{self.get_state_display()}]"

    @property
    def est_publie(self):
        return self.state == self.State.PUBLISHED

    @property
    def est_modifiable(self):
        return self.state in (self.State.DRAFT, self.State.REVIEW)

    # --- transitions. Chacune refuse tout état de départ non prévu : une
    # machine à états qui accepte n'importe quelle transition n'en est pas une.

    def _exiger(self, *etats):
        if self.state not in etats:
            attendus = ", ".join(etats)
            raise ValidationError(
                f"Transition impossible depuis « {self.get_state_display()} ». "
                f"États attendus : {attendus}."
            )

    def soumettre(self, reviewer=None):
        self._exiger(self.State.DRAFT)
        self.state = self.State.REVIEW
        self.reviewer = reviewer
        self.submitted_at = timezone.now()
        self.save(update_fields=["state", "reviewer", "submitted_at", "updated_at"])

    def valider(self, par):
        self._exiger(self.State.REVIEW)
        if par == self.author:
            raise ValidationError("Un auteur ne peut pas valider son propre contenu.")
        self.state = self.State.APPROVED
        self.approved_by = par
        self.approved_at = timezone.now()
        self.save(update_fields=["state", "approved_by", "approved_at", "updated_at"])

    def renvoyer_en_brouillon(self, motif=""):
        self._exiger(self.State.REVIEW, self.State.APPROVED)
        self.state = self.State.DRAFT
        self.approved_by = None
        self.approved_at = None
        if motif:
            self.notes = f"{self.notes}\n— renvoyé en brouillon : {motif}".strip()
        self.save(update_fields=["state", "approved_by", "approved_at", "notes", "updated_at"])

    def publier(self):
        self._exiger(self.State.APPROVED, self.State.UNPUBLISHED)

        # Bascule des leçons : la précédente sort de ligne avant que la
        # nouvelle n'y entre. Deux instructions distinctes, parce que la
        # contrainte d'unicité partielle est vérifiée à chaque instruction.
        # `update()` court-circuite `save()`, dont le verrou d'immuabilité
        # bloquerait précisément cette bascule.
        for lecon in self.lessons.all():
            Lesson.objects.filter(
                course_id=lecon.course_id, day_number=lecon.day_number, is_live=True
            ).exclude(pk=lecon.pk).update(is_live=False)
            Lesson.objects.filter(pk=lecon.pk).update(is_live=True)

        self.state = self.State.PUBLISHED
        self.published_at = self.published_at or timezone.now()
        self.unpublished_at = None
        self.save(update_fields=["state", "published_at", "unpublished_at", "updated_at"])

    def depublier(self):
        self._exiger(self.State.PUBLISHED)
        # Dépublier retire de la ligne sans rien supprimer : le contenu reste
        # lisible pour l'équipe et consultable dans l'historique.
        Lesson.objects.filter(content_version=self).update(is_live=False)
        self.state = self.State.UNPUBLISHED
        self.unpublished_at = timezone.now()
        self.save(update_fields=["state", "unpublished_at", "updated_at"])

    def creer_revision(self, author):
        """Duplique un lot publié dans un nouveau brouillon.

        C'est la seule manière de corriger du contenu publié. Modifier sur
        place changerait rétroactivement ce que les apprenants ont vu, et
        rendrait toute analyse de cohorte fausse sans que personne s'en
        aperçoive.
        """
        self._exiger(self.State.PUBLISHED, self.State.UNPUBLISHED)
        revision = ContentVersion.objects.create(
            label=f"{self.label} (révision)", author=author, remplace=self,
        )
        for lecon in self.lessons.all():
            competences = list(lecon.skills.all())
            lecon.pk = None
            lecon.id = None
            lecon.content_version = revision
            # La copie n'est pas en ligne : l'original continue d'être servi
            # tant que la révision n'est pas publiée à son tour.
            lecon.is_live = False
            lecon.save()
            lecon.skills.set(competences)
        for exercice in self.exercises.all():
            exercice.pk = None
            exercice.id = None
            exercice.content_version = revision
            exercice.save()
        return revision


class VersionedContent(models.Model):
    """Contenu soumis au cycle éditorial.

    Une fois publié, il est immuable : `save()` refuse. La correction passe
    par `ContentVersion.creer_revision()`.
    """

    content_version = models.ForeignKey(
        ContentVersion, on_delete=models.CASCADE, related_name="%(class)ss",
        null=True, blank=True,
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.pk:
            ancien = type(self).objects.filter(pk=self.pk).select_related(
                "content_version"
            ).first()
            if (
                ancien
                and ancien.content_version_id
                and ancien.content_version.state == ContentVersion.State.PUBLISHED
                and ancien.content_version_id == self.content_version_id
            ):
                raise ValidationError(
                    "Ce contenu est publié : il est immuable. Passe par "
                    "« Créer une révision » sur sa version."
                )
        super().save(*args, **kwargs)

    @property
    def est_publie(self):
        return bool(self.content_version_id) and self.content_version.est_publie


# ------------------------------------------------------------------ structure


class Course(TimeStampedModel):
    """Un parcours. Pluriel dès le premier schéma : les parcours avancés
    doivent être une insertion, pas une réécriture (D4)."""

    code = models.CharField(max_length=32, primary_key=True)
    title_fr = models.CharField(max_length=120)
    description_fr = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "parcours"
        verbose_name_plural = "parcours"
        ordering = ["order"]

    def __str__(self):
        return self.title_fr


class Module(TimeStampedModel):
    """Un bloc du parcours, couvrant une plage de jours."""

    code = models.CharField(max_length=48, primary_key=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="modules")
    title_fr = models.CharField(max_length=120)
    order = models.PositiveSmallIntegerField(default=0)
    day_start = models.PositiveSmallIntegerField()
    day_end = models.PositiveSmallIntegerField()

    class Meta:
        verbose_name = "module"
        ordering = ["course", "order"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(day_end__gte=models.F("day_start")),
                name="module_plage_de_jours_coherente",
            ),
        ]

    def __str__(self):
        return f"{self.title_fr} (J{self.day_start}-{self.day_end})"


class Skill(TimeStampedModel):
    """L'unité atomique du produit.

    Clé primaire textuelle (`syllable.dad.fatha`) et non UUID : elle apparaît
    dans les journaux, les analytics et les fichiers de contenu. Un identifiant
    lisible évite d'avoir à corréler pour comprendre une trace.
    """

    class Type(models.TextChoices):
        LETTER_RECOGNIZE = "letter.recognize", "Reconnaître une lettre"
        LETTER_SOUND = "letter.sound", "Son d'une lettre"
        LETTER_FORM = "letter.form", "Forme positionnelle"
        HARAKA = "haraka", "Accent"
        SYLLABLE = "syllable", "Syllabe"
        MARK = "mark", "Signe"
        CONTRAST = "contrast", "Contraste"
        WORD = "word", "Mot"
        FLUENCY = "fluency", "Fluidité"

    id = models.CharField(max_length=64, primary_key=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="skills")
    type = models.CharField(max_length=24, choices=Type, db_index=True)
    arabic = models.CharField(max_length=16, blank=True)
    label_fr = models.CharField(max_length=120, blank=True)
    difficulty = models.PositiveSmallIntegerField(default=1)

    # Ordre PAR DÉFAUT, pas calendrier : le moteur adaptatif peut devancer ou
    # retarder une compétence selon les performances (D11).
    introduced_on_day = models.PositiveSmallIntegerField(null=True, blank=True, db_index=True)
    latency_threshold_ms = models.PositiveIntegerField(default=1500)

    prerequisites = models.ManyToManyField(
        "self", through="SkillPrerequisite", symmetrical=False, related_name="dependants",
    )

    class Meta:
        verbose_name = "compétence"
        verbose_name_plural = "compétences"
        ordering = ["introduced_on_day", "id"]

    def __str__(self):
        return f"{self.id}{f' — {self.arabic}' if self.arabic else ''}"


class SkillPrerequisite(models.Model):
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="liens_prerequis")
    requires = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="liens_dependants")

    class Meta:
        verbose_name = "prérequis"
        verbose_name_plural = "prérequis"
        constraints = [
            models.UniqueConstraint(fields=["skill", "requires"], name="prerequis_unique"),
            models.CheckConstraint(
                condition=~models.Q(skill=models.F("requires")),
                name="prerequis_pas_de_boucle_directe",
            ),
        ]

    def __str__(self):
        return f"{self.skill_id} ← {self.requires_id}"


# ------------------------------------------------------------------ éditorial


class Media(BaseModel):
    class Kind(models.TextChoices):
        AUDIO_REFERENCE = "audio_reference", "Audio de référence"
        IMAGE = "image", "Image"
        VIDEO = "video", "Vidéo"

    kind = models.CharField(max_length=20, choices=Kind)
    key = models.CharField(max_length=255, unique=True, help_text="Nom du fichier ou clé S3.")
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    checksum = models.CharField(max_length=64, blank=True)

    # Embarqué dans l'application : disponible hors ligne sans téléchargement.
    # C'est le cas des ~158 audios de référence.
    bundled = models.BooleanField(default=False)

    class Meta:
        verbose_name = "média"
        verbose_name_plural = "médias"

    def __str__(self):
        return self.key


class Lesson(VersionedContent, TimeStampedModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="lessons")
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="lessons")
    day_number = models.PositiveSmallIntegerField()
    title_fr = models.CharField(max_length=120)
    intro_text_fr = models.TextField(blank=True)
    estimated_minutes = models.PositiveSmallIntegerField(default=15)
    is_free = models.BooleanField(default=False, help_text="Accessible sans achat.")

    # Les nouveautés du jour. La leçon ne contient PAS la liste des exercices
    # de la séance : celle-ci est composée à l'exécution par le moteur
    # adaptatif (D11).
    skills = models.ManyToManyField(Skill, blank=True, related_name="lessons")

    # Plusieurs leçons peuvent exister pour le jour 8 — une par version — mais
    # une seule est servie aux apprenants. Sans ce drapeau, réviser une leçon
    # publiée serait impossible : la contrainte d'unicité sur (parcours, jour)
    # refuserait la copie.
    is_live = models.BooleanField(
        "en ligne", default=False,
        help_text="Version actuellement servie aux apprenants pour ce jour.",
    )

    class Meta:
        verbose_name = "leçon"
        verbose_name_plural = "leçons"
        ordering = ["course", "day_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["course", "day_number", "content_version"],
                name="lecon_unique_par_jour_et_version",
                # Sans cela, PostgreSQL considère deux NULL comme distincts et
                # laisserait passer plusieurs leçons non versionnées pour le
                # même jour.
                nulls_distinct=False,
            ),
            models.UniqueConstraint(
                fields=["course", "day_number"],
                condition=models.Q(is_live=True),
                name="une_seule_lecon_en_ligne_par_jour",
            ),
        ]

    def __str__(self):
        return f"Jour {self.day_number} — {self.title_fr}"

    def clean(self):
        if self.module_id and self.course_id and self.module.course_id != self.course_id:
            raise ValidationError({"module": "Ce module n'appartient pas à ce parcours."})
        if self.module_id and not (self.module.day_start <= self.day_number <= self.module.day_end):
            raise ValidationError(
                {"day_number": f"Le jour {self.day_number} est hors de la plage du module "
                               f"({self.module.day_start}-{self.module.day_end})."}
            )


class Exercise(VersionedContent, BaseModel):
    class Type(models.TextChoices):
        LETTER_TO_SOUND = "letter_to_sound_mcq", "Lettre → son"
        SOUND_TO_LETTER = "sound_to_letter_mcq", "Son → lettre"
        PAIR_DISCRIMINATION = "pair_discrimination", "Discrimination de paire"
        FAMILY_ODD_ONE_OUT = "family_odd_one_out", "Intrus dans la famille"
        FIND_IN_WORD = "find_in_word", "Repérer dans un mot"
        BUILD_SYLLABLE = "build_syllable", "Composer une syllabe"
        SYLLABLE_TO_SOUND = "syllable_to_sound_mcq", "Syllabe → son"
        WORD_ASSEMBLY = "word_assembly", "Assembler un mot"
        READ_ALOUD = "read_aloud", "Lecture à voix haute"
        TIMED_SYLLABLE_RUN = "timed_syllable_run", "Mode vitesse"
        WORD_TO_MEANING = "word_to_meaning_mcq", "Mot → sens"
        LETTER_DICTATION = "letter_dictation", "Dictée de lettre"
        TIMED_PASSAGE = "timed_passage", "Lecture chronométrée"

    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="exercises")
    type = models.CharField(max_length=32, choices=Type, db_index=True)

    # Un seul schéma pour treize types : ajouter un type n'exige aucune
    # migration. Le client dispose d'un rendu par type.
    payload = models.JSONField(default=dict)

    difficulty = models.PositiveSmallIntegerField(default=1)
    media = models.ManyToManyField(Media, blank=True, related_name="exercises")

    class Meta:
        verbose_name = "exercice"
        verbose_name_plural = "exercices"
        ordering = ["skill", "difficulty"]
        indexes = [models.Index(fields=["skill", "difficulty"])]

    def __str__(self):
        return f"{self.get_type_display()} — {self.skill_id}"
