# Application IqraGo

Flutter 3.47 · Dart 3.13. Tranche verticale : un type d'exercice qui traverse
réellement Flutter → API → PostgreSQL → maîtrise → révision.

**État : la boucle complète tourne sur du réel.** Aucune donnée simulée.

## Lancer

Le backend doit tourner ([../backend/README.md](../backend/README.md)) et au
moins un lot de contenu doit être **publié** — un brouillon n'est jamais servi.

```bash
cd app && flutter run -d chrome --dart-define=API_BASE=http://127.0.0.1:8000/api/v1
```

Sur émulateur Android, l'hôte est `10.0.2.2` et non `127.0.0.1` :

```bash
flutter run --dart-define=API_BASE=http://10.0.2.2:8000/api/v1
```

L'origine du client doit figurer dans `CORS_ALLOWED_ORIGINS` côté Django.

## Tests

```bash
cd app && flutter test
```

---

## Organisation

```
lib/
  main.dart                       connecté ou non — rien d'autre
  core/api.dart                   client Dio, jeton, intercepteur
  core/modeles.dart               Seance, Item, Option
  features/auth/                  écran de connexion
  features/session/               la séance : jouer, mesurer, synchroniser
  shared/arabic_text.dart         le seul widget qui affiche de l'arabe
fonts/NotoNaskhArabic-Regular.ttf police embarquée (OFL 1.1)
```

## Trois règles inscrites dans le code

**`ArabicText` est le seul widget autorisé à afficher de l'arabe.** Police
embarquée, `height: 1.5`, `TextHeightBehavior` par défaut — les trois valeurs
sortent de 720 mesures au pixel ([../docs/07-rendu-arabe.md](../docs/07-rendu-arabe.md)).
`height: 1.0`, la valeur qu'on écrit spontanément pour serrer une carte, rogne
jusqu'à 31 px sur `بُّ`. Un test verrouille la configuration : le rognage des
harakat ne casse aucun test fonctionnel, il faut donc le vérifier exprès.

**Le client n'implémente aucune pédagogie.** La séance arrive déjà composée :
révisions, nouveautés, lecture finale. Le moteur adaptatif peut donc évoluer
sans publier une nouvelle version de l'application.

**La latence est mesurée ici, jamais interprétée ici.** C'est le serveur qui
décide si une réponse juste était une hésitation, en la comparant au seuil de
la compétence. Un client modifié ne doit pas pouvoir s'attribuer une maîtrise.

## Ce qui n'existe pas encore

| Élément | État |
|---|---|
| **Mode hors ligne** | ⬜ Le plus gros manque. [D2](../docs/05-decisions.md#d2--tout-fonctionne-hors-ligne) exige SQLite local + file `outbox` ; aujourd'hui la séance exige le réseau de bout en bout |
| Onboarding, diagnostic | ⬜ Existent côté API, aucun écran |
| Types d'exercices | 🔶 Les QCM s'affichent ; `find_in_word`, `build_syllable`, `word_assembly`, `read_aloud` ont leur donnée mais pas leur rendu |
| Audio | ⬜ Aucun fichier enregistré |
| Progression, statistiques | ⬜ `progress/overview` répond, aucun écran |
| Paywall | ⬜ Le 403 est affiché comme un message, pas comme une offre |
