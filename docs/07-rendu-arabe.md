# Étape 1 — Rendu de l'arabe et des harakat sur Android

Exécution de [D10](05-decisions.md#d10--le-rendu-des-harakat-est-le-risque-technique-n1) et de l'étape 1 de la [roadmap](06-roadmap.md).

**État : ✅ terminé, décision rendue le 30/08/2026.**

> **Noto Naskh Arabic · `height: 1.5` · `TextHeightBehavior` par défaut.**
> Seule des trois polices à atteindre 0,00 px de débordement. Détail : §4.

Le critère éliminatoire est levé. Les critères 4 et 5 (poids de la police sous-ensemblée, performance) se vérifient à la beta et ne bloquent pas le développement.

---

## 1. Ce qu'on cherche exactement

Le risque n'est pas « l'arabe s'affiche mal ». Il est précis :

> Sur Android, l'encre des signes diacritiques déborde fréquemment de la boîte de mise en page calculée par Flutter. Dans un conteneur à hauteur contrainte — une carte d'exercice, un bouton de réponse, une ligne de liste — le signe est alors **rogné**.

Une application qui enseigne fathah, kasra et damma pendant trois semaines et qui les affiche coupés n'enseigne rien. Et le défaut est sournois : il n'apparaît ni sur un émulateur récent, ni sur un iPhone, ni au premier coup d'œil sur un texte court. Il apparaît sur `بُّ` à 48 px dans une carte de 64 px de haut, sur un Android 8.

Quatre modes de défaillance connus :

| Mode | Cause |
|---|---|
| Rognage haut | `height` trop faible : l'ascendante calculée ignore les signes empilés |
| Rognage bas | Kasra sous une lettre qui descend déjà (ج, ع en finale) |
| Signes mal positionnés | Substitution de police : la lettre vient d'une fonte, le signe d'une autre |
| Variation par appareil | La police arabe système diffère selon le constructeur et la version d'Android |

Le quatrième est la raison pour laquelle **la police est embarquée**, jamais empruntée au système. Ce point n'a pas besoin d'être mesuré : il est décidé.

---

## 2. La méthode : mesurer, pas regarder

Un banc de test qui affiche du texte et demande « est-ce que ça vous paraît correct ? » ne prouve rien. Un débordement de 2 px se voit mal, se photographie mal, et se discute sans fin.

Le banc mesure. Pour chaque combinaison, il :

1. calcule la mise en page (`TextPainter.layout`) ;
2. peint le texte dans un canevas **entouré de 120 px de marge vide** ;
3. relève la première et la dernière ligne de pixels contenant de l'encre ;
4. compare cette boîte d'encre à la boîte de mise en page.

Débordement > 0 → l'encre sort de la boîte → **rognage garanti** dans un conteneur contraint.

La marge est le point qui fait tenir la méthode : peindre dans une image de la taille exacte de la boîte reviendrait à rogner l'encre avant de pouvoir la mesurer, c'est-à-dire à ne rien mesurer.

### Le plan d'expérience

| Axe | Valeurs | Nb |
|---|---|---|
| Police | système, Amiri, Scheherazade New, Noto Naskh Arabic | 4 |
| Configuration de hauteur | défaut · `1.0` · `1.5` · `1.8` · `1.8` + `applyHeightToFirstAscent: false` | 5 |
| Taille | 18 · 32 · 48 px | 3 |
| Cas de test | 12 (ci-dessous) | 12 |

**720 mesures**, chacune donnant un débordement haut et bas en pixels.

### Les douze cas

Chacun correspond à une notion réellement enseignée, avec le jour où elle arrive dans le parcours ([01-pedagogie.md](01-pedagogie.md#2-programme-30-jours--variante-b-retenue)) :

| # | Texte | Ce qu'il éprouve | Jour |
|---|---|---|---|
| 1 | `بَ` | Fathah, le signe le plus fréquent | 1 |
| 2 | `بِ` | Kasra, sous la lettre | 4 |
| 3 | `بُ` | Damma | 5 |
| 4 | `بْ` | Sukun, cercle haut | 19 |
| 5 | `آ` | Madd au-dessus de alif | 20 |
| 6 | `بَّ` | Shadda + fathah empilées | 22 |
| 7 | `بُّ` | **Shadda + damma — le cas le plus haut** | 22 |
| 8 | `بِّ` | Shadda dessus, kasra dessous : les deux bords à la fois | 22 |
| 9 | `بٌ` | Tanwin damma, double boucle | 23 |
| 10 | `جِ` | Kasra sous une lettre qui descend déjà | 9 |
| 11 | `الطَّالِبُ` | Mot réel : shadda sur ط, damma finale | 24 |
| 12 | `Lis بَ maintenant` | Arabe et latin sur la même ligne (RTL dans LTR) | — |

Les cas 7 et 8 décident. Le 7 est le plus haut du système d'écriture ; le 8 est le seul qui sollicite les deux bords simultanément.

---

## 3. Critères d'acceptation

La configuration retenue devra satisfaire **tous** les points suivants :

| # | Critère | Seuil |
|---|---|---|
| 1 | Aucun débordement, sur aucun des 12 cas, à 18 / 32 / 48 px | ≤ 0,5 px (tolérance d'anticrénelage) |
| 2 | Résultat identique sur les 3 appareils de test | écart ≤ 1 px |
| 3 | Le mot `الطَّالِبُ` est intégralement lisible dans une carte de 64 px | visuel |
| 4 | Poids de la police embarquée, sous-ensemble arabe | ≤ 400 Ko |
| 5 | Pas de saccade à l'affichage d'une liste de 20 items | < 16 ms/frame |

**Le critère 1 est éliminatoire.** Une police qui déborde d'un pixel sur un seul cas est écartée : le parcours affichera ce cas des centaines de fois.

### Où mesurer — révision

J'avais écrit qu'un émulateur ne remplaçait aucun appareil réel. C'est exagéré dans notre cas précis, et la nuance change ce qu'il faut se procurer.

**Flutter n'utilise pas la pile de texte d'Android.** Son moteur embarque son propre Skia et son propre moteur de mise en page. Dès lors que la police est **embarquée dans l'application** — ce qui est décidé — la géométrie des glyphes et des signes vient de notre fichier et du moteur Flutter, pas de la version d'Android ni du constructeur.

Ce qui reste réellement dépendant de l'appareil :

| Aspect | Dépend de l'appareil ? | Où le mesurer |
|---|---|---|
| Débordement des signes (critère 1) | **Non** — moteur Flutter + police embarquée | Chrome ou émulateur suffit |
| Arrondi de la boîte à faible densité | Un peu — `devicePixelRatio` bas | Émulateur en profil basse densité |
| Repli de police sur le cas mixte (12) | **Oui** — le latin vient de la police système | Appareil réel |
| Performance (critère 5) | **Oui** | Appareil réel |
| Lisibilité effective sur 5 pouces | **Oui** | Appareil réel |

**Conséquence pratique : l'absence d'un Android 8 ne bloque rien.** Les critères 1 à 3 se mesurent sans aucun téléphone. Les critères 4 et 5, et le confort de lecture, se vérifient plus tard sur n'importe quel Android — et l'appareil bas de gamme trouve naturellement sa place au moment de la beta, où il faut de toute façon des testeurs réels.

| Étape | Support | Ce qu'elle valide |
|---|---|---|
| **Maintenant** | Chrome, via Flutter Web | Critères 1, 2, 3 — le cœur de la décision |
| Ensuite | Émulateur en 480×854, densité mdpi | Arrondi à faible densité |
| À la beta | Téléphones des testeurs | Repli latin, performance, lisibilité |

---

## 4. Livrables attendus

1. Le tableau des 720 mesures (export JSON, bouton **Copier** dans le banc).
2. Une capture d'écran par appareil.
3. **Une décision écrite** : police retenue, `height` retenu, `TextHeightBehavior` retenu.
4. Le widget `ArabicText` figé à partir de cette décision — le seul widget de l'application autorisé à afficher de l'arabe ([00-blueprint.md §17](00-blueprint.md#17-architecture-flutter)).
5. Un golden test qui verrouille le rendu, pour qu'une montée de version de Flutter ne le casse pas en silence.

### Grille de résultats — 720 mesures, exécutées le 30/08/2026

Flutter 3.47.2 stable · CanvasKit · Chrome. Pire débordement en pixels ; **0,00 = aucun rognage possible**.

| Police | défaut | `1.0` | `1.5` | `1.8` | `1.8`+asc |
|---|---:|---:|---:|---:|---:|
| **Noto Naskh Arabic** | **0,00** | 11,00 | **0,00** | **0,00** | **0,00** |
| Scheherazade New | 2,00 | 28,00 | 13,00 | 6,00 | 5,00 |
| Amiri | 8,00 | 31,00 | 16,00 | 7,00 | 8,00 |
| ~~police système~~ | — | — | — | — | — |

**186 rognages sur 720 mesures.**

La ligne « police système » est **écartée comme non concluante**, et pas parce qu'elle serait mauvaise : elle affichait 0,00 partout. Flutter Web n'a aucune police arabe à substituer — rien n'est dessiné, donc rien ne déborde, et le banc lui accordait le meilleur score possible. **C'est un défaut du banc, corrigé depuis** : `!inkFound` compte désormais comme un échec. Une police qui ne dessine rien ne doit jamais se classer devant une police qui rend correctement le texte.

### Décision

> **Noto Naskh Arabic, `height: 1.5`, `TextHeightBehavior` par défaut.**

C'est **la seule des trois polices à atteindre 0,00**, et elle y parvient sur quatre configurations sur cinq. `1.5` est retenu plutôt que `défaut` parce qu'une hauteur explicite rend la boîte de ligne prévisible pour dimensionner les cartes d'exercice, et plutôt que `1.8` parce que la réserve supplémentaire ne sert à rien et coûte de la place sur un écran de 5 pouces.

### Le résultat qui compte pour l'équipe

**`height: 1.0` échoue sur les trois polices** — 11, 28 et 31 px de rognage. C'est la valeur qu'un développeur écrit spontanément pour serrer une carte, et c'est la pire possible. Le pire cas absolu est `بُّ` (shadda + damma) en Amiri : **31 px d'encre coupée**, soit les deux signes entièrement effacés.

Les trois cas fautifs sont toujours les mêmes, et ce sont trois notions du programme : `بُّ` (shadda + damma, jour 22), `الطَّالِبُ` (mot avec article, jour 24), `جِ` (kasra sous une lettre descendante, jour 9).

### La sonde navigateur avait tort

| | Sonde navigateur | Banc Flutter |
|---|---|---|
| 1er | Scheherazade New | **Noto Naskh Arabic** |
| 2e | Amiri | Scheherazade New |
| Écarté | **Noto Naskh Arabic** | Amiri (le pire) |

Le classement s'est **inversé**. La sonde comparait l'encre à la boîte déclarée par la police (`fontBoundingBox`) ; Flutter calcule sa boîte de mise en page à partir d'autres métriques, plus serrées. Scheherazade New déclare de vastes métriques — ce qui la flattait au navigateur — dont Flutter ne tient pas compte.

C'est précisément pourquoi le §6 disait que la sonde navigateur ne pouvait pas valider le critère 1. La conclusion « Scheherazade New en tête » qui y figurait était fausse : elle est corrigée ici.

**À retenir au-delà de ce ticket :** un proxy de mesure ne vaut que ce que vaut son hypothèse. Celui-ci supposait que la boîte déclarée par la police était celle qu'utilise le moteur. Elle ne l'est pas.

### Ce qui reste ouvert

| Point | Statut |
|---|---|
| Critère 1 — aucun débordement | ✅ Noto Naskh Arabic + `height: 1.5` |
| Critère 2 — trois appareils | ⬜ Mesuré sur un seul moteur (CanvasKit) |
| Critère 3 — `الطَّالِبُ` lisible en carte 64 px | ⬜ Contrôle visuel sur appareil |
| Critère 4 — police ≤ 400 Ko | ⬜ 308 Ko en fonte complète ; sous-ensemblage à faire |
| Critère 5 — performance | ⬜ Appareil réel, à la beta |

Le critère éliminatoire est levé. Le reste se vérifie à la beta, sur les téléphones des testeurs — sans bloquer le développement.

---

## 5. Ce qui bloque, et comment le débloquer

Le banc est écrit et complet : [`tools/arabic_render_probe/`](../tools/arabic_render_probe/). Il n'a **pas été exécuté** — ce poste n'a ni Flutter, ni SDK Android, ni Java :

```
flutter : introuvable
adb     : introuvable
java    : introuvable
Android SDK : absent de %LOCALAPPDATA%\Android\Sdk
```

Rien dans ce document ne rapporte donc un résultat de mesure. Les seuils, les cas et la méthode sont posés ; les chiffres restent à produire.

### Installation — Flutter seul suffit pour l'instant

Android Studio et le SDK Android pèsent une dizaine de gigaoctets et ne servent qu'à produire un `.apk`. Le banc n'en a pas besoin : **Flutter Web (CanvasKit) utilise le même Skia et le même moteur de mise en page que le mobile**, donc `height` et `TextHeightBehavior` s'y comportent à l'identique. C'est précisément ce que la sonde navigateur ne pouvait pas atteindre.

> **Le SDK Flutter n'est pas distribué par winget.** `winget install --id Flutter.Flutter` échoue avec *No package found* : le dépôt ne contient que le SDK Dart (`Google.DartSDK`) et des applications écrites en Flutter. L'installation officielle sur Windows se fait par archive.

Version installée : **stable 3.47.2** (27/08/2026), Dart 3.13.2.

1. Télécharger l'archive :
   `https://storage.googleapis.com/flutter_infra_release/releases/stable/windows/flutter_windows_3.47.2-stable.zip`
   La liste des versions se lit dans `releases_windows.json`, au même emplacement.
2. Extraire dans `C:\src\flutter` — **jamais** sous `C:\Program Files` : Flutter écrit dans son propre dossier et l'élévation de privilèges le casse.
3. Ajouter `C:\src\flutter\bin` au `PATH` **utilisateur**.
4. Ouvrir un terminal neuf et vérifier :

```bash
flutter doctor
```

Seule la ligne **Flutter** doit être verte à ce stade. Les avertissements sur Android toolchain et Android Studio sont attendus et sans effet ici.

Android Studio viendra plus tard, quand il y aura une application à empaqueter — et lui est bien dans winget :

```bash
winget install --id Google.AndroidStudio -e
```

### Polices — ✅ en place

Téléchargées le 29/08/2026 dans `tools/arabic_render_probe/fonts/` :

| Fichier | Poids | Licence |
|---|---:|---|
| `Amiri-Regular.ttf` | 431 Ko | OFL 1.1 |
| `ScheherazadeNew-Regular.ttf` | 332 Ko | OFL 1.1 |
| `NotoNaskhArabic-Regular.ttf` | 308 Ko (fonte variable) | OFL 1.1 |

Les fichiers `OFL-*.txt` sont conservés à côté : la SIL Open Font License 1.1 autorise l'usage commercial, à condition de joindre la licence en cas de redistribution — ce qui est le cas dans un `.apk`.

Ces poids sont ceux des fontes **complètes**. Le critère 4 (≤ 400 Ko) porte sur le sous-ensemble arabe qui sera réellement embarqué : réduite aux blocs arabes en graisse normale, chacune tombe autour de 100 à 150 Ko. Le sous-ensemblage se fera après la décision, sur la seule police retenue.

### Exécution

```bash
cd tools/arabic_render_probe && flutter create --platforms=web .
```

Cette commande n'ajoute que l'échafaudage web manquant : elle ne touche ni `lib/`, ni `pubspec.yaml`.

```bash
flutter run -d chrome --release
```

`--release` et non `--debug` : le mode debug désactive des optimisations de rendu et fausserait la mesure de performance.

Appuyer sur **Lancer les mesures**, puis sur l'icône **Copier** pour récupérer le rapport JSON des 720 mesures.

---

## 6. Mesure intermédiaire au navigateur

En attendant l'installation, une mesure partielle est possible : Chrome et Flutter partagent le même moteur de façonnage de texte (HarfBuzz) et le même rasteriseur (Skia). Une page de test locale ouverte dans un navigateur donne donc un signal réel sur **la qualité de positionnement des signes par la police**.

**Ce qu'elle prouve :** si une police place mal une shadda ou une kasra, on le voit.
**Ce qu'elle ne prouve pas :** le rognage propre à Flutter, qui vient du calcul de `height` et de `TextHeightBehavior` — des mécanismes qui n'existent pas dans le navigateur. Le critère 1 ne peut pas être validé ainsi.

C'est un dégrossissage, pas la mesure. Il ne dispense pas de l'exécution sur appareil.

### Sonde navigateur — résultat, et pourquoi il était faux

Exécutée le 29/08/2026, elle plaçait Scheherazade New en tête et écartait Noto Naskh Arabic. **Le banc Flutter a inversé ce classement** : voir §4. Le détail de la sonde n'est plus reproduit ici, il n'a servi qu'à montrer que le proxy ne valait pas la mesure.

Ce qu'elle a tout de même établi, et qui tient : la police système déborde jusqu'à 6,96 px — embarquer une police n'est pas un principe mais une nécessité mesurée.
