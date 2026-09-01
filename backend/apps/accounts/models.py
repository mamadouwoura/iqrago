"""Identité : compte utilisateur et consentements.

D8 — le modèle `User` doit exister avant la première migration. C'est le seul
point irréversible du projet.
"""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

from common.models import BaseModel, TimeStampedModel, UUIDModel

phone_validator = RegexValidator(
    regex=r"^\+[1-9]\d{7,18}$",
    message="Le numéro doit être au format international, par exemple +221771234567.",
)


class UserManager(BaseUserManager):
    """Crée des comptes identifiés par e-mail **ou** par téléphone.

    Le téléphone n'est pas un ajout de confort : sur le marché initial, une
    partie de la cible n'a pas d'adresse e-mail active alors que tout le monde
    a un numéro. Exiger un e-mail couperait le tunnel d'inscription.
    """

    use_in_migrations = True

    def _create_user(self, email=None, phone=None, password=None, **extra):
        if not email and not phone:
            raise ValueError("Un compte exige au moins un e-mail ou un téléphone.")
        email = self.normalize_email(email).lower() if email else None
        user = self.model(email=email or None, phone=phone or None, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email=None, phone=None, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, phone, password, **extra)

    def create_superuser(self, email=None, phone=None, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        if extra.get("is_staff") is not True:
            raise ValueError("Un superutilisateur doit avoir is_staff=True.")
        if extra.get("is_superuser") is not True:
            raise ValueError("Un superutilisateur doit avoir is_superuser=True.")
        return self._create_user(email, phone, password, **extra)


class User(UUIDModel, TimeStampedModel, AbstractBaseUser, PermissionsMixin):
    class InterfaceLanguage(models.TextChoices):
        FR = "fr", "Français"
        EN = "en", "English"

    email = models.EmailField("adresse e-mail", unique=True, null=True, blank=True)
    phone = models.CharField(
        "téléphone",
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        validators=[phone_validator],
        help_text="Format international, par exemple +221771234567.",
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    interface_language = models.CharField(
        max_length=5, choices=InterfaceLanguage, default=InterfaceLanguage.FR
    )

    # Suppression logique : le compte disparaît immédiatement pour
    # l'utilisateur, la purge effective suit la politique de conservation.
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"
        constraints = [
            # La règle est en base, pas seulement dans un formulaire : un
            # compte sans aucun moyen d'identification est irrécupérable.
            models.CheckConstraint(
                condition=models.Q(email__isnull=False) | models.Q(phone__isnull=False),
                name="user_email_ou_phone",
            ),
        ]

    def __str__(self):
        return self.email or self.phone or str(self.id)

    @property
    def is_deleted(self):
        return self.deleted_at is not None

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.is_active = False
        self.save(update_fields=["deleted_at", "is_active", "updated_at"])


class ConsentRecord(BaseModel):
    """Trace d'un consentement.

    Une ligne n'est jamais écrasée : accorder puis retirer un consentement
    produit deux lignes. Sans cet historique, on ne peut pas répondre à la
    seule question qui compte en cas de litige — *à quoi cette personne
    avait-elle consenti, et à quelle date ?*
    """

    class Kind(models.TextChoices):
        VOICE = "voice", "Enregistrement vocal"
        ANALYTICS = "analytics", "Mesure d'usage"
        TERMS = "terms", "Conditions d'utilisation"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="consents")
    kind = models.CharField(max_length=20, choices=Kind)
    granted = models.BooleanField()
    policy_version = models.CharField(max_length=10)
    granted_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "consentement"
        verbose_name_plural = "consentements"
        indexes = [models.Index(fields=["user", "kind", "-granted_at"])]
        ordering = ["-granted_at"]

    def __str__(self):
        etat = "accordé" if self.granted else "retiré"
        return f"{self.user} — {self.get_kind_display()} {etat}"
