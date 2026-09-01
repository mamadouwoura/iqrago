# Schéma de base de données

PostgreSQL 16. Notation : `pk` clé primaire, `fk` clé étrangère, `uq` unique, `idx` index.
Toutes les tables portent `created_at` et `updated_at` — non répétés ci-dessous.

---

## 1. Identité et profil

### `User` — application `accounts`
**Modèle personnalisé, créé avant la première migration.** Voir [D8](05-decisions.md#d8--modèle-user-personnalisé-au-premier-commit). Irréversible.

| Champ | Type | Note |
|---|---|---|
| `id` | UUID pk | Pas de séquentiel : l'identifiant transite par les URL |
| `email` | citext uq null | Facultatif : l'inscription par téléphone doit rester possible |
| `phone` | varchar(20) uq null | Format E.164. Au moins l'un des deux est requis |
| `password` | varchar | Argon2 |
| `is_active`, `is_staff` | bool | |
| `interface_language` | varchar(5) | `fr` au lancement ; wo, ff, en prévus |
| `deleted_at` | timestamptz null | Suppression logique, purge à 30 jours |

Contrainte : `CHECK (email IS NOT NULL OR phone IS NOT NULL)`.

### `Profile` — un pour un avec `User`

| Champ | Type | Note |
|---|---|---|
| `user_id` | fk uq | |
| `declared_level` | enum | `zero`, `knows_letters`, `improve_reading` — écran 1 de l'onboarding |
| `daily_minutes` | smallint | 10 / 15 / 20 / 30 — pilote la taille de séance |
| `current_day` | smallint | 0 à 30 |
| `streak_days` | smallint | |
| `last_session_date` | date | |
| `timezone` | varchar(40) | Pour l'heure des notifications |

### `Goal`
Table séparée et non un champ : l'écran 3 doit pouvoir devenir multi-sélection sans migration.

| Champ | Type |
|---|---|
| `profile_id` | fk |
| `code` | enum `read_arabic`, `read_faster`, `read_texts`, `resume` |

`uq (profile_id, code)`.

### `ConsentRecord`
Le consentement vocal est une donnée juridique : il faut savoir **quand** et **à quelle version du texte** l'utilisateur a consenti.

| Champ | Type |
|---|---|
| `user_id` | fk |
| `kind` | enum `voice`, `analytics`, `terms` |
| `granted` | bool |
| `policy_version` | varchar(10) |
| `granted_at` | timestamptz |

Historique conservé : on n'écrase jamais une ligne, on en ajoute une.

---

## 2. Catalogue

### `Skill` — l'unité atomique du produit

| Champ | Type | Note |
|---|---|---|
| `id` | varchar(64) pk | L'identifiant lisible : `syllable.dad.fatha` |
| `type` | enum | Les 9 types de [01-pedagogie.md](01-pedagogie.md) |
| `arabic` | varchar(16) null | Le caractère concerné |
| `label_fr` | varchar(80) | |
| `difficulty` | smallint | 1 à 5 |
| `introduced_on_day` | smallint null | Ordre par défaut ; le moteur peut le devancer |
| `latency_threshold_ms` | int | Seuil d'automatisation (§15) |
| `course_id` | fk | Parcours 1 ou 2 — jamais mélangés (§5) |

Clé primaire textuelle et non UUID : elle apparaît dans les analytics, les journaux et les fichiers de contenu. Un `syllable.dad.fatha` lisible vaut mieux qu'un UUID à corréler.

### `SkillPrerequisite`

| Champ | Type |
|---|---|
| `skill_id` | fk |
| `requires_id` | fk |

`uq (skill_id, requires_id)`. Un cycle rendrait le parcours impossible : détection par tri topologique dans un test unitaire, exécuté en CI.

### `Course` / `Module` / `Lesson`

```
Course (parcours 1 : lire l'arabe | parcours 2 : textes religieux)
  └── Module (les 10 blocs : alphabet, connexions, harakat, fusion…)
        └── Lesson (une par jour : day_number 1..30)
              └── skills : M2M vers Skill (les nouveautés du jour)
```

| `Lesson` | Type |
|---|---|
| `module_id` | fk |
| `day_number` | smallint |
| `title_fr` | varchar(120) |
| `intro_text_fr` | text |
| `estimated_minutes` | smallint |
| `is_free` | bool — vrai pour les jours 1 à 3 |

`uq (course_id, day_number)`.

`Lesson` décrit **ce qui est introduit ce jour-là**. Elle ne contient pas la liste des exercices de la séance : celle-ci est composée à l'exécution par le moteur adaptatif (§14). C'est la différence structurelle entre ce produit et un cours linéaire.

### `Exercise`

| Champ | Type | Note |
|---|---|---|
| `id` | UUID pk | |
| `skill_id` | fk | |
| `type` | enum | Les 13 types |
| `payload` | jsonb | Structure de [01-pedagogie.md §3](01-pedagogie.md#3-types-dexercices) |
| `difficulty` | smallint | |
| `content_version_id` | fk | |

`idx (skill_id, difficulty)` — c'est la requête chaude du moteur.
Contrainte : `CHECK (jsonb_typeof(payload->'options') = 'array')` pour les types à choix multiple.

### `Media`

| Champ | Type |
|---|---|
| `id` | UUID pk |
| `kind` | enum `audio_reference`, `image`, `video` |
| `s3_key` | varchar(255) |
| `duration_ms` | int null |
| `checksum` | varchar(64) |
| `bundled` | bool |

`bundled = true` : le fichier est embarqué dans l'application, disponible hors ligne sans téléchargement. C'est le cas des ~180 audios de référence.

### `ContentVersion` — la machine à états du §47

| Champ | Type |
|---|---|
| `id` | UUID pk |
| `state` | enum `draft`, `review`, `approved`, `published`, `unpublished` |
| `author_id` | fk User |
| `reviewer_id` | fk User null |
| `approved_by_id` | fk User null |
| `published_at` | timestamptz null |
| `unpublished_at` | timestamptz null |
| `notes` | text |

Deux règles appliquées en base, pas seulement en code :
- `CHECK (approved_by_id IS NULL OR approved_by_id <> author_id)` — un auteur ne valide pas son propre contenu.
- Un contenu `published` est immuable : toute correction crée une version suivante. Sinon corriger une faute change rétroactivement ce que les utilisateurs ont vu, et fausse toute analyse de cohorte.

---

## 3. Apprentissage

### `MasteryState` — la table chaude

Une ligne par (utilisateur × compétence). ~297 lignes par utilisateur. Lue à chaque composition de séance.

| Champ | Type | Note |
|---|---|---|
| `user_id` | fk | |
| `skill_id` | fk | |
| `level` | smallint | 0 à 4 |
| `due_at` | date null | |
| `seen_count`, `correct_count` | int | |
| `hesitation_count` | int | Réponses justes au-delà du seuil |
| `avg_latency_ms` | int | Moyenne glissante sur 5 |
| `last_seen_at` | timestamptz | |

`uq (user_id, skill_id)` · `idx (user_id, due_at) WHERE due_at IS NOT NULL` — index partiel : seules les cartes programmées sont interrogées.

`ReviewSchedule` du §25 est fusionné ici. Une table séparée dupliquerait `due_at` et introduirait une incohérence possible entre les deux ; il n'y a jamais qu'une seule échéance par carte.

### `SessionRun`

| Champ | Type |
|---|---|
| `id` | UUID pk |
| `user_id` | fk |
| `lesson_id` | fk null |
| `day_number` | smallint |
| `started_at`, `completed_at` | timestamptz |
| `planned_items`, `completed_items` | smallint |
| `abandoned_at_index` | smallint null |
| `source` | enum `online`, `offline_sync` |

`abandoned_at_index` est le champ le plus utile de la table : il dit **à quel exercice précis** la séance meurt. Sans lui, on optimise la rétention à l'aveugle.

### `ExerciseAttempt`

| Champ | Type | Note |
|---|---|---|
| `id` | UUID pk | |
| `client_id` | UUID uq | **Généré par le téléphone.** Clé de déduplication du mode hors ligne |
| `session_run_id` | fk | |
| `exercise_id` | fk | |
| `skill_id` | fk | Dénormalisé : évite une jointure sur la requête d'analyse |
| `is_correct` | bool | |
| `latency_ms` | int | |
| `is_hesitation` | bool | |
| `level_before`, `level_after` | smallint | Trace : permet de rejouer l'historique |
| `answered_at` | timestamptz | Horodatage **client** |
| `received_at` | timestamptz | Horodatage **serveur** |

`uq (client_id)` est ce qui rend la synchronisation idempotente : un lot renvoyé trois fois n'écrit qu'une fois. Sans cette contrainte, une coupure réseau au mauvais moment fait progresser un utilisateur deux fois.

Deux horodatages parce que l'horloge d'un téléphone n'est pas fiable : `answered_at` sert à la pédagogie, `received_at` à l'audit.

---

## 4. Diagnostic

### `DiagnosticRun`

| Champ | Type | Note |
|---|---|---|
| `id` | UUID pk | |
| `user_id` | fk null | **Nullable** : le diagnostic se fait sans compte (§4) |
| `anonymous_key` | UUID | Rattachement au compte lors de l'inscription |
| `kind` | enum `initial`, `final` | |
| `score_letters`, `score_sounds`, `score_harakat`, `score_fusion`, `score_fluency` | smallint | 0 à 100 |
| `score_global` | smallint | Formule du §15 |
| `level` | smallint | 0 à 7 (§20) |
| `item_set_version` | varchar(10) | |

`item_set_version` est indispensable : comparer un jour 30 passé avec la v2 des items à un jour 0 passé avec la v1 n'a aucun sens. Si la version diffère, l'écran de comparaison le signale au lieu d'afficher un progrès faux.

### `DiagnosticItem`
Une ligne par question posée, avec la réponse et la latence. Conservé pour pouvoir **recalculer** un score si la formule évolue, sans avoir à refaire passer le test.

---

## 5. Lecture orale

### `AudioAttempt`

| Champ | Type | Note |
|---|---|---|
| `id` | UUID pk | |
| `user_id`, `skill_id` | fk | |
| `s3_key` | varchar(255) null | Null après la purge à 30 jours |
| `duration_ms`, `snr_db` | int | Mesurés sur le téléphone |
| `local_verdict` | enum | `ok`, `no_speech`, `too_short`, `too_noisy` — niveau L1 |
| `expires_at` | date | Cycle de vie S3 |
| `consent_id` | fk ConsentRecord | **Sans consentement, pas de ligne.** |

### `SpeechScore`
Séparée d'`AudioAttempt` : un même audio peut être réanalysé par un moteur plus récent, et on veut comparer.

| Champ | Type | Note |
|---|---|---|
| `audio_attempt_id` | fk | |
| `engine`, `engine_version` | varchar | Traçabilité indispensable pour L3 |
| `level` | enum `L1`, `L2`, `L3` | |
| `accuracy`, `fluency` | smallint null | 0 à 100 |
| `wpm` | smallint null | |
| `confidence` | numeric(4,3) | **Sous le seuil, aucun retour n'est affiché** |
| `phoneme_scores` | jsonb null | L3 uniquement |

---

## 6. Droits et paiement

Trois tables et non une. Voir [D3](05-decisions.md#d3--paiement-hybride-conforme-aux-plateformes).

```
Payment (une transaction)  ──►  Subscription (un contrat, facultatif)  ──►  Entitlement (un droit)
```

### `Payment`

| Champ | Type |
|---|---|
| `provider` | enum `play`, `apple`, `paydunya`, `wave`, `orange_money`, `card`, `manual` |
| `provider_ref` | varchar uq |
| `amount_xof` | int |
| `status` | enum `pending`, `paid`, `failed`, `refunded` |
| `raw_payload` | jsonb |

`raw_payload` conserve la charge utile du webhook telle quelle : les litiges de paiement se règlent sur la donnée d'origine.

### `Subscription` — absente pour un paiement unique

| Champ | Type | Note |
|---|---|---|
| `user_id` | fk | |
| `plan` | enum `program_once`, `premium_annual`, `premium_monthly` | Les offres de [D4](05-decisions.md#d4--modèle-économique--le-mensuel-nest-pas-le-cœur) |
| `state` | enum | Les huit états ci-dessous |
| `provider`, `provider_sub_id` | varchar | `provider_sub_id` = jeton d'achat Play / identifiant de transaction original Apple |
| `current_period_end` | timestamptz null | |
| `cancel_at_period_end` | bool | |
| `previous_plan` | varchar null | Trace d'un `plan_changed` |

**Les huit états du cycle de vie** ([D3](05-decisions.md#d3--paiement-hybride-conforme-aux-plateformes)) :

| État | Déclencheur | Effet sur `Entitlement` |
|---|---|---|
| `free` | par défaut | aucun droit payant |
| `program_purchased` | paiement unique confirmé | droit **sans** `expires_at` |
| `premium` | abonnement actif | droit avec `expires_at` |
| `expired` | échéance dépassée sans renouvellement | droit échu, données conservées |
| `renewed` | webhook de renouvellement | `expires_at` prolongé, sans interruption |
| `restored` | l'utilisateur restaure ses achats sur un nouvel appareil | droit rétabli à l'identique |
| `refunded` | remboursement Play / Apple / PSP | droit **révoqué** |
| `plan_changed` | passage d'une offre à l'autre | ancien droit clos, nouveau ouvert, proratisation |

`restored` et `refunded` sont les deux que l'on oublie, et ce sont exactement ceux qui provoquent les rejets de publication (Apple exige un bouton « Restaurer les achats ») et les litiges. Ils existent dès la première migration.

Le `provider_sub_id` est ce qui rend `restored` possible : à la réinstallation, l'application redemande ses achats à Play ou Apple, le serveur retrouve la souscription par ce jeton et rouvre le droit. Sans ce champ, un utilisateur qui change de téléphone perd ce qu'il a payé.

### `Entitlement` — la seule table interrogée par l'application

| Champ | Type |
|---|---|
| `user_id` | fk |
| `feature` | varchar(40) — `course.1`, `reading_mirror`, `speed_mode` |
| `granted_at`, `expires_at` | timestamptz |
| `source` | enum |

`idx (user_id, feature, expires_at)`.

Un paiement unique produit un `Entitlement` sans `expires_at` et sans `Subscription`. Un abonnement en produit un renouvelé par webhook. Une offre promotionnelle en produit un manuel. **L'application ne connaît que cette table** : `entitlements.has(user, "reading_mirror")`. Changer de moyen de paiement ne touche pas une ligne du code produit.

---

## 7. Gamification, notifications

### `Achievement` / `UserAchievement`
Définition en base, pas en dur : ajouter un badge ne doit pas exiger un déploiement.
Trois badges au MVP seulement — la gamification consomme du temps de développement et n'a jamais retenu personne qui n'apprenait pas déjà.

### `Notification`

| Champ | Type |
|---|---|
| `user_id` | fk |
| `kind` | enum `daily_reminder`, `streak_at_risk`, `review_due`, `weekly_report` |
| `scheduled_for` | timestamptz |
| `sent_at`, `opened_at` | timestamptz null |

Au MVP, les rappels quotidiens sont **locaux** (planifiés sur le téléphone) : pas de push serveur, pas de FCM, pas de clés à gérer. Le push serveur arrive quand on veut relancer les inactifs — ce qui suppose d'avoir des inactifs.

Règle produit : jamais de notification culpabilisante. Une série perdue repart à 1 sans écran d'échec.

---

## 8. Côté téléphone (SQLite / Drift)

Le mode hors ligne ([D2](05-decisions.md#d2--tout-fonctionne-hors-ligne)) exige un miroir local :

| Table locale | Rôle |
|---|---|
| `cached_lesson`, `cached_exercise`, `cached_media` | Contenu préchargé à la séance précédente |
| `local_mastery` | Copie de `MasteryState`, mise à jour immédiatement |
| `outbox` | File des tentatives à envoyer : `client_id`, `payload`, `attempts`, `last_error` |

Synchronisation : lot de 50, réessai à intervalle croissant, `client_id` pour la déduplication.
**Résolution de conflit :** en cas de divergence, le serveur retient le niveau de maîtrise **le plus bas**. On ne rend jamais une compétence acquise par accident de synchronisation — une compétence faussement acquise ne sera plus jamais révisée.

---

## 9. Volumétrie

Par utilisateur ayant terminé le parcours :

| Table | Lignes |
|---|---|
| `MasteryState` | ~297 |
| `ExerciseAttempt` | ~500 |
| `AudioAttempt` | ~90 |
| `SessionRun` | ~35 |

Soit **~900 lignes par utilisateur**. À 10 000 utilisateurs : 9 millions de lignes, dont 5 millions dans `ExerciseAttempt`. PostgreSQL absorbe cela sans partitionnement.

Le point de vigilance est `MasteryState`, lue et écrite à chaque exercice : elle doit rester en cache mémoire. Partitionner `ExerciseAttempt` par mois devient utile au-delà de ~50 000 utilisateurs, pas avant.
