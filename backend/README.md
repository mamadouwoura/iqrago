# Backend IqraGo

Django 5.2 · DRF · PostgreSQL 17 · Celery/Redis.
Architecture : [../docs/00-blueprint.md](../docs/00-blueprint.md) §18 · Schéma : [../docs/02-donnees.md](../docs/02-donnees.md) · API : [../docs/03-api.md](../docs/03-api.md)

**État : bloc B terminé, CI verte.** Socle sur PostgreSQL, catalogue peuplé (283 compétences, 506 prérequis, 30 leçons, 158 médias), API REST et authentification en service, moteur de séance et répétition espacée opérationnels. **122 tests**, `check --deploy` sans avertissement, image Docker construite et démarrée en intégration continue. Ce qui n'est pas encore là est listé en fin de document.

---

## Installation

Prérequis : **Python 3.13** (via le lanceur `py`) et **PostgreSQL 17**.

```bash
winget install --id PostgreSQL.PostgreSQL.17 -e
```

### 1. Environnement virtuel

```bash
cd backend && py -3 -m venv .venv
```

Sous `cmd.exe`, les chemins prennent des antislashs :

```bash
.venv\Scripts\python.exe -m pip install -r requirements/dev.txt
```

### 2. Base de données

Rôle dédié plutôt que le superutilisateur `postgres` : le développement
rencontre ainsi les mêmes limites de droits que la production, et les erreurs
de permission se voient tout de suite au lieu d'apparaître au déploiement.

```bash
psql -U postgres -c "CREATE ROLE iqrago WITH LOGIN PASSWORD 'choisis-un-mot-de-passe' CREATEDB;"
```

Choisis-en un et reporte-le dans `DATABASE_URL` (étape 3). Aucun mot de passe réel n'est écrit dans ce dépôt, même pour du développement local : un identifiant publié finit toujours par être réutilisé ailleurs.

```bash
psql -U postgres -c "CREATE DATABASE iqrago OWNER iqrago ENCODING 'UTF8';"
```

`CREATEDB` est nécessaire : `pytest` crée et détruit une base de test à chaque exécution.

`psql` n'est pas dans le `PATH` après l'installation ; il se trouve dans `C:\Program Files\PostgreSQL\17\bin\`.

### 3. Configuration

```bash
cp .env.example .env
```

Puis générer une clé et la reporter dans `SECRET_KEY` :

```bash
.venv\Scripts\python.exe -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

`.env` n'est **jamais** versionné. `.env.example` documente les variables sans valeur réelle.

### 4. Migrations

```bash
.venv\Scripts\python.exe manage.py migrate
```

### 5. Compte d'administration

```bash
.venv\Scripts\python.exe manage.py createsuperuser
```

### 6. Import du socle pédagogique

```bash
.venv\Scripts\python.exe manage.py importer_contenu
```

Lit `content/*.json` et peuple parcours, modules, compétences, prérequis, leçons et médias. **Idempotent** : réexécutable sans doublon, ce qui permet de retravailler les fichiers source et de réimporter. `--dry-run` compte sans écrire.

### 7. Import des exercices

```bash
dart run tools/contenu/exercices.dart
```

```bash
.venv\Scripts\python.exe manage.py importer_exercices
```

Les brouillons ne sont pas versionnés — ils se regénèrent à l'identique. L'import crée **un lot par jour de parcours** : « Jour 08 — La famille ٮ » groupe la trentaine d'exercices du jour, se relit d'une traite et se publie d'un seul tenant.

**L'import ne publie jamais rien.** Tout entre à l'état de brouillon ; la publication exige une relecture puis une validation par un tiers. Idempotent : l'identifiant de chaque exercice est dérivé de son contenu, et le générateur étant déterministe, réimporter n'écrit qu'une version.

Les fichiers de `content/` sont la source de vérité jusqu'à ce que l'admin prenne le relais ; ensuite c'est la base qui fait foi, et la commande ne sert plus qu'à amorcer un environnement neuf.

---

## Lancement

```bash
.venv\Scripts\python.exe manage.py runserver
```

| Adresse | Contenu |
|---|---|
| `http://127.0.0.1:8000/admin/` | Interface d'administration |
| `http://127.0.0.1:8000/api/v1/health` | Sonde de vivacité, sans authentification |

---

## API

Base `/api/v1/`, JWT en `Authorization: Bearer <access>`.

| Méthode | Route | Accès |
|---|---|---|
| `POST` | `auth/register` | public — e-mail **ou** téléphone |
| `POST` | `auth/login` | public — un seul champ `identifier` |
| `POST` | `auth/refresh` · `auth/logout` | jeton |
| `GET` `PATCH` `DELETE` | `me` | jeton |
| `GET` `POST` | `me/consents` | jeton |
| `POST` | `onboarding` | jeton |
| `GET` `PATCH` | `profile` | jeton |
| `GET` | `courses` | **public** |
| `GET` | `courses/<code>/programme` | **public** — les 30 jours en résumé |
| `GET` | `courses/<code>/lessons/<jour>` | jeton + droit d'accès |
| `GET` | `skills` | jeton — `?jusqu_au_jour=N` |
| `GET` | `media/manifest` | jeton |
| `GET` | `session/today` | jeton + droit d'accès |
| `POST` | `session/sync` | jeton |
| `GET` | `progress/overview` | jeton |

**Connexion par e-mail ou téléphone.** `ModelBackend` n'interroge que `USERNAME_FIELD` : un compte créé avec un numéro et sans adresse aurait été impossible à ouvrir. `EmailOuTelephoneBackend` comble l'écart, et hache un mot de passe même quand l'identifiant est inconnu — sinon un compte inexistant répondrait plus vite, ce qui permet de les énumérer au chronomètre.

**Le programme est public, les leçons ne le sont pas.** On montre les trente jours — c'est la page de vente — on n'en sert que trois.

**Seules les leçons `is_live` sont servies.** Un brouillon ou une version dépubliée n'atteint jamais un apprenant, même s'il existe en base. Un test le vérifie explicitement.

### Droits d'accès

`common/acces.py` est le point d'extension du futur service d'`Entitlement` (D3). La règle actuelle est réelle, pas simulée : jours 1 à 3 ouverts, le reste renvoie `403 entitlement_required` — parce qu'aucun moyen de payer n'existe encore. L'équipe (`is_staff`) accède à tout. Quand la facturation arrivera, seule `peut_acceder()` change.

## Tests et style

```bash
.venv\Scripts\python.exe -m pytest
```

```bash
.venv\Scripts\python.exe -m ruff check .
```

Les tests tournent sur **PostgreSQL**, pas sur SQLite : les contraintes `CHECK`, les index partiels et le `JSONB` ne se comportent pas pareil, et un test qui passe sur SQLite ne prouve rien sur la base de production.

---

## Organisation

```
backend/
  config/
    settings/  base · dev · staging · prod
    urls.py  wsgi.py  asgi.py  celery.py
  common/models.py      UUIDModel, TimeStampedModel, BaseModel
  apps/
    accounts/  User, ConsentRecord, forms, admin, tests
    profiles/  Profile, Goal, admin
    catalog/   Course, Module, Skill, Lesson, Exercise, Media, ContentVersion
    learning/  MasteryState, SessionRun, ExerciseAttempt, srs, composition
  requirements/  base · dev · prod
```

---

## Le cycle éditorial

C'est par là que passe toute production de contenu.

```
brouillon ──► en relecture ──► validé ──► publié ──► dépublié
     ▲                                        │
     └────────── créer une révision ◄──────────┘
```

Les transitions sont des **actions** dans l'admin, jamais un champ `state` modifiable : un menu déroulant permettrait de sauter de « brouillon » à « publié » sans relecture.

| Règle | Où elle tient |
|---|---|
| Publier exige d'être passé par la relecture **et** la validation | Machine à états, `ValidationError` |
| Un auteur ne valide pas son propre contenu | Méthode **et** contrainte `CHECK` en base |
| Le contenu publié est immuable | `save()` refuse ; la correction passe par « Créer une révision » |
| Une seule leçon en ligne par jour | Index unique partiel sur `is_live` |

**L'unité de relecture est le lot, pas l'exercice.** Faire valider 283 exercices un par un est impraticable ; « Jour 8 — famille ٮ », qui contient la leçon et ses exercices, se relit d'une traite et se publie sans état intermédiaire visible par l'apprenant.

**Pourquoi `is_live`.** Plusieurs leçons coexistent pour le jour 8 — une par version — mais une seule est servie. Sans ce drapeau, réviser une leçon publiée serait impossible : la contrainte d'unicité `(parcours, jour)` refuserait la copie. C'est un défaut qui n'est apparu qu'en déroulant le scénario complet, pas au premier jeu de tests.

---

## Le moteur de séance

**Aucun écran ne demande « quelle est la leçon suivante ? ».** Il demande « quelles compétences sont dues, et laquelle est prête ? ». La séance est composée **par le serveur** : le client n'implémente aucune règle pédagogique, ce qui permet d'ajuster le moteur sans publier une nouvelle version de l'application.

### Répétition espacée

Niveaux 0-4, intervalles 1 / 2 / 4 / 8 jours, gigue ±10 % pour éviter que toutes les cartes d'un même jour ne reviennent ensemble.

| Résultat | Effet |
|---|---|
| juste et rapide | niveau +1 (plafond 4), échéance espacée |
| **juste mais lent** | **niveau inchangé**, retour demain |
| faux | niveau −1 (plancher 1), retour demain |

La deuxième ligne est le mécanisme qui produit de la fluidité au lieu d'une simple exactitude : sans elle, on entraîne des gens qui répondent bien en cinq secondes — c'est-à-dire qui épellent encore. Le seuil est porté par chaque compétence (`latency_threshold_ms`).

**Une carte ratée ne revient jamais immédiatement.** Réussir dix secondes après un échec ne teste que la mémoire de travail.

### Composition

| Règle | Effet |
|---|---|
| Verrou de prérequis | Une compétence ne s'ouvre que si **tous** ses prérequis sont au niveau ≥ 3 |
| Zéro surprise | Un item composé n'apparaît que si tous ses atomes sont au niveau ≥ 2 |
| Plancher de révision | 2 places minimum réservées tant qu'une carte est due |
| Plafond de révision | 50 % de la séance au maximum — une longue absence ne produit pas 40 minutes |

**Aucune dette n'est affichée.** Les cartes en retard attendent leur tour. Un compteur « 47 révisions en retard » est la première cause d'abandon des applications à répétition espacée.

### Synchronisation

`POST /session/sync` est **idempotent sur `client_id`** : un lot renvoyé trois fois après une coupure n'écrit qu'une fois. Le serveur **recalcule les niveaux lui-même** à partir des tentatives brutes ; il n'accepte jamais un niveau calculé par le client.

La série compte **les jours de pratique, pas les séances** : quatre séances dans la même soirée valent un jour. Sinon elle mesurerait l'empressement au lieu de la régularité.

### Une limite connue

Sans exercices en base, une séance ne propose qu'**un item par compétence**. Le jour 1 n'ouvre que trois compétences — `letter.dal.recognize`, `letter.dhal.recognize`, `haraka.fatha` — parce que le son d'une lettre exige que sa reconnaissance soit au niveau 3, ce qui demande trois réponses justes.

Trois items pour une séance de quinze minutes, c'est trop peu. La réponse n'est pas d'assouplir le verrou de prérequis mais de produire le contenu : trois exercices par compétence donnent neuf items pour ces mêmes trois compétences. Le moteur les servira sans modification.

---

## Docker

```bash
cp .env.docker.example .env.docker
```

```bash
docker compose up --build
```

Quatre services : `postgres`, `redis`, `api`, `worker`. Le service `speech` viendra quand le code existera — l'ajouter maintenant donnerait l'illusion d'un traitement vocal qui n'est pas écrit.

**Les migrations ne tournent pas au démarrage du conteneur.** C'est délibéré : avec plusieurs répliques, un `migrate` automatique au boot les fait courir en concurrence sur le même schéma. Elles restent une étape contrôlée (§49) :

```bash
docker compose run --rm api python manage.py migrate
```

**L'image tourne sous un utilisateur non privilégié** (`uid 10001`). Le `.dockerignore` exclut `.env` : les secrets viennent de l'environnement d'exécution, jamais d'une couche d'image.

`SECURE_SSL_REDIRECT` est pilotable par l'environnement, à `True` par défaut. Sans cela, une sonde HTTP dans un conteneur derrière un proxy qui termine déjà TLS recevrait une redirection et échouerait.

## Intégration continue

`.github/workflows/ci.yml` — trois travaux :

| Travail | Contenu |
|---|---|
| **Style** | `ruff check` |
| **Tests** | PostgreSQL 17 en service · `makemigrations --check` · `pytest` · `check --deploy --fail-level WARNING` |
| **Image** | Construction du `Dockerfile`, puis **démarrage réel du conteneur** et interrogation de la sonde |

`makemigrations --check` détecte un modèle modifié sans migration correspondante — cas qui passe les tests et casse le déploiement.

Le travail « Image » ne se contente pas de construire : **construire une image ne prouve pas qu'elle démarre**. Il la lance et attend une réponse de `/api/v1/health`.

### Réglages par environnement

`DJANGO_SETTINGS_MODULE` vaut `config.settings.dev` par défaut (`manage.py`), et `config.settings.prod` pour WSGI/ASGI. La configuration passe par des variables d'environnement, jamais par une branche conditionnelle dans le code.

---

## Décisions inscrites dans le code

**`AUTH_USER_MODEL = "accounts.User"` avant la première migration.** Seul point irréversible du projet ([D8](../docs/05-decisions.md#d8--modèle-user-personnalisé-au-premier-commit)) : le changer après une mise en production est une opération de plusieurs jours avec risque de perte de données.

**Clé primaire UUID.** L'identifiant transite par les URL ; un entier incrémental révélerait publiquement le nombre d'inscrits et l'ordre d'inscription.

**E-mail *ou* téléphone**, garanti par une contrainte `CHECK` en base et pas seulement par un formulaire. Sur le marché initial, une partie de la cible n'a pas d'adresse e-mail active alors que tout le monde a un numéro : exiger un e-mail couperait le tunnel d'inscription.

**Argon2**, pas le PBKDF2 par défaut de Django.

**`ConsentRecord` dès maintenant.** Le consentement vocal est une donnée juridique : il faut pouvoir dire *à quoi* une personne a consenti et *à quelle date*. Une ligne n'est jamais écrasée — accorder puis retirer produit deux lignes. Le poser à l'étape 5 évite une migration de données plus tard.

**`ATOMIC_REQUESTS = True`.** Une requête HTTP est une transaction : une vue qui échoue à mi-parcours ne laisse pas la progression d'un utilisateur à moitié écrite.

---

## Ce qui n'existe pas encore

À ne pas confondre avec ce qui fonctionne :

| Élément | État |
|---|---|
| `config/celery.py` | **Configuré, aucune tâche écrite.** Il n'y a aucun traitement asynchrone en fonctionnement |
| Redis | Référencé par la configuration, pas installé ni requis pour l'instant |
| **Exercices** | **Le catalogue les accueille, mais la base n'en contient aucun.** ~850 restent à produire |
| Séances riches | Le moteur tourne, mais sans exercices une séance ne propose qu'un item par compétence — voir « une limite connue » |
| Diagnostic initial et évaluation du jour 30 | Plus tard |
| Facturation | `common/acces.py` ouvre les jours 1-3 et refuse le reste : c'est réel, mais aucun moyen de payer n'existe |
| Docker en local | Non installé sur le poste de développement (8 Go de RAM). L'image est construite et démarrée **par la CI**, sur les exécuteurs GitHub — c'est là qu'elle est vérifiée |
