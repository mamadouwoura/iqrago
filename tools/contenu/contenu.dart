// Outil de contenu IqraGo.
//
//   dart run tools/contenu/contenu.dart valider
//   dart run tools/contenu/contenu.dart generer
//
// `valider` rend mécanique la règle qui, sinon, ne tient qu'à la vigilance
// d'un relecteur : un mot n'apparaît que si TOUTES ses lettres et TOUTES ses
// marques sont déjà acquises ce jour-là. Il vérifie en outre que la chaîne
// arabe réellement écrite correspond aux lettres et aux marques déclarées —
// c'est ce contrôle-là qui attrape les fautes de frappe invisibles à l'œil,
// une kasra glissée à la place d'une fatha, une lettre oubliée.
//
// `generer` produit competences.json : le graphe des compétences, dérivé du
// socle. Il n'est jamais écrit à la main.

import 'dart:convert';
import 'dart:io';

// ------------------------------------------------------------------ unicode

/// Signes diacritiques, par point de code.
const diacritiques = <int, String>{
  0x064E: 'fatha',
  0x0650: 'kasra',
  0x064F: 'damma',
  0x0652: 'sukun',
  0x0651: 'shadda',
  0x064B: 'tanwin.an',
  0x064D: 'tanwin.in',
  0x064C: 'tanwin.un',
};

/// Marques structurelles : elles ne correspondent à aucun point de code isolé
/// et ne sont donc vérifiées que par déclaration.
const marquesStructurelles = {'madd.alif', 'madd.waw', 'madd.ya', 'article'};

bool estLettreArabe(int c) => c >= 0x0621 && c <= 0x064A && !diacritiques.containsKey(c);

/// Position d'une lettre dans un mot, d'après la liaison à gauche.
///
/// Toutes les lettres acceptent une liaison venant de la droite ; six
/// (ا د ذ ر ز و) ne se lient jamais à la suivante.
String positionDans(List<String> cs, int i, Map<String, bool> attache) {
  final avant = i > 0 && (attache[cs[i - 1]] ?? false);
  final apres = i < cs.length - 1 && (attache[cs[i]] ?? false);
  if (!avant && !apres) return 'isolee';
  if (!avant) return 'initial';
  return apres ? 'medial' : 'final';
}

/// Le premier jour où un mot du corpus montre cette lettre à cette position,
/// ou `null` si aucun ne le fait.
int? premierJourAvec(String car, String pos, List<Map<String, dynamic>> mots) {
  int? plusTot;
  for (final m in mots) {
    final cs = (m['lettres'] as List).cast<String>();
    for (var i = 0; i < cs.length; i++) {
      if (cs[i] == car && positionDans(cs, i, _attache) == pos) {
        final j = m['jour'] as int;
        if (plusTot == null || j < plusTot) plusTot = j;
      }
    }
  }
  return plusTot;
}

/// caractère -> se lie-t-il à la lettre suivante ?
final _attache = <String, bool>{};

/// Sépare une chaîne vocalisée en (lettres, signes rencontrés).
({List<String> lettres, Set<String> signes}) decomposer(String mot) {
  final lettres = <String>[];
  final signes = <String>{};
  for (final c in mot.runes) {
    if (diacritiques.containsKey(c)) {
      signes.add(diacritiques[c]!);
    } else if (estLettreArabe(c)) {
      lettres.add(String.fromCharCode(c));
    }
  }
  return (lettres: lettres, signes: signes);
}

// ------------------------------------------------------------------ chargement

Map<String, dynamic> lire(String chemin) {
  final f = File(chemin);
  if (!f.existsSync()) {
    stderr.writeln('Fichier introuvable : $chemin');
    exit(1);
  }
  return jsonDecode(f.readAsStringSync()) as Map<String, dynamic>;
}

// ------------------------------------------------------------------ validation

int valider(Map<String, dynamic> l, Map<String, dynamic> m) {
  final erreurs = <String>[];
  final avertissements = <String>[];

  final lettres = (l['lettres'] as List).cast<Map<String, dynamic>>();
  final harakat = (l['harakat'] as List).cast<Map<String, dynamic>>();
  final marques = (l['marques'] as List).cast<Map<String, dynamic>>();
  final familles = (l['familles'] as List).cast<Map<String, dynamic>>();
  final contrastes = (l['contrastes'] as List).cast<Map<String, dynamic>>();
  final mots = (m['mots'] as List).cast<Map<String, dynamic>>();

  // --- 1. Le socle est-il complet et cohérent ?

  if (lettres.length != 28) {
    erreurs.add('L\'alphabet compte ${lettres.length} lettres au lieu de 28.');
  }

  final jourDeLettre = <String, int>{};
  final idDeLettre = <String, String>{};
  for (final x in lettres) {
    final car = x['lettre'] as String;
    if (jourDeLettre.containsKey(car)) erreurs.add('Lettre $car déclarée deux fois.');
    jourDeLettre[car] = x['jour'] as int;
    idDeLettre[car] = x['id'] as String;
  }

  final jourDeMarque = <String, int>{};
  for (final h in harakat) {
    jourDeMarque[h['id'] as String] = h['jour'] as int;
  }
  for (final s in marques) {
    jourDeMarque[s['id'] as String] = s['jour'] as int;
  }

  // Les familles ne doivent citer que des lettres existantes.
  for (final f in familles) {
    for (final car in (f['lettres'] as List).cast<String>()) {
      if (!jourDeLettre.containsKey(car)) {
        erreurs.add('Famille ${f['id']} cite $car, qui n\'est pas dans l\'alphabet.');
      }
    }
  }

  // Un contraste ne peut être enseigné avant ses deux lettres.
  for (final c in contrastes) {
    final paire = (c['paire'] as List).cast<String>();
    final jour = c['jour'] as int;
    for (final car in paire) {
      final jl = jourDeLettre[car];
      if (jl == null) {
        erreurs.add('Contraste ${c['id']} cite $car, inconnue.');
      } else if (jl > jour) {
        erreurs.add('Contraste ${c['id']} au jour $jour, mais $car arrive au jour $jl.');
      }
    }
  }

  // --- 2. Zéro surprise, et fidélité de la chaîne écrite

  final vus = <String>{};
  for (final mot in mots) {
    final texte = mot['mot'] as String;
    final jour = mot['jour'] as int;
    final declLettres = (mot['lettres'] as List).cast<String>();
    final declMarques = (mot['marques'] as List).cast<String>();

    if (!vus.add(texte)) avertissements.add('« $texte » apparaît deux fois.');

    // 2a. Toutes les lettres sont-elles acquises ce jour-là ?
    for (final car in declLettres) {
      final jl = jourDeLettre[car];
      if (jl == null) {
        erreurs.add('« $texte » (jour $jour) utilise $car, absente de l\'alphabet.');
      } else if (jl > jour) {
        erreurs.add('« $texte » au jour $jour utilise $car, enseignée au jour $jl. '
            'ZÉRO SURPRISE VIOLÉ.');
      }
    }

    // 2b. Toutes les marques le sont-elles ?
    for (final mk in declMarques) {
      final jm = jourDeMarque[mk];
      if (jm == null) {
        erreurs.add('« $texte » déclare la marque inconnue « $mk ».');
      } else if (jm > jour) {
        erreurs.add('« $texte » au jour $jour utilise $mk, enseignée au jour $jm. '
            'ZÉRO SURPRISE VIOLÉ.');
      }
    }

    // 2c. La chaîne écrite correspond-elle à ce qui est déclaré ?
    //     C'est le contrôle qui attrape les fautes de frappe.
    final d = decomposer(texte);

    // L'article ال ajoute deux caractères qui ne sont pas des "lettres du mot"
    // au sens pédagogique : on les tolère en tête quand `article` est déclaré.
    var lettresLues = d.lettres;
    if (declMarques.contains('article') &&
        lettresLues.length >= 2 &&
        lettresLues[0] == 'ا' &&
        lettresLues[1] == 'ل' &&
        declLettres.length >= 2 &&
        declLettres[0] == 'ا') {
      // déclaré avec l'article inclus : rien à retirer
    }

    if (lettresLues.join() != declLettres.join()) {
      erreurs.add('« $texte » : la chaîne contient [${lettresLues.join(' ')}] '
          'mais déclare [${declLettres.join(' ')}].');
    }

    final signesDeclaresVerifiables =
        declMarques.where((x) => !marquesStructurelles.contains(x)).toSet();
    final manquants = signesDeclaresVerifiables.difference(d.signes);
    final enTrop = d.signes.difference(signesDeclaresVerifiables);
    if (manquants.isNotEmpty) {
      erreurs.add('« $texte » déclare ${manquants.join(', ')} mais ne les écrit pas.');
    }
    if (enTrop.isNotEmpty) {
      erreurs.add('« $texte » écrit ${enTrop.join(', ')} sans les déclarer.');
    }
  }

  // --- 3. Rapport

  stdout.writeln('Lettres    : ${lettres.length}');
  stdout.writeln('Harakat    : ${harakat.length}');
  stdout.writeln('Marques    : ${marques.length}');
  stdout.writeln('Contrastes : ${contrastes.length}');
  stdout.writeln('Mots       : ${mots.length}');
  stdout.writeln('');

  for (final a in avertissements) {
    stdout.writeln('AVERTISSEMENT  $a');
  }
  for (final e in erreurs) {
    stdout.writeln('ERREUR  $e');
  }

  if (erreurs.isEmpty) {
    stdout.writeln(avertissements.isEmpty
        ? 'Contenu valide.'
        : 'Contenu valide, ${avertissements.length} avertissement(s).');
    return 0;
  }
  stdout.writeln('');
  stdout.writeln('${erreurs.length} erreur(s). Contenu refusé.');
  return 1;
}

// ------------------------------------------------------------------ génération

int generer(Map<String, dynamic> l, Map<String, dynamic> m) {
  final lettres = (l['lettres'] as List).cast<Map<String, dynamic>>();
  final harakat = (l['harakat'] as List).cast<Map<String, dynamic>>();
  final marques = (l['marques'] as List).cast<Map<String, dynamic>>();
  final contrastes = (l['contrastes'] as List).cast<Map<String, dynamic>>();
  final mots = (m['mots'] as List).cast<Map<String, dynamic>>();

  final idDeLettre = {for (final x in lettres) x['lettre'] as String: x['id'] as String};
  _attache
    ..clear()
    ..addEntries(lettres.map((x) =>
        MapEntry(x['lettre'] as String, x['attache_suivante'] == true)));
  final competences = <Map<String, dynamic>>[];

  void ajouter(String id, String type, int jour, List<String> prereq,
      {String? arabe, int seuil = 1500}) {
    competences.add({
      'id': id,
      'type': type,
      'arabic': arabe,
      'introduced_on_day': jour,
      'latency_threshold_ms': seuil,
      'prerequisites': prereq,
    });
  }

  // Lettres : reconnaître, puis sonoriser, puis les formes positionnelles.
  for (final x in lettres) {
    final id = x['id'] as String;
    final car = x['lettre'] as String;
    final jour = x['jour'] as int;
    ajouter('letter.$id.recognize', 'letter.recognize', jour, [], arabe: car);
    ajouter('letter.$id.sound', 'letter.sound', jour, ['letter.$id.recognize'], arabe: car);
    if (x['attache_suivante'] == true) {
      for (final pos in ['initial', 'medial', 'final']) {
        // Une forme positionnelle ne s'enseigne pas avant qu'un mot puisse la
        // montrer : « touche le ت au milieu » n'a pas de sens s'il n'existe
        // aucun mot lisible qui le contienne. Le jour est donc calculé, non
        // recopié de la lettre — et il avance tout seul quand le corpus
        // s'enrichit.
        final support = premierJourAvec(car, pos, mots);
        final jourForme = support == null || support < jour ? jour : support;
        ajouter('letter.$id.form.$pos', 'letter.form', jourForme,
            ['letter.$id.recognize'], arabe: car);
      }
    }
  }

  for (final h in harakat) {
    ajouter('haraka.${h['id']}', 'haraka', h['jour'] as int, [], arabe: h['signe'] as String);
  }
  for (final s in marques) {
    ajouter('mark.${s['id']}', 'mark', s['jour'] as int, [], arabe: s['signe'] as String);
  }

  // Syllabes : une lettre habillée d'un accent. Jour = le plus tardif des deux.
  for (final x in lettres) {
    for (final h in harakat) {
      final jour = (x['jour'] as int) > (h['jour'] as int) ? x['jour'] as int : h['jour'] as int;
      ajouter(
        'syllable.${x['id']}.${h['id']}',
        'syllable',
        jour,
        ['letter.${x['id']}.sound', 'haraka.${h['id']}'],
        arabe: '${x['lettre']}${h['signe']}',
        seuil: 2000,
      );
    }
  }

  for (final c in contrastes) {
    final paire = (c['paire'] as List).cast<String>();
    ajouter(
      'contrast.${c['id']}',
      'contrast',
      c['jour'] as int,
      [for (final car in paire) 'letter.${idDeLettre[car]}.recognize'],
    );
  }

  // Mots : prérequis = TOUS les atomes. C'est la règle « zéro surprise »
  // traduite en arêtes du graphe, donc appliquée par le moteur et non par
  // la vigilance de qui saisit le contenu.
  for (final mot in mots) {
    final texte = mot['mot'] as String;
    final declLettres = (mot['lettres'] as List).cast<String>();
    final declMarques = (mot['marques'] as List).cast<String>();
    final prereq = <String>{
      for (final car in declLettres) 'letter.${idDeLettre[car]}.sound',
      for (final mk in declMarques)
        mk == 'fatha' || mk == 'kasra' || mk == 'damma' ? 'haraka.$mk' : 'mark.$mk',
    }.toList()
      ..sort();
    ajouter('word.${mot['translit']}', 'word', mot['jour'] as int, prereq,
        arabe: texte, seuil: 3500);
  }

  for (var n = 1; n <= 7; n++) {
    ajouter('fluency.level.$n', 'fluency', 0, [], seuil: 0);
  }

  // Contrôle : aucun prérequis pendant, aucun cycle, aucun prérequis plus tardif.
  final index = {for (final c in competences) c['id'] as String: c};
  final erreurs = <String>[];
  for (final c in competences) {
    for (final p in (c['prerequisites'] as List).cast<String>()) {
      final cible = index[p];
      if (cible == null) {
        erreurs.add('${c['id']} exige $p, qui n\'existe pas.');
      } else if ((cible['introduced_on_day'] as int) > (c['introduced_on_day'] as int)) {
        erreurs.add('${c['id']} (jour ${c['introduced_on_day']}) exige $p '
            '(jour ${cible['introduced_on_day']}).');
      }
    }
  }

  final parType = <String, int>{};
  for (final c in competences) {
    parType[c['type'] as String] = (parType[c['type'] as String] ?? 0) + 1;
  }
  final types = parType.keys.toList()..sort();
  for (final t in types) {
    stdout.writeln('${t.padRight(18)} ${parType[t]}');
  }
  stdout.writeln('${'TOTAL'.padRight(18)} ${competences.length}');
  stdout.writeln('');

  if (erreurs.isNotEmpty) {
    for (final e in erreurs) {
      stdout.writeln('ERREUR  $e');
    }
    stdout.writeln('${erreurs.length} erreur(s) dans le graphe. Rien écrit.');
    return 1;
  }

  competences.sort((a, b) {
    final d = (a['introduced_on_day'] as int).compareTo(b['introduced_on_day'] as int);
    return d != 0 ? d : (a['id'] as String).compareTo(b['id'] as String);
  });

  File('content/competences.json').writeAsStringSync(
    const JsonEncoder.withIndent('  ').convert({
      '_': 'GÉNÉRÉ par tools/contenu/contenu.dart generer — ne pas éditer à la main.',
      'version': l['version'],
      'total': competences.length,
      'competences': competences,
    }),
  );
  stdout.writeln('content/competences.json écrit.');

  // --- Manifeste audio : la feuille de route de la journée de studio.
  final audios = <Map<String, dynamic>>[];
  for (final x in lettres) {
    audios.add({
      'fichier': 'lettre_${x['id']}.opus',
      'arabe': x['lettre'],
      'a_dire': 'le son « ${x['son']} », pas le nom de la lettre',
      'categorie': 'lettre',
    });
    for (final h in harakat) {
      audios.add({
        'fichier': 'syllabe_${x['id']}_${h['id']}.opus',
        'arabe': '${x['lettre']}${h['signe']}',
        'a_dire': '${x['son']}${h['son']}',
        'categorie': 'syllabe',
      });
    }
  }
  for (final mot in mots) {
    audios.add({
      'fichier': 'mot_${mot['translit']}.opus',
      'arabe': mot['mot'],
      'a_dire': mot['translit'],
      'sens': mot['sens'],
      'categorie': 'mot',
    });
  }

  File('content/audio-manifeste.json').writeAsStringSync(
    const JsonEncoder.withIndent('  ').convert({
      '_': 'GÉNÉRÉ. Feuille de route de la journée de studio. Voix humaine native, '
          'débit lent et articulé. Jamais de synthèse vocale : l\'apprenant imite '
          'ce qu\'il entend, une référence approximative enseigne une erreur.',
      'format': 'Opus 24 kbps mono, ~4 Ko/s',
      'total': audios.length,
      'audios': audios,
    }),
  );
  stdout.writeln('content/audio-manifeste.json écrit — ${audios.length} enregistrements.');
  return 0;
}

// ------------------------------------------------------------------ entrée

void main(List<String> args) {
  if (args.isEmpty || !['valider', 'generer'].contains(args.first)) {
    stdout.writeln('usage: dart run tools/contenu/contenu.dart [valider|generer]');
    exit(2);
  }
  final l = lire('content/lettres.json');
  final m = lire('content/mots.json');
  exit(args.first == 'valider' ? valider(l, m) : generer(l, m));
}
