"""Endpoints des comptes."""

from django.db import transaction
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import ConsentRecord

from .serializers import (
    ConnexionSerializer,
    ConsentementSerializer,
    InscriptionSerializer,
    UtilisateurMajSerializer,
    UtilisateurSerializer,
    jetons_pour,
)


class InscriptionView(generics.CreateAPIView):
    serializer_class = InscriptionSerializer
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = s.save()
        return Response(
            {"user": UtilisateurSerializer(user).data, "tokens": jetons_pour(user)},
            status=status.HTTP_201_CREATED,
        )


class ConnexionView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        s = ConnexionSerializer(data=request.data, context={"request": request})
        s.is_valid(raise_exception=True)
        user = s.validated_data["user"]
        return Response({"user": UtilisateurSerializer(user).data, "tokens": jetons_pour(user)})


class DeconnexionView(APIView):
    """Met le jeton de rafraîchissement en liste noire.

    Sans cela, « se déconnecter » ne ferait qu'oublier le jeton côté client : il
    resterait valable trente jours pour quiconque l'aurait intercepté.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh = request.data.get("refresh")
        if not refresh:
            return Response(
                {"error": {"code": "refresh_manquant",
                           "message": "Le jeton de rafraîchissement est requis."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            RefreshToken(refresh).blacklist()
        except TokenError:
            return Response(
                {"error": {"code": "jeton_invalide", "message": "Jeton déjà expiré ou invalide."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_205_RESET_CONTENT)


class MoiView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UtilisateurSerializer(request.user).data)

    def patch(self, request):
        s = UtilisateurMajSerializer(request.user, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(UtilisateurSerializer(request.user).data)

    @transaction.atomic
    def delete(self, request):
        """Suppression du compte.

        Suppression logique immédiate — le compte disparaît pour l'utilisateur
        et ses jetons cessent d'ouvrir quoi que ce soit. La purge effective
        suivra la politique de conservation, une fois les données de paiement
        et d'audio en place.
        """
        user = request.user
        user.soft_delete()
        for jeton in getattr(user, "outstandingtoken_set", []).all():
            try:
                RefreshToken(jeton.token).blacklist()
            except TokenError:
                continue
        return Response(status=status.HTTP_204_NO_CONTENT)


class ConsentementsView(generics.ListCreateAPIView):
    """Historique des consentements.

    On n'écrase jamais une ligne : accorder puis retirer produit deux entrées.
    C'est la seule façon de répondre plus tard à « à quoi cette personne
    avait-elle consenti, et quand ? ».
    """

    serializer_class = ConsentementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ConsentRecord.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
