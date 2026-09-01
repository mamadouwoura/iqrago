from rest_framework import serializers

from apps.profiles.models import Goal, Profile


class OnboardingSerializer(serializers.Serializer):
    """Les trois écrans d'onboarding en un appel.

    Un appel par écran multiplierait les occasions d'abandonner en cours de
    route sur une connexion instable.
    """

    declared_level = serializers.ChoiceField(choices=Profile.DeclaredLevel.choices)
    daily_minutes = serializers.ChoiceField(choices=Profile.DailyMinutes.choices)
    goals = serializers.ListField(
        child=serializers.ChoiceField(choices=Goal.Code.choices),
        allow_empty=True, max_length=len(Goal.Code.choices),
    )

    def save(self, user):
        profil, _ = Profile.objects.update_or_create(
            user=user,
            defaults={
                "declared_level": self.validated_data["declared_level"],
                "daily_minutes": self.validated_data["daily_minutes"],
            },
        )
        # Remplacement complet : repasser l'onboarding doit refléter les
        # nouveaux choix, pas les cumuler avec les anciens.
        profil.goals.all().delete()
        Goal.objects.bulk_create(
            [Goal(profile=profil, code=c) for c in dict.fromkeys(self.validated_data["goals"])]
        )
        return profil


class ProfilSerializer(serializers.ModelSerializer):
    goals = serializers.SlugRelatedField(many=True, read_only=True, slug_field="code")

    class Meta:
        model = Profile
        fields = ("declared_level", "daily_minutes", "current_day", "streak_days",
                  "last_session_date", "timezone", "goals")
        read_only_fields = ("current_day", "streak_days", "last_session_date")
