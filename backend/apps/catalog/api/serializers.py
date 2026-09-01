from rest_framework import serializers

from apps.catalog.models import Course, Lesson, Media, Module, Skill


class CompetenceSerializer(serializers.ModelSerializer):
    prerequisites = serializers.SlugRelatedField(many=True, read_only=True, slug_field="id")

    class Meta:
        model = Skill
        fields = ("id", "type", "arabic", "label_fr", "difficulty",
                  "introduced_on_day", "latency_threshold_ms", "prerequisites")


class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = ("code", "title_fr", "order", "day_start", "day_end")


class ParcoursSerializer(serializers.ModelSerializer):
    modules = ModuleSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = ("code", "title_fr", "description_fr", "order", "modules")


class LeconSerializer(serializers.ModelSerializer):
    skills = serializers.SlugRelatedField(many=True, read_only=True, slug_field="id")
    module = serializers.SlugRelatedField(read_only=True, slug_field="code")

    class Meta:
        model = Lesson
        fields = ("day_number", "title_fr", "intro_text_fr", "estimated_minutes",
                  "is_free", "module", "skills")


class LeconResumeSerializer(serializers.ModelSerializer):
    """Sans le détail : sert la liste du parcours, y compris les jours non
    débloqués. Masquer entièrement les jours payants empêcherait d'afficher
    ce que contient le programme — donc de donner envie de l'acheter."""

    class Meta:
        model = Lesson
        fields = ("day_number", "title_fr", "estimated_minutes", "is_free")


class MediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Media
        fields = ("key", "kind", "duration_ms", "checksum", "bundled")
