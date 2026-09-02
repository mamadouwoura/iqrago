/// Modèles de données de l'application.
library;

/// Les objets que l'API renvoie, tels qu'ils sont consommés par les écrans.
///
/// Aucune règle pédagogique ici : la séance arrive **déjà composée**. Le
/// client ne décide ni de l'ordre, ni des révisions, ni des prérequis — c'est
/// ce qui permet d'ajuster le moteur sans republier l'application.

class Option {
  Option(this.texte, this.correcte, {this.estArabe = true});

  factory Option.depuisJson(Map<String, dynamic> j) {
    final arabe = j['arabic'] as String?;
    return Option(
      arabe ?? (j['text'] as String? ?? ''),
      j['correct'] == true,
      estArabe: arabe != null,
    );
  }

  final String texte;
  final bool correcte;
  final bool estArabe;
}

class Item {
  Item({
    required this.skillId,
    required this.arabe,
    required this.seuilMs,
    this.exerciceId,
    this.typeExercice,
    this.enonceFr,
    this.enonceArabe,
    this.options = const [],
  });

  factory Item.depuisJson(Map<String, dynamic> j) {
    final ex = j['exercise'] as Map<String, dynamic>?;
    final payload = (ex?['payload'] as Map<String, dynamic>?) ?? const {};
    final prompt = (payload['prompt'] as Map<String, dynamic>?) ?? const {};
    return Item(
      skillId: j['skill_id'] as String,
      arabe: (j['arabic'] as String?) ?? '',
      seuilMs: (j['latency_threshold_ms'] as int?) ?? 1500,
      exerciceId: ex?['id'] as String?,
      typeExercice: ex?['type'] as String?,
      enonceFr: prompt['text_fr'] as String?,
      enonceArabe: prompt['arabic'] as String?,
      options: ((payload['options'] as List?) ?? const [])
          .map((o) => Option.depuisJson(o as Map<String, dynamic>))
          .toList(),
    );
  }

  final String skillId;
  final String arabe;
  final int seuilMs;
  final String? exerciceId, typeExercice, enonceFr, enonceArabe;
  final List<Option> options;

  /// Un item sans exercice publié n'est pas jouable : le contenu existe en
  /// brouillon mais n'a pas encore été relu.
  bool get jouable => options.length >= 2;
}

class Seance {
  Seance({required this.jour, required this.titre, required this.items});

  factory Seance.depuisJson(Map<String, dynamic> j) {
    final items = <Item>[];
    for (final bloc in (j['blocks'] as List)) {
      for (final i in (bloc['items'] as List)) {
        items.add(Item.depuisJson(i as Map<String, dynamic>));
      }
    }
    return Seance(
      jour: j['day_number'] as int,
      titre: (j['lesson_title'] as String?) ?? '',
      items: items,
    );
  }

  final int jour;
  final String titre;
  final List<Item> items;

  List<Item> get jouables => items.where((i) => i.jouable).toList();
}
