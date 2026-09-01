# Banc de mesure du rendu des harakat

Étape 1 de la roadmap, exécution de [D10](../../docs/05-decisions.md#d10--le-rendu-des-harakat-est-le-risque-technique-n1).
Protocole, critères d'acceptation et résultats : [docs/07-rendu-arabe.md](../../docs/07-rendu-arabe.md).

**Projet jetable.** Il ne fait pas partie de l'application et ne sera pas repris dans le dépôt final. Son seul livrable est une décision : quelle police, quel `height`, quel `TextHeightBehavior`.

## Deux sondes

| Fichier | Ce qu'il mesure | Prérequis |
|---|---|---|
| `sonde-navigateur.html` | La police place-t-elle correctement les signes ? | Un navigateur. **Déjà exécuté** — résultats dans la doc |
| `lib/main.dart` | Flutter rogne-t-il l'encre ? 720 mesures | Flutter + SDK Android + un vrai téléphone |

La sonde navigateur dégrossit : elle classe les polices. Elle ne peut pas valider le critère éliminatoire, qui dépend de mécanismes propres à Flutter (`height`, `TextHeightBehavior`) absents d'un navigateur.

## Faire tourner la sonde navigateur

Ouvrir `sonde-navigateur.html`. Elle charge les polices depuis Google Fonts, donc il faut du réseau la première fois.

Elle affiche le pire débordement par police et par taille, puis le détail des cas fautifs.

## Faire tourner le banc Flutter

### 1. Flutter seul — pas besoin d'Android Studio

Flutter Web en mode CanvasKit utilise le **même Skia et le même moteur de mise en page** que le mobile. `height` et `TextHeightBehavior` s'y comportent à l'identique — c'est exactement ce que la sonde navigateur ne pouvait pas atteindre.

**Le SDK Flutter n'est pas dans winget** (`Flutter.Flutter` n'existe pas). Installation par archive : extraire `flutter_windows_<version>-stable.zip` dans `C:\src\flutter`, puis ajouter `C:\src\flutter\bin` au `PATH` utilisateur. Ne pas installer sous `C:\Program Files` — Flutter écrit dans son propre dossier.

Dans un terminal neuf :

```bash
flutter doctor
```

Seule la ligne **Flutter** doit être verte. Les avertissements Android sont attendus et sans effet ici.

### 2. Polices — déjà en place

`fonts/` contient les trois `.ttf` et leurs licences OFL 1.1, téléchargés depuis le dépôt `google/fonts`. Rien à faire.

### 3. Exécution

```bash
flutter create --platforms=web .
```

N'ajoute que l'échafaudage web manquant ; ne touche ni `lib/`, ni `pubspec.yaml`.

```bash
flutter run -d chrome --release
```

`--release` et non `--debug` : le mode debug fausse la mesure de performance.

Appuyer sur **Lancer les mesures**, puis sur l'icône **Copier** pour récupérer le rapport JSON.

### 4. Plus tard, sur Android

Quand il y aura une application à empaqueter :

```bash
winget install --id Google.AndroidStudio -e
```

```bash
flutter doctor --android-licenses
```

## Ce que le banc mesure

Pour chaque combinaison police × configuration de hauteur × taille × cas :

1. mise en page (`TextPainter.layout`) ;
2. peinture dans un canevas entouré de 120 px de marge vide ;
3. relevé de la première et de la dernière ligne de pixels encrés ;
4. comparaison de la boîte d'encre à la boîte de mise en page.

Débordement > 0,5 px → rognage garanti dans un conteneur contraint.

La marge de 120 px est le cœur de la méthode : peindre dans une image de la taille exacte de la boîte reviendrait à rogner l'encre avant de la mesurer.

## Appareils

Flutter n'utilise pas la pile de texte d'Android : son moteur embarque son propre Skia. Avec une police embarquée, la géométrie des signes ne dépend donc **pas** de la version d'Android ni du constructeur.

| Aspect | Dépend de l'appareil ? | Où le mesurer |
|---|---|---|
| Débordement des signes (critère éliminatoire) | non | Chrome, maintenant |
| Arrondi à faible densité | un peu | Émulateur 480×854 mdpi |
| Repli de police sur le cas mixte arabe/latin | oui | Appareil réel |
| Performance, lisibilité sur 5 pouces | oui | Appareil réel, à la beta |

**L'absence d'un Android bas de gamme ne bloque donc pas l'étape 1.** Elle repousse seulement la vérification des critères 4 et 5, qui trouvent leur place au moment de la beta — où il faut de toute façon des testeurs réels.
