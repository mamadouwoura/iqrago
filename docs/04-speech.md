# Architecture audio, ASR et évaluation de la lecture

Ce document développe [D1](05-decisions.md#d1--coach-vocal--quatre-niveaux-progressifs).

---

## 1. Le malentendu à lever

Trois tâches sont régulièrement confondues sous le mot « IA vocale ». Elles n'ont ni la même difficulté, ni les mêmes modèles, ni la même fiabilité.

| Tâche | Question posée | Difficulté |
|---|---|---|
| **ASR** — reconnaissance | *Qu'est-ce qui a été dit ?* | Résolue pour l'arabe standard, lecture adulte, audio propre |
| **Alignement forcé** | *Le texte attendu étant connu, où tombe chaque son ?* | Solide, y compris sur de la lecture hésitante |
| **Évaluation de prononciation** | *Ce son est-il bien réalisé, et sinon lequel a été produit ?* | Problème de recherche ouvert, spécifique à la langue |

Le cahier des charges demande la troisième (§12 : « il reste une difficulté sur ض ») et propose la première comme moyen (§14 : Whisper). **La première ne produit pas la troisième.**

### Pourquoi Whisper ne peut pas noter une prononciation arabe

1. **Il corrige ce qu'il entend.** Un modèle de bout en bout intègre un modèle de langage : il produit la séquence la plus *plausible*, pas la plus *fidèle*. Un apprenant qui dit « sa » au lieu de « ṣa » se voit transcrire صَ. L'erreur qu'on veut détecter est réparée avant qu'on puisse la voir.
2. **Sa sortie arabe est non vocalisée.** Il rend `كتب`, jamais `كَتَبَ`. Les harakat — trois semaines de programme — sont absentes de sa sortie. Une confusion fathah/damma est structurellement invisible.
3. **Il hallucine sur les segments courts.** `بَ` dure ~300 ms. Sans contexte, le décodeur produit des mots entiers à partir d'un souffle, voire des fragments de ses données d'entraînement. Les jours 1 à 12 sont presque exclusivement des items isolés.
4. **Ses faiblesses coïncident exactement avec nos cibles.** Emphatiques (ص ض ط ظ) et gutturales (ع ح غ خ ق) sont le point faible connu des ASR arabes grand public. Ce sont précisément les paires que l'application doit corriger, et celles où un francophone se trompe.

Le problème n'est pas la qualité de Whisper. C'est qu'on lui demande une tâche pour laquelle il n'est pas construit.

---

## 2. Cinq niveaux, livrés dans cet ordre

### L0 — Miroir (MVP)

Le système n'affirme rien.

```
[Écouter le modèle]  →  🎙️ [Appuie et lis]  →  [Ta voix]  [Le modèle]
                                                  ↓
                                    « Je l'ai dit »   « J'hésite »
```

L'utilisateur s'entend juste après la référence, et juge. C'est de l'auto-évaluation guidée : la comparaison immédiate rend le jugement bien plus juste qu'une évaluation à froid, et l'écoute de sa propre voix est en soi un outil pédagogique reconnu.

Coût serveur : **zéro**. Latence : **zéro**. Fonctionne hors ligne. Ne ment jamais.
Deux boutons, pas trois : une échelle plus fine invite à la complaisance.

### L1 — Qualité du signal (MVP)

Le seul jugement automatique honnête au lancement, parce qu'il est purement acoustique.

| Verdict | Détection | Message |
|---|---|---|
| `no_speech` | VAD : aucun segment vocal | « Je n'ai rien entendu. » |
| `too_short` | durée utile < 40 % de la référence | « C'était très court, recommence. » |
| `too_noisy` | SNR < 10 dB | « Il y a du bruit autour de toi. » |
| `ok` | — | On passe au miroir L0 |

**Tourne sur le téléphone**, en Dart, avec un VAD énergétique simple (ou Silero VAD converti en TFLite si nécessaire). Aucun octet envoyé, aucune seconde de serveur. Cela intercepte l'essentiel des enregistrements ratés — qui sont, sur un premier usage, la majorité.

### L1.5 — Transcription conditionnelle (MVP)

Ajoutée par l'arbitrage [D1](05-decisions.md#d1--coach-vocal--quatre-niveaux-progressifs). Le système affiche **ce qu'il a entendu**, et seulement si sa confiance le permet.

C'est une affirmation **descriptive**, pas évaluative : « voici ce que j'ai entendu », jamais « voici ce que tu as mal dit ». La différence n'est pas rhétorique — elle détermine ce que le système a le droit de faire quand il se trompe. Une transcription fausse est une gêne ; une correction fausse est une perte de confiance.

Trois garde-fous, sans lesquels L1.5 redevient un jugement déguisé :

| Garde-fou | Raison |
|---|---|
| **Jamais sur un item isolé** — mots et phrases uniquement, à partir du jour 8 | Une syllabe de 300 ms fait halluciner le décodeur (§1.3) |
| **Comparaison sur le squelette consonantique seul** | La sortie de Whisper est non vocalisée : comparer les harakat produirait un écart systématique et faux (§1.2) |
| **Seuil de confiance strict, silence en dessous** | Le seuil se calibre sur les données de beta, pas *a priori* |

Le retour utilisateur reste simple : combien de mots attendus ont été reconnus, et lesquels. Pas de pourcentage de précision, pas de désignation de phonème.

**Ce qu'il faut surveiller en analytics :** le taux d'activation de L1.5. S'il se tait dans plus de la moitié des cas, le problème est le seuil ou la chaîne audio — pas l'utilisateur. Un événement `speech_low_confidence` est émis à chaque silence, avec le SNR et la durée, précisément pour pouvoir trancher.

### L2 — Fluidité (Beta)

Ici le serveur intervient, mais **sans jamais juger un phonème**.

Le texte attendu est connu. On l'aligne sur l'audio (CTC-segmentation sur un modèle acoustique arabe, ou Whisper avec horodatage au mot), et on en tire :

| Mesure | Fiabilité |
|---|---|
| Mots par minute | Élevée |
| Nombre et durée des pauses internes | Élevée |
| Latence avant le premier son | Élevée |
| Mots omis ou répétés | Bonne |
| Ordre respecté | Bonne |

Ces mesures ne demandent aucune décision phonétique : il suffit de savoir *où* ça parle et *combien de temps*. Elles sont robustes même sur une lecture approximative.

**C'est la moitié honnête du « coach vocal », et c'est celle qui se voit.** Un utilisateur qui passe de 22 à 61 mots par minute en trois semaines voit une courbe monter. C'est plus convaincant qu'un « précision : 92 % » qu'il ne sait pas interpréter.

L2 ne s'applique qu'aux **mots et aux phrases** — jamais aux syllabes isolées, où la notion de vitesse n'a pas de sens.

### L3 — Prononciation (après corpus)

La fonctionnalité du §12. Elle exige une chaîne différente de l'ASR :

```
audio + texte attendu
   ↓  phonémisation du texte attendu (lexique arabe vocalisé → phonèmes)
   ↓  alignement forcé (modèle acoustique, pas de modèle de langage)
   ↓  GOP — Goodness of Pronunciation
        pour chaque phonème : log P(phonème attendu | segment)
                            − log P(meilleur phonème concurrent | segment)
   ↓  seuil par phonème, calibré sur corpus annoté
   ↓  retour : « ton ض ressemble à un د »
```

Le point clé est le **retrait du modèle de langage**. Un aligneur forcé ne cherche pas ce qui est plausible : il mesure à quel point le signal correspond au son attendu. C'est ce qui le rend capable de voir une erreur au lieu de la corriger.

Le GOP produit un score par phonème, pas un pourcentage global. Le « 92 % » du cahier des charges serait une agrégation de ces scores — utilisable en affichage, mais dérivée, jamais mesurée directement.

**Ce qui bloque L3 n'est pas le code. C'est le seuil.** Un score GOP brut n'a aucune signification absolue : il dépend du locuteur, du micro, de la pièce, de la langue maternelle. Le convertir en « c'est faux » exige de savoir, sur des données réelles, où placer la frontière — et donc un corpus annoté.

---

## 3. Le corpus d'évaluation

**C'est le vrai chemin critique du coach vocal**, et c'est un travail de terrain, pas de développement.

| Élément | Cible |
|---|---|
| Locuteurs | 40 à 60 francophones débutants, représentatifs (Dakar, diaspora, âges et genres variés) |
| Enregistrements | 300 à 500, dans les conditions réelles : téléphone, pièce ordinaire, bruit de fond |
| Contenu | Les 12 contrastes, ×3 harakat, plus 20 mots et 10 phrases |
| Annotation | Par un enseignant compétent : pour chaque phonème, *correct* / *substitué (par quoi)* / *omis* |
| Double annotation | ~20 % du corpus par deux annotateurs, pour mesurer l'accord inter-juges |

### Gouvernance du corpus ([D12](05-decisions.md#d12--contenu-et-corpus-vocal--deux-chantiers-parallèles))

La collecte démarre en phase A, avant le socle technique. Six exigences, toutes bloquantes avant tout usage des données :

| Exigence | Traduction opérationnelle |
|---|---|
| **Profils variés** | Âges, genres, niveaux ; Dakar **et** diaspora — un corpus tourné sur une seule population produit un seuil qui ne vaut que pour elle |
| **Conditions documentées** | Un formulaire par enregistrement : modèle d'appareil, lieu, bruit ambiant estimé, distance au micro. Sans ces métadonnées, un score aberrant est ininterprétable |
| **Consentement** | Écrit, explicite, spécifique à l'usage « entraînement et évaluation d'un système automatique », révocable à tout moment |
| **Anonymisation** | Identifiant aléatoire. Aucun nom, aucun numéro — ni dans les fichiers, ni dans les noms de fichiers, ni dans les métadonnées audio |
| **Conservation** | Durée définie à l'avance, suppression effective à l'échéance, révocation honorée sous 30 jours |
| **Annotation exploitable** | **Avant** tout entraînement ou toute évaluation. Un corpus non annoté ne mesure rien : il donne l'illusion d'avoir des données |

**Petit et bien annoté plutôt que grand et inexploitable.** C'est la règle posée à l'arbitrage, et elle est juste : 300 enregistrements annotés phonème par phonème permettent de calibrer un seuil ; 5 000 enregistrements bruts ne permettent rien du tout.

Le corpus est stocké **séparément** des audios de production, dans un bucket dédié, avec sa propre politique de rétention. Les enregistrements d'utilisateurs de l'application n'y entrent jamais automatiquement — leur consentement porte sur l'analyse de leur lecture, pas sur la constitution d'un jeu d'entraînement. Verser un audio de production au corpus exige un consentement distinct, demandé explicitement.

### Mesurer avant de croire

L'accord inter-juges est la mesure la plus importante du lot, et celle qu'on oublie toujours. Si deux enseignants ne sont d'accord que dans 70 % des cas sur ce qu'est un « ض correct », **aucun système automatique ne peut faire mieux que 70 %**, et il faut le dire au lieu d'afficher un pourcentage à la décimale.

**Métriques de sortie, à publier avant d'activer L3 :**

| Métrique | Seuil d'activation proposé |
|---|---|
| Faux positifs (dit « faux » alors que c'est correct) | **< 5 %** |
| Faux négatifs (laisse passer une vraie erreur) | < 30 % |
| Accord avec l'annotateur humain | > 80 % |
| Taux de « je n'ai pas bien entendu » | < 15 % |

L'asymétrie entre les deux premiers seuils est délibérée. Manquer une erreur laisse l'utilisateur dans l'état où il serait sans coach : coût nul. Inventer une erreur lui fait corriger quelque chose de correct et lui apprend à douter de l'application : coût irréversible. **Le système doit préférer se taire.**

Durée : 3 à 6 semaines de terrain, en parallèle du développement, à lancer en phase 1.

---

## 4. L'abstraction `SpeechService`

Exigée par le §13. Trois méthodes, aucune fuite du moteur sous-jacent.

```python
class SignalReport(TypedDict):
    verdict: Literal["ok", "no_speech", "too_short", "too_noisy"]
    duration_ms: int
    snr_db: float

class SpeechService(Protocol):
    def check_signal(self, audio: Audio) -> SignalReport: ...
    def align(self, audio: Audio, expected: str) -> Alignment | None: ...
    def score(self, alignment: Alignment) -> PronunciationScore | None: ...
```

| Implémentation | Fournit | Phase |
|---|---|---|
| `LocalSignalService` | `check_signal` seul, sur le téléphone | MVP |
| `WhisperAlignService` | `+ align` (faster-whisper, horodatage au mot) | Beta |
| `GopService` | `+ score` (modèle acoustique + GOP calibré) | Après corpus |
| `VendorService` | Repli sur une API tierce, si elle se révèle meilleure | Optionnel |

`align` et `score` renvoient `None` quand la confiance est insuffisante. **`None` n'est pas une erreur** : c'est le comportement attendu, et l'interface utilisateur doit le traiter comme un cas normal (« je n'ai pas bien entendu ») et non comme une panne.

Le choix de l'implémentation est une variable d'environnement, jamais un `if` dans le code produit.

---

## 5. Modèles candidats

| Modèle | Rôle envisagé | Verdict |
|---|---|---|
| `faster-whisper` small/medium | Alignement L2 | **Retenu pour L2.** ~0,3-0,5× temps réel sur CPU, horodatage au mot correct |
| Whisper large | Transcription | Écarté : trop lourd pour du CPU, et ne résout aucun problème que small ne résout |
| MMS / wav2vec2 arabe | Modèle acoustique pour L3 | **Piste principale.** Sortie par phonème, sans modèle de langage — c'est ce qu'il faut |
| Montreal Forced Aligner | Alignement L3 | Solide, mais lourd à déployer ; à comparer à la CTC-segmentation |
| Silero VAD | L1 sur le téléphone | **Retenu** si le VAD énergétique se révèle insuffisant. ~1 Mo en TFLite |
| API commerciales | Repli | À réévaluer : le prix par minute décide, pas la qualité seule |

Aucun de ces choix n'est définitif : c'est précisément le rôle de l'abstraction.

---

## 6. Coûts

Ordres de grandeur **à confirmer par mesure**, pas des engagements.

Un parcours complet ≈ 90 enregistrements × ~6 s ≈ **9 minutes d'audio par utilisateur**.

| Niveau | Coût CPU par parcours | Note |
|---|---|---|
| L0 + L1 | 0 | Tout se passe sur le téléphone |
| L2 (faster-whisper small) | ~4 à 5 min CPU | À 0,5× temps réel |
| L3 (alignement + GOP) | ~8 à 12 min CPU | Estimation large |

Sur un serveur à 4 vCPU (~25 000 FCFA/mois), en réservant 50 % à l'inférence : ~1 440 vCPU-heures utiles par mois, soit de l'ordre de **7 000 parcours L2/mois** ou **3 500 en L3**. C'est confortable jusqu'au palier de 5 000 abonnés du §38.

**Conséquence d'architecture :** le traitement passe par Celery, jamais dans le cycle requête/réponse. Une file qui prend deux minutes de retard est invisible pour l'utilisateur — il a déjà eu son retour L0/L1 local. Une requête HTTP qui prend deux minutes est un produit cassé.

Stockage : ~9 min d'Opus à 24 kbps ≈ **1,6 Mo par utilisateur**, supprimé à 30 jours. Négligeable.

---

## 7. Synthèse vocale (§16)

**Les audios de référence sont enregistrés par un humain, pas synthétisés.**

Une voix TTS sur `ضَ` produit une approximation. L'utilisateur imite ce qu'il entend : une référence approximative enseigne une erreur — et l'enseigne à tout le monde, définitivement. C'est le poste où l'économie est la plus tentante et la plus coûteuse.

| | |
|---|---|
| Volume | 28 lettres × 3 harakat + ~60 mots + ~30 phrases ≈ **180 fichiers** |
| Production | Une journée de studio, un locuteur natif, débit lent et articulé |
| Format | Opus 24 kbps mono, ~4 Ko/s |
| Poids total | **< 3 Mo** — embarqué dans l'application, hors ligne, sans téléchargement |
| Vitesses | 0,75× / 1× / 1,25× par étirement temporel côté client (`just_audio`), pas trois fichiers |

Le TTS garde une place : le contenu **généré** (phrases d'entraînement supplémentaires, parcours 2), où l'approximation est acceptable parce que le contenu n'est pas un référentiel.

---

## 8. Protocole de test (§48)

Les tests IA ne sont pas des tests unitaires : ce sont des mesures, avec des seuils, exécutées sur un corpus figé.

| Test | Corpus | Seuil |
|---|---|---|
| VAD — détection de parole | 100 enregistrements étiquetés | > 95 % de justesse |
| VAD — rejet du bruit | 50 enregistrements sans parole | > 90 % de rejet |
| Alignement L2 | 50 lectures avec frontières annotées | erreur médiane < 80 ms |
| Mots/minute | 30 lectures chronométrées à la main | écart < 10 % |
| GOP L3 | corpus annoté complet | faux positifs < 5 % |
| Bruit | mêmes items à 20, 15, 10, 5 dB de SNR | dégradation progressive, jamais de faux positif qui augmente |

Le dernier est le plus important et le plus souvent omis : un système dont les **faux positifs augmentent** quand le signal se dégrade est dangereux, parce qu'il devient d'autant plus affirmatif qu'il en sait moins. Le comportement correct est l'inverse — quand le signal se dégrade, le système doit se taire davantage.

Ces mesures tournent en intégration continue sur le corpus figé, et toute régression au-delà du seuil bloque le déploiement du service speech.
