from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Course, Lesson, Media, Skill
from common.acces import motif_refus, peut_acceder

from .serializers import (
    CompetenceSerializer,
    LeconResumeSerializer,
    LeconSerializer,
    MediaSerializer,
    ParcoursSerializer,
)


class ParcoursListView(generics.ListAPIView):
    serializer_class = ParcoursSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    queryset = Course.objects.filter(is_active=True).prefetch_related("modules")


class ProgrammeView(generics.ListAPIView):
    """Le programme complet en résumé, sans authentification.

    C'est aussi la page de vente : on montre les trente jours, on n'en sert que
    trois.
    """

    serializer_class = LeconResumeSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        return Lesson.objects.filter(
            course_id=self.kwargs["code"], is_live=True
        ).order_by("day_number")


class LeconDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, code, jour):
        # `is_live` seul : un brouillon ou une version dépubliée ne doit
        # jamais atteindre un apprenant.
        lecon = get_object_or_404(
            Lesson.objects.prefetch_related("skills"),
            course_id=code, day_number=jour, is_live=True,
        )
        if not peut_acceder(request.user, lecon):
            return Response({"error": motif_refus(lecon)}, status=status.HTTP_403_FORBIDDEN)
        return Response(LeconSerializer(lecon).data)


class CompetencesListView(generics.ListAPIView):
    """Le graphe complet. Mis en cache par le client : il ne change qu'à
    chaque publication de contenu."""

    serializer_class = CompetenceSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        qs = Skill.objects.prefetch_related("prerequisites").order_by("introduced_on_day", "id")
        jour = self.request.query_params.get("jusqu_au_jour")
        if jour and jour.isdigit():
            qs = qs.filter(introduced_on_day__lte=int(jour))
        return qs


class ManifesteMediasView(generics.ListAPIView):
    """Empreintes et tailles : le client compare à son cache et ne télécharge
    que le delta. C'est ce qui rend le préchargement supportable en data
    prépayée."""

    serializer_class = MediaSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    queryset = Media.objects.all().order_by("key")
