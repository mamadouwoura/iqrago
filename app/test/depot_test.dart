import 'package:flutter_test/flutter_test.dart';
import 'package:iqrago/core/stockage.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Ce qui compte hors ligne n'est pas de savoir jouer sans réseau — c'est de
/// ne rien perdre. Ces tests portent sur la file.
void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  test('une séance rangée se retrouve', () async {
    final s = Stockage();
    await s.rangerSeance(3, {'day_number': 3, 'blocks': []});
    expect((await s.seance(3))!['day_number'], 3);
    expect(await s.seance(9), isNull);
  });

  test('les tentatives s\'empilent au lieu de se perdre', () async {
    final s = Stockage();
    await s.empiler(1, [
      {'client_id': 'a', 'skill_id': 'letter.dal.recognize'},
      {'client_id': 'b', 'skill_id': 'letter.dhal.recognize'},
    ]);
    await s.empiler(2, [
      {'client_id': 'c', 'skill_id': 'haraka.fatha'}
    ]);

    expect((await s.fileAttente()).length, 2, reason: 'deux lots distincts');
    expect(await s.nbTentativesEnAttente(), 3);
  });

  test('un envoi partiel ne vide pas la file', () async {
    final s = Stockage();
    await s.empiler(1, [
      {'client_id': 'a'}
    ]);
    await s.empiler(2, [
      {'client_id': 'b'}
    ]);

    final file = await s.fileAttente();
    await s.retirer([file.first]); // seul le premier lot est parti

    final restants = await s.fileAttente();
    expect(restants.length, 1,
        reason: 'une coupure au milieu ne doit pas effacer la séance suivante');
    expect(restants.first['day_number'], 2);
  });

  test('empiler une liste vide ne crée pas de lot fantôme', () async {
    final s = Stockage();
    await s.empiler(1, []);
    expect(await s.fileAttente(), isEmpty);
  });

  test('la file survit à un redémarrage', () async {
    await Stockage().empiler(1, [
      {'client_id': 'a'}
    ]);
    // Une instance neuve, comme après une fermeture de l'application.
    expect(await Stockage().nbTentativesEnAttente(), 1);
  });

  test('le jour courant ne saute pas à cause du préchargement', () async {
    final s = Stockage();
    // L'apprenant est au jour 1 ; les jours 2 et 3 sont rangés d'avance.
    await s.noterJourCourant(1);
    for (final j in [1, 2, 3]) {
      await s.rangerSeance(j, {'day_number': j, 'blocks': []});
    }
    expect(await s.jourCourant(), 1,
        reason: 'précharger ne fait pas avancer l\'apprenant');
  });

  test('terminer une séance fait avancer le jour, hors ligne aussi', () async {
    final s = Stockage();
    await s.noterJourCourant(1);
    await s.noterJourCourant(2); // ce que fait Depot.terminer
    expect(await s.jourCourant(), 2,
        reason: 'sans cela, on rejouerait la même séance indéfiniment');
  });
}
