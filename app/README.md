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

---

## Hors ligne

Le contenu est **téléchargé à l'avance**, la séance se joue sans réseau, la
progression **remonte à la reconnexion**. C'est [D2](../docs/05-decisions.md#d2--tout-fonctionne-hors-ligne).

| | |
|---|---|
| Jours préchargés | 2 d'avance — pas trente : sur une data prépayée, précharger le parcours entier coûterait cher pour du contenu qui aura peut-être changé |
| Détection du réseau | **Aucune.** On essaie, et l'échec bascule sur le cache |
| File de tentatives | Empilée **avant** tout envoi, idempotente sur `client_id` |
| Jour courant | Suivi séparément des jours rangés |

**On n'interroge pas l'état du réseau, on essaie.** Un téléphone peut être
« connecté » à un portail captif, à une 4G qui ne passe pas, à un wifi sans
sortie. Le seul test fiable est la requête elle-même.

**Le jour courant est distinct des jours rangés.** Les suivants sont
téléchargés d'avance ; servir « le dernier rangé » ferait sauter l'apprenant
du jour 1 au jour 3 dès la première coupure. Il avance localement à chaque
séance terminée — c'est ce qui permet d'enchaîner plusieurs séances hors ligne.

**Un refus n'est pas une panne.** Un 401 ou un 403 ne bascule jamais sur le
cache : sinon un utilisateur sans droit croirait la séance ouverte.

### Pourquoi pas Drift, alors que D2 annonce SQLite

Parce que le client ne fait **aucune pédagogie**. La séance arrive composée par
le serveur : le téléphone n'a rien à interroger, il a des séances à garder et
des tentatives à mettre en file. Un magasin clé-valeur suffit ; une base
relationnelle serait ici du décor.

Le jour où le client devra décider seul — composer la séance du lendemain après
quatre jours hors ligne, calculer ce qui est dû — il faudra des requêtes, donc
Drift. Ce moment est identifié, il n'est pas arrivé.

### Vérifié en conditions réelles

Serveur coupé, séance jouée, serveur rallumé :

```
SEANCES
  jour 1 | 2 items | source = online
  jour 1 | 1 items | source = offline_sync   ← jouée sans réseau
```
