from rest_framework import serializers

from apps.learning.models import SessionRun


class TentativeSerializer(serializers.Serializer):
    client_id = serializers.UUIDField()
    skill_id = serializers.CharField(max_length=64)
    exercise_id = serializers.UUIDField(required=False, allow_null=True)
    is_correct = serializers.BooleanField()
    latency_ms = serializers.IntegerField(min_value=0, max_value=600_000)
    answered_at = serializers.DateTimeField()


class SynchroSerializer(serializers.Serializer):
    """Lot de tentatives issu d'une séance, jouée en ligne ou hors ligne."""

    session_id = serializers.UUIDField(required=False, allow_null=True)
    day_number = serializers.IntegerField(min_value=1, max_value=30)
    lesson_id = serializers.UUIDField(required=False, allow_null=True)
    started_at = serializers.DateTimeField(required=False, allow_null=True)
    completed_at = serializers.DateTimeField(required=False, allow_null=True)
    abandoned_at_index = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    source = serializers.ChoiceField(
        choices=SessionRun.Source.choices, default=SessionRun.Source.ONLINE
    )
    # 200 : une séance en compte au plus 26, mais un rattrapage après plusieurs
    # jours hors ligne peut en cumuler. Au-delà, c'est un client fautif.
    attempts = serializers.ListField(child=TentativeSerializer(), max_length=200)

    def validate_attempts(self, value):
        vus = set()
        for a in value:
            if a["client_id"] in vus:
                raise serializers.ValidationError(
                    f"client_id répété dans le même lot : {a['client_id']}"
                )
            vus.add(a["client_id"])
        return value
