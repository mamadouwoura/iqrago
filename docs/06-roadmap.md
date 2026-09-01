# Roadmap et ordre exact de développement

---

## Le principe qui dicte l'ordre

Trois choses peuvent tuer ce projet, et **aucune n'est du code** :

1. **Le contenu** — ~900 exercices et ~180 audios. Le poste le plus long, et le seul qui ne s'accélère pas en travaillant plus vite sur le reste.
2. **Le corpus d'évaluation vocale** — 3 à 6 semaines de terrain, sans lesquelles le coach vocal ne peut pas exister honnêtement.
3. **Le rendu du texte arabe sur Android bas de gamme** — s'il ne passe pas, toute l'architecture d'interface change.

Ces trois-là démarrent **en premier**, en parallèle du développement. Les traiter en série ajoute quatre mois au projet.

Deuxième principe : **une tranche verticale avant toute largeur.** Un seul type d'exercice qui traverse réellement Flutter → API → PostgreSQL → maîtrise → révision, avant d'en écrire treize. C'est là que se découvrent les erreurs d'architecture, et elles coûtent dix fois moins cher à ce moment-là.

---

## Phase 0 — Arbitrages ✅ TERMINÉE (29/08/2026)

Les douze décisions sont tranchées ([05-decisions.md](05-decisions.md)).

| Décision | Arbitrage |
|---|---|
| [D1](05-decisions.md#d1--coach-vocal--quatre-niveaux-progressifs) — coach vocal | Cinq niveaux ; **L0 + L1 + L1.5 au MVP**, L2 en beta, L3 après corpus |
| [D3](05-decisions.md#d3--paiement-hybride-conforme-aux-plateformes) — paiement | Play Billing + web (Wave, OM, carte), droits centralisés, 8 états |
| [D4](05-decisions.md#d4--modèle-économique--le-mensuel-nest-pas-le-cœur) — offres | Paiement unique 9 900 + premium annuel 19 900 ; mensuel secondaire |
| [D6](05-decisions.md#d6--variante-b--lire-avant-de-tout-mémoriser) — progression | **Variante B** : premier mot lu au jour 3, 28 lettres sur 18 jours |
| [D11](05-decisions.md#d11--architecture-adaptative-par-compétences) — pédagogie | Adaptative par compétences ; le calendrier est un défaut, pas une obligation |
| [D12](05-decisions.md#d12--contenu-et-corpus-vocal--deux-chantiers-parallèles) — contenu et corpus | Deux chantiers parallèles, prioritaires ; corpus petit mais bien annoté |

**Reste à faire dans cette phase :** vérification du nom (OAPI, INPI, domaines, stores) — une heure, avant que « IqraGo » n'entre dans les identifiants de package Android et iOS, où il devient très coûteux à changer.

---

## Ordre exact de développement

### Bloc A — Lever les risques (semaines 1-3)

**1. Test de rendu arabe en Flutter.** ✅ **terminé le 30/08/2026** — décision : **Noto Naskh Arabic, `height: 1.5`** — 720 mesures : 12 cas × 4 polices × 5 configurations de hauteur × 3 tailles. Détection du rognage au pixel, pas à l'œil.
→ *Où :* **dans Chrome, via Flutter Web.** CanvasKit partage le Skia et le moteur de mise en page du mobile, donc `height` et `TextHeightBehavior` s'y comportent à l'identique. Aucun téléphone requis pour le critère éliminatoire.
→ *Livrable :* rapport JSON des 720 mesures, police et configuration arrêtées, widget `ArabicText` figé, golden test qui le verrouille.
→ *Pourquoi ici :* [D10](05-decisions.md#d10--le-rendu-des-harakat-est-le-risque-technique-n1). Si les harakat sont rognées, toute l'architecture d'interface change. Détail et résultats intermédiaires : [07-rendu-arabe.md](07-rendu-arabe.md). Trois jours.

**2. Lancer la production de contenu.** Recruter la personne compétente qui validera l'arabe (§47), figer la liste des ~297 compétences, produire les exercices des jours 1 à 5 comme échantillon de calibrage.
→ *Court en tâche de fond jusqu'à la beta.*

**3. Lancer le corpus vocal** ([D12](05-decisions.md#d12--contenu-et-corpus-vocal--deux-chantiers-parallèles)). Recrutement de locuteurs variés (Dakar et diaspora), protocole et formulaire de conditions d'enregistrement, formulaire de consentement, procédure d'anonymisation, politique de conservation, recrutement de l'annotateur.
→ *Court en tâche de fond. Sans démarrage ici, L3 glisse de six mois.*
→ *Priorité d'annotation :* les emphatiques et gutturales d'abord — ce sont les premières cibles de L3.

**4. Journée de studio.** Les ~180 audios de référence.
→ *Pourquoi tôt :* c'est un rendez-vous physique à caler, et rien de sonore ne peut être testé avant.

### Bloc B — Socle (semaines 4-6)

**5. Squelette Django.** `config/settings/{base,dev,staging,prod}`, `User` personnalisé, première migration.
→ [D8](05-decisions.md#d8--modèle-user-personnalisé-au-premier-commit) : le `User` doit être là avant `migrate`. C'est le seul point irréversible du projet.

**6. Docker Compose + CI.** Les cinq conteneurs, GitHub Actions (lint, tests, `check --deploy`).
→ *Pourquoi maintenant :* mettre en place l'intégration continue après coup, c'est la mettre en place sur un projet qui ne passe déjà plus.

**7. Auth + JWT + `/me` + consentements.** Avec les tests.

**8. Modèles du catalogue + admin Django + `ContentVersion`.**
→ *Livrable :* la personne en charge du contenu peut commencer à saisir. Elle n'attend plus le développement à partir d'ici — c'est tout l'objet de ce séquencement.

### Bloc C — Tranche verticale (semaines 7-9)

**9. Moteur de compétences.** Graphe, prérequis, verrou, détection de cycle.
→ *Test en premier :* c'est le cœur du produit et la partie la plus facile à casser sans s'en apercevoir.

**10. Répétition espacée.** Niveaux, intervalles, transitions, règle du retour différé.
→ *Testable entièrement hors interface. À faire avant tout écran.*

**11. Composition de séance.** L'algorithme du §14, avec ses cas limites : jour 1, retour après quinze jours d'absence, aucune carte due.

**12. `GET /session/today` + `POST /session/sync`.** Avec l'idempotence sur `client_id`.

**13. Flutter : un seul type d'exercice, de bout en bout.** `letter_to_sound_mcq` : écran, réponse, écriture locale, `outbox`, synchronisation, mise à jour de la maîtrise, réapparition en révision le lendemain.
→ *Le jalon le plus important du projet.* À la fin de l'étape 13, la boucle complète du §3 tourne sur du réel. Tout ce qui suit est de la multiplication.

### Bloc D — Largeur (semaines 10-15)

**14. Les huit autres types d'exercices.** Le moteur ne change plus, seuls les `ExerciseRenderer` s'ajoutent.

**15. Diagnostic initial.** Tests A à D, calcul du profil, `item_set_version`.
→ *Écrit pour être rejoué au jour 30 : même code, mêmes items, aucune duplication.*

**16. Onboarding + accueil + progression + statistiques.**

**17. Miroir de lecture L0 + L1 + L1.5.** Enregistrement, VAD local, rejeu comparé, auto-évaluation, consentement vocal. Puis transcription conditionnelle côté serveur (mots et phrases seulement, seuil de confiance, silence en dessous).
→ *Test :* sur un item isolé, L1.5 ne s'active jamais. Sur un enregistrement bruité, le système se tait au lieu de deviner.

**18. Préchargement et mode hors ligne complet.** Manifeste de médias, cache, séance entière à zéro barre.
→ *Test d'acceptation :* faire la séance en mode avion, de bout en bout, puis synchroniser.

**19. Droits + paywall + paiement.** Google Play Billing (avec vérification serveur du jeton d'achat), paiement web (Wave, Orange Money, carte), droits centralisés, les huit états du cycle de vie.
→ *Test :* un compte gratuit se heurte réellement au jour 4 ; un droit acquis persiste 7 jours hors ligne ; une application modifiée ne peut pas fabriquer un droit ; **une restauration d'achat sur un téléphone neuf rouvre le droit** ; un remboursement le révoque.
→ *Point d'attention :* `restored` et `refunded` sont les deux états qui provoquent les rejets de publication et les litiges. Ils se testent ici, pas au moment de la soumission au store.

**20. Analytics + notifications locales.**

**21. Évaluation du jour 30 + écran de comparaison.**
→ *La promesse du §2 devient démontrable ici, et pas avant.*

### Bloc E — Beta (semaines 16-21)

**22. Recrutement de 50 à 200 utilisateurs** (§35), via WhatsApp et TikTok.
Mesures : activation, J1, J7, J30, complétion, progression réelle, conversion, coût par utilisateur, et surtout `session_abandoned` — **où exactement** on perd les gens.

**23. Étude de progression** (§36) : jour 0 contre jour 30 sur la cohorte.
→ *C'est ici, et seulement ici, que le marketing gagne le droit de parler de résultats.*

**24. Corpus vocal terminé → calibrage L2, puis mesure de L3** contre les seuils de [04-speech.md §3](04-speech.md#3-le-corpus-dévaluation).

### Bloc F — Lancement et suite

**25.** Landing page (§34), avec le diagnostic comme outil d'acquisition.
**26.** iOS, si Android a validé le modèle.
**27.** Back-office React (§28), quand une personne dédiée au contenu le justifie.
**28.** Coach vocal L3 — **seulement si les seuils sont atteints.** Sinon on reste en L2, et on le dit.
**29.** Parcours 2 (textes religieux), avec validation par des experts compétents.
**30.** Pack famille, B2B, tableau de bord enseignant, autres langues d'interface.

---

## Calendrier

| Phase | Semaines | Jalon |
|---|---|---|
| 0 — Arbitrages | — | Les quatre décisions tranchées |
| A — Risques | 1-3 | Rendu arabe validé, contenu et corpus lancés |
| B — Socle | 4-6 | Saisie de contenu possible |
| C — Tranche verticale | 7-9 | **La boucle complète tourne sur du réel** |
| D — Largeur | 10-15 | MVP fonctionnel |
| E — Beta | 16-21 | Données de progression réelles |
| F — Lancement | 22-25 | Public |

**~6 mois** à un développeur à temps plein, à condition que le contenu et le corpus avancent en parallèle. En série, compter dix mois.

---

## Trois manières de se tromper d'ordre

**Commencer par l'interface.** Les écrans sont la partie visible et gratifiante. Mais un moteur de compétences faux se découvre au jour 12 d'un parcours, jamais dans un écran. Étapes 9 à 11 avant tout écran, et testées sans interface.

**Écrire les treize types d'exercices avant d'en avoir fait tourner un seul de bout en bout.** C'est la façon la plus courante de découvrir en semaine 14 une erreur d'architecture qui coûtait trois jours en semaine 8.

**Repousser le contenu à « après le développement ».** Le développement prend 15 semaines ; le contenu aussi. En série, cela fait 30. En parallèle, 15. C'est la seule décision de planification qui change l'échéance de plusieurs mois — et c'est pour cela que l'étape 8 (admin utilisable) est placée aussi tôt.
