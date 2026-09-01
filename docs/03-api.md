# Contrat d'API

REST, JSON, `Accept-Language: fr`. Base : `/api/v1/`.
Authentification : `Authorization: Bearer <access>` (JWT, 15 min ; rafraîchissement 30 j, rotatif).

Deux endpoints portent la logique du produit et méritent d'être lus en entier : `GET /session/today` et `POST /session/sync`.

---

## Conventions

**Erreurs** — une seule forme, toujours :
```json
{ "error": { "code": "entitlement_required",
             "message": "Cette leçon fait partie du programme complet.",
             "details": { "feature": "course.1" } } }
```
`code` est stable et destiné au client ; `message` est affichable et traduit.

**Pagination** — curseur, jamais de `offset` (les listes bougent sous la pagination).
**Idempotence** — toute écriture porte un `client_id` UUID généré par le téléphone.
**Versions** — `/api/v1/`. Une v2 coexiste avec la v1 pendant au moins six mois : sur ce marché, les mises à jour d'application sont lentes.

---

## 1. Authentification — `accounts`

| Méthode | Chemin | Rôle |
|---|---|---|
| `POST` | `/auth/register` | E-mail **ou** téléphone + mot de passe |
| `POST` | `/auth/login` | Renvoie `access` + `refresh` |
| `POST` | `/auth/refresh` | Rotation du jeton de rafraîchissement |
| `POST` | `/auth/logout` | Met le `refresh` en liste noire |
| `POST` | `/auth/password/reset` | Envoi par e-mail ou SMS |
| `GET` `PATCH` | `/me` | Profil complet |
| `DELETE` | `/me` | Suppression du compte — purge audio immédiate |
| `GET` `POST` | `/me/consents` | Consentements vocal / analytics / CGU |

`POST /auth/register` accepte un `anonymous_key` : c'est ce qui rattache au nouveau compte un diagnostic passé **avant** l'inscription (§4 du parcours utilisateur).

Limite de débit : 5/min sur `login` et `register`, par IP et par identifiant.

---

## 2. Onboarding et diagnostic

| Méthode | Chemin | Rôle |
|---|---|---|
| `POST` | `/onboarding` | `declared_level`, `daily_minutes`, `goals[]` |
| `POST` | `/diagnostic/start` | **Sans authentification.** Renvoie les items et un `anonymous_key` |
| `POST` | `/diagnostic/{id}/answer` | Une réponse : `item_id`, `answer`, `latency_ms` |
| `POST` | `/diagnostic/{id}/audio` | Test E — lecture orale |
| `POST` | `/diagnostic/{id}/complete` | Calcule et renvoie le profil |
| `GET` | `/diagnostic/comparison` | Jour 0 contre jour 30 |

`POST /diagnostic/{id}/complete` → 200 :
```json
{
  "level": 1,
  "level_label": "Je reconnais les lettres",
  "scores": { "letters": 72, "sounds": 58, "harakat": 34, "fusion": 12, "fluency": 8 },
  "score_global": 18,
  "item_set_version": "v1",
  "recommended_program": { "course_id": "course.1", "days": 30, "daily_minutes": 15 }
}
```

`GET /diagnostic/comparison` refuse de renvoyer une progression si les deux passages n'ont pas le même `item_set_version` — il renvoie alors `comparable: false` avec la raison. Afficher un progrès mesuré avec deux instruments différents serait un mensonge, même involontaire.

---

## 3. Catalogue — lecture seule

| Méthode | Chemin | Rôle |
|---|---|---|
| `GET` | `/courses` | Parcours disponibles |
| `GET` | `/courses/{id}/modules` | |
| `GET` | `/lessons/{day}` | Contenu d'un jour |
| `GET` | `/skills` | Le graphe complet — mis en cache par le client |
| `GET` | `/media/manifest` | Liste, empreintes et tailles des audios |

`GET /media/manifest` sert le préchargement : le client compare les empreintes à son cache local et ne télécharge que le delta. En-têtes `ETag` et `Cache-Control: max-age=86400`.

---

## 4. Séance — le cœur

### `GET /session/today`

Le serveur renvoie une séance **déjà composée** (§14). **Le client n'implémente aucune règle pédagogique** — c'est ce qui permet d'ajuster le moteur adaptatif sans publier une nouvelle version de l'application.

```json
{
  "session_id": "b3f1…",
  "day_number": 12,
  "estimated_minutes": 18,
  "blocks": [
    { "kind": "review",   "minutes": 4, "items": [ /* … */ ] },
    { "kind": "new",      "minutes": 5, "lesson_id": "…", "items": [ /* … */ ] },
    { "kind": "practice", "minutes": 6, "items": [ /* … */ ] },
    { "kind": "reading",  "minutes": 3, "items": [ /* … */ ] }
  ],
  "prefetch": { "media": ["…"], "next_day_available_at": "2026-08-30T00:00:00Z" }
}
```

Chaque `item` est un `Exercise` complet, `payload` inclus : une fois la séance reçue, **plus aucun appel réseau n'est nécessaire pour la terminer.**

Le champ `prefetch.media` liste ce que le client doit télécharger pour la séance **du lendemain**, pendant que l'utilisateur fait celle d'aujourd'hui. C'est ce qui rend le mode hors ligne réel plutôt que théorique.

`403 entitlement_required` si le jour dépasse 3 sans droit d'accès — avec, dans `details`, la fonctionnalité manquante et le jour atteint, pour que le paywall soit contextuel.

### `POST /session/sync`

Le pivot du mode hors ligne. Lot idempotent, rejouable sans limite.

```json
{
  "session_id": "b3f1…",
  "started_at": "2026-08-29T07:12:03Z",
  "completed_at": "2026-08-29T07:29:41Z",
  "abandoned_at_index": null,
  "attempts": [
    { "client_id": "a1…", "exercise_id": "e9…", "skill_id": "syllable.dad.fatha",
      "is_correct": true, "latency_ms": 1840, "answered_at": "2026-08-29T07:13:11Z" }
  ]
}
```

Réponse :
```json
{
  "accepted": 14, "duplicates": 3,
  "mastery_updates": [ { "skill_id": "syllable.dad.fatha", "level": 3, "due_at": "2026-09-02" } ],
  "streak_days": 12,
  "xp_gained": 120
}
```

`duplicates` n'est pas une erreur : c'est le comportement normal d'un lot renvoyé après une coupure. Le serveur reconnaît les `client_id` déjà reçus et les ignore silencieusement.

Le serveur recalcule les niveaux de maîtrise **lui-même** à partir des tentatives brutes. Il n'accepte jamais un niveau calculé par le client : une application modifiée pourrait sinon s'attribuer la maîtrise complète.

En cas de divergence, la règle est le niveau **le plus bas** ([D2](05-decisions.md#d2--tout-fonctionne-hors-ligne)).

| Méthode | Chemin | Rôle |
|---|---|---|
| `GET` | `/session/today` | |
| `POST` | `/session/sync` | |
| `GET` | `/session/history` | |
| `POST` | `/session/{id}/abandon` | Envoyé aussi quand l'app passe en arrière-plan |

---

## 5. Lecture orale

| Méthode | Chemin | Rôle |
|---|---|---|
| `POST` | `/speech/upload-url` | URL S3 présignée, 10 min |
| `POST` | `/speech/attempts` | Déclare l'enregistrement, lance la tâche Celery |
| `GET` | `/speech/attempts/{id}` | Résultat, ou `status: processing` |

`POST /speech/attempts` répond **202** et n'attend jamais l'analyse. Le client affiche immédiatement le retour local L0/L1 ; le résultat serveur arrive plus tard, ou jamais si le réseau est absent — sans que la séance en souffre.

Refus **400** si aucun consentement vocal actif. Pas d'exception, pas de mode dégradé.

Deux réponses possibles pour `GET /speech/attempts/{id}`, et une seule règle : **le niveau de confiance est toujours présent** ([D1](05-decisions.md#d1--coach-vocal--quatre-niveaux-progressifs)).

Confiance suffisante — niveau L1.5, transcription descriptive :
```json
{ "status": "ok", "level": "L1.5", "confidence": 0.87,
  "transcript": "كتب الطالب",
  "expected":   "كَتَبَ الطَّالِبُ",
  "matched_words": 2, "total_words": 2,
  "message": "J'ai bien entendu les deux mots." }
```

Confiance insuffisante :
```json
{ "status": "low_confidence", "confidence": 0.31,
  "message": "Je n'ai pas bien entendu. Essaie dans un endroit plus calme." }
```

Trois interdits absolus à ce niveau :
- **jamais de transcription sur un item isolé** — L1.5 ne s'active que sur les mots et les phrases, à partir du jour 8 ;
- **jamais de comparaison des harakat** — la sortie ASR est non vocalisée, `expected` est affiché vocalisé mais la comparaison porte sur le squelette consonantique seul ;
- **jamais de correction phonétique** avant que L3 n'ait passé ses seuils.

---

## 6. Progression et statistiques

| Méthode | Chemin | Rôle |
|---|---|---|
| `GET` | `/progress/overview` | L'écran d'accueil en un appel |
| `GET` | `/progress/skills` | Maîtrise par compétence |
| `GET` | `/progress/stats` | Les huit indicateurs du §22 |
| `GET` | `/progress/achievements` | |

`GET /progress/overview` est appelé à chaque ouverture : il doit tenir en une requête SQL et être mis en cache Redis 60 s.

---

## 7. Droits et paiement

| Méthode | Chemin | Rôle |
|---|---|---|
| `GET` | `/billing/entitlements` | **Le seul que l'app interroge pour savoir ce qui est ouvert** |
| `GET` | `/billing/plans` | Offres et prix, servis par le serveur |
| `POST` | `/billing/play/verify` | Vérifie un jeton d'achat Google Play côté serveur |
| `POST` | `/billing/restore` | **Restauration d'achat** — obligatoire chez Apple, exigée par Google |
| `POST` | `/billing/change-plan` | Changement d'offre, avec proratisation |
| `POST` | `/billing/checkout` | Paiement web : crée une intention, renvoie une URL (Wave, Orange Money, carte) |
| `POST` | `/billing/webhook/{provider}` | `play`, `apple`, `paydunya`, `wave`, `orange_money` |

**Un jeton d'achat Play n'est jamais accepté sur la seule parole du client.** `POST /billing/play/verify` le revalide auprès de l'API Google Play Developer côté serveur avant d'ouvrir le moindre droit. Une application modifiée peut fabriquer une réponse de facturation ; elle ne peut pas fabriquer une confirmation Google.

Les huit états du cycle de vie ([D3](05-decisions.md#d3--paiement-hybride-conforme-aux-plateformes)) sont pilotés par ces routes et les webhooks : `renewed` et `refunded` arrivent par webhook, `restored` et `plan_changed` à l'initiative de l'utilisateur.

Les prix sont servis par l'API et jamais codés en dur dans l'application : le §30 dit qu'ils doivent être testés, ce qui suppose de pouvoir les changer sans publier une mise à jour.

Réponse de `/billing/entitlements` :
```json
{
  "features": ["course.1", "reading_mirror"],
  "expires_at": null,
  "signature": "…",
  "offline_grace_days": 7
}
```
La `signature` permet au client de faire confiance à son cache pendant les sept jours de tolérance hors ligne, sans qu'une application modifiée puisse fabriquer un droit.

Les webhooks sont vérifiés par signature, rejouables, et idempotents sur `provider_ref`.

---

## 8. Analytics

| Méthode | Chemin | Rôle |
|---|---|---|
| `POST` | `/analytics/events` | Lot d'événements, relayés vers PostHog |

Le relais passe par le serveur plutôt que par le SDK PostHog directement, pour trois raisons : filtrer côté serveur ce qui ne doit jamais partir (§22), fonctionner hors ligne comme le reste, et pouvoir changer d'outil sans toucher à l'application.

---

## 9. Administration

`/api/admin/*` — `IsAdminUser`, mêmes ressources en écriture, plus la machine à états du contenu :

```
POST /api/admin/content/{id}/submit    draft     → review
POST /api/admin/content/{id}/approve   review    → approved
POST /api/admin/content/{id}/publish   approved  → published
POST /api/admin/content/{id}/unpublish published → unpublished
```

Au MVP, ces routes ne sont consommées par personne : l'interface est l'admin Django ([D5](05-decisions.md#d5--admin-django-au-mvp-react-plus-tard)). Elles existent quand même, pour que le front React de la phase 5 se branche sans réécriture du back.

---

## 10. Divers

| Méthode | Chemin | Rôle |
|---|---|---|
| `GET` | `/health` | Sonde de vivacité |
| `GET` | `/config` | Drapeaux de fonctionnalités, version minimale requise |

`GET /config` porte `min_supported_version` : le moyen de forcer une mise à jour quand une v2 d'API devient obligatoire, sans casser les téléphones qui n'ont pas mis à jour.
