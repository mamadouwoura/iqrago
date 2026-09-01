from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Lesson
from apps.learning import composition, services
from common.acces import motif_refus, peut_acceder

from .serializers import SynchroSerializer


def _profil(user):
    return getattr(user, "profile", None)


class SeanceDuJourView(APIView):
    """La séance, composée par le serveur.

    Le client n'implémente aucune règle pédagogique : c'est ce qui permet
    d'ajuster le moteur adaptatif sans publier une nouvelle version de
    l'application.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        profil = _profil(request.user)
        if profil is None:
            return Response(
                {"error": {"code": "onboarding_requis",
                           "message": "L'onboarding n'a pas encore été fait."}},
                status=status.HTTP_404_NOT_FOUND,
            )

        jour = max(1, profil.current_day or 1)
        lecon = get_object_or_404(Lesson, course_id="course.1", day_number=jour, is_live=True)
        if not peut_acceder(request.user, lecon):
            return Response({"error": motif_refus(lecon)}, status=status.HTTP_403_FORBIDDEN)

        seance = composition.composer(
            request.user, jour, minutes=profil.daily_minutes, course_id=lecon.course_id
        )
        seance["lesson_title"] = lecon.title_fr
        return Response(seance)


class SynchroSeanceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        s = SynchroSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data

        resultat = services.synchroniser(
            request.user,
            day_number=d["day_number"],
            attempts=d["attempts"],
            session_id=d.get("session_id"),
            lesson_id=d.get("lesson_id"),
            started_at=d.get("started_at"),
            completed_at=d.get("completed_at"),
            abandoned_at_index=d.get("abandoned_at_index"),
            source=d["source"],
        )

        profil = _profil(request.user)
        resultat["streak_days"] = profil.streak_days if profil else 0
        return Response(resultat)


class ApercuProgressionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(services.apercu_progression(request.user))
