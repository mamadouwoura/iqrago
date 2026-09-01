// Banc de test du rendu des harakat — IqraGo, étape 1 (D10).
//
// Le problème : sur Android, les signes diacritiques arabes débordent souvent
// au-dessus ou en dessous de la boîte de mise en page calculée par Flutter.
// Dans un conteneur à hauteur contrainte, ils sont alors rognés — et une
// application qui enseigne fathah / kasra / damma en affichant des accents
// coupés est morte.
//
// Ce banc ne demande pas un jugement à l'œil. Il MESURE : pour chaque
// combinaison (police × configuration de hauteur × taille × cas de test), il
// peint le texte dans un canevas généreusement marge, relève la boîte
// englobante de l'encre réellement déposée, et la compare à la boîte de mise
// en page. Un débordement positif = un rognage garanti en conteneur contraint.

import 'dart:convert';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const ProbeApp());
}

// ---------------------------------------------------------------- cas de test

class ProbeCase {
  const ProbeCase(this.id, this.text, this.why);
  final String id;
  final String text;
  final String why;
}

/// Les douze cas qui cassent, classés du plus simple au plus haut.
/// Chacun correspond à une notion réellement enseignée dans le parcours.
const cases = <ProbeCase>[
  ProbeCase('fatha', 'بَ', 'Fathah — le signe le plus courant, jour 1'),
  ProbeCase('kasra', 'بِ', 'Kasra sous la lettre — jour 4'),
  ProbeCase('damma', 'بُ', 'Damma — jour 5'),
  ProbeCase('sukun', 'بْ', 'Sukun, cercle haut — jour 19'),
  ProbeCase('madd_alif', 'آ', 'Madd au-dessus de alif — jour 20'),
  ProbeCase('shadda_fatha', 'بَّ', 'Shadda + fathah empilées — jour 22'),
  ProbeCase('shadda_damma', 'بُّ', 'Shadda + damma : LE cas le plus haut'),
  ProbeCase('shadda_kasra', 'بِّ', 'Shadda dessus + kasra dessous'),
  ProbeCase('tanwin_damma', 'بٌ', 'Tanwin damma, double boucle — jour 23'),
  ProbeCase('kasra_descend', 'جِ', 'Kasra sous une lettre qui descend déjà'),
  ProbeCase('mot_article', 'الطَّالِبُ', 'Mot réel, shadda sur ط + damma finale'),
  ProbeCase('mixte', 'Lis بَ maintenant', 'Arabe et latin sur la même ligne'),
];

// ------------------------------------------------------ axes de configuration

const fonts = <String?>[null, 'Amiri', 'ScheherazadeNew', 'NotoNaskhArabic'];
const sizes = <double>[18, 32, 48];

class HeightConfig {
  const HeightConfig(this.id, this.height, this.behavior, this.note);
  final String id;
  final double? height;
  final TextHeightBehavior? behavior;
  final String note;
}

const heightConfigs = <HeightConfig>[
  HeightConfig('defaut', null, null, 'Aucune hauteur imposée — le défaut Flutter'),
  HeightConfig('h1.0', 1.0, null, 'height: 1.0 — le choix naïf, celui qui rogne'),
  HeightConfig('h1.5', 1.5, null, 'height: 1.5'),
  HeightConfig('h1.8', 1.8, null, 'height: 1.8 — généreux'),
  HeightConfig(
    'h1.8+asc',
    1.8,
    TextHeightBehavior(applyHeightToFirstAscent: false),
    'height: 1.8 sans application à la première ascendante',
  ),
];

// -------------------------------------------------------------------- mesure

class InkReport {
  const InkReport({
    required this.layoutWidth,
    required this.layoutHeight,
    required this.overflowTop,
    required this.overflowBottom,
    required this.inkFound,
  });

  final double layoutWidth;
  final double layoutHeight;

  /// Hauteur d'encre au-dessus de la boîte de mise en page. > 0 = rognage.
  final double overflowTop;

  /// Idem en dessous.
  final double overflowBottom;

  final bool inkFound;

  /// 0,5 px de tolérance pour l'anticrénelage.
  ///
  /// `!inkFound` compte comme un échec : une police qui ne dessine rien ne
  /// déborde pas, et serait sinon notée 0,00 px — le meilleur score possible.
  /// C'est exactement ce qui est arrivé à la ligne « système » au premier
  /// passage, où Flutter Web n'a aucune police arabe à substituer.
  bool get clipped => !inkFound || overflowTop > 0.5 || overflowBottom > 0.5;

  /// Valeur sentinelle pour « rien de dessiné » : un débordement nul ne doit
  /// pas se classer devant une police qui rend correctement le texte.
  double get worst {
    if (!inkFound) return 9999;
    return overflowTop > overflowBottom ? overflowTop : overflowBottom;
  }

  Map<String, dynamic> toJson() => {
        'layout_w': layoutWidth.toStringAsFixed(1),
        'layout_h': layoutHeight.toStringAsFixed(1),
        'overflow_top': overflowTop.toStringAsFixed(2),
        'overflow_bottom': overflowBottom.toStringAsFixed(2),
        'clipped': clipped,
      };
}

/// Peint [text] dans un canevas bordé de [pad] pixels vides, puis relève la
/// première et la dernière ligne de pixels contenant de l'encre.
///
/// La marge est indispensable : peindre dans une image de la taille exacte de
/// la boîte de mise en page reviendrait à rogner l'encre avant de pouvoir la
/// mesurer — c'est-à-dire à ne rien mesurer du tout.
Future<InkReport> measure({
  required String text,
  required String? fontFamily,
  required double fontSize,
  required HeightConfig config,
}) async {
  const pad = 120.0;

  final painter = TextPainter(
    text: TextSpan(
      text: text,
      style: TextStyle(
        fontFamily: fontFamily,
        fontSize: fontSize,
        height: config.height,
        color: const Color(0xFF000000),
      ),
    ),
    textDirection: TextDirection.rtl,
    textHeightBehavior: config.behavior,
  )..layout();

  final w = (painter.width + pad * 2).ceil();
  final h = (painter.height + pad * 2).ceil();
  if (w <= 0 || h <= 0 || w > 8192 || h > 8192) {
    return const InkReport(
      layoutWidth: 0,
      layoutHeight: 0,
      overflowTop: 0,
      overflowBottom: 0,
      inkFound: false,
    );
  }

  final recorder = ui.PictureRecorder();
  final canvas = Canvas(recorder);
  painter.paint(canvas, const Offset(pad, pad));
  final image = await recorder.endRecording().toImage(w, h);
  final data = await image.toByteData(format: ui.ImageByteFormat.rawRgba);
  image.dispose();
  if (data == null) {
    return const InkReport(
      layoutWidth: 0,
      layoutHeight: 0,
      overflowTop: 0,
      overflowBottom: 0,
      inkFound: false,
    );
  }

  final bytes = data.buffer.asUint8List();
  int? inkTop;
  int? inkBottom;
  for (var y = 0; y < h; y++) {
    final rowStart = y * w * 4;
    var hasInk = false;
    for (var x = 0; x < w; x++) {
      if (bytes[rowStart + x * 4 + 3] > 8) {
        hasInk = true;
        break;
      }
    }
    if (hasInk) {
      inkTop ??= y;
      inkBottom = y;
    }
  }

  if (inkTop == null || inkBottom == null) {
    return InkReport(
      layoutWidth: painter.width,
      layoutHeight: painter.height,
      overflowTop: 0,
      overflowBottom: 0,
      inkFound: false,
    );
  }

  // La boîte de mise en page occupe [pad, pad + painter.height] dans l'image.
  final overflowTop = pad - inkTop;
  final overflowBottom = (inkBottom + 1) - (pad + painter.height);

  return InkReport(
    layoutWidth: painter.width,
    layoutHeight: painter.height,
    overflowTop: overflowTop > 0 ? overflowTop : 0,
    overflowBottom: overflowBottom > 0 ? overflowBottom : 0,
    inkFound: true,
  );
}

// --------------------------------------------------------------------- résultat

class Row {
  Row(this.font, this.config, this.size, this.probe, this.report);
  final String font;
  final HeightConfig config;
  final double size;
  final ProbeCase probe;
  final InkReport report;
}

// -------------------------------------------------------------------- interface

class ProbeApp extends StatelessWidget {
  const ProbeApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'IqraGo — rendu arabe',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(useMaterial3: true, colorSchemeSeed: Colors.teal),
        home: const ProbePage(),
      );
}

class ProbePage extends StatefulWidget {
  const ProbePage({super.key});
  @override
  State<ProbePage> createState() => _ProbePageState();
}

class _ProbePageState extends State<ProbePage> {
  final rows = <Row>[];
  bool running = false;
  String status = 'Prêt.';

  @override
  void initState() {
    super.initState();
    // Lancement automatique : le rapport est écrit dans la console, ce qui
    // permet de relever les chiffres sans dépendre d'un clic ni d'un écran.
    WidgetsBinding.instance.addPostFrameCallback((_) => runAll());
  }

  /// Écrit le rapport complet sur la sortie console.
  void dumpToConsole() {
    final s = worstByFontConfig.entries.toList()..sort((a, b) => a.value.compareTo(b.value));
    // ignore: avoid_print
    print('===IQRAGO_DEBUT===');
    // ignore: avoid_print
    print('mesures=${rows.length} rognages=${rows.where((r) => r.report.clipped).length}');
    // ignore: avoid_print
    print('--- PIRE DEBORDEMENT PAR POLICE ET CONFIG (px) ---');
    for (final e in s) {
      // ignore: avoid_print
      print('${e.key} = ${e.value.toStringAsFixed(2)}');
    }
    // ignore: avoid_print
    print('--- PIRE CAS PAR POLICE+CONFIG SANS ROGNAGE, DETAIL DES FAUTIFS ---');
    final byCase = <String, double>{};
    for (final r in rows.where((r) => r.report.clipped)) {
      final k = '${r.font}|${r.config.id}|${r.probe.id}';
      if (r.report.worst > (byCase[k] ?? -1)) byCase[k] = r.report.worst;
    }
    final worstCases = byCase.entries.toList()..sort((a, b) => b.value.compareTo(a.value));
    for (final e in worstCases.take(40)) {
      // ignore: avoid_print
      print('${e.key} = ${e.value.toStringAsFixed(2)}');
    }
    // ignore: avoid_print
    print('===IQRAGO_FIN===');
  }

  Future<void> runAll() async {
    setState(() {
      running = true;
      rows.clear();
      status = 'Mesure en cours…';
    });

    for (final font in fonts) {
      for (final config in heightConfigs) {
        for (final size in sizes) {
          for (final probe in cases) {
            final report = await measure(
              text: probe.text,
              fontFamily: font,
              fontSize: size,
              config: config,
            );
            rows.add(Row(font ?? 'système', config, size, probe, report));
          }
        }
      }
      if (mounted) setState(() => status = 'Police ${font ?? "système"} terminée…');
    }

    if (mounted) {
      setState(() {
        running = false;
        status = '${rows.length} mesures. ${rows.where((r) => r.report.clipped).length} rognages.';
      });
    }
    dumpToConsole();
  }

  /// Pire débordement par (police, configuration) — c'est la seule ligne qui
  /// décide : une police n'est utilisable que si AUCUN cas ne déborde.
  Map<String, double> get worstByFontConfig {
    final out = <String, double>{};
    for (final r in rows) {
      final key = '${r.font} · ${r.config.id}';
      final v = r.report.worst;
      if (v > (out[key] ?? -1)) out[key] = v;
    }
    return out;
  }

  void copyJson() {
    final payload = {
      'generated_at': DateTime.now().toIso8601String(),
      'device': MediaQuery.of(context).size.toString(),
      'dpr': MediaQuery.of(context).devicePixelRatio,
      'summary': worstByFontConfig.map((k, v) => MapEntry(k, v.toStringAsFixed(2))),
      'clipped': rows
          .where((r) => r.report.clipped)
          .map((r) => {
                'font': r.font,
                'config': r.config.id,
                'size': r.size,
                'case': r.probe.id,
                ...r.report.toJson(),
              })
          .toList(),
    };
    Clipboard.setData(ClipboardData(text: const JsonEncoder.withIndent('  ').convert(payload)));
    ScaffoldMessenger.of(context)
        .showSnackBar(const SnackBar(content: Text('Rapport JSON copié.')));
  }

  @override
  Widget build(BuildContext context) {
    final summary = worstByFontConfig;
    final failures = rows.where((r) => r.report.clipped).toList();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Rendu des harakat'),
        actions: [
          if (rows.isNotEmpty)
            IconButton(onPressed: copyJson, icon: const Icon(Icons.copy), tooltip: 'Copier le JSON'),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(status, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          FilledButton.icon(
            onPressed: running ? null : runAll,
            icon: running
                ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                : const Icon(Icons.play_arrow),
            label: const Text('Lancer les mesures'),
          ),
          const SizedBox(height: 24),

          // --- Aperçu visuel : ce que l'œil doit confirmer après la mesure.
          Text('Aperçu', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          for (final font in fonts)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(font ?? 'police système', style: const TextStyle(fontWeight: FontWeight.bold)),
                    const SizedBox(height: 6),
                    // Conteneur volontairement contraint : c'est là que le
                    // rognage se voit, comme dans une vraie carte d'exercice.
                    Container(
                      height: 64,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(border: Border.all(color: Colors.red.shade200)),
                      child: Text(
                        'بُّ  الطَّالِبُ  بٌ  جِ',
                        textDirection: TextDirection.rtl,
                        style: TextStyle(fontFamily: font, fontSize: 40, height: 1.0),
                      ),
                    ),
                    const SizedBox(height: 4),
                    const Text('height: 1.0, conteneur 64 px — le cas qui rogne',
                        style: TextStyle(fontSize: 11, color: Colors.black54)),
                  ],
                ),
              ),
            ),

          if (summary.isNotEmpty) ...[
            const SizedBox(height: 24),
            Text('Pire débordement par police et configuration',
                style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 4),
            const Text('0,00 px = aucun rognage possible. Toute valeur > 0 disqualifie la configuration.',
                style: TextStyle(fontSize: 12, color: Colors.black54)),
            const SizedBox(height: 8),
            ...(summary.entries.toList()..sort((a, b) => a.value.compareTo(b.value))).map(
              (e) => ListTile(
                dense: true,
                leading: Icon(e.value <= 0.5 ? Icons.check_circle : Icons.error,
                    color: e.value <= 0.5 ? Colors.green : Colors.red),
                title: Text(e.key),
                trailing: Text('${e.value.toStringAsFixed(2)} px'),
              ),
            ),
          ],

          if (failures.isNotEmpty) ...[
            const SizedBox(height: 24),
            Text('Rognages (${failures.length})', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            ...failures.take(60).map(
                  (r) => ListTile(
                    dense: true,
                    title: Text('${r.probe.text}   ${r.probe.id}',
                        style: const TextStyle(fontSize: 14)),
                    subtitle: Text('${r.font} · ${r.config.id} · ${r.size.toInt()} px'),
                    trailing: Text(
                      '↑${r.report.overflowTop.toStringAsFixed(1)}  ↓${r.report.overflowBottom.toStringAsFixed(1)}',
                      style: const TextStyle(fontSize: 12),
                    ),
                  ),
                ),
            if (failures.length > 60)
              const Padding(
                padding: EdgeInsets.all(8),
                child: Text('… et davantage. Utiliser le rapport JSON.',
                    style: TextStyle(fontSize: 12, color: Colors.black54)),
              ),
          ],
        ],
      ),
    );
  }
}
