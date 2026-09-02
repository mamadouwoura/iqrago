/// Le dépôt : la seule porte par laquelle les écrans obtiennent une séance.
library;

import 'api.dart';
import 'modeles.dart';
import 'stockage.dart';

/// D'où vient la séance, et ce que l'utilisateur doit en savoir.
enum Provenance {
  /// Fraîche, du serveur.
  reseau,

  /// Rangée à l'avance. La séance se joue normalement.
  cache,

  /// Ni réseau ni contenu rangé : c'est le seul cas bloquant.
  rien,
}

class Resultat {
  Resultat(this.seance, this.provenance, {this.enAttente = 0});
  final Seance? seance;
  final Provenance provenance;
  final int enAttente;
}

/// Hors ligne d'abord.
///
/// Le principe qui gouverne ce fichier : **on n'interroge pas l'état du
/// réseau, on essaie**. Un téléphone peut être « connecté » à un portail
/// captif, à une 4G qui ne passe pas, à un wifi sans sortie. Le seul test
/// fiable est la requête elle-même, et son échec bascule sur le contenu rangé.
class Depot {
  Depot(this.api, this.stockage);

  final Api api;
  final Stockage stockage;

  /// Combien de jours d'avance on garde.
  ///
  /// Deux, pas trente : sur une data prépayée, précharger le parcours entier
  /// coûterait cher pour du contenu qui aura peut-être changé. Deux jours
  /// couvrent une soirée hors ligne et un trajet du lendemain.
  static const joursDAvance = 2;

  Future<Resultat> seanceDuJour() async {
    // Toute remontée de progression passe d'abord : le serveur doit connaître
    // les tentatives d'hier avant de composer la séance d'aujourd'hui, sinon
    // il propose des révisions déjà faites.
    await remonterLaFile();

    try {
      final r = await api.seanceDuJour();
      if (r.statusCode == 200) {
        final data = r.data as Map<String, dynamic>;
        final seance = Seance.depuisJson(data);
        await stockage.rangerSeance(seance.jour, data);
        await stockage.noterJourCourant(seance.jour);
        await stockage.noterSynchro();
        _precharger(seance.jour);
        return Resultat(seance, Provenance.reseau,
            enAttente: await stockage.nbTentativesEnAttente());
      }
      if (r.statusCode == 401 || r.statusCode == 403) {
        // Un refus est une réponse, pas une panne : ne pas le masquer par du
        // cache, sinon un utilisateur sans droit croirait la séance ouverte.
        return Resultat(null, Provenance.rien);
      }
    } catch (_) {
      // Réseau absent — on continue sur le contenu rangé.
    }

    return _depuisLeCache();
  }

  Future<Resultat> _depuisLeCache() async {
    final rangees = await stockage.seancesRangees();
    if (rangees.isEmpty) return Resultat(null, Provenance.rien);

    // Le jour où en est l'apprenant, pas le plus récemment téléchargé.
    //
    // Les jours suivants sont rangés d'avance : servir « le dernier rangé »
    // ferait sauter l'apprenant du jour 1 au jour 3 dès qu'il perd le réseau.
    // Le jour courant vient du dernier appel réseau réussi, et avance
    // localement à chaque séance terminée — c'est ce qui permet d'enchaîner
    // plusieurs séances hors ligne.
    final jours = rangees.keys.map(int.parse).toList()..sort();
    final courant = await stockage.jourCourant() ?? jours.first;
    final choisi = jours.contains(courant) ? courant : jours.first;

    return Resultat(
      Seance.depuisJson(rangees['$choisi'] as Map<String, dynamic>),
      Provenance.cache,
      enAttente: await stockage.nbTentativesEnAttente(),
    );
  }

  /// Range les jours suivants pendant que l'utilisateur joue celui-ci.
  ///
  /// Silencieux : c'est un confort, pas une étape. Son échec ne doit jamais
  /// interrompre une séance en cours.
  Future<void> _precharger(int jourActuel) async {
    for (var j = jourActuel + 1; j <= jourActuel + joursDAvance; j++) {
      try {
        final r = await api.seanceDuJour(jour: j);
        if (r.statusCode == 200) {
          await stockage.rangerSeance(j, r.data as Map<String, dynamic>);
        }
      } catch (_) {
        return; // réseau reparti : inutile d'insister
      }
    }
  }

  /// Termine une séance : la file d'abord, le réseau ensuite.
  ///
  /// Les tentatives sont **empilées avant toute tentative d'envoi**. Si
  /// l'application meurt entre les deux, rien n'est perdu.
  Future<bool> terminer(int jour, List<Map<String, dynamic>> tentatives) async {
    await stockage.empiler(jour, tentatives);
    // Le jour avance localement : sans cela, un apprenant hors ligne rejouerait
    // la même séance indéfiniment. Le serveur reste l'autorité — il corrigera
    // à la prochaine connexion s'il n'est pas d'accord.
    await stockage.noterJourCourant(jour + 1);
    return remonterLaFile();
  }

  /// Renvoie tout ce qui attend. Vrai si la file est vidée.
  Future<bool> remonterLaFile() async {
    final file = await stockage.fileAttente();
    if (file.isEmpty) return true;

    final partis = <Map<String, dynamic>>[];
    for (final lot in file) {
      try {
        final r = await api.synchroniser({
          'day_number': lot['day_number'],
          'attempts': lot['attempts'],
          'source': 'offline_sync',
          'completed_at': DateTime.now().toUtc().toIso8601String(),
        });
        if (r.statusCode == 200) {
          partis.add(lot);
        } else if (r.statusCode == 400) {
          // Un lot que le serveur refuse ne partira jamais : le garder
          // bloquerait tous les suivants derrière lui.
          partis.add(lot);
        } else {
          break;
        }
      } catch (_) {
        break; // réseau absent : on réessaiera au prochain lancement
      }
    }

    if (partis.isNotEmpty) {
      await stockage.retirer(partis);
      await stockage.noterSynchro();
    }
    return partis.length == file.length;
  }
}
