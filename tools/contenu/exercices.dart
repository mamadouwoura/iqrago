// Générateur d'exercices IqraGo.
//
//   dart run tools/contenu/exercices.dart
//
// Produit `content/exercices/jour-NN.json` — un lot par jour de parcours —
// et `content/exercices/LACUNES.md`, la liste exacte de ce qui manque.
//
// CE QUI SORT D'ICI SONT DES BROUILLONS. Rien ne se publie sans relecture
// humaine (§47). Le cycle éditorial l'impose en base.
//
// Deux propriétés tenues :
//
// * **Déterminisme.** Regénérer produit exactement le même contenu. Sans
//   cela, chaque exécution ferait bouger 850 fichiers et rendrait toute
//   relecture incrémentale impossible.
// * **Aucun distracteur non enseigné.** Montrer une lettre inconnue comme
//   mauvaise réponse l'enseigne de travers.

import 'dart:convert';
import 'dart:io';
import 'dart:math';

// ---------------------------------------------------------------- données

late Map<String, dynamic> socle;
late List<Map<String, dynamic>> lettres;
late List<Map<String, dynamic>> harakat;
late List<Map<String, dynamic>> marques;
late List<Map<String, dynamic>> contrastes;
late List<Map<String, dynamic>> mots;
late List<Map<String, dynamic>> competences;

/// caractère -> fiche lettre
final parCaractere = <String, Map<String, dynamic>>{};

/// identifiant de famille -> caractères
final familles = <String, List<String>>{};

/// caractère -> identifiant de famille (ou null)
final familleDe = <String, String?>{};

/// Une case manquante du corpus : ce qu'il faut trouver, et à quelle date.
class Manque {
  Manque({
    required this.jour,
    required this.competence,
    required this.lettre,
    required this.besoin,
    this.partiel = 0,
  });
  final int jour;
  final String competence, lettre, besoin;
  final int partiel; // nb de mots déjà trouvés (0 = aucun)
}

final manques = <Manque>[];
final lacunes = <String>[];

// ------------------------------------------------------------- utilitaires

/// Aléa reproductible, dérivé de l'identifiant de la compétence : la même
/// compétence produit toujours les mêmes exercices.
Random alea(String graine) {
  var h = 0;
  for (final c in graine.codeUnits) {
    h = (h * 31 + c) & 0x7fffffff;
  }
  return Random(h);
}

List<T> melanger<T>(List<T> liste, Random r) {
  final copie = [...liste];
  for (var i = copie.length - 1; i > 0; i--) {
    final j = r.nextInt(i + 1);
    final t = copie[i];
    copie[i] = copie[j];
    copie[j] = t;
  }
  return copie;
}

/// Les lettres enseignées à cette date, cible exclue.
List<String> lettresConnues(int jour, {String? sauf}) => lettres
    .where((l) => (l['jour'] as int) <= jour && l['lettre'] != sauf)
    .map((l) => l['lettre'] as String)
    .toList();

/// Distracteurs, par ordre de valeur pédagogique décroissante.
///
/// 1. les sœurs de famille — même squelette, c'est là qu'est la confusion ;
/// 2. les lettres les plus récentes — plus fragiles que celles acquises
///    depuis deux semaines ;
/// 3. le reste de l'acquis.
///
/// Jamais une lettre non encore enseignée.
List<String> distracteurs(String cible, int jour, int combien, Random r) {
  final connues = lettresConnues(jour, sauf: cible);
  final soeurs = (familles[familleDe[cible]] ?? [])
      .where((c) => c != cible && connues.contains(c))
      .toList();

  final recentes = [...connues]..sort(
      (a, b) => (parCaractere[b]!['jour'] as int)
          .compareTo(parCaractere[a]!['jour'] as int));

  final choix = <String>[];
  for (final source in [melanger(soeurs, r), recentes]) {
    for (final c in source) {
      if (choix.length >= combien) break;
      if (!choix.contains(c)) choix.add(c);
    }
  }
  return choix;
}

/// 3 à 5 options : une taille constante se lit comme un gabarit, et
/// l'apprenant finit par répondre à la forme de la question.
int nbOptions(Random r) => 3 + r.nextInt(3);

String sonDe(String c) => parCaractere[c]!['son'] as String;

// ------------------------------------------------- position dans un mot

/// initiale / médiane / finale / isolée, d'après la liaison à gauche.
///
/// Toutes les lettres acceptent une liaison venant de la droite ; six
/// (ا د ذ ر ز و) ne se lient jamais à la suivante.
String position(List<String> caracteres, int i) {
  final avant = i > 0 && (parCaractere[caracteres[i - 1]]?['attache_suivante'] == true);
  final apres = i < caracteres.length - 1 &&
      (parCaractere[caracteres[i]]?['attache_suivante'] == true);
  if (!avant && !apres) return 'isolee';
  if (!avant && apres) return 'initial';
  if (avant && apres) return 'medial';
  return 'final';
}

/// Les mots disponibles à cette date contenant `cible` à cette position.
List<Map<String, dynamic>> motsAvec(String cible, String pos, int jour) {
  final trouves = <Map<String, dynamic>>[];
  for (final m in mots) {
    if ((m['jour'] as int) > jour) continue;
    final cs = (m['lettres'] as List).cast<String>();
    for (var i = 0; i < cs.length; i++) {
      if (cs[i] == cible && position(cs, i) == pos) {
        trouves.add({...m, 'index': i});
        break;
      }
    }
  }
  return trouves;
}

// ------------------------------------------------------------- fabrication

Map<String, dynamic> ex(
  String type,
  String skillId,
  int seuil, {
  Map<String, dynamic>? prompt,
  List<Map<String, dynamic>>? options,
  Map<String, dynamic>? extra,
}) =>
    {
      'type': type,
      'skill_id': skillId,
      if (prompt != null) 'prompt': prompt,
      if (options != null) 'options': options,
      if (extra != null) ...extra,
      'latency_threshold_ms': seuil,
    };

List<Map<String, dynamic>> opt(String bonne, List<String> mauvaises, Random r,
    {String champ = 'arabic'}) {
  final tout = [
    {champ: bonne, 'correct': true},
    ...mauvaises.map((m) => {champ: m, 'correct': false}),
  ];
  return melanger(tout, r);
}

// ------------------------------------------------ générateurs par compétence

List<Map<String, dynamic>> pourReconnaissance(Map<String, dynamic> c) {
  final id = c['id'] as String, cible = c['arabic'] as String;
  final jour = c['introduced_on_day'] as int, seuil = c['latency_threshold_ms'] as int;
  final r = alea(id);
  final sortie = <Map<String, dynamic>>[];

  // 1. « Laquelle est X ? » — contre ses sœurs de famille d'abord.
  final d1 = distracteurs(cible, jour, nbOptions(r) - 1, r);
  if (d1.isNotEmpty) {
    sortie.add(ex('pair_discrimination', id, seuil,
        prompt: {'text_fr': 'Laquelle est « ${sonDe(cible)} » ?'},
        options: opt(cible, d1, r)));
  }

  // 2. La même question, distracteurs renouvelés. Sans cela l'apprenant
  //    retient le quatuor plutôt que la lettre.
  final d2 = distracteurs(cible, jour, nbOptions(alea('$id.bis')) - 1, alea('$id.bis'));
  if (d2.isNotEmpty && d2.join() != d1.join()) {
    sortie.add(ex('pair_discrimination', id, seuil,
        prompt: {'text_fr': 'Retrouve « ${sonDe(cible)} ».'},
        options: opt(cible, d2, alea('$id.bis2'))));
  }

  // 3. L'intruse : plusieurs lettres d'une même famille, et la cible qui n'en
  //    est pas. Cherchée dans TOUTE famille enseignée, pas seulement celle de
  //    la cible — sinon les huit lettres à forme unique n'en ont jamais.
  final famillesUtiles = familles.entries
      .where((e) =>
          e.key != familleDe[cible] &&
          e.value.where((x) => (parCaractere[x]!['jour'] as int) <= jour).length >= 2)
      .toList();
  if (famillesUtiles.isNotEmpty) {
    final choisie = famillesUtiles[r.nextInt(famillesUtiles.length)];
    final membres = choisie.value
        .where((x) => (parCaractere[x]!['jour'] as int) <= jour)
        .take(3)
        .toList();
    sortie.add(ex('family_odd_one_out', id, seuil,
        prompt: {'text_fr': 'Trouve celle qui n\'est pas de la même famille.'},
        options: opt(cible, membres, r)));
  }

  // 4. Reconnaissance dans un mot, si un mot la contient.
  final supports = motsAvec(cible, 'isolee', jour) + motsAvec(cible, 'final', jour);
  if (supports.isNotEmpty && sortie.length < 4) {
    final m = supports[r.nextInt(supports.length)];
    sortie.add(ex('find_in_word', id, seuil,
        prompt: {'text_fr': 'Touche la lettre « ${sonDe(cible)} ».', 'arabic': m['mot']},
        extra: {'target_index': m['index']}));
  }

  return sortie;
}

List<Map<String, dynamic>> pourSon(Map<String, dynamic> c) {
  final id = c['id'] as String, cible = c['arabic'] as String;
  final jour = c['introduced_on_day'] as int, seuil = c['latency_threshold_ms'] as int;
  final r = alea(id);
  final ident = parCaractere[cible]!['id'] as String;

  final d = distracteurs(cible, jour, nbOptions(r) - 1, r);
  if (d.isEmpty) return [];

  return [
    // Voir la lettre, choisir le son.
    ex('letter_to_sound_mcq', id, seuil,
        prompt: {'arabic': cible},
        options: opt(sonDe(cible), d.map(sonDe).toList(), r, champ: 'text')),
    // Entendre le son, choisir la lettre.
    ex('sound_to_letter_mcq', id, seuil,
        prompt: {'audio': 'lettre_$ident.opus', 'text_fr': 'Quelle lettre entends-tu ?'},
        options: opt(cible, d, r)),
    // Même exercice, distracteurs renouvelés : sans cela l'apprenant retient
    // le quatuor plutôt que la lettre.
    ex('letter_to_sound_mcq', id, seuil,
        prompt: {'arabic': cible},
        options: opt(sonDe(cible),
            distracteurs(cible, jour, 3, alea('$id.bis')).map(sonDe).toList(), r,
            champ: 'text')),
  ];
}

List<Map<String, dynamic>> pourForme(Map<String, dynamic> c) {
  final id = c['id'] as String, cible = c['arabic'] as String;
  final jour = c['introduced_on_day'] as int, seuil = c['latency_threshold_ms'] as int;
  final pos = id.split('.').last;
  final supports = motsAvec(cible, pos, jour);

  if (supports.isEmpty) {
    manques.add(Manque(jour: jour, competence: id, lettre: cible, besoin: pos));
    return [];
  }
  if (supports.length < 3) {
    manques.add(Manque(
        jour: jour, competence: id, lettre: cible, besoin: pos,
        partiel: supports.length));
  }

  final r = alea(id);
  final libelle = {'initial': 'au début', 'medial': 'au milieu', 'final': 'à la fin'}[pos] ?? '';
  return melanger(supports, r).take(3).map((m) {
    return ex('find_in_word', id, seuil,
        prompt: {
          'text_fr': 'Touche la lettre « ${sonDe(cible)} » — elle est $libelle.',
          'arabic': m['mot'],
        },
        extra: {'target_index': m['index'], 'position': pos});
  }).toList();
}

List<Map<String, dynamic>> pourSyllabe(Map<String, dynamic> c) {
  final id = c['id'] as String;
  final jour = c['introduced_on_day'] as int, seuil = c['latency_threshold_ms'] as int;
  final parts = id.split('.'); // syllable.<lettre>.<haraka>
  final lettre = lettres.firstWhere((l) => l['id'] == parts[1]);
  final haraka = harakat.firstWhere((h) => h['id'] == parts[2]);
  final r = alea(id);

  final car = lettre['lettre'] as String;
  final son = '${lettre['son']}${haraka['son']}';

  // Le distracteur idéal : la MÊME lettre habillée des autres accents. C'est
  // exactement la confusion qu'on veut éteindre, et elle est invisible si on
  // met d'autres lettres en face.
  final autresAccents = harakat
      .where((h) => h['id'] != haraka['id'] && (h['jour'] as int) <= jour)
      .toList();

  final sortie = <Map<String, dynamic>>[
    ex('syllable_to_sound_mcq', id, seuil,
        prompt: {'arabic': '$car${haraka['signe']}'},
        options: opt(son, autresAccents.map((h) => '${lettre['son']}${h['son']}').toList(), r,
            champ: 'text')),
    ex('build_syllable', id, seuil,
        prompt: {'text_fr': 'Compose « $son ».', 'arabic': car},
        options: opt(haraka['signe'] as String,
            autresAccents.map((h) => h['signe'] as String).toList(), r)),
  ];

  // Troisième : contre d'autres lettres portant le même accent — l'autre
  // moitié de la confusion.
  final d = distracteurs(car, jour, 3, r);
  if (d.isNotEmpty) {
    sortie.add(ex('syllable_to_sound_mcq', id, seuil,
        prompt: {'audio': 'syllabe_${lettre['id']}_${haraka['id']}.opus'},
        options: opt('$car${haraka['signe']}',
            d.map((x) => '$x${haraka['signe']}').toList(), r)));
  }
  return sortie;
}

List<Map<String, dynamic>> pourContraste(Map<String, dynamic> c) {
  final id = c['id'] as String;
  final jour = c['introduced_on_day'] as int, seuil = c['latency_threshold_ms'] as int;
  final def = contrastes.firstWhere((x) => 'contrast.${x['id']}' == id, orElse: () => {});
  if (def.isEmpty) return [];

  final paire = (def['paire'] as List).cast<String>();
  final r = alea(id);
  final sortie = <Map<String, dynamic>>[];

  // Une question par membre de la paire : demander toujours la même
  // apprendrait « ce n'est pas l'autre » au lieu de la distinguer.
  for (final cible in paire) {
    sortie.add(ex('pair_discrimination', id, seuil,
        prompt: {'text_fr': 'Laquelle est « ${sonDe(cible)} » ?'},
        options: opt(cible, paire.where((x) => x != cible).toList(), r)));
  }

  // Contraste de son : c'est l'oreille qu'on entraîne, pas l'œil. On
  // interroge chaque membre, sinon on apprend « ce n'est pas l'autre ».
  if (def['nature'] == 'son') {
    for (final cible in paire) {
      sortie.add(ex('sound_to_letter_mcq', id, seuil,
          prompt: {
            'audio': 'lettre_${parCaractere[cible]!['id']}.opus',
            'text_fr': 'Écoute bien : douce ou emphatique ?',
          },
          options: opt(cible, paire.where((x) => x != cible).toList(), r)));
    }
  } else {
    // Contraste de forme : le repérer dans un mot vaut mieux qu'un troisième
    // QCM isolé — c'est en lisant qu'on confond.
    for (final cible in paire) {
      final supports = [
        ...motsAvec(cible, 'isolee', jour),
        ...motsAvec(cible, 'final', jour),
        ...motsAvec(cible, 'initial', jour),
      ];
      if (supports.isNotEmpty && sortie.length < 4) {
        final m = supports[r.nextInt(supports.length)];
        sortie.add(ex('find_in_word', id, seuil,
            prompt: {
              'text_fr': 'Touche « ${sonDe(cible)} », pas sa sœur.',
              'arabic': m['mot'],
            },
            extra: {'target_index': m['index']}));
      }
    }
  }
  return sortie.take(4).toList();
}

List<Map<String, dynamic>> pourMot(Map<String, dynamic> c) {
  final id = c['id'] as String;
  final jour = c['introduced_on_day'] as int, seuil = c['latency_threshold_ms'] as int;
  final translit = id.substring('word.'.length);
  final mot = mots.firstWhere((m) => m['translit'] == translit, orElse: () => {});
  if (mot.isEmpty) return [];

  final r = alea(id);
  final caracteres = (mot['lettres'] as List).cast<String>();

  // Sens d'autres mots déjà débloqués : un distracteur pris hors de l'acquis
  // se repère à ce qu'il détonne, sans qu'on ait lu.
  final autresSens = mots
      .where((m) => (m['jour'] as int) <= jour && m['translit'] != translit)
      .map((m) => m['sens'] as String)
      .toList();

  final sortie = <Map<String, dynamic>>[
    ex('word_assembly', id, seuil,
        prompt: {'text_fr': 'Remets les lettres dans l\'ordre.', 'arabic': mot['mot']},
        extra: {'lettres': melanger(caracteres, r), 'solution': caracteres}),
    ex('read_aloud', id, seuil,
        prompt: {'text_fr': 'Appuie et lis.', 'arabic': mot['mot']},
        extra: {'audio_reference': 'mot_$translit.opus'}),
  ];

  if (autresSens.length >= 2) {
    sortie.add(ex('word_to_meaning_mcq', id, seuil,
        prompt: {'arabic': mot['mot'], 'text_fr': 'Que veut dire ce mot ?'},
        options: opt(mot['sens'] as String, melanger(autresSens, r).take(3).toList(), r,
            champ: 'text')));
  } else {
    lacunes.add('| `$id` | ${mot['mot']} | sens | jour $jour '
        '| moins de 2 autres mots pour les distracteurs |');
  }
  return sortie;
}

List<Map<String, dynamic>> pourHaraka(Map<String, dynamic> c) {
  final id = c['id'] as String;
  final jour = c['introduced_on_day'] as int, seuil = c['latency_threshold_ms'] as int;
  final h = harakat.firstWhere((x) => 'haraka.${x['id']}' == id, orElse: () => {});
  if (h.isEmpty) return [];

  final r = alea(id);
  final autres = harakat.where((x) => x['id'] != h['id'] && (x['jour'] as int) <= jour).toList();
  final support = lettresConnues(jour);
  if (support.isEmpty) return [];

  final sortie = <Map<String, dynamic>>[
    ex('pair_discrimination', id, seuil,
        prompt: {'text_fr': 'Quel signe fait « ${h['son']} » ?'},
        options: opt(h['signe'] as String, autres.map((x) => x['signe'] as String).toList(), r)),
  ];

  for (final car in melanger(support, r).take(2)) {
    sortie.add(ex('build_syllable', id, seuil,
        prompt: {
          'text_fr': 'Pose le signe qui fait « ${h['son']} ». ${h['geste']}.',
          'arabic': car,
        },
        options: opt(h['signe'] as String, autres.map((x) => x['signe'] as String).toList(), r)));
  }
  return sortie;
}

List<Map<String, dynamic>> pourMarque(Map<String, dynamic> c) {
  final id = c['id'] as String;
  final jour = c['introduced_on_day'] as int;
  final porteurs = mots.where((m) =>
      (m['jour'] as int) <= jour &&
      (m['marques'] as List).contains(id.substring('mark.'.length)));

  if (porteurs.isEmpty) {
    lacunes.add('| `$id` | ${c['arabic'] ?? ''} | signe | jour $jour '
        '| aucun mot ne le porte |');
    return [];
  }

  final r = alea(id);
  final seuil = c['latency_threshold_ms'] as int;
  final signe = (c['arabic'] as String?) ?? '';
  final sortie = <Map<String, dynamic>>[];

  // Reconnaître le signe lui-même, contre les autres déjà enseignés. Ne
  // dépend d'aucun mot : c'est ce qui garantit trois exercices même quand le
  // corpus est mince.
  final autresSignes = [
    ...harakat.where((h) => (h['jour'] as int) <= jour).map((h) => h['signe'] as String),
    ...marques
        .where((m) => (m['jour'] as int) <= jour && m['signe'] != signe)
        .map((m) => m['signe'] as String),
  ].where((s) => s != signe && s.length == 1).toSet().toList();

  if (signe.isNotEmpty && autresSignes.length >= 2) {
    final def = marques.firstWhere((m) => 'mark.${m['id']}' == id, orElse: () => {});
    sortie.add(ex('pair_discrimination', id, seuil,
        prompt: {'text_fr': 'Quel signe est ${def['libelle'] ?? 'celui-ci'} ?'},
        options: opt(signe, melanger(autresSignes, r).take(3).toList(), r)));
  }

  sortie.addAll(melanger(porteurs.toList(), r).take(3).map((m) {
    return ex('read_aloud', id, seuil,
        prompt: {'text_fr': 'Appuie et lis.', 'arabic': m['mot']},
        extra: {'audio_reference': 'mot_${m['translit']}.opus'});
  }));
  return sortie;
}

List<Map<String, dynamic>> pourFluidite(Map<String, dynamic> c) {
  // La fluidité se mesure sur du contenu déjà acquis : les suites se
  // composent à l'exécution par le moteur, pas ici.
  lacunes.add('| `${c['id']}` | — | fluidité | — '
      '| suites composées à l\'exécution, hors génération |');
  return [];
}

// ------------------------------------------------------------------ entrée

void main() {
  final racine = Directory.current.path;
  Map<String, dynamic> lire(String f) =>
      jsonDecode(File('$racine/content/$f').readAsStringSync()) as Map<String, dynamic>;

  socle = lire('lettres.json');
  lettres = (socle['lettres'] as List).cast<Map<String, dynamic>>();
  harakat = (socle['harakat'] as List).cast<Map<String, dynamic>>();
  marques = (socle['marques'] as List).cast<Map<String, dynamic>>();
  contrastes = (socle['contrastes'] as List).cast<Map<String, dynamic>>();
  mots = (lire('mots.json')['mots'] as List).cast<Map<String, dynamic>>();
  competences = (lire('competences.json')['competences'] as List).cast<Map<String, dynamic>>();

  for (final l in lettres) {
    parCaractere[l['lettre'] as String] = l;
    familleDe[l['lettre'] as String] = l['famille'] as String?;
  }
  for (final f in (socle['familles'] as List).cast<Map<String, dynamic>>()) {
    familles[f['id'] as String] = (f['lettres'] as List).cast<String>();
  }

  final generateurs = {
    'letter.recognize': pourReconnaissance,
    'letter.sound': pourSon,
    'letter.form': pourForme,
    'syllable': pourSyllabe,
    'contrast': pourContraste,
    'word': pourMot,
    'haraka': pourHaraka,
    'mark': pourMarque,
    'fluency': pourFluidite,
  };

  final parJour = <int, List<Map<String, dynamic>>>{};
  final parType = <String, int>{};
  var sansExercice = 0, sousTrois = 0;

  for (final c in competences) {
    final gen = generateurs[c['type']];
    if (gen == null) continue;
    final produits = gen(c);

    if (produits.isEmpty) {
      sansExercice++;
    } else if (produits.length < 3) {
      sousTrois++;
    }
    for (final e in produits) {
      parType[e['type'] as String] = (parType[e['type'] as String] ?? 0) + 1;
    }
    final jour = (c['introduced_on_day'] as int?) ?? 0;
    if (jour > 0) parJour.putIfAbsent(jour, () => []).addAll(produits);
  }

  final dossier = Directory('$racine/content/exercices');
  if (dossier.existsSync()) dossier.deleteSync(recursive: true);
  dossier.createSync(recursive: true);

  var total = 0;
  for (final jour in parJour.keys.toList()..sort()) {
    final lot = parJour[jour]!;
    total += lot.length;
    final nom = jour.toString().padLeft(2, '0');
    File('${dossier.path}/jour-$nom.json').writeAsStringSync(
      const JsonEncoder.withIndent('  ').convert({
        '_': 'BROUILLONS générés. Aucun ne se publie sans relecture (§47).',
        'jour': jour,
        'total': lot.length,
        'exercices': lot,
      }),
    );
  }

  // --- rapport

  stdout.writeln('EXERCICES PAR TYPE');
  final types = parType.keys.toList()..sort();
  for (final t in types) {
    stdout.writeln('  ${t.padRight(24)} ${parType[t]}');
  }
  stdout.writeln('  ${'TOTAL'.padRight(24)} $total');
  stdout.writeln('');
  stdout.writeln('COUVERTURE');
  stdout.writeln('  compétences sans exercice   $sansExercice');
  stdout.writeln('  compétences sous 3 exercices $sousTrois');
  stdout.writeln('  lots écrits                  ${parJour.length}');

  // --- Le rapport de lacunes, groupé par jour.
  //
  // Une liste de manques ne sert à rien si elle n'indique pas AVEC QUOI
  // chercher. Chaque jour rappelle donc l'alphabet et les signes disponibles :
  // trouver un mot devient un problème fermé au lieu d'une recherche ouverte.

  final libelles = {'initial': 'en début de mot', 'medial': 'au milieu', 'final': 'en fin de mot'};
  final parJourManque = <int, List<Manque>>{};
  for (final m in manques) {
    parJourManque.putIfAbsent(m.jour, () => []).add(m);
  }

  final buffer = StringBuffer()
    ..writeln('# Ce qui manque au corpus')
    ..writeln()
    ..writeln('Généré par `tools/contenu/exercices.dart`. **Ne pas éditer** —')
    ..writeln('ajouter les mots à `content/mots.json`, puis regénérer.')
    ..writeln()
    ..writeln('${manques.where((m) => m.partiel == 0).length} cases vides et '
        '${manques.where((m) => m.partiel > 0).length} cases incomplètes, '
        'sur ${parJourManque.length} jours.')
    ..writeln()
    ..writeln('Chaque section donne **l\'alphabet et les signes disponibles ce '
        'jour-là**. Un mot n\'est recevable que s\'il n\'utilise rien d\'autre.')
    ..writeln();

  for (final jour in parJourManque.keys.toList()..sort()) {
    final dispo = lettresConnues(jour);
    final signesDispo = [
      ...harakat.where((h) => (h['jour'] as int) <= jour).map((h) => '${h['signe']} ${h['id']}'),
      ...marques.where((m) => (m['jour'] as int) <= jour).map((m) => m['id'] as String),
    ];
    buffer
      ..writeln('## Jour $jour')
      ..writeln()
      ..writeln('**Lettres disponibles (${dispo.length})** — ${dispo.join(' ')}')
      ..writeln()
      ..writeln('**Signes** — ${signesDispo.isEmpty ? 'aucun' : signesDispo.join(' · ')}')
      ..writeln()
      ..writeln('| Il faut un mot avec | À la position | Déjà trouvés | Manquants |')
      ..writeln('|---|---|---:|---:|');
    for (final m in parJourManque[jour]!..sort((a, b) => a.lettre.compareTo(b.lettre))) {
      buffer.writeln('| **${m.lettre}** (${sonDe(m.lettre)}) '
          '| ${libelles[m.besoin] ?? m.besoin} | ${m.partiel} | ${3 - m.partiel} |');
    }
    buffer.writeln();
  }

  if (lacunes.isNotEmpty) {
    buffer
      ..writeln('---')
      ..writeln()
      ..writeln('## Autres lacunes')
      ..writeln()
      ..writeln('| Compétence | Élément | Besoin | Jour | Pourquoi |')
      ..writeln('|---|---|---|---|---|')
      ..writeln((lacunes..sort()).join('\n'))
      ..writeln();
  }

  buffer
    ..writeln('---')
    ..writeln()
    ..writeln('## La règle, pour chaque mot ajouté')
    ..writeln()
    ..writeln('1. Un mot arabe **réel et courant** — pas une construction pour')
    ..writeln('   satisfaire la contrainte.')
    ..writeln('2. Contenant la lettre demandée à la position demandée.')
    ..writeln('3. Dont **toutes** les lettres figurent dans l\'alphabet du jour.')
    ..writeln('4. Dont **tous** les signes figurent dans les signes du jour.')
    ..writeln()
    ..writeln('`dart run tools/contenu/contenu.dart valider` refuse')
    ..writeln('mécaniquement un mot qui viole ces règles — mais il ne le trouve')
    ..writeln('pas. C\'est le seul poste du chantier qui demande une vraie')
    ..writeln('connaissance de la langue.');

  File('${dossier.path}/LACUNES.md').writeAsStringSync(buffer.toString());
  stdout.writeln('');
  stdout.writeln('${manques.length + lacunes.length} lacunes '
      '-> content/exercices/LACUNES.md');
}
