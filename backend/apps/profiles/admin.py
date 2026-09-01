from django.contrib import admin

from .models import Goal, Profile


class GoalInline(admin.TabularInline):
    model = Goal
    extra = 0


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "declared_level", "daily_minutes", "current_day", "streak_days")
    list_filter = ("declared_level", "daily_minutes")
    search_fields = ("user__email", "user__phone")
    inlines = [GoalInline]
