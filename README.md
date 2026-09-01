# IqraGo

Coach personnel intelligent pour apprendre à lire l'arabe.

**État : blueprint arbitré, rendu arabe tranché. Production du contenu en cours.**

## Documents

| Fichier | Contenu |
|---|---|
| [docs/05-decisions.md](docs/05-decisions.md) | **Les douze décisions, toutes tranchées. À lire en premier.** |
| [docs/00-blueprint.md](docs/00-blueprint.md) | Document maître : produit, architecture, business |
| [docs/01-pedagogie.md](docs/01-pedagogie.md) | Programme 30 jours (variante B), ~297 compétences, 13 types d'exercices |
| [docs/02-donnees.md](docs/02-donnees.md) | Schéma de base de données |
| [docs/03-api.md](docs/03-api.md) | Contrat d'API REST |
| [docs/04-speech.md](docs/04-speech.md) | Architecture audio, ASR, évaluation de prononciation |
| [docs/06-roadmap.md](docs/06-roadmap.md) | Complexité par module, ordre exact de développement |
| [docs/07-rendu-arabe.md](docs/07-rendu-arabe.md) | Étape 1 — protocole, critères, résultats |

## Outils

| Dossier | Rôle |
|---|---|
| [content/](content/) | Socle pédagogique : lettres, mots, 283 compétences, manifeste audio |
| [tools/contenu/](tools/contenu/) | Validateur et générateur de contenu (`dart run`) |
| [tools/arabic_render_probe/](tools/arabic_render_probe/) | Banc de mesure du rendu des harakat (Flutter + sonde navigateur) |

## Où on en est

- Les douze décisions d'architecture sont arbitrées.
- Le programme pédagogique retenu est la **variante B** : premier mot lu au jour 3.
- **Étape 1 terminée** : 720 mesures Flutter. Police retenue — **Noto Naskh Arabic, `height: 1.5`**, seule configuration à 0,00 px de débordement.
- ⚠️ `height: 1.0` rogne sur les trois polices, jusqu'à 31 px. C'est la valeur à ne jamais écrire.
- **Prochaine action :** production du contenu pédagogique (`content/`) — le chemin critique du projet.

## Deux chantiers à lancer en parallèle du développement

Ce sont les deux vrais chemins critiques, et aucun n'est du code ([D12](docs/05-decisions.md#d12--contenu-et-corpus-vocal--deux-chantiers-parallèles)) :

1. **Contenu** — ~900 exercices, ~180 audios, validés avant publication.
2. **Corpus vocal** — 300 à 500 lectures annotées, consenties, anonymisées.

Menés en série après le développement, ils ajoutent quatre mois au projet.
