/// Stockage local : le cache de contenu et la file de tentatives.
library;

import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

/// Pourquoi pas Drift, alors que [D2] annonce SQLite ?
///
/// Parce que le client ne fait **aucune pédagogie**. La séance arrive composée
/// par le serveur : le téléphone n'a rien à interroger, il a des séances à
/// garder et des tentatives à mettre en file. Un magasin clé-valeur suffit, et
/// une base relationnelle serait ici du décor.
///
/// Le jour où le client devra décider seul — composer la séance du lendemain
/// après quatre jours hors ligne, calculer ce qui est dû — il faudra des
/// requêtes, donc Drift. Ce moment est identifié, il n'est pas arrivé.
class Stockage {
  static const _cleSeances = 'seances_prechargees';
  static const _cleFile = 'file_tentatives';
  static const _cleDerniereSynchro = 'derniere_synchro';
  static const _cleJourCourant = 'jour_courant';

  Future<SharedPreferences> get _prefs => SharedPreferences.getInstance();

  // ------------------------------------------------------------- contenu

  /// Range une séance pour pouvoir la jouer sans réseau.
  Future<void> rangerSeance(int jour, Map<String, dynamic> seance) async {
    final p = await _prefs;
    final tout = await seancesRangees();
    tout['$jour'] = seance;
    await p.setString(_cleSeances, jsonEncode(tout));
  }

  Future<Map<String, dynamic>> seancesRangees() async {
    final brut = (await _prefs).getString(_cleSeances);
    if (brut == null) return {};
    return (jsonDecode(brut) as Map).cast<String, dynamic>();
  }

  Future<Map<String, dynamic>?> seance(int jour) async =>
      (await seancesRangees())['$jour'] as Map<String, dynamic>?;

  /// Le jour où en est l'apprenant.
  ///
  /// Distinct des jours rangés : ceux-ci vont plus loin, pour couvrir une
  /// coupure. Confondre les deux ferait sauter des jours dès la première
  /// perte de réseau.
  Future<void> noterJourCourant(int jour) async =>
      (await _prefs).setInt(_cleJourCourant, jour);

  Future<int?> jourCourant() async => (await _prefs).getInt(_cleJourCourant);

  // ---------------------------------------------------------------- file

  /// Empile des tentatives à envoyer plus tard.
  ///
  /// Chaque tentative porte déjà son `client_id` : la synchronisation est
  /// idempotente, donc renvoyer un lot après une coupure n'écrit qu'une fois.
  /// C'est ce qui permet d'empiler sans crainte plutôt que de perdre.
  Future<void> empiler(int jour, List<Map<String, dynamic>> tentatives) async {
    if (tentatives.isEmpty) return;
    final p = await _prefs;
    final file = await fileAttente();
    file.add({
      // Un identifiant de lot, parce qu'en Dart deux `Map` de contenu
      // identique ne sont pas égales : sans lui, `retirer` ne retirerait
      // jamais rien et la file grossirait sans fin.
      'lot_id': '${DateTime.now().microsecondsSinceEpoch}-${file.length}',
      'day_number': jour,
      'attempts': tentatives,
    });
    await p.setString(_cleFile, jsonEncode(file));
  }

  Future<List<Map<String, dynamic>>> fileAttente() async {
    final brut = (await _prefs).getString(_cleFile);
    if (brut == null) return [];
    return (jsonDecode(brut) as List).cast<Map<String, dynamic>>();
  }

  Future<void> viderFile() async => (await _prefs).remove(_cleFile);

  /// Retire les lots déjà partis, garde les autres.
  ///
  /// On ne vide jamais la file en bloc après un envoi partiel : le lot qui a
  /// échoué doit survivre, sans quoi une coupure au milieu de la remontée
  /// effacerait une séance entière.
  Future<void> retirer(List<Map<String, dynamic>> partis) async {
    final p = await _prefs;
    final idsPartis = partis.map((lot) => lot['lot_id']).toSet();
    final restants = (await fileAttente())
        .where((lot) => !idsPartis.contains(lot['lot_id']))
        .toList();
    await p.setString(_cleFile, jsonEncode(restants));
  }

  Future<int> nbTentativesEnAttente() async {
    var n = 0;
    for (final lot in await fileAttente()) {
      n += (lot['attempts'] as List).length;
    }
    return n;
  }

  // -------------------------------------------------------------- divers

  Future<void> noterSynchro() async =>
      (await _prefs).setString(_cleDerniereSynchro, DateTime.now().toIso8601String());

  Future<DateTime?> derniereSynchro() async {
    final brut = (await _prefs).getString(_cleDerniereSynchro);
    return brut == null ? null : DateTime.tryParse(brut);
  }

  Future<void> toutEffacer() async {
    final p = await _prefs;
    await p.remove(_cleSeances);
    await p.remove(_cleFile);
    await p.remove(_cleDerniereSynchro);
  }
}
