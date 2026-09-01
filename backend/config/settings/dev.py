"""Développement local."""

from .base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]

# Le courrier reste dans la console : rien ne part vers l'extérieur en dev.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Les jetons de développement vivent plus longtemps, pour ne pas devoir se
# reconnecter à chaque essai. Jamais en production.
from datetime import timedelta  # noqa: E402

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=8),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}
