"""Modèles de base réutilisés partout."""

import uuid

from django.db import models


class TimeStampedModel(models.Model):
    """Horodatage de création et de dernière modification."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    """Clé primaire UUID.

    Pas de séquentiel : l'identifiant transite par les URL, et un entier
    incrémental révèle publiquement le nombre d'inscrits et l'ordre
    d'inscription.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class BaseModel(UUIDModel, TimeStampedModel):
    class Meta:
        abstract = True
