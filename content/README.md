# Contenu pédagogique

Chantier prioritaire, mené **en parallèle** du développement ([D12](../docs/05-decisions.md#d12--contenu-et-corpus-vocal--deux-chantiers-parallèles)). C'est le poste le plus long du projet : le développement prend ~15 semaines, le contenu aussi. En série, cela fait 30.

---

## Les fichiers

| Fichier | Nature | Qui l'édite |
|---|---|---|
| `lettres.json` | **Source.** 28 lettres, 9 familles, 3 harakat, 9 marques, 12 contrastes, avec leur jour d'introduction | Contenu + validateur arabe |
| `mots.json` | **Source.** Les mots lisibles, décomposés, avec leur jour de déblocage | Contenu + validateur arabe |
| `competences.json` | **Généré.** Le graphe des 283 compétences et leurs prérequis | Personne — `generer` l'écrit |
| `audio-manifeste.json` | **Généré.** Les 158 enregistrements de la journée de studio | Personne — `generer` l'écrit |

Les deux fichiers générés ne s'éditent **jamais** à la main. Ajouter une lettre ou un mot à la source suffit : le graphe et le manifeste suivent.

---

## Le cycle de travail

```
éditer lettres.json / mots.json
        ↓
   valider          ← refuse tout ce qui casse la règle
        ↓
   generer          ← reconstruit le graphe et le manifeste
        ↓
   relecture par le validateur arabe   (draft → review → approved)
        ↓
   publication                         (published, immuable)
```

```bash
dart run tools/contenu/contenu.dart valider
```

```bash
dart run tools/contenu/contenu.dart generer
```

`valider` doit passer avant toute relecture humaine. Faire relire un contenu qui viole une règle mécanique, c'est gaspiller le temps de la seule personne qu'on ne peut pas remplacer.

---

## Ce que le validateur vérifie

**1. Zéro surprise.** Un mot n'apparaît que si toutes ses lettres et toutes ses marques sont enseignées **à cette date ou avant**. Sans exception, y compris pour « faire joli » dans une leçon. C'est l'expérience la plus décourageante du débutant : un mot contenant une lettre qu'on ne lui a jamais montrée.

**2. Fidélité de la chaîne écrite.** Il décompose la chaîne arabe caractère par caractère et la compare aux lettres et marques déclarées. C'est le contrôle qui attrape ce que l'œil laisse passer : une kasra à la place d'une fatha, une lettre oubliée dans la décomposition.

> Ce contrôle a servi dès le premier passage. `بَيْتًا` était déclaré `ب ي ت`, alors que la chaîne contient un alif final — le support orthographique du tanwin fathah, qui s'écrit mais ne se lit pas. Un relecteur humain aurait très bien pu ne pas le voir : il ne se prononce pas.

**3. Cohérence du socle.** 28 lettres exactement, pas de doublon, familles ne citant que des lettres existantes, contrastes jamais enseignés avant leurs deux lettres.

**4. Cohérence du graphe** (à la génération). Aucun prérequis manquant, aucun prérequis introduit **après** la compétence qui en dépend.

---

## Les 283 compétences

| Type | Nombre |
|---|---:|
| `syllable` | 84 |
| `letter.form` | 66 |
| `word` | 46 |
| `letter.recognize` | 28 |
| `letter.sound` | 28 |
| `contrast` | 12 |
| `mark` | 9 |
| `fluency` | 7 |
| `haraka` | 3 |
| **Total** | **283** |

66 formes positionnelles et non 84 : six lettres (**ا د ذ ر ز و**) ne se lient jamais à la suivante et n'ont donc ni forme initiale ni forme médiane distincte. C'est ce fait qui rend la variante B possible — l'apprenant lit `وَرَد` au jour 3 sans avoir appris une seule forme positionnelle.

---

## Reste à produire

| Livrable | Volume | État |
|---|---|---|
| Socle lettres et marques | — | ✅ |
| Mots des jours 3 à 24 | 46 | ✅ premier jet, **à faire valider** |
| Graphe de compétences | 283 | ✅ généré |
| Manifeste audio | 158 | ✅ généré |
| **Exercices** | **~850** | ⬜ **le gros du travail** |
| Phrases (jours 26-27) | ~30 | ⬜ |
| Paragraphes (jour 28) | ~6 | ⬜ |
| Enregistrements audio | 158 + phrases | ⬜ journée de studio à réserver |

**Trois exercices minimum par compétence.** En dessous, l'utilisateur mémorise la présentation au lieu du contenu : il retient la position du bon bouton, pas la lettre. 283 × 3 ≈ 850.

---

## La journée de studio

`audio-manifeste.json` est la feuille de route : 158 enregistrements, avec pour chacun le fichier attendu, la chaîne arabe et ce qu'il faut prononcer.

| | |
|---|---|
| Voix | Locuteur natif, débit lent et articulé |
| Format | Opus 24 kbps mono (~4 Ko/s) |
| Poids total | < 3 Mo — embarqué dans l'application, disponible hors ligne |
| Vitesses 0,75× / 1× / 1,25× | Étirement temporel côté client, pas trois fichiers |

**Jamais de synthèse vocale pour le référentiel.** Une voix TTS sur `ضَ` produit une approximation. L'apprenant imite ce qu'il entend : une référence approximative enseigne une erreur — et l'enseigne à tout le monde, définitivement. C'est le poste où l'économie est la plus tentante et la plus coûteuse.

**On enseigne le son, pas le nom.** L'apprenant dit « ba », jamais « bâ' ». Le nom appris trop tôt produit l'épellation (« bâ'-fathah-bâ' ») au lieu de la lecture. Le manifeste porte cette consigne sur chaque ligne de lettre.

---

## Le validateur arabe

Une personne compétente relit **tout** avant publication ([D12](../docs/05-decisions.md#d12--contenu-et-corpus-vocal--deux-chantiers-parallèles)). Ce n'est pas une formalité : le sens des mots, la justesse des vocalisations et la pertinence pédagogique ne se vérifient pas mécaniquement.

Elle ne peut pas être l'auteur du contenu qu'elle valide — la contrainte est appliquée en base (`approved_by ≠ author`, voir [02-donnees.md](../docs/02-donnees.md#contentversion--la-machine-à-états-du-47)).

Un contenu publié est **immuable** : toute correction crée une version suivante. Sinon, corriger une faute change rétroactivement ce que les utilisateurs ont vu, et fausse toute analyse de cohorte.
