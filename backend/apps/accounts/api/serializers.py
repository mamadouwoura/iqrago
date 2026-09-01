"""Sérialiseurs des comptes.

Lecture et écriture sont séparées : elles divergent toujours, et les fusionner
finit par exposer en écriture un champ qui devait rester en lecture seule.
"""

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import ConsentRecord

User = get_user_model()


def jetons_pour(user):
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


class InscriptionSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True, max_length=20)
    password = serializers.CharField(
        write_only=True, min_length=8, style={"input_type": "password"}
    )

    def validate_email(self, value):
        value = (value or "").strip().lower()
        if value and User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Un compte utilise déjà cette adresse.")
        return value or None

    def validate_phone(self, value):
        value = (value or "").strip()
        if value and User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("Un compte utilise déjà ce numéro.")
        return value or None

    def validate(self, attrs):
        if not attrs.get("email") and not attrs.get("phone"):
            raise serializers.ValidationError(
                {"identifiant": "Renseigne une adresse e-mail ou un numéro de téléphone."}
            )
        try:
            validate_password(attrs["password"])
        except DjangoValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)}) from e
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class ConnexionSerializer(serializers.Serializer):
    """Un seul champ d'identification.

    Demander à l'utilisateur de choisir entre « e-mail » et « téléphone » avant
    de taper est une friction inutile : le serveur sait faire la différence.
    """

    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate(self, attrs):
        user = authenticate(
            request=self.context.get("request"),
            username=attrs["identifier"],
            password=attrs["password"],
        )
        if not user:
            # Message unique : distinguer « compte inconnu » de « mot de passe
            # faux » permettrait de savoir qui a un compte.
            raise serializers.ValidationError("Identifiant ou mot de passe incorrect.")
        attrs["user"] = user
        return attrs


class UtilisateurSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "phone", "interface_language", "created_at")
        read_only_fields = ("id", "created_at")


class UtilisateurMajSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("interface_language",)


class ConsentementSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsentRecord
        fields = ("id", "kind", "granted", "policy_version", "granted_at")
        read_only_fields = ("id", "granted_at")
