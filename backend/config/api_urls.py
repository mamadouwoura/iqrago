"""Routes de l'API v1.

Une v2 devra coexister avec la v1 pendant au moins six mois : sur le marché
initial, les mises à jour d'application sont lentes et un utilisateur qui ne
met pas à jour ne doit pas se retrouver devant une application morte.
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.api.views import (
    ConnexionView,
    ConsentementsView,
    DeconnexionView,
    InscriptionView,
    MoiView,
)
from apps.catalog.api.views import (
    CompetencesListView,
    LeconDetailView,
    ManifesteMediasView,
    ParcoursListView,
    ProgrammeView,
)
from apps.learning.api.views import (
    ApercuProgressionView,
    SeanceDuJourView,
    SynchroSeanceView,
)
from apps.profiles.api.views import OnboardingView, ProfilView

urlpatterns = [
    # --- comptes
    path("auth/register", InscriptionView.as_view(), name="inscription"),
    path("auth/login", ConnexionView.as_view(), name="connexion"),
    path("auth/refresh", TokenRefreshView.as_view(), name="refresh"),
    path("auth/logout", DeconnexionView.as_view(), name="deconnexion"),
    path("me", MoiView.as_view(), name="moi"),
    path("me/consents", ConsentementsView.as_view(), name="consentements"),
    # --- profil
    path("onboarding", OnboardingView.as_view(), name="onboarding"),
    path("profile", ProfilView.as_view(), name="profil"),
    # --- séance et progression
    path("session/today", SeanceDuJourView.as_view(), name="seance-du-jour"),
    path("session/sync", SynchroSeanceView.as_view(), name="seance-sync"),
    path("progress/overview", ApercuProgressionView.as_view(), name="apercu-progression"),
    # --- catalogue
    path("courses", ParcoursListView.as_view(), name="parcours"),
    path("courses/<str:code>/programme", ProgrammeView.as_view(), name="programme"),
    path("courses/<str:code>/lessons/<int:jour>", LeconDetailView.as_view(), name="lecon"),
    path("skills", CompetencesListView.as_view(), name="competences"),
    path("media/manifest", ManifesteMediasView.as_view(), name="manifeste-medias"),
]
