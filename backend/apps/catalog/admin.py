"""Administration du catalogue.

C'est l'interface de travail de la personne en charge du contenu. Les
transitions éditoriales passent par des actions explicites, jamais par un
champ `state` qu'on modifierait à la main : un menu déroulant permettrait de
sauter de « brouillon » à « publié » sans relecture.
"""

from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.utils.html import format_html

from .models import (
    ContentVersion,
    Course,
    Exercise,
    Lesson,
    Media,
    Module,
    Skill,
    SkillPrerequisite,
)

COULEURS = {
    "draft": "#6b7280",
    "review": "#d97706",
    "approved": "#2563eb",
    "published": "#059669",
    "unpublished": "#dc2626",
}


def _appliquer(modeladmin, request, queryset, methode, libelle, **kwargs):
    """Applique une transition à une sélection, en comptant les refus.

    Une action qui échoue en silence sur la moitié de la sélection est pire
    qu'une action qui refuse : on croit avoir publié.
    """
    ok, refus = 0, []
    for version in queryset:
        try:
            getattr(version, methode)(**kwargs)
            ok += 1
        except ValidationError as e:
            refus.append(f"{version.label} : {'; '.join(e.messages)}")
    if ok:
        modeladmin.message_user(request, f"{ok} version(s) — {libelle}.", messages.SUCCESS)
    for motif in refus:
        modeladmin.message_user(request, motif, messages.ERROR)


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 0
    fields = ("day_number", "title_fr", "estimated_minutes", "is_free")
    show_change_link = True


class ExerciseInline(admin.TabularInline):
    model = Exercise
    extra = 0
    fields = ("skill", "type", "difficulty")
    autocomplete_fields = ("skill",)
    show_change_link = True


@admin.register(ContentVersion)
class ContentVersionAdmin(admin.ModelAdmin):
    list_display = ("label", "etat_colore", "author", "approved_by", "nb_lecons",
                    "nb_exercices", "published_at")
    list_filter = ("state", "author")
    search_fields = ("label", "notes")
    readonly_fields = ("id", "state", "submitted_at", "approved_at", "published_at",
                       "unpublished_at", "approved_by", "remplace", "created_at", "updated_at")
    inlines = [LessonInline, ExerciseInline]
    actions = ("action_soumettre", "action_valider", "action_publier",
               "action_depublier", "action_renvoyer", "action_reviser")

    @admin.display(description="état", ordering="state")
    def etat_colore(self, obj):
        return format_html(
            '<b style="color:{}">{}</b>', COULEURS.get(obj.state, "#000"), obj.get_state_display()
        )

    @admin.display(description="leçons")
    def nb_lecons(self, obj):
        return obj.lessons.count()

    @admin.display(description="exercices")
    def nb_exercices(self, obj):
        return obj.exercises.count()

    def save_model(self, request, obj, form, change):
        if not change and not obj.author_id:
            obj.author = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description="Soumettre à la relecture")
    def action_soumettre(self, request, queryset):
        _appliquer(self, request, queryset, "soumettre", "soumise(s) à la relecture")

    @admin.action(description="Valider (relecteur)")
    def action_valider(self, request, queryset):
        _appliquer(self, request, queryset, "valider", "validée(s)", par=request.user)

    @admin.action(description="Publier")
    def action_publier(self, request, queryset):
        _appliquer(self, request, queryset, "publier", "publiée(s)")

    @admin.action(description="Dépublier")
    def action_depublier(self, request, queryset):
        _appliquer(self, request, queryset, "depublier", "dépubliée(s)")

    @admin.action(description="Renvoyer en brouillon")
    def action_renvoyer(self, request, queryset):
        _appliquer(self, request, queryset, "renvoyer_en_brouillon", "renvoyée(s) en brouillon")

    @admin.action(description="Créer une révision (contenu publié)")
    def action_reviser(self, request, queryset):
        for version in queryset:
            try:
                revision = version.creer_revision(author=request.user)
                self.message_user(request, f"Révision créée : {revision.label}", messages.SUCCESS)
            except ValidationError as e:
                self.message_user(request, "; ".join(e.messages), messages.ERROR)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "title_fr", "order", "is_active", "nb_modules", "nb_competences")
    list_filter = ("is_active",)
    search_fields = ("code", "title_fr")

    @admin.display(description="modules")
    def nb_modules(self, obj):
        return obj.modules.count()

    @admin.display(description="compétences")
    def nb_competences(self, obj):
        return obj.skills.count()


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ("code", "title_fr", "course", "day_start", "day_end", "order")
    list_filter = ("course",)
    search_fields = ("code", "title_fr")


class PrerequisiteInline(admin.TabularInline):
    model = SkillPrerequisite
    fk_name = "skill"
    extra = 0
    autocomplete_fields = ("requires",)
    verbose_name = "prérequis"
    verbose_name_plural = "prérequis"


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("id", "arabic", "type", "introduced_on_day", "difficulty",
                    "latency_threshold_ms", "nb_exercices")
    list_filter = ("type", "course", "introduced_on_day")
    search_fields = ("id", "arabic", "label_fr")
    inlines = [PrerequisiteInline]
    list_per_page = 50

    @admin.display(description="exercices")
    def nb_exercices(self, obj):
        n = obj.exercises.count()
        # Sous trois exercices, l'apprenant mémorise la présentation au lieu
        # du contenu. Le signal doit sauter aux yeux dans la liste.
        couleur = "#059669" if n >= 3 else "#dc2626"
        return format_html('<b style="color:{}">{}</b>', couleur, n)


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("day_number", "title_fr", "course", "module", "is_free",
                    "estimated_minutes", "etat_version")
    list_filter = ("course", "module", "is_free")
    search_fields = ("title_fr",)
    filter_horizontal = ("skills",)
    ordering = ("course", "day_number")

    @admin.display(description="état")
    def etat_version(self, obj):
        if not obj.content_version_id:
            return "—"
        v = obj.content_version
        return format_html('<b style="color:{}">{}</b>',
                           COULEURS.get(v.state, "#000"), v.get_state_display())

    def get_readonly_fields(self, request, obj=None):
        # Le contenu publié est immuable : l'admin doit le montrer plutôt que
        # de laisser saisir puis échouer à l'enregistrement.
        if obj and obj.est_publie:
            return [f.name for f in self.model._meta.fields] + ["skills"]
        return super().get_readonly_fields(request, obj)


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ("__str__", "type", "skill", "difficulty", "etat_version")
    list_filter = ("type", "difficulty", "skill__type")
    search_fields = ("skill__id", "skill__arabic")
    autocomplete_fields = ("skill",)
    filter_horizontal = ("media",)
    list_per_page = 50

    @admin.display(description="état")
    def etat_version(self, obj):
        if not obj.content_version_id:
            return "—"
        v = obj.content_version
        return format_html('<b style="color:{}">{}</b>',
                           COULEURS.get(v.state, "#000"), v.get_state_display())

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.est_publie:
            return [f.name for f in self.model._meta.fields] + ["media"]
        return super().get_readonly_fields(request, obj)


@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = ("key", "kind", "duration_ms", "bundled")
    list_filter = ("kind", "bundled")
    search_fields = ("key",)
