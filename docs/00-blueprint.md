# IqraGo — Blueprint produit et technique

Version 2 — 29 août 2026. Document maître.
**Arbitrages rendus : les douze décisions sont tranchées** ([05-decisions.md](05-decisions.md)).
Développement en cours, étape 1 : [07-rendu-arabe.md](07-rendu-arabe.md).

---

## 1. Nom provisoire

**IqraGo** — de اقْرَأْ, « lis ». Le mot est immédiatement reconnu par la cible, se prononce sans effort en français et en wolof, et le suffixe le rend disponible en domaine et sur les stores là où « Iqra » seul est saturé.

À vérifier avant tout dépôt de marque ou achat de nom de domaine :
- disponibilité OAPI (Afrique de l'Ouest) et INPI (France, pour la diaspora) en classes 9, 41, 42 ;
- `iqrago.com`, `iqrago.sn`, `@iqrago` sur TikTok / Instagram / YouTube ;
- absence de collision sur Play Store et App Store.

Noms de repli, dans l'ordre : **Harf** (حرف, « la lettre »), **Qira**, **Nuur**, **Alif**.

Cette vérification prend une heure et doit être faite avant que le nom apparaisse dans les identifiants de package Android / iOS, où il devient très coûteux à changer.

---

## 2. Proposition de valeur

**Phrase produit :**
> Tu ne sais pas lire l'arabe. En un mois, mesure exactement combien tu as progressé.

**Ce qu'on promet :** une mesure avant / après, avec le même instrument aux deux bouts.
**Ce qu'on ne promet pas :** « tu sauras lire en 30 jours ». Cette phrase n'apparaît nulle part dans le produit tant qu'une cohorte réelle ne l'a pas validée (§36).

La preuve est intégrée au produit, pas au marketing : le diagnostic du jour 0 et l'évaluation du jour 30 utilisent **les mêmes items, dans le même ordre de difficulté**. L'écran final n'est pas une félicitation, c'est une comparaison.

**Pourquoi ce produit n'existe pas déjà :**

| Ce qui existe | Ce qui manque |
|---|---|
| Duolingo, Busuu | N'enseignent pas la lecture arabe à des francophones ; visent le vocabulaire |
| Applications de Coran | Supposent que l'utilisateur sait déjà lire |
| Daara, cours du soir | Hors ligne, non mesurés, horaires fixes, pas de rythme individuel |
| Vidéos YouTube | Passives, pas de correction, pas de mémoire de ce qui est acquis |

Le trou : **un parcours court, mesuré, mobile, en français, qui traite la lecture et rien d'autre.**

---

## 3. Personas

### Mamadou — 24 ans, Dakar, la cible principale
Bac+2, travaille dans le commerce. A fait le daara enfant : il récite de mémoire mais ne décode pas. Vit cela comme un manque personnel, pas comme un projet scolaire.
Android milieu de gamme, data prépayée achetée par tranches, Wave installé, pas de carte bancaire. Apprend dans les transports, le soir.
**Abandonne si :** la séance exige du réseau, dépasse 20 minutes, ou ne montre rien de lisible avant une semaine.
**Ce que le produit doit faire :** fonctionner à zéro barre, et lui faire lire un vrai mot arabe le plus tôt possible.

### Aïssatou — 32 ans, Paris, la diaspora
Née en France, parents sénégalais. Veut lire pour accompagner ses enfants à l'école coranique et ne pas transmettre son propre manque.
iPhone, carte bancaire, wifi permanent. Habituée aux abonnements.
**Abandonne si :** elle se sent infantilisée, ou si le produit est visiblement moins soigné que les apps qu'elle utilise déjà.
**Ce que le produit doit faire :** un niveau de finition occidental, et un mode « famille » à terme (§31).

### Ibrahima — 45 ans, Thiès, la motivation religieuse
Commerçant. Objectif explicite : lire les textes religieux lui-même. Patient, régulier, peu à l'aise avec la technique.
Android bas de gamme, 2 Go de RAM, Android 8, écran 5 pouces, connexion instable.
**Abandonne si :** l'application rame, si le texte arabe est petit, ou s'il se perd dans la navigation.
**Ce que le produit doit faire :** tourner sur son téléphone, gros caractères, un seul bouton par écran — et lui montrer que le parcours 2 existe.

### Fatou — 19 ans, étudiante, l'accélératrice
Curiosité linguistique, aucune pratique religieuse particulière. Apprend vite, teste beaucoup d'applications, en abandonne la plupart.
**Abandonne si :** le rythme est imposé et qu'elle doit attendre demain pour continuer.
**Ce que le produit doit faire :** la laisser enchaîner plusieurs séances, tout en lui expliquant que les révisions, elles, se répartissent dans le temps.

**Ce que ces quatre personas imposent, ensemble :** hors ligne, léger, gros texte, un seul bouton principal par écran, paiement mobile money, rythme non bloquant.

---

## 4. Parcours utilisateur

```
TikTok / WhatsApp
      ↓
Landing page ── « Tester mon niveau gratuitement »
      ↓
DIAGNOSTIC (3-5 min, sans compte)          ← l'outil d'acquisition (§33)
      ↓
Écran de profil : « Score global 18/100 »
      ↓
Création de compte pour SAUVEGARDER le résultat  ← le compte se justifie par le résultat
      ↓
Onboarding (3 questions : niveau, temps, objectif)
      ↓
Jour 1 ─ Jour 2 ─ Jour 3          gratuit, sans friction
      ↓
Paywall au jour 4                  après le premier vrai résultat, jamais avant
      ↓
Jours 4-29 : boucle quotidienne
      ↓
Jour 30 : évaluation finale, comparée au jour 0
      ↓
Écran de progression partageable   ← boucle d'acquisition
      ↓
Rétention : parcours 2, ou mode entretien
```

**Deux décisions de parcours qui comptent :**

Le diagnostic se fait **sans compte**. Demander une inscription avant d'avoir donné quoi que ce soit coupe le tunnel de moitié. Le résultat est stocké localement et rattaché au compte à l'inscription.

Le paywall arrive **au jour 4**, pas au jour 1. Trois séances complètes, c'est assez pour que l'utilisateur ait ressenti la progression et pas assez pour qu'il ait fini. C'est le moment où la valeur perçue est maximale par rapport à ce qu'il a payé (rien).

---

## 5. Architecture fonctionnelle

Huit domaines. Chacun devient un module Django et une feature Flutter.

| Domaine | Responsabilité | Dépend de |
|---|---|---|
| **Identité** | Compte, session, consentements (vocal, analytics) | — |
| **Profil** | Niveau déclaré, temps quotidien, objectif, langue | Identité |
| **Catalogue** | Cours, modules, leçons, compétences, exercices, médias, versions | — |
| **Diagnostic** | Test initial, calcul du profil, évaluation finale | Catalogue |
| **Apprentissage** | Composition de séance, tentatives, maîtrise, révisions | Catalogue, Profil |
| **Lecture orale** | Capture, envoi, analyse, restitution | Apprentissage |
| **Droits** | Ce que l'utilisateur peut faire, d'où que vienne le paiement | Identité |
| **Mesure** | Événements, statistiques utilisateur, KPI | tous |

La règle qui structure tout : **le Catalogue ne connaît aucun utilisateur, l'Apprentissage ne connaît aucun paiement.** Le domaine Droits est interrogé par une seule fonction, `entitlements.has(user, feature)`, appelée depuis les vues — jamais depuis les modèles.

---

## 6. Architecture technique

```
   Flutter (Android, iOS)
     │  SQLite local (Drift) = vérité pendant la séance
     │  file d'attente `outbox`
     ↓  HTTPS / JSON
   Django + DRF  ──────────►  PostgreSQL
     │                          ▲
     ├──► Redis  ──► Celery ────┘
     │                 │
     │                 ↓
     └──────────► Speech Service (FastAPI, conteneur séparé)
                       │
                       └──► S3 (audio privé, cycle de vie 30 j)
```

**Cinq conteneurs au MVP :** `api`, `worker`, `speech`, `postgres`, `redis`.
Un seul `docker-compose.yml`, trois fichiers d'environnement (dev / staging / prod).

**Ce qui est volontairement absent :** passerelle d'API, service mesh, découpage en microservices, Kubernetes. Voir [D9](05-decisions.md#d9--un-seul-service-séparé--le-speech).

**Choix et justification courte :**

| Choix | Pourquoi |
|---|---|
| Flutter | Un code pour Android et iOS ; le rendu du texte arabe passe par Skia, contrôlable — contrairement aux WebView |
| Django + DRF | Admin gratuit (D5), auth mature, ORM sûr sur des relations profondes |
| PostgreSQL | Contraintes réelles, JSONB pour le contenu variable des exercices |
| Redis + Celery | L'analyse audio ne doit jamais bloquer une requête HTTP |
| FastAPI pour le speech | Charge des modèles au démarrage, garde le processus chaud, async natif |
| S3 compatible | Les audios ne passent pas par Django : URL présignées, upload direct |

---

## 7. Base de données

Détail complet : [02-donnees.md](02-donnees.md).

Les cinq points structurants :

1. **`User` personnalisé dès la première migration** ([D8](05-decisions.md#d8--modèle-user-personnalisé-au-premier-commit)) — irréversible.
2. **`Skill` est l'unité atomique**, pas `Lesson`. Une leçon est une vue sur des compétences. C'est ce qui rend le §10 possible.
3. **`MasteryState`** (user × skill) est la table chaude : une ligne par compétence et par utilisateur, ~230 lignes par utilisateur, lue à chaque composition de séance. Index sur `(user_id, due_at)`.
4. **`ContentVersion`** rend le contenu immuable après publication : on ne modifie pas une leçon publiée, on publie une version suivante. Sans cela, corriger une faute change rétroactivement ce que les utilisateurs ont vu, et fausse toute analyse.
5. **`Entitlement`** est séparé de `Subscription` et de `Payment` ([D3](05-decisions.md#d3--paiement-hybride-conforme-aux-plateformes)).

---

## 8. Architecture IA

Détail complet : [04-speech.md](04-speech.md). Résumé :

**Trois usages distincts de l'IA, à ne jamais confondre :**

| Usage | Technique | Rôle | Statut |
|---|---|---|---|
| Miroir + qualité du signal | VAD local | Rejoue, et dit seulement s'il a entendu | **MVP** (L0, L1) |
| Transcription conditionnelle | faster-whisper | Affiche ce qu'il a entendu **si la confiance suffit** ; mots et phrases seulement | **MVP** (L1.5) |
| Alignement + fluidité | CTC-segmentation | Vitesse, hésitations, omissions, répétitions | Beta (L2) |
| Prononciation | GOP sur modèle acoustique | Dit *quel phonème* est raté | Après corpus (L3) |
| Explication, variantes, encouragements | LLM | Rédige, ne note jamais | MVP, hors des séances |

**Les deux règles qui protègent l'utilisateur** ([D1](05-decisions.md#d1--coach-vocal--quatre-niveaux-progressifs)) :

1. **Un niveau de confiance est toujours affiché** quand l'analyse est incertaine.
2. **Quand l'audio est insuffisant, le système demande de recommencer** au lieu de produire un résultat dégradé. Il ne dit pas « c'est faux », il dit « je n'ai pas bien entendu ».

Un coach qui hésite reste crédible ; un coach qui se trompe avec assurance ne l'est plus jamais.

**L'abstraction `SpeechService`** (§13) est une interface à trois méthodes, implémentée par des adaptateurs interchangeables :

```python
class SpeechService(Protocol):
    def check_signal(audio) -> SignalReport      # L1
    def align(audio, expected) -> Alignment      # L2
    def score(alignment) -> PronunciationScore   # L3
```

L'implémentation MVP (`NullSpeechService`) ne renvoie que `check_signal`. Le reste de l'application n'a pas à savoir laquelle tourne.

---

## 9. Architecture audio

**Deux flux qui n'ont rien en commun.**

### Sortie — écouter (§16)
Chaque contenu arabe a un audio de référence, **enregistré par un humain**, pas synthétisé. Une voix TTS sur `ضَ` produit une approximation, et l'utilisateur imite ce qu'il entend : une référence approximative enseigne une erreur.

Volume à produire : ~28 lettres × 3 harakat + ~60 mots + ~30 phrases ≈ **180 fichiers**. Une journée de studio avec un locuteur natif. C'est le seul poste de contenu qu'on ne peut pas générer.

Format : Opus 24 kbps mono (~4 Ko/seconde). Le pack complet tient sous 3 Mo, embarqué dans l'application — donc disponible hors ligne, sans téléchargement.

Vitesses 0,75× / 1× / 1,25× par étirement temporel côté client (`just_audio`), pas trois fichiers.

Le TTS reste utilisé pour le contenu **généré** (phrases d'entraînement du parcours 2, plus tard), jamais pour le référentiel.

### Entrée — être entendu (§13)
```
Micro (16 kHz mono PCM)
  → gain automatique + filtre passe-haut 80 Hz
  → VAD : découpe le silence, mesure durée utile et SNR
  → si signal insuffisant : retour immédiat, local, aucun envoi
  → sinon : Opus, upload S3 présigné, tâche Celery
  → SpeechService (L1/L2/L3 selon disponibilité)
  → SpeechScore en base
  → notification push locale ou affichage au retour sur l'écran
```

Le point important : **le VAD tourne sur le téléphone**. 80 % des enregistrements ratés (rien dit, trop court, trop bruyant) sont détectés sans consommer un octet de data ni une seconde de serveur.

**Conservation :** audio supprimé à 30 jours par cycle de vie S3. Consentement explicite requis avant le premier enregistrement. `DELETE /me` purge immédiatement.

---

## 10. Architecture pédagogique

Détail : [01-pedagogie.md](01-pedagogie.md).

Le principe du §10, formulé en une contrainte de code :

> **Aucun écran ne peut demander « quelle est la leçon suivante ? ».**
> Il demande « quelles compétences sont dues, et laquelle est prête à être introduite ? »

Cela se traduit par trois règles appliquées par le moteur :

1. **Verrou de prérequis** — une compétence n'est introduite que si tous ses prérequis sont à un niveau ≥ 3.
2. **Zéro surprise** — un item composé (syllabe, mot, phrase) n'est jamais présenté si l'un de ses atomes est à un niveau < 2. Un mot n'apparaît que quand toutes ses lettres et tous ses accents sont acquis.
3. **Plancher de révision** — tant qu'une compétence est due, deux places de la séance lui restent réservées, même un jour chargé en nouveautés.

---

## 11. Programme 30 jours

Détail jour par jour : [01-pedagogie.md](01-pedagogie.md) §2.
**Variante B retenue** ([D6](05-decisions.md#d6--variante-b--lire-avant-de-tout-mémoriser)) : les 28 lettres réparties sur 18 jours au lieu de 3, premier mot lu au **jour 3**, formes positionnelles apprises avec la lettre. La version §8 du cahier des charges est conservée en annexe de [01-pedagogie.md](01-pedagogie.md#4-annexe--la-version-8-du-cahier-des-charges-écartée).

---

## 12. Compétences

Taxonomie complète : [01-pedagogie.md](01-pedagogie.md) §1.

Ordre de grandeur, qui conditionne le plan de production de contenu :

| Type | Nombre |
|---|---|
| `letter.*.recognize` | 28 |
| `letter.*.sound` | 28 |
| `letter.*.form.{initial,medial,final}` | 66 |
| `haraka.*` | 3 |
| `syllable.*` | 84 |
| `mark.*` (sukun, madd, shadda, tanwin) | 8 |
| `contrast.*` (paires confondues) | 12 |
| `word.*` | ~60 |
| `fluency.level.*` | 7 |
| **Total** | **≈ 297** |

Chaque compétence a besoin d'au moins 3 exercices distincts pour ne pas être mémorisée par sa présentation plutôt que par son contenu. **Environ 900 exercices à produire.** C'est le vrai chemin critique du projet, plus long que le développement.

---

## 13. Types d'exercices

Détail : [01-pedagogie.md](01-pedagogie.md) §3. Treize types, dont neuf au MVP.

---

## 14. Moteur adaptatif

```python
def compose_session(user, day):
    slots = SLOTS[user.daily_minutes]        # 10min→10, 15→14, 20→18, 30→26

    due = mastery.due(user, today)            # niveau croissant, échéance croissante
    new = catalog.unlockable(user, day)       # prérequis tous à niveau >= 3

    # 1. plancher : les révisions ne sont jamais totalement évincées
    reserved = min(len(due), max(2, int(slots * 0.30)))

    # 2. plafond : une longue absence ne produit pas une séance de 40 minutes
    due_taken = min(len(due), int(slots * 0.50))
    due_taken = max(due_taken, reserved)

    items  = pick(due, due_taken)
    items += pick(new, slots - due_taken - 1)
    items += pick(mastery.weakest(user, level__lt=3), remaining)

    # 3. toute séance se termine par une lecture réelle
    items += [reading_item(user)]             # composé uniquement de l'acquis
    return items
```

**Adaptation en cours de séance :**
- 3 échecs consécutifs sur la même famille → on bascule sur un type d'exercice plus facile pour cette famille, et le bloc de nouveauté est écourté. Protéger l'utilisateur de la séance qui s'effondre est plus important que finir le programme du jour.
- 5 réussites rapides consécutives → un item supplémentaire de niveau supérieur est proposé, sans engagement.

**Ce que le moteur ne fait jamais :** afficher une dette. Les cartes en retard attendent leur tour. Un compteur « 47 révisions en retard » est la première cause d'abandon des applications à répétition espacée.

---

## 15. Système de scoring

Trois scores distincts, jamais mélangés.

### a. `attempt` — une tentative
```
correct: bool
latency_ms: int
hesitation: bool = correct and latency_ms > seuil(skill.type)
```

Seuils d'automatisation — c'est par eux qu'on mesure le passage **analytique → automatique** (§11) :

| Type d'item | Seuil |
|---|---|
| lettre | 1 500 ms |
| syllabe | 2 000 ms |
| mot | 3 500 ms |
| phrase | 350 ms / caractère |

**Une réponse juste mais lente ne fait pas monter le niveau.** C'est le mécanisme qui produit de la fluidité au lieu d'une simple exactitude. Sans lui, on entraîne des gens qui répondent bien en cinq secondes — c'est-à-dire qui épellent.

### b. `mastery_level` — 0 à 4, par compétence
Voir §16.

### c. `profile_score` — 0 à 100, deux fois dans la vie de l'utilisateur

```
score = 0.20 × lettres
      + 0.20 × sons
      + 0.20 × harakat
      + 0.25 × fusion
      + 0.15 × fluidité
```

La fusion pèse le plus : c'est la compétence qui distingue « je connais les lettres » de « je lis » (§11).

Ce score est calculé **au jour 0 et au jour 30, avec les mêmes items**. C'est ce qui rend la comparaison valide et la promesse du §2 démontrable. Il n'est jamais affiché pendant le parcours : un score global quotidien encourage l'optimisation du chiffre au lieu de l'apprentissage.

---

## 16. Répétition espacée

Niveaux et intervalles :

| Niveau | Nom | Prochaine révision |
|---|---|---|
| 0 | inconnue | — |
| 1 | découverte | +1 jour |
| 2 | fragile | +2 jours |
| 3 | solide | +4 jours |
| 4 | acquise | +8 jours |

Transitions :

| Résultat | Effet |
|---|---|
| juste et rapide | niveau +1 (plafond 4) |
| juste mais hésitant | niveau inchangé, échéance demain |
| faux | niveau −1 (plancher 1), **remise en fin de séance**, puis demain |

**Une carte ratée ne revient jamais immédiatement.** Réussir dix secondes après un échec ne teste que la mémoire de travail et produit un faux signal de maîtrise.

Un aléa de ±10 % est appliqué aux intervalles pour éviter que toutes les cartes d'un même jour ne reviennent ensemble.

Justification du choix « règles fixes » : [D7](05-decisions.md#d7--répétition-espacée-à-règles-fixes).

---

## 17. Architecture Flutter

```
lib/
  main.dart
  app/          router (go_router), theme, l10n, injection
  core/
    error/      Failure, Result<T>
    network/    dio, intercepteurs (auth, retry, hors-ligne)
    db/         drift : schéma local, outbox, migrations
    audio/      lecteur, enregistreur, VAD
    sync/       moteur de synchronisation
  features/
    onboarding/     data | domain | presentation
    diagnostic/
    session/        le cœur : composition, exercices, résultat
    reading/        miroir de lecture
    progress/
    subscription/
    profile/
  shared/
    widgets/    ArabicText, HarakatText, MicButton, MasteryBar, PrimaryButton
```

**Gestion d'état : Riverpod 2 avec génération de code.** Contre Bloc : moins de code répétitif pour un développeur seul, injection vérifiée à la compilation, et gestion naturelle de l'asynchrone — ce qui compte quand tout passe par une base locale et une file de synchronisation.

**Trois contraintes non négociables, issues des personas :**
1. `ArabicText` est le **seul** widget autorisé à afficher de l'arabe. Police embarquée, `height` explicite, taille minimale 32 sp pour les items d'exercice. Voir [D10](05-decisions.md#d10--le-rendu-des-harakat-est-le-risque-technique-n1).
2. Aucun écran ne bloque sur le réseau. Toute vue a un état hors ligne fonctionnel.
3. Un seul bouton d'action principale par écran (§45). Contrainte vérifiée en revue, pas seulement en design.

**Tests :** widget tests sur les cinq écrans du tunnel, test d'intégration sur « onboarding → diagnostic → jour 1 → synchronisation », golden tests sur le rendu arabe (c'est là que les régressions passent inaperçues).

---

## 18. Architecture Django

```
backend/
  config/
    settings/   base.py, dev.py, staging.py, prod.py
    urls.py  celery.py  asgi.py  wsgi.py
  apps/
    accounts/       User, authentification, JWT, consentements
    profiles/       Profile, Goal, préférences
    catalog/        Course, Module, Lesson, Skill, Exercise, Media, ContentVersion
    learning/       MasteryState, ReviewSchedule, SessionRun, ExerciseAttempt
    diagnostic/     DiagnosticRun, DiagnosticItem, calcul du profil
    speech/         AudioAttempt, SpeechScore, client SpeechService
    billing/        Subscription, Payment, Entitlement, webhooks
    notifications/  planification, envoi, préférences
    analytics/      ingestion d'événements, relais PostHog
  common/           permissions, pagination, throttling, mixins, types
  tests/
```

**Conventions imposées dès le départ :**
- Toute logique métier dans `apps/<app>/services.py`. Les vues valident et délèguent ; les modèles ne contiennent pas de règles métier.
- Sérialiseurs séparés en lecture et écriture — ils divergent toujours, et les fusionner produit des failles d'écriture sur des champs en lecture seule.
- Aucune requête dans une boucle : `select_related` / `prefetch_related` systématiques sur les vues de séance, qui touchent 4 tables jointes.
- `python manage.py check --deploy` sans avertissement, en CI, avant tout déploiement.

---

## 19. Back-office

**MVP : admin Django.** Voir [D5](05-decisions.md#d5--admin-django-au-mvp-react-plus-tard).

La machine à états du contenu (§47) est réelle, pas décorative :

```
draft ──► review ──► approved ──► published
  ▲                                   │
  └────────── nouvelle version ◄──────┘
```

- `review` : verrouille l'édition, notifie le relecteur.
- `approved` : signé par un `approved_by` qui ne peut pas être l'auteur.
- `published` : **immuable**. Toute correction crée une version suivante.
- Dépublier ne supprime rien : `unpublished_at` est renseigné, le contenu reste lisible pour les utilisateurs qui l'ont déjà vu.

**Phase 5 : React + TypeScript + Tailwind**, branché sur `/api/admin/*`, quand une personne dédiée au contenu rejoint le projet.

---

## 20. API

Contrat complet : [03-api.md](03-api.md).

Principes : REST, JSON, versionnée sous `/api/v1/`, authentification JWT.
Deux endpoints portent la logique du produit :
- `GET /api/v1/session/today` — renvoie une séance **déjà composée** par le serveur. Le client n'implémente aucune pédagogie.
- `POST /api/v1/session/sync` — lot idempotent de tentatives, avec `client_id` pour la déduplication. C'est le pivot du mode hors ligne.

---

## 21. Abonnement

Arbitré : [D3](05-decisions.md#d3--paiement-hybride-conforme-aux-plateformes) (circuit) et [D4](05-decisions.md#d4--modèle-économique--le-mensuel-nest-pas-le-cœur) (offres).

**Grille retenue pour le test — le mensuel n'est pas la vitrine :**

| Offre | Prix (hypothèse) | ≈ € | Contenu |
|---|---|---|---|
| **Free** | 0 | — | Diagnostic, premières leçons, exercices limités |
| **Programme complet** — paiement unique | 9 900 FCFA | 15,09 € | Parcours intensif complet |
| **Premium annuel** | 19 900 FCFA/an | 30,34 € | Coach vocal, parcours avancés, statistiques, contenus supplémentaires |
| Mensuel (option secondaire) | 2 500–3 000 FCFA | 3,81–4,57 € | — |

Prix = hypothèses à valider sur données réelles, donc **servis par l'API** et jamais codés en dur.

**Circuit de paiement.** Google Play Billing pour les achats in-app sur Android lorsque les règles l'imposent ; web (Wave, Orange Money, carte) sous réserve de disponibilité. Compte unique et droits centralisés entre l'application et le site. **Aucun mécanisme de contournement des règles Google Play ou Apple.**

**Modèle technique :** `Payment` (transaction) → `Subscription` (contrat, absent pour un paiement unique) → `Entitlement` (droit : `feature`, `expires_at`, `source`). Le serveur fait autorité ; le client met en cache un jeton signé avec **7 jours de tolérance hors ligne** — sans quoi un utilisateur payant perd l'accès dans les transports.

**Les huit états du cycle de vie**, modélisés dès la première migration : `free`, `program_purchased`, `premium`, `expired`, `renewed`, `restored`, `refunded`, `plan_changed`. Les deux qu'on oublie — `restored` et `refunded` — sont ceux qui provoquent les rejets de publication et les litiges.

**Rétention après le jour 30** ([D4](05-decisions.md#d4--modèle-économique--le-mensuel-nest-pas-le-cœur)) : `Course` est plurielle dès le premier schéma, et les droits sont accordés par fonctionnalité et par parcours (`course.1`, `course.2`, `speed_mode`), jamais par un booléen `is_premium`. Ajouter un parcours avancé est une insertion, pas une migration.

---

## 22. Analytics

PostHog, hébergement UE (la persona diaspora place le projet sous RGPD).

Les 14 événements du §29, plus quatre que je juge indispensables :

```
session_abandoned        { day, item_index, item_type }   ← où exactement on perd les gens
mastery_level_changed    { skill_id, from, to }
audio_rejected_local     { reason: no_speech|too_short|too_noisy }
paywall_dismissed        { day, seconds_visible }
```

`session_abandoned` est le plus important du lot : il indique l'exercice précis sur lequel la séance meurt. Sans lui, on optimise à l'aveugle.

**Interdits :** aucun audio, aucun e-mail, aucun nom, aucun contenu de réponse libre. Identifiant pseudonyme, dissocié du compte. Consentement demandé, refusable, et le refus n'altère aucune fonctionnalité.

---

## 23. Sécurité

| Sujet | Mesure |
|---|---|
| Transport | HTTPS seul, HSTS, `SECURE_SSL_REDIRECT`, cookies `Secure` + `HttpOnly` + `SameSite=Lax` |
| Mots de passe | Argon2 (`argon2-cffi`), pas le PBKDF2 par défaut |
| Jetons | Accès 15 min, rafraîchissement 30 j avec rotation et liste noire |
| Débit | 5/min sur la connexion, 20/h sur l'envoi audio, 100/min global par IP |
| Accès | Permissions DRF par objet ; jamais de filtre d'autorisation côté client |
| Audio | Bucket privé, URL présignées 10 min, cycle de vie 30 j, consentement obligatoire |
| Suppression | `DELETE /api/v1/me` : purge audio immédiate, anonymisation des tentatives, 30 j de rétention légale des paiements |
| Secrets | `django-environ` + SOPS. Jamais dans le dépôt. Rotation documentée |
| Sauvegardes | Dump PostgreSQL quotidien chiffré, hors du serveur, **restauration testée une fois par mois** |
| Journaux | Structurés JSON, sans données personnelles, Sentry avec `send_default_pii=False` |
| Dépendances | `pip-audit` et `flutter pub outdated` en CI, bloquants sur sévérité haute |

**Le point qui mérite d'être traité sérieusement :** la voix est une donnée à caractère personnel, proche du biométrique. Consentement explicite, séparé de celui des analytics, révocable, avec une finalité écrite en français simple à l'écran — pas enterrée dans des CGU.

---

## 24. Roadmap

Détail et jalons : [06-roadmap.md](06-roadmap.md).

| Phase | Contenu | Durée estimée |
|---|---|---|
| 1 | Recherche pédagogique, arbitrage D1/D3/D4/D6, corpus audio | 3 semaines |
| 2 | Socle technique + prototype vertical (1 exercice de bout en bout) | 3 semaines |
| 3 | MVP complet | 8 semaines |
| 4 | Beta fermée, 50 à 200 utilisateurs | 6 semaines |
| 5 | Lancement, back-office React, paiement élargi | 4 semaines |
| 6 | Coach vocal L3, parcours 2 | 8 semaines |
| 7 | Autres langues d'interface, B2B | — |

Total jusqu'au lancement : **environ 6 mois** à un développeur à temps plein, en supposant que la production de contenu avance en parallèle et non en série.

---

## 25. MVP

**Dedans :**
onboarding · diagnostic · programme 30 jours variante B · compétences (~297, modélisées individuellement) · leçons · exercices (9 types) · audio de référence hors ligne · miroir de lecture **L0 + L1 + L1.5** · scoring · répétition espacée · progression · statistiques · notifications locales · Play Billing + web + droits centralisés (8 états) · admin Django · synchronisation hors ligne.

**Dehors, explicitement :**
fluidité L2 (beta) · évaluation phonétique L3 (après corpus) · TTS · parcours avancés · back-office React · pack famille · B2B et tableau de bord enseignant · classements · social · chat LLM · badges au-delà de trois · autres langues d'interface · iOS si le budget est contraint (Android d'abord : c'est l'essentiel du marché sénégalais).

**Le critère de fin de MVP**, en une phrase :
> Un utilisateur inconnu installe l'application, fait son diagnostic, suit trente séances hors ligne, paie en FCFA, et l'écran du jour 30 lui montre une comparaison exacte avec son jour 0 — sans qu'aucune donnée soit simulée.

---

## 26. Complexité par module

Échelle : **S** ≤ 3 j · **M** 4-8 j · **L** 9-15 j · **XL** > 15 j. Un développeur.

| Module | Complexité | Risque | Note |
|---|---|---|---|
| Auth + User + JWT | M | faible | Chemin balisé |
| Profil + onboarding | S | faible | |
| Catalogue + ContentVersion | L | moyen | La machine à états est le vrai travail |
| Admin Django | S | faible | 2 j si les modèles sont propres |
| Moteur de compétences + prérequis | L | **élevé** | Cœur du produit, à tester unitairement en premier |
| Répétition espacée | M | moyen | Simple à coder, subtil à régler |
| Composition de séance | L | **élevé** | Beaucoup de cas limites (jour 1, longue absence, rattrapage) |
| Diagnostic + scoring | M | moyen | Doit être réutilisable au jour 30 : même code, même items |
| Moteur d'exercices Flutter | XL | **élevé** | 9 types × états × hors ligne |
| Rendu du texte arabe | M | **élevé** | Risque technique n°1, à lever en semaine 1 |
| Audio en lecture | M | moyen | Le studio est le chemin critique, pas le code |
| Miroir de lecture L0/L1 | M | moyen | Le VAD local est la partie délicate |
| Speech Service L2 | L | **élevé** | Alignement forcé, hors MVP |
| Speech Service L3 | XL | **très élevé** | Bloqué par le corpus, pas par le code |
| Synchronisation hors ligne | L | **élevé** | Idempotence, conflits, rejeu |
| Droits + paiement | L | **élevé** | Risque juridique, pas technique |
| Analytics | S | faible | |
| Notifications | S | faible | Locales au MVP |
| Statistiques | M | faible | |
| Docker + CI/CD | M | faible | |
| **Contenu pédagogique (~900 exercices)** | **XL** | **très élevé** | **Le vrai chemin critique** |

**Ce que ce tableau dit :** les deux plus gros risques du projet ne sont pas du code. Ce sont **la production du contenu** et **le corpus d'évaluation vocale**. Les deux se lancent en phase 1, en parallèle du développement, ou le projet glisse de plusieurs mois.

---

## Annexe — Scénarios financiers (§38)

Ces chiffres sont des **simulations**, pas des prévisions. Aucune n'est atteignable sans validation préalable du §36.

Avec les offres de [D4](05-decisions.md#d4--modèle-économique--le-mensuel-nest-pas-le-cœur), **l'unité de mesure change** : ce n'est plus « le nombre d'abonnés » mais **le nombre d'acheteurs par mois**. Un paiement unique ne produit pas de MRR.

Hypothèse de mixte : 70 % « programme complet » (9 900) + 30 % « premium annuel » (19 900) → **revenu moyen par acheteur ≈ 12 900 FCFA**.
Hypothèse de conversion gratuit → payant : 3 % (fourchette haute d'un freemium bien exécuté).

| Acheteurs / mois | Revenu brut / mois | Installations nécessaires | Réaliste ? |
|---|---|---|---|
| 500 | 6 450 000 FCFA | ~16 700 | Atteignable en organique sur 6-12 mois |
| 2 000 | 25 800 000 FCFA | ~66 700 | Demande une acquisition payante rentable |
| 5 000 | 64 500 000 FCFA | ~166 700 | Nécessite plusieurs marchés |
| 20 000 | 258 000 000 FCFA | ~666 700 | Horizon 3-5 ans, pas un objectif de lancement |

**Ce que ces chiffres cachent.** Le paiement unique encaisse davantage par acheteur, mais **il n'y a pas de base récurrente sous les pieds** : le mois où l'acquisition s'arrête, le revenu s'arrête. Seul le premium annuel se renouvelle. Le tableau ci-dessus décrit donc une machine à acquisition, pas une rente.

**Plafond de CAC.** À 12 900 FCFA par acheteur et 3 % de conversion, chaque installation rapporte ~390 FCFA brut. Pour garder une marge après coûts, viser un **CAC sous ~4 000 FCFA par acheteur** — soit ~120 FCFA par installation. C'est atteignable en organique (TikTok, WhatsApp), tendu en publicité payante. **Le canal organique n'est pas un choix de départ modeste : c'est la condition de rentabilité du modèle.**

**Le brut n'est pas le net.** À déduire : commission de la plateforme (15-30 % sur Play Billing, 2-3 % en mobile money — l'écart est considérable et justifie que le web soit privilégié quand les règles le permettent), infrastructure (~50 000 FCFA/mois jusqu'à 5 000 utilisateurs actifs), inférence audio quand L2/L3 tournent (~4 à 12 min de CPU par parcours, voir [04-speech.md §6](04-speech.md#6-coûts)), production de contenu, corpus vocal, support.

**Le levier de long terme reste la rétention après le jour 30.** Un acheteur du « programme complet » qui prend ensuite le premium annuel double sa valeur. C'est la raison pour laquelle les parcours avancés sont une contrainte d'architecture ([D4](05-decisions.md#d4--modèle-économique--le-mensuel-nest-pas-le-cœur)) et non une idée pour plus tard.
