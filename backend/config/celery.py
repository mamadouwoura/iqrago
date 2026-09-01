"""Application Celery.

Configurée, mais AUCUNE tâche n'est encore écrite. Le traitement audio, les
notifications et l'analyse vocale viendront plus tard : il n'y a pour l'instant
aucun traitement asynchrone en fonctionnement, et ce fichier ne doit pas
laisser croire le contraire.
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("iqrago")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
