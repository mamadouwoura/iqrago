# Architecture pédagogique

Conforme aux arbitrages [D6](05-decisions.md#d6--variante-b--lire-avant-de-tout-mémoriser) (variante B) et [D11](05-decisions.md#d11--architecture-adaptative-par-compétences) (moteur adaptatif par compétences).

---

## 1. Taxonomie des compétences

Une **compétence** (`Skill`) est la plus petite chose qu'on puisse savoir ou ne pas savoir, et dont la maîtrise se mesure séparément. C'est l'unité du moteur adaptatif : le programme de 30 jours n'est qu'un **ordre d'introduction par défaut** posé par-dessus ce graphe ([D11](05-decisions.md#d11--architecture-adaptative-par-compétences)).

### Convention de nommage

```
<type>.<identifiant>[.<qualificatif>]
```

Stable, lisible dans les journaux et les analytics, jamais traduite.

### Les neuf types

| Type | Exemple | Ce que ça mesure | Nb |
|---|---|---|---|
| `letter.recognize` | `letter.dad.recognize` | Reconnaître la forme et la distinguer de sa sœur | 28 |
| `letter.sound` | `letter.dad.sound` | Associer la forme au son | 28 |
| `letter.form` | `letter.ba.form.medial` | Reconnaître la lettre en position initiale / médiane / finale | 66 |
| `haraka` | `haraka.fatha` | Reconnaître le signe et savoir ce qu'il fait | 3 |
| `syllable` | `syllable.ba.fatha` | Prononcer la lettre habillée de son accent | 84 |
| `mark` | `mark.shadda`, `mark.madd.alif` | Sukun, madd (×3), shadda, tanwin (×3), article | 9 |
| `contrast` | `contrast.sin_sad` | Ne plus confondre deux lettres proches | 12 |
| `word` | `word.dar` | Lire un mot d'un trait, sans épeler | ~60 |
| `fluency` | `fluency.level.4` | Atteindre un seuil de vitesse à un niveau donné | 7 |

**Total ≈ 297 compétences.** Chacune est modélisée individuellement, avec son historique de tentatives brutes — c'est la condition posée par [D11](05-decisions.md#d11--architecture-adaptative-par-compétences) pour qu'un moteur adaptatif puisse être construit ensuite.

> 66 formes positionnelles et non 84 : six lettres (**ا د ذ ر ز و**) ne se lient jamais à la suivante et n'ont donc ni forme initiale ni forme médiane distincte. C'est ce fait qui rend la variante B possible.

### Les 12 contrastes

Les confusions réelles des débutants francophones. Chacune est une compétence testée par un exercice dédié — on ne suppose jamais qu'elle se règle d'elle-même.

| Contraste | Nature | Jour |
|---|---|---|
| `contrast.dal_dhal` — د ذ | forme, points | 1 |
| `contrast.ra_zay` — ر ز | forme, points | 2 |
| `contrast.ba_ta_tha` — ب ت ث | forme, points | 8 |
| `contrast.jim_ha_kha` — ج ح خ | forme, points | 9 |
| `contrast.sin_shin` — س ش | forme, points | 10 |
| `contrast.ayn_ghayn` — ع غ | forme, points | 15 |
| `contrast.fa_qaf` — ف ق | forme, points | 16 |
| `contrast.sad_dad` — ص ض | forme, points | 17 |
| `contrast.ta_zah` — ط ظ | forme, points | 18 |
| `contrast.sin_sad` — س ص | **son** : douce / emphatique | 21 |
| `contrast.ta_tah` — ت ط | **son** : douce / emphatique | 21 |
| `contrast.dal_dad` — د ض | **son** : douce / emphatique | 21 |

Les trois derniers sont d'une autre nature : ce n'est pas la forme qui se ressemble, c'est le **son**. Ils sont les plus difficiles pour un francophone, dont la langue n'a pas d'emphatiques, et ils ont une journée entière en semaine 3. Ce sont aussi les premières cibles de l'évaluation phonétique L3 ([D1](05-decisions.md#d1--coach-vocal--quatre-niveaux-progressifs)).

### Le graphe de prérequis

```
letter.X.recognize
   ├──► letter.X.sound
   │        └──► syllable.X.<haraka>        (+ haraka.<h>)
   │                  └──► word.<w>          (+ TOUS les atomes du mot)
   │                            └──► fluency.level.N
   ├──► letter.X.form.{initial,medial,final}   ◄── le MÊME jour que la lettre
   └──► contrast.X_Y                            (+ letter.Y.recognize)
```

**Les formes positionnelles s'apprennent avec la lettre**, pas dans un bloc différé ([D6](05-decisions.md#d6--variante-b--lire-avant-de-tout-mémoriser), règle 3). Le corps ne change pas ; seul le bout se tend vers la voisine. Une lettre connue est une lettre connue dans les quatre positions — sinon « je connais ب » est une affirmation fausse dès qu'un mot apparaît.

**Deux règles appliquées par le code, pas par le contenu :**

1. **Verrou de prérequis** — une compétence n'est jamais introduite si un prérequis est à un niveau < 3.
2. **Zéro surprise, sans exception** — un item composé n'apparaît que si tous ses atomes sont à un niveau ≥ 2. `وَرَد` n'existe que lorsque `letter.waw.sound`, `letter.ra.sound`, `letter.dal.sound` et `haraka.fatha` sont acquis. Y compris pour « faire joli » dans une leçon.

La seconde évite l'expérience la plus décourageante du débutant : un mot contenant une lettre qu'on ne lui a jamais montrée.

---

## 2. Programme 30 jours — variante B (retenue)

**Principe :** APPRENDRE → UTILISER IMMÉDIATEMENT → RÉPÉTER → RENFORCER.
**Chaîne :** lettres sélectionnées → sons → harakat → combinaisons → syllabes → mots → phrases → textes.

Les 28 lettres sont réparties sur **18 jours**, non sur 3. La lecture précoce vient de la **sélection** des premières lettres, jamais d'une accélération : chaque fondamental garde sa journée entière ([D6](05-decisions.md#d6--variante-b--lire-avant-de-tout-mémoriser), règle 1).

Rappel : ce calendrier est un **ordre par défaut**. Le moteur adaptatif peut retarder une introduction si les prérequis ne sont pas solides, ou la devancer si l'utilisateur avance vite ([D11](05-decisions.md#d11--architecture-adaptative-par-compétences)).

### Semaine 1 — Le noyau libre : 6 lettres, 3 harakat (J1-7)

Les six lettres **ا د ذ ر ز و** ne se lient jamais à la suivante : elles gardent partout la forme apprise en isolé. Aucune forme positionnelle, aucune charge cachée.

| Jour | Nouveautés | Utilisation immédiate | Sortie |
|---|---|---|---|
| **1** | د ذ + **fathah** | `دَ` `ذَ` — première syllabe dès le jour 1 | Distinguer د/ذ ; prononcer دَ et ذَ |
| **2** | ر ز ا | `رَ` `زَ` ; ا de prolongation : `دَا` `رَا` | Le a long entendu et vu |
| **3** | و | **`وَرَد`** et **`دَار`** — premiers mots lus | *Le déclic : « je lis l'arabe »* |
| **4** | **kasra** | `دِ ذِ رِ زِ وِ` ; contraste `دَ` / `دِ` | Les lèvres s'étirent |
| **5** | **damma** | `دُ ذُ رُ زُ وُ` ; **`ذُو`** ; contraste `دَ دِ دُ` | Les trois sons distingués |
| **6** | — | Les 18 syllabes ; **`زَاد`** **`زَار`** ; mode vitesse léger | 18 syllabes automatisées |
| **7** | *respiration* | Révision seule, aucune nouveauté | La série est protégée |

Fin de semaine : **6 lettres · 3 harakat · 18 syllabes · 5 mots lus.**

Le jour 3 est le jalon le plus important du parcours : c'est là que se joue la rétention. La courbe d'abandon est maximale entre J2 et J5, et un utilisateur qui a lu un vrai mot arabe n'abandonne pas de la même façon qu'un utilisateur qui mémorise encore des dessins.

Les jours 7, 14, 21 et 28 n'apportent rien de neuf. Ce ne sont pas des jours perdus : ils consolident, absorbent le retard de révision, et protègent la série quotidienne.

### Semaine 2 — Les familles connectées régulières (J8-14)

À partir d'ici, chaque lettre est enseignée **avec ses quatre formes** le jour même.

| Jour | Nouveautés | Mots débloqués |
|---|---|---|
| **8** | **ب ت ث** (famille ٮ) + les 4 formes | `بَاب` `بَرَد` `ثَابِت` |
| **9** | **ج ح خ** (famille ح) | `حَجَر` `خَرَجَ` `حَار` |
| **10** | **س ش** (famille س) | `دَرَسَ` `شَجَر` `سَحَاب` |
| **11** | **ل م** | `جَمَل` `مَال` `سَلَام` |
| **12** | **ن ي** | `نَار` `بَنَات` `يَد` |
| **13** | **ك ه** — les deux plus irrégulières | `كَتَبَ` `ذَهَبَ` `نَهَر` `كِتَاب` |
| **14** | *respiration* | — |

Fin de semaine : **20 lettres · ~18 mots lus.**

ه a sa journée avec ك parce que c'est la lettre dont la forme varie le plus entre les positions (ه ـه ـهـ هـ). L'expédier avec cinq autres garantit la confusion.

### Semaine 3 — Les familles restantes et les signes (J15-21)

| Jour | Nouveautés | Mots débloqués |
|---|---|---|
| **15** | **ع غ** (famille ع) | `عَمَل` `سَمِعَ` `غُرَاب` |
| **16** | **ف ق** (famille ڡ) | `قَلَم` `قَمَر` `فَتَحَ` |
| **17** | **ص ض** (famille ص) | `صَبَرَ` `ضَرَبَ` |
| **18** | **ط ظ** (famille ط) — **les 28 lettres sont acquises** | `مَطَر` `نَظَرَ` |
| **19** | **Sukun** ْ — la lettre sans voyelle | `بَيْت` `وَرْد` `قَلْب` |
| **20** | **Madd** — les trois prolongations ا و ي, formalisées | `كِتَاب` `نُور` `كَبِير` |
| **21** | *respiration* + **les couples doux / emphatiques** : س/ص · ت/ط · د/ض · ذ/ظ | Discrimination auditive |

Fin de semaine : **28 lettres · 3 harakat · sukun · madd · ~35 mots.**

Le jour 21 est une respiration en apparence seulement : les quatre couples doux / emphatiques n'introduisent aucune forme nouvelle, mais c'est la journée la plus exigeante à l'oreille. Elle est placée là parce qu'elle demande que les huit lettres concernées soient déjà solides.

### Semaine 4 — Le système complet, puis la lecture (J22-30)

| Jour | Nouveautés | Contenu |
|---|---|---|
| **22** | **Shadda** ّ — la lettre doublée | `جَدّ` `مُدَرِّس` |
| **23** | **Tanwin** ً ٍ ٌ | `كِتَابٌ` `بَيْتًا` `قَلَمٍ` |
| **24** | **L'article ال**, lettres solaires et lunaires | `الْقَمَر` `الشَّمْس` |
| **25** | — | Mots longs, listes, ancrage du sens |
| **26** | — | Phrases de 3 mots |
| **27** | — | Phrases de 5 à 8 mots |
| **28** | *respiration* | Paragraphe complet |
| **29** | — | **Fluidité** : mots/minute, relecture d'un texte déjà lu, réduction des hésitations |
| **30** | — | **Évaluation finale** |

À la fin du jour 24, **le système d'écriture vocalisé est intégralement couvert.** Les six derniers jours sont de l'entraînement pur — c'est là que la fluidité se construit, et c'est pour cela qu'ils ne sont pas négociables.

**Jour 30 — l'évaluation finale reprend exactement les items du diagnostic du jour 0**, dans le même ordre et dans la même version (`item_set_version`). C'est la seule façon d'obtenir une comparaison valide, et c'est ce qui rend démontrable la promesse du produit. L'écran final n'est pas une félicitation : ce sont les cinq sous-scores, jour 0 contre jour 30, côte à côte — puis la suite disponible ([D4](05-decisions.md#d4--modèle-économique--le-mensuel-nest-pas-le-cœur)).

### Récapitulatif

| Semaine | Lettres cumulées | Acquis |
|---|---|---|
| 1 | 6 | 3 harakat, 18 syllabes, 5 mots |
| 2 | 20 | formes positionnelles, ~18 mots |
| 3 | 28 | sukun, madd, emphatiques, ~35 mots |
| 4 | 28 | shadda, tanwin, article, phrases, textes, ~60 mots |

---

## 3. Types d'exercices

Neuf types au MVP, quatre ajoutés ensuite.

| # | Type | Compétence testée | Interaction | Hors ligne | MVP |
|---|---|---|---|---|---|
| 1 | `letter_to_sound_mcq` | `letter.*.sound` | Voir la lettre, choisir le son parmi 4 | oui | ✅ |
| 2 | `sound_to_letter_mcq` | `letter.*.sound` | Écouter, choisir la lettre parmi 4 | oui | ✅ |
| 3 | `pair_discrimination` | `contrast.*` | Deux lettres, « laquelle est ث ? » | oui | ✅ |
| 4 | `family_odd_one_out` | `letter.*.recognize` | Quatre lettres, trouver l'intruse | oui | ✅ |
| 5 | `find_in_word` | `letter.*.form.*` | Toucher la lettre dans un mot écrit | oui | ✅ |
| 6 | `build_syllable` | `syllable.*` | Glisser un accent sur une lettre | oui | ✅ |
| 7 | `syllable_to_sound_mcq` | `syllable.*` | Voir `بِ`, choisir « bi » | oui | ✅ |
| 8 | `word_assembly` | `word.*` | Remettre les lettres dans l'ordre | oui | ✅ |
| 9 | `read_aloud` | `word.*`, `fluency.*` | Miroir de lecture (L0 / L1 / L1.5) | oui\* | ✅ |
| 10 | `timed_syllable_run` | `fluency.*` | Mode vitesse chronométré | oui | ⬜ |
| 11 | `word_to_meaning_mcq` | `word.*` | Mot → sens parmi 4 | oui | ⬜ |
| 12 | `letter_dictation` | `letter.*.sound` | Écouter, saisir au clavier arabe | oui | ⬜ |
| 13 | `timed_passage` | `fluency.*` | Lecture continue, mots/minute | oui\* | ⬜ |

\* Enregistrement et retour L0/L1 en local, toujours. L1.5 (transcription conditionnelle) et l'analyse serveur sont **différées à la reconnexion** et ne bloquent jamais la séance.

**Structure commune, en JSONB :**

```json
{
  "type": "pair_discrimination",
  "skill_id": "contrast.sin_sad",
  "prompt": { "audio": "sad_fatha.opus", "text_fr": "Laquelle dis-tu ainsi ?" },
  "options": [
    { "arabic": "صَ", "correct": true },
    { "arabic": "سَ", "correct": false }
  ],
  "latency_threshold_ms": 2000
}
```

Un seul schéma pour treize types : le client possède un `ExerciseRenderer` par type, et ajouter un type n'exige aucune migration.

**Trois exercices minimum par compétence**, sinon l'utilisateur mémorise la présentation au lieu du contenu — il retient la position du bon bouton. Soit **~900 exercices**, chantier prioritaire mené en parallèle du développement ([D12](05-decisions.md#d12--contenu-et-corpus-vocal--deux-chantiers-parallèles)).

---

## 4. Annexe — La version §8 du cahier des charges (écartée)

Conservée comme trace de la décision. Écartée par [D6](05-decisions.md#d6--variante-b--lire-avant-de-tout-mémoriser).

| Jours | Contenu proposé | Motif de l'écart |
|---|---|---|
| 1-3 | Les 28 lettres | ~9 formes nouvelles par séance de 15 min ; saturation des révisions dès J5 |
| 4-6 | Formes et connexions | 66 compétences en trois jours |
| 7-9 | Harakat | Première syllabe au jour 7, premier mot au jour 10 — trop tard face à la courbe d'abandon |
| 10-12 | Fusion | — |
| 13-30 | Sukun, madd, shadda, tanwin, mots, phrases, paragraphes, fluidité, évaluation | **Conservé tel quel dans la variante B**, aux jours 19-30 |

La variante B ne raccourcit rien : elle redistribue. Les deux versions couvrent le même système d'écriture en trente jours, et la variante B consacre **plus** de temps aux fondamentaux (une journée entière pour sukun, pour madd, pour shadda, pour tanwin, pour l'article) — elle prend ce temps sur le bloc de mémorisation initiale, pas sur la lecture.
