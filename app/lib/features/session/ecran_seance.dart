import 'package:flutter/material.dart';
import 'package:uuid/uuid.dart';

import '../../core/api.dart';
import '../../core/modeles.dart';
import '../../shared/arabic_text.dart';

/// La séance du jour.
///
/// Elle arrive **déjà composée** par le serveur : révisions, nouveautés,
/// lecture finale. Cet écran ne fait que jouer ce qu'on lui donne, mesurer le
/// temps de réponse, et renvoyer les tentatives brutes.
///
/// La latence est mesurée ici mais **jamais interprétée ici** : c'est le
/// serveur qui décide si une réponse juste était une hésitation, en la
/// comparant au seuil de la compétence. Un client modifié ne doit pas pouvoir
/// s'attribuer une maîtrise.
class EcranSeance extends StatefulWidget {
  const EcranSeance({super.key, required this.api, required this.onDeconnexion});

  final Api api;
  final VoidCallback onDeconnexion;

  @override
  State<EcranSeance> createState() => _EcranSeanceState();
}

class _EcranSeanceState extends State<EcranSeance> {
  static const _uuid = Uuid();

  Seance? _seance;
  String? _erreur;
  bool _chargement = true;

  int _index = 0;
  DateTime? _afficheA;
  Option? _choisie;
  final _tentatives = <Map<String, dynamic>>[];
  Map<String, dynamic>? _bilan;

  @override
  void initState() {
    super.initState();
    _charger();
  }

  Future<void> _charger() async {
    setState(() {
      _chargement = true;
      _erreur = null;
    });
    try {
      final r = await widget.api.seanceDuJour();
      if (!mounted) return;
      if (r.statusCode == 403) {
        setState(() {
          _erreur = 'Cette leçon fait partie du programme complet.';
          _chargement = false;
        });
        return;
      }
      if (r.statusCode == 401) {
        widget.onDeconnexion();
        return;
      }
      if (r.statusCode != 200) {
        setState(() {
          _erreur = 'Le serveur a répondu ${r.statusCode}.';
          _chargement = false;
        });
        return;
      }
      setState(() {
        _seance = Seance.depuisJson(r.data as Map<String, dynamic>);
        _chargement = false;
        _afficheA = DateTime.now();
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _erreur = 'Serveur injoignable.';
        _chargement = false;
      });
    }
  }

  void _repondre(Item item, Option option) {
    if (_choisie != null) return; // une seule réponse par item
    final latence = DateTime.now().difference(_afficheA!).inMilliseconds;
    setState(() => _choisie = option);

    _tentatives.add({
      'client_id': _uuid.v4(),
      'skill_id': item.skillId,
      if (item.exerciceId != null) 'exercise_id': item.exerciceId,
      'is_correct': option.correcte,
      'latency_ms': latence,
      'answered_at': DateTime.now().toUtc().toIso8601String(),
    });
  }

  Future<void> _suivant(List<Item> items) async {
    if (_index + 1 < items.length) {
      setState(() {
        _index++;
        _choisie = null;
        _afficheA = DateTime.now();
      });
      return;
    }
    await _terminer();
  }

  Future<void> _terminer() async {
    setState(() => _chargement = true);
    try {
      final r = await widget.api.synchroniser({
        'day_number': _seance!.jour,
        'attempts': _tentatives,
        'completed_at': DateTime.now().toUtc().toIso8601String(),
      });
      if (!mounted) return;
      setState(() {
        _bilan = r.statusCode == 200 ? r.data as Map<String, dynamic> : null;
        _erreur = r.statusCode == 200 ? null : 'La synchronisation a échoué.';
        _chargement = false;
      });
    } catch (_) {
      if (!mounted) return;
      // Les tentatives restent en mémoire : rien n'est perdu, la
      // synchronisation est idempotente et pourra être rejouée.
      setState(() {
        _erreur = 'Séance terminée, mais pas encore synchronisée.';
        _chargement = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_seance == null
            ? 'IqraGo'
            : 'Jour ${_seance!.jour} — ${_seance!.titre}'),
        actions: [
          IconButton(
            tooltip: 'Se déconnecter',
            icon: const Icon(Icons.logout),
            onPressed: () async {
              await widget.api.oublierJetons();
              widget.onDeconnexion();
            },
          ),
        ],
      ),
      body: _corps(),
    );
  }

  Widget _corps() {
    if (_chargement) return const Center(child: CircularProgressIndicator());
    if (_bilan != null) return _ecranBilan();
    if (_erreur != null) return _ecranErreur();

    final items = _seance?.jouables ?? const <Item>[];
    if (items.isEmpty) return _ecranRienAJouer();
    return _ecranItem(items);
  }

  Widget _ecranItem(List<Item> items) {
    final item = items[_index];
    return Column(
      children: [
        LinearProgressIndicator(value: (_index + 1) / items.length),
        Expanded(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Column(
              children: [
                if (item.enonceFr != null)
                  Text(item.enonceFr!,
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 24),
                if (item.enonceArabe != null)
                  ArabicText(item.enonceArabe!, taille: 56),
                const SizedBox(height: 32),
                ...item.options.map((o) => _bouton(item, o)),
                if (_choisie != null) ...[
                  const SizedBox(height: 24),
                  FilledButton(
                    onPressed: () => _suivant(items),
                    style: FilledButton.styleFrom(
                        minimumSize: const Size.fromHeight(52)),
                    child: Text(_index + 1 < items.length
                        ? 'Continuer'
                        : 'Terminer la séance'),
                  ),
                ],
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _bouton(Item item, Option option) {
    final repondu = _choisie != null;
    Color? fond;
    if (repondu) {
      // On montre la bonne réponse même quand l'utilisateur s'est trompé :
      // laisser une erreur sans correction, c'est la laisser s'installer.
      if (option.correcte) {
        fond = Colors.green.withValues(alpha: 0.18);
      } else if (option == _choisie) {
        fond = Theme.of(context).colorScheme.error.withValues(alpha: 0.15);
      }
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Material(
        color: fond ?? Theme.of(context).colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(12),
        child: InkWell(
          borderRadius: BorderRadius.circular(12),
          onTap: repondu ? null : () => _repondre(item, option),
          child: Container(
            // 64 px : assez grand pour un doigt, assez haut pour que les
            // harakat ne soient pas rognées.
            constraints: const BoxConstraints(minHeight: 64),
            alignment: Alignment.center,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            child: option.estArabe
                ? ArabicText(option.texte, taille: 40)
                : Text(option.texte,
                    style: Theme.of(context).textTheme.titleLarge),
          ),
        ),
      ),
    );
  }

  Widget _ecranBilan() {
    final justes = _tentatives.where((t) => t['is_correct'] == true).length;
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.check_circle_outline, size: 64),
            const SizedBox(height: 16),
            Text('Séance terminée',
                style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 24),
            Text('$justes bonne(s) réponse(s) sur ${_tentatives.length}'),
            const SizedBox(height: 8),
            Text('Série : ${_bilan!['streak_days']} jour(s)'),
            const SizedBox(height: 8),
            Text('${_bilan!['accepted']} tentative(s) enregistrée(s)'),
            const SizedBox(height: 32),
            OutlinedButton(
              onPressed: () {
                setState(() {
                  _bilan = null;
                  _index = 0;
                  _choisie = null;
                  _tentatives.clear();
                });
                _charger();
              },
              child: const Text('Revenir à la séance'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _ecranRienAJouer() => Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.hourglass_empty, size: 48),
              const SizedBox(height: 16),
              Text('Rien à jouer aujourd\'hui',
                  style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 12),
              const Text(
                'La séance est composée, mais aucun de ses exercices n\'est '
                'encore publié. Un contenu en cours de relecture n\'est jamais '
                'servi.',
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 24),
              OutlinedButton(onPressed: _charger, child: const Text('Réessayer')),
            ],
          ),
        ),
      );

  Widget _ecranErreur() => Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.error_outline, size: 48),
              const SizedBox(height: 16),
              Text(_erreur!, textAlign: TextAlign.center),
              const SizedBox(height: 24),
              OutlinedButton(onPressed: _charger, child: const Text('Réessayer')),
            ],
          ),
        ),
      );
}
