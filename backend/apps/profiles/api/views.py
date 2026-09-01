from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.profiles.models import Profile

from .serializers import OnboardingSerializer, ProfilSerializer


class OnboardingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        s = OnboardingSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        profil = s.save(user=request.user)
        return Response(ProfilSerializer(profil).data, status=status.HTTP_201_CREATED)


class ProfilView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profil = Profile.objects.filter(user=request.user).prefetch_related("goals").first()
        if not profil:
            return Response(
                {"error": {"code": "onboarding_requis",
                           "message": "L'onboarding n'a pas encore été fait."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(ProfilSerializer(profil).data)

    def patch(self, request):
        profil = Profile.objects.filter(user=request.user).first()
        if not profil:
            return Response(status=status.HTTP_404_NOT_FOUND)
        s = ProfilSerializer(profil, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)
