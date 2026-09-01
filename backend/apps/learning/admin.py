from django.contrib import admin

from .models import ExerciseAttempt, MasteryState, SessionRun


@admin.register(MasteryState)
class MasteryStateAdmin(admin.ModelAdmin):
    list_display = ("user", "skill", "level", "due_at", "seen_count",
                    "correct_count", "hesitation_count", "avg_latency_ms")
    list_filter = ("level", "skill__type")
    search_fields = ("user__email", "user__phone", "skill__id")
    autocomplete_fields = ("skill",)
    list_per_page = 50


class AttemptInline(admin.TabularInline):
    model = ExerciseAttempt
    extra = 0
    # Une tentative est une trace : elle se consulte, elle ne se réécrit pas.
    readonly_fields = ("skill", "is_correct", "latency_ms", "is_hesitation",
                       "level_before", "level_after", "answered_at")
    fields = readonly_fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(SessionRun)
class SessionRunAdmin(admin.ModelAdmin):
    list_display = ("user", "day_number", "started_at", "completed_at",
                    "planned_items", "completed_items", "abandoned_at_index", "source")
    list_filter = ("day_number", "source")
    search_fields = ("user__email", "user__phone")
    inlines = [AttemptInline]
