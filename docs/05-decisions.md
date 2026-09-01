# Décisions d'architecture

**Arbitrages rendus le 29/08/2026. Ce document fait référence pour la suite du projet.**

## Correspondance des numérotations

Tes arbitrages emploient une numérotation différente de celle du blueprint initial. Voici la table de correspondance ; **la numérotation ci-dessous (D1…D12) est désormais la seule en vigueur**, les documents y renvoient.

| Ton n° | Sujet | N° en vigueur |
|---|---|---|
| D1 | Coach vocal IA | **D1** |
| D2 | Architecture adaptative par compétences | **D11** (nouvelle) |
| D3 | Paiement | **D3** |
| D4 | Modèle économique | **D4** |
| D5 | Contenu et corpus vocal | **D12** (nouvelle) |
| D6 | Progression des premières semaines | **D6** |
| — | Hors-ligne (tranché par moi, non contesté) | D2 |
| — | Admin Django, SRS, User, speech isolé, rendu arabe | D5, D7, D8, D9, D10 |

---

## D1 — Coach vocal : quatre niveaux progressifs

**✅ ARBITRÉ**

**Décision :** approche progressive validée, avec un MVP plus large que ma proposition initiale.

| Niveau | Contenu | Phase |
|---|---|---|
| **L0** — Miroir | Enregistrement, rejeu comparé à la référence, auto-évaluation à deux boutons | **MVP** |
| **L1** — Qualité du signal | VAD, durée, SNR. « Je n'ai rien entendu », « recommence dans un endroit plus calme » | **MVP** |
| **L1.5** — Transcription conditionnelle | **Transcription affichée uniquement si la fiabilité est suffisante**, retour simple sur la lecture (mots reconnus / non reconnus). Aucune prétention phonétique | **MVP** |
| **L2** — Fluidité | Vitesse de lecture, hésitations, omissions, répétitions | **Beta** |
| **L3** — Évaluation phonétique | Notation par phonème, en commençant par les difficultés majeures | **Après corpus** |

**Règles transverses, applicables à tous les niveaux :**

1. L'application **affiche toujours un niveau de confiance** quand l'analyse est incertaine.
2. Quand l'audio est insuffisant, elle **demande de recommencer** au lieu de produire un résultat dégradé.
3. L3 ne sera présenté comme fiable qu'après **mesure publiée des faux positifs et des faux négatifs** — seuils dans [04-speech.md §3](04-speech.md#3-le-corpus-dévaluation).
4. L3 attaque d'abord les difficultés les plus importantes : les emphatiques (ص ض ط ظ) et les gutturales (ع ح غ خ ق), là où un francophone échoue le plus.

**Ce que L1.5 ajoute par rapport à ma proposition initiale, et ce qu'il coûte :** la transcription conditionnelle est utile et honnête tant qu'elle reste descriptive (« voici ce que j'ai entendu »). Deux garde-fous techniques sont donc obligatoires, faute de quoi elle redevient un jugement déguisé :

- **Jamais sur un item isolé.** Une syllabe de 300 ms produit des hallucinations. L1.5 ne s'active que sur les mots et les phrases — à partir du jour 8 du parcours.
- **Seuil de confiance strict, et silence en dessous.** Le seuil se calibre sur les données de la beta, pas *a priori*. En attendant, valeur de départ conservatrice, et un compteur d'activation suivi en analytics : si L1.5 se tait dans plus de la moitié des cas, le problème est le seuil, pas l'utilisateur.

Détail complet : [04-speech.md](04-speech.md).

---

## D2 — Tout fonctionne hors ligne

**✅ TRANCHÉ (non contesté)**

SQLite local (Drift) = source de vérité *pendant* la séance ; le serveur = source de vérité *entre* les séances. Contenu du jour suivant préchargé, file `outbox` idempotente sur `client_id`, résolution de conflit au niveau de maîtrise **le plus bas**.

Marché initial : data prépayée, réseau instable. Une séance qui s'interrompt à la troisième carte est un utilisateur perdu.

---

## D3 — Paiement hybride, conforme aux plateformes

**✅ ARBITRÉ**

**Décision :** architecture hybride, sans aucun mécanisme de contournement des règles Google Play ou Apple.

| Canal | Moyens | Usage |
|---|---|---|
| **Android (in-app)** | Google Play Billing | Achats numériques faits dans l'application, lorsque les règles l'imposent |
| **Web** | Wave, Orange Money, carte bancaire | Sous réserve de disponibilité et des règles applicables |

**Compte unique, droits centralisés.** L'application et le site partagent le même `User` et le même service d'`Entitlement`. Le canal de paiement est une propriété de la transaction, jamais une variable du produit.

**Cycle de vie complet à prévoir dès l'architecture — les huit états :**

| État | Ce qu'il implique |
|---|---|
| `free` | Diagnostic, jours 1 à 3, exercices limités |
| `program_purchased` | Paiement unique, droit sans expiration |
| `premium` | Abonnement actif |
| `expired` | Droit échu, données conservées, réactivation en un geste |
| `renewed` | Prolongation par webhook, sans interruption |
| `restored` | Restauration d'achat — **obligatoire chez Apple, exigée par Google** |
| `refunded` | Révocation du droit sur remboursement |
| `plan_changed` | Passage d'une offre à l'autre, avec proratisation |

`restored` et `refunded` sont les deux que l'on oublie le plus souvent et qui provoquent des rejets de publication ou des litiges. Ils sont modélisés dès la première migration.

Conséquence sur les données : `Payment` → `Subscription` (facultative) → `Entitlement`. Détail dans [02-donnees.md §6](02-donnees.md#6-droits-et-paiement).

---

## D4 — Modèle économique : le mensuel n'est pas le cœur

**✅ ARBITRÉ**

**Décision :** trois offres testées, l'abonnement mensuel relégué au rang d'option.

| Offre | Prix (hypothèse) | Contenu |
|---|---|---|
| **Free** | 0 | Diagnostic, premières leçons, exercices limités |
| **Programme complet** — paiement unique | ~9 900 FCFA | Parcours intensif complet |
| **Premium annuel** | ~19 900 FCFA/an | Coach vocal, parcours avancés, statistiques, contenus supplémentaires |
| Mensuel (secondaire) | ~2 500–3 000 FCFA | Option, pas la vitrine |

Prix = hypothèses, à valider sur données réelles. Ils sont donc **servis par l'API** et jamais codés en dur dans l'application.

**Exigence de long terme :** après le parcours initial, l'utilisateur doit avoir de bonnes raisons de rester. Cela cesse d'être une question de marketing et devient une contrainte d'architecture :

- `Course` est plurielle dès le premier schéma — les parcours avancés ne sont pas une réécriture mais une insertion.
- Les `Entitlement` sont accordés **par fonctionnalité et par parcours** (`course.1`, `course.2`, `speed_mode`…), jamais par un simple booléen `is_premium`. C'est ce qui rend l'offre annuelle extensible sans migration.
- Le jour 30 n'affiche pas « terminé » mais une comparaison chiffrée **et** la suite disponible.

Ce que cela change dans le blueprint : l'annexe financière du §38 est recalculée sur ces trois offres — voir [00-blueprint.md](00-blueprint.md#annexe--scénarios-financiers-38).

---

## D5 — Admin Django au MVP, React plus tard

**✅ TRANCHÉ (non contesté)**

Tout ce que demande le §28 est couvert par l'admin Django : ~2 jours contre ~20. L'API `/api/admin/*` existe quand même dès le MVP pour que le front React de la phase 5 se branche sans réécrire le back.

---

## D6 — Variante B : lire avant de tout mémoriser

**✅ ARBITRÉ**

**Décision : variante B.** Aucun bloc de mémorisation des 28 lettres isolées avant de commencer à lire.

**Principe directeur :** APPRENDRE → UTILISER IMMÉDIATEMENT → RÉPÉTER → RENFORCER.

**Chaîne de progression :** lettres sélectionnées → sons → harakat → combinaisons → syllabes → mots → phrases → textes.

**Contrainte que tu poses, et qui compte autant que le reste :** la rigueur pédagogique ne se sacrifie pas à la gratification immédiate. Traduite en règles appliquées par le programme :

1. **Chaque fondamental garde sa journée entière** — sukun, madd, shadda, tanwin, article défini. Aucun n'est expédié pour aller plus vite aux textes.
2. **Les 28 lettres sont introduites sur 18 jours**, non sur 3. La lecture précoce vient de la *sélection* des premières lettres, pas d'une accélération.
3. **Les formes positionnelles s'apprennent avec la lettre**, le même jour, et non dans un bloc différé. Une lettre connue est une lettre connue dans les quatre positions.
4. **Zéro surprise, sans exception** : un mot n'apparaît que si toutes ses lettres et tous ses accents sont acquis.

**Le pivot :** les six lettres **ا د ذ ر ز و** ne se lient jamais à la lettre suivante. Elles gardent partout la forme apprise en isolé. En les enseignant d'abord, l'apprenant lit `وَرَد` au jour 3 sans avoir appris une seule forme positionnelle — aucune charge cachée.

Programme jour par jour : [01-pedagogie.md §2](01-pedagogie.md#2-programme-30-jours--variante-b-retenue).
La version §8 du cahier des charges est conservée en annexe, à titre de trace.

---

## D7 — Répétition espacée à règles fixes

**✅ TRANCHÉ (non contesté)**

Niveaux 0-4, intervalles 1/2/4/8 jours. SM-2 et FSRS ont besoin de 6 à 10 révisions par carte pour converger ; un parcours de 30 jours en donne 4 à 6. Ils produiraient du bruit, pas de la personnalisation. Migration envisageable au-delà de ~100 000 révisions réelles.

---

## D8 — Modèle User personnalisé au premier commit

**✅ TRANCHÉ — irréversible**

`AUTH_USER_MODEL` avant la première migration. Seul point non rattrapable du projet.

---

## D9 — Un seul service séparé : le speech

**✅ TRANCHÉ (non contesté)**

Cinq conteneurs : `api`, `worker`, `speech`, `postgres`, `redis`. Le speech est isolé parce que son profil de charge diffère et qu'on en changera le moteur. Rien d'autre n'est découpé.

---

## D10 — Le rendu des harakat est le risque technique n°1

**✅ TRANCHÉ — étape 1**

Police embarquée (jamais la police système), `TextHeightBehavior` et `height` explicites, validation sur Android 8 / 2 Go de RAM **avant** d'écrire le reste de l'interface.

C'est l'étape en cours. Voir [07-rendu-arabe.md](07-rendu-arabe.md).

---

## D11 — Architecture adaptative par compétences

**✅ ARBITRÉ**

**Décision :** architecture adaptative fondée sur les compétences, non un parcours linéaire.

Le système doit déterminer en permanence : ce que l'utilisateur sait · ce qu'il ne maîtrise pas · ce qu'il doit réviser · quand introduire une compétence nouvelle.

**Le programme de 30 jours est une structure de progression, pas une obligation.** Deux utilisateurs peuvent suivre des parcours légèrement différents selon leurs performances.

**Toutes les compétences sont modélisées individuellement** (~297, voir [01-pedagogie.md §1](01-pedagogie.md#1-taxonomie-des-compétences)), afin qu'un véritable moteur adaptatif puisse être construit ensuite sur cette base.

Conséquences déjà inscrites dans l'architecture, et désormais obligatoires :

- `Skill` est l'unité atomique ; `Lesson` n'est qu'une **vue** sur des compétences, jamais un conteneur d'exercices figé.
- Aucun écran ne demande « quelle est la leçon suivante ? ». Il demande « quelles compétences sont dues, et laquelle est prête ? ».
- La séance est composée **par le serveur** à l'exécution ([03-api.md](03-api.md#get-sessiontoday)) : le moteur adaptatif évolue sans publier une nouvelle version de l'application.
- `introduced_on_day` sur `Skill` est un **ordre par défaut**, que le moteur peut devancer ou retarder — pas un calendrier.
- Chaque tentative est conservée brute (`ExerciseAttempt`), avec sa latence. C'est la matière première du futur moteur adaptatif : sans elle, il n'y aura rien à entraîner le jour venu.

Ce que je ne fais **pas** au MVP : de l'apprentissage automatique. Le moteur reste à règles explicites ([00-blueprint.md §14](00-blueprint.md#14-moteur-adaptatif)). On accumule les données pour le suivant.

---

## D12 — Contenu et corpus vocal : deux chantiers parallèles

**✅ ARBITRÉ**

**Décision :** contenu pédagogique et corpus vocal sont deux chantiers prioritaires, menés **en parallèle** du développement, non à sa suite.

### Contenu pédagogique

| | |
|---|---|
| Volume initial | ~900 exercices, ~180 audios |
| Structure | Par compétence (~297) |
| Validation | **Chaque contenu est révisé et validé avant publication** |

Machine à états `draft → review → approved → published`, avec un `approved_by` qui ne peut pas être l'auteur, et immuabilité après publication ([02-donnees.md](02-donnees.md#contentversion--la-machine-à-états-du-47)).

### Corpus vocal

| Exigence | Traduction opérationnelle |
|---|---|
| Collecte au plus tôt | Démarre en phase A, avant le socle technique |
| Profils variés | Âges, genres, niveaux, Dakar et diaspora |
| Conditions documentées | Appareil, lieu, bruit ambiant, distance au micro — un formulaire par enregistrement |
| Consentements | Écrit, explicite, spécifique à l'usage « entraînement et évaluation », révocable |
| Anonymisation | Identifiant aléatoire ; aucun nom, aucun numéro dans les fichiers ni les métadonnées |
| Conservation | Durée définie, suppression effective à l'échéance, révocation honorée sous 30 jours |
| Annotation | Exploitable **avant** tout usage d'entraînement ou d'évaluation |

**Ta règle, et c'est la bonne :** un corpus plus petit et correctement annoté vaut mieux qu'un grand volume inexploitable. Un corpus non annoté ne mesure rien — il donne seulement l'illusion d'avoir des données.

J'ajoute une exigence qui découle de la tienne : **une double annotation sur ~20 % du corpus**, pour mesurer l'accord entre annotateurs. Si deux enseignants ne s'accordent que dans 70 % des cas sur ce qu'est un ض correct, aucun système automatique ne fera mieux, et il faut le savoir avant d'afficher un pourcentage.

Gouvernance détaillée : [04-speech.md §3](04-speech.md#3-le-corpus-dévaluation).
