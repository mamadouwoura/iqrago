# syntax=docker/dockerfile:1

# ---------------------------------------------------------------- base
# `slim` et non `alpine` : psycopg et argon2-cffi compilent contre la glibc.
# Sur Alpine (musl) il faut reconstruire les roues, pour un gain de taille
# qui ne compense pas le temps de build ni les surprises à l'exécution.
FROM python:3.13-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends libpq5 curl \
 && rm -rf /var/lib/apt/lists/*

# ------------------------------------------------------------ dépendances
# Étape séparée : les dépendances ne changent presque jamais, le code change à
# chaque commit. Copier `requirements/` avant le reste garde le cache Docker
# valide et fait passer un rebuild de plusieurs minutes à quelques secondes.
FROM base AS deps

COPY requirements/ requirements/
ARG REQUIREMENTS=requirements/prod.txt
RUN pip install --no-cache-dir -r ${REQUIREMENTS}

# ---------------------------------------------------------------- runtime
FROM deps AS runtime

# Utilisateur non privilégié : un conteneur qui tourne en root donne à une
# éventuelle exécution de code arbitraire les pleins pouvoirs sur le système
# de fichiers de l'image.
RUN useradd --create-home --uid 10001 iqrago

COPY --chown=iqrago:iqrago . .

USER iqrago

EXPOSE 8000

# Le port et le nombre de workers restent réglables sans reconstruire l'image.
ENV PORT=8000 \
    WEB_CONCURRENCY=3 \
    DJANGO_SETTINGS_MODULE=config.settings.prod

HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:${PORT}/api/v1/health || exit 1

CMD ["sh", "-c", "gunicorn config.wsgi:application \
     --bind 0.0.0.0:${PORT} \
     --workers ${WEB_CONCURRENCY} \
     --timeout 60 \
     --access-logfile - \
     --error-logfile -"]
