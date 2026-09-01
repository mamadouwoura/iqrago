from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .forms import UserChangeForm, UserCreationForm
from .models import ConsentRecord, User


class ConsentInline(admin.TabularInline):
    model = ConsentRecord
    extra = 0
    # Un consentement est une trace : il se consulte, il ne se réécrit pas.
    readonly_fields = ("kind", "granted", "policy_version", "granted_at")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    ordering = ("-created_at",)
    list_display = ("__str__", "email", "phone", "is_active", "is_staff", "created_at")
    list_filter = ("is_active", "is_staff", "is_superuser", "interface_language")
    search_fields = ("email", "phone")
    readonly_fields = ("id", "created_at", "updated_at", "last_login")
    inlines = [ConsentInline]

    fieldsets = (
        (None, {"fields": ("id", "email", "phone", "password")}),
        ("Préférences", {"fields": ("interface_language",)}),
        ("Droits", {"fields": (
            "is_active", "is_staff", "is_superuser", "groups", "user_permissions",
        )}),
        ("Dates", {"fields": ("last_login", "created_at", "updated_at", "deleted_at")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "phone", "password1", "password2"),
        }),
    )

    def get_inlines(self, request, obj=None):
        # Pas de consentements sur le formulaire de création : ils se
        # rattachent à un utilisateur qui n'existe pas encore, et leur
        # formset vide fait échouer l'enregistrement.
        return [] if obj is None else self.inlines


@admin.register(ConsentRecord)
class ConsentRecordAdmin(admin.ModelAdmin):
    list_display = ("user", "kind", "granted", "policy_version", "granted_at")
    list_filter = ("kind", "granted", "policy_version")
    search_fields = ("user__email", "user__phone")
    readonly_fields = ("id", "created_at", "updated_at")
