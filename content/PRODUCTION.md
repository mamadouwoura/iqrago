# Comment le contenu se produit

Document de travail pour la personne en charge du contenu et pour le validateur arabe.

---

## 1. Le principe : générer le volume, valider à la main

Produire ~850 exercices à la main est irréaliste et inutile. La plupart se **dérivent mécaniquement** du socle : les 28 lettres, leurs 9 familles, les 3 harakat et les mots connaissent déjà tout ce qu'il faut pour fabriquer un QCM juste.

Ce que la génération ne peut pas faire, c'est **juger**. Le §47 du cahier des charges est explicite : rien de généré ne se publie sans vérification. Le cycle éditorial l'impose en base — un contenu ne passe à `published` qu'après relecture et validation par quelqu'un qui n'en est pas l'auteur.

> **Générer produit des brouillons. Rien d'autre.**

---

## 2. Ce qui est générable, et ce qui ne l'est pas

Mesuré sur le socle réel, pas estimé.

| Type de compétence | Nb | Exercices | Générable ? |
|---|---:|---:|---|
| `letter.recognize` | 28 | 84 | ✅ distracteurs = sœurs de famille |
| `letter.sound` | 28 | 84 | ✅ |
| `syllable` | 84 | 252 | ✅ distracteurs = même lettre, autres accents |
| `word` | 46 | 138 | ✅ assemblage, sens, lecture |
| `contrast` | 12 | 36 | ✅ |
| `fluency` | 7 | 21 | ✅ suites tirées de l'acquis |
| `haraka` | 3 | 9 | ✅ |
| `letter.form` | 66 | 198 | ⚠️ **seulement si un mot support existe** |
| `mark` | 9 | 27 | ⚠️ demande des mots porteurs du signe |
| **Total** | **283** | **~849** | |

**Le distracteur est ce qui fait la valeur.** Un QCM dont les mauvaises réponses sont tirées au hasard n'enseigne rien : l'apprenant élimine par la forme sans lire. La règle est donc :

1. **Les sœurs de famille d'abord** — ب/ت/ث partagent un squelette, c'est là qu'est la confusion réelle ;
2. **jamais une lettre non encore enseignée** — montrer une forme inconnue comme mauvaise réponse l'enseigne de travers ;
3. **compléter par les lettres les plus récentes**, plus fragiles que celles acquises depuis deux semaines.

---

## 3. Le goulot : le corpus de mots

**27 des 66 compétences de forme positionnelle n'ont aujourd'hui aucun mot qui les supporte.**

Exemples : `letter.ta.form.initial`, `letter.tha.form.medial`, `letter.kha.form.final`, `letter.sin.form.medial`.

On ne peut pas demander « touche le ت dans ce mot » s'il n'existe aucun mot contenant ت en position initiale et composé uniquement de lettres déjà enseignées. Aucun contournement : la règle « zéro surprise » n'a pas d'exception.

Le corpus compte **46 mots**. Il en faut environ **150** pour couvrir les 66 formes, avec deux à trois mots par jour de parcours.

C'est du travail humain, contraint et non créatif : pour chaque case manquante, trouver un mot arabe réel, courant, dont *toutes* les lettres et *tous* les signes sont enseignés à cette date. Le validateur `contenu.dart` vérifie mécaniquement la contrainte — il refuse le mot fautif — mais il ne trouve pas le mot.

**~13 % des exercices sont bloqués sur ce corpus. Les 87 % restants se génèrent dès aujourd'hui.**

---

## 4. La chaîne, dans l'ordre

```
lettres.json + mots.json          ← saisie humaine, sous contrainte
        ↓  contenu.dart valider   ← refuse toute violation de « zéro surprise »
        ↓  contenu.dart generer   ← compétences, manifeste audio
        ↓  generer-exercices      ← ~740 brouillons (à écrire)
        ↓  importer_contenu       ← entrée en base, état « brouillon »
        ↓  admin : relecture par lot
        ↓  validation par un tiers (jamais l'auteur — contrainte en base)
        ↓  publication            ← immuable ; corriger = créer une révision
```

**L'unité de relecture est le lot, pas l'exercice.** Relire 850 items un par un est impraticable. Un lot — « Jour 8, famille ٮ » — contient la leçon du jour et ses ~30 exercices, se relit d'une traite en vingt minutes, et se publie sans état intermédiaire visible par l'apprenant. Trente lots, un par jour de parcours.

---

## 5. Qui fait quoi

| Rôle | Tâches | Qui |
|---|---|---|
| **Développement** | Écrire le générateur, la commande d'import | Fait en interne |
| **Contenu** | Étendre le corpus à ~150 mots, écrire phrases et paragraphes, saisir les textes d'introduction, corriger les brouillons rejetés | **à recruter** |
| **Validation arabe** | Relire les 30 lots avant publication : justesse des vocalisations, sens des mots, pertinence pédagogique | **à recruter — ne peut pas être l'auteur** |
| **Voix** | 158 enregistrements, une journée de studio | **à recruter** |

Les trois dernières lignes ne dépendent pas du développement. **Elles sont le vrai chemin critique**, et rien ne les accélère côté code.

---

## 6. Effort réaliste

| Poste | Durée | Dépend de |
|---|---|---|
| Écrire le générateur d'exercices | 2 à 3 jours | dev |
| Étendre le corpus de 46 à ~150 mots | 4 à 6 jours | contenu + validation |
| Phrases (jours 26-27) et paragraphes (jour 28) | 3 à 4 jours | contenu |
| Textes d'introduction des 30 leçons | 2 jours | contenu |
| Relecture et validation des 30 lots | 3 à 4 jours | **validateur arabe** |
| Journée de studio + découpe des 158 pistes | 2 jours | voix |

**Environ trois semaines**, dont l'essentiel n'est pas du développement. En série avec le reste du projet, c'est trois semaines ajoutées ; en parallèle, c'est zéro.

---

## 7. Deux risques, et ce qu'on en fait

**L'uniformité.** Des exercices tous produits par la même règle se ressemblent : quatre options, distracteurs de la même famille, énoncé identique. L'apprenant finit par lire la *forme* de la question au lieu de son contenu.
→ Faire varier le nombre d'options (3 à 5), alterner les stratégies de distracteurs, et **écrire à la main les exercices des jours 1 à 3** — ceux que tout le monde voit, y compris ceux qui n'achèteront jamais.

**La relecture bâclée.** 850 items, c'est le volume où l'on commence à valider sans lire. Un contenu approuvé sans relecture réelle est pire qu'un contenu non relu : il porte un tampon.
→ Les lots de 30 rendent la tâche finie et mesurable. Le champ `notes` de chaque version garde la trace de ce qui a été renvoyé en brouillon et pourquoi. Un lot renvoyé perd sa validation — c'est voulu.

---

## 8. Ce qui reste à écrire côté code

Une seule chose : **le générateur d'exercices**, `tools/contenu/exercices.dart`, avec :

- une stratégie de distracteurs par type d'exercice ;
- le refus d'utiliser une lettre non enseignée comme distracteur ;
- un **rapport de lacunes** — la liste exacte des compétences sans exercice possible et pourquoi, pour que la personne en charge du contenu sache quels mots trouver au lieu de chercher à l'aveugle.

Le reste de la chaîne existe et fonctionne : validateur, générateur de compétences, import, cycle éditorial, admin.
