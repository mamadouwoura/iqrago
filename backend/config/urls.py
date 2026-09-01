from django.conf import settings
from django.contrib import admin
from django.db import transaction
from django.http import JsonResponse
from django.urls import include, path


@transaction.non_atomic_requests
def health(_request):
    """Sonde de vivacité.

    `non_atomic_requests` est indispensable : `ATOMIC_REQUESTS = True` ouvre
    une transaction sur *chaque* requête, y compris celle-ci. La sonde
    toucherait donc la base, et une brève indisponibilité de PostgreSQL la
    ferait échouer — l'orchestrateur tuerait alors des conteneurs sains, et un
    hoquet de la base deviendrait une panne du service.
    """
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health", health, name="health"),
    path("api/v1/", include("config.api_urls")),
]

if settings.DEBUG:
    from django.conf.urls.static import static

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
