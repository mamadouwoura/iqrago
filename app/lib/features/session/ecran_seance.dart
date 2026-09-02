import 'package:flutter/material.dart';
import 'package:uuid/uuid.dart';

import '../../core/api.dart';
import '../../core/depot.dart';
import '../../core/modeles.dart';
import '../../shared/arabic_text.dart';

/// La séance du jour.
///
/// Elle arrive **déjà composée** par le serveur : révisions, nouveautés,
/// lecture finale. Cet écran ne fait que jouer ce qu'on lui donne, mesurer le
/// temps de réponse, et remettre les tentatives au dépôt.
///
/// La latence est mesurée ici mais **jamais interprétée ici** : c'est le
/// serveur qui décide si une réponse juste était une hésitation, en la
/// comparant au seuil de la compétence. Un client modifié ne doit pas pouvoir
/// s'attribuer une maîtrise.
///
/// Rien dans cet écran ne distingue « en ligne » de « hors ligne » : le dépôt
/// sert une séance, point. Seul un bandeau le signale.
class EcranSeance extends StatefulWidget {
  const EcranSeance({
    super.key,
    required this.api,
    required this.depot,
    required this.onDeconnexion,
  });

  final Api api;
  final Depot depot;
  final VoidCallback onDeconnexion;

  @override
  State<EcranSeance> createState() => _EcranSeanceState();
}

class _EcranSeanceState extends State<EcranSeance> {
  static const _uuid = Uuid();

  Seance? _seance;
  Provenance _provenance = Provenance.reseau;
  int _enAttente = 0;
  bool _chargement = true;

  int _index = 0;
  DateTime? _afficheA;
  Option? _choisie;
  final _tentatives = <Map<String, dynamic>>[];
  Map<String, dynamic>? _bilan;
  bool _synchronise = true;

  @override
  void initState() {
    super.initState();
    _charger();
  }

  Future<void> _charger() async {
    setState(() => _chargement = true);
    final r = await widget.depot.seanceDuJour();
    if (!mounted) return;
    setState(() {
      _seance = r.seance;
      _provenance = r.provenance;
      _enAttente = r.enAttente;
      _chargement = false;
      _index = 0;
      _choisie = null;
      _bilan = null;
      _tentatives.clear();
      _afficheA = DateTime.now();
    });
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

    setState(() => _chargement = true);
    // Le dépôt empile avant d'essayer d'envoyer : le travail est sauvé même
    // si le réseau manque, même si l'application meurt maintenant.
    final parti = await widget.depot.terminer(_seance!.jour, _tentatives);
    final restant = await widget.depot.stockage.nbTentativesEnAttente();
    if (!mounted) return;
    setState(() {
      _bilan = {'justes': _tentatives.where((t) => t['is_correct'] == true).length};
      _synchronise = parti;
      _enAttente = restant;
      _chargement = false;
    });
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
      body: Column(
        children: [
          if (_provenance == Provenance.cache) const _BandeauHorsLigne(),
          if (_enAttente > 0) _BandeauEnAttente(n: _enAttente),
          Expanded(child: _corps()),
        ],
      ),
    );
  }

  Widget _corps() {
    if (_chargement) return const Center(child: CircularProgressIndicator());
    if (_bilan != null) return _ecranBilan();
    if (_seance == null) return _ecranRien();

    final items = _seance!.jouables;
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

  Widget _ecranBilan() => Center(
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
              Text('${_bilan!['justes']} bonne(s) réponse(s) '
                  'sur ${_tentatives.length}'),
              const SizedBox(height: 16),
              // Le message dit ce qui est vrai : le travail est gardé, il
              // partira. Pas « échec de synchronisation », qui laisse croire
              // que la séance est perdue.
              Text(
                _synchronise
                    ? 'Progression enregistrée.'
                    : 'Gardée sur ton téléphone. Elle partira à la prochaine '
                        'connexion.',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 32),
              OutlinedButton(onPressed: _charger, child: const Text('Continuer')),
            ],
          ),
        ),
      );

  Widget _ecranRienAJouer() => _message(
        Icons.hourglass_empty,
        'Rien à jouer aujourd\'hui',
        'La séance est composée, mais aucun de ses exercices n\'est encore '
            'publié. Un contenu en cours de relecture n\'est jamais servi.',
      );

  Widget _ecranRien() => _message(
        Icons.cloud_off,
        'Rien à jouer pour l\'instant',
        'Aucune séance n\'a encore été téléchargée sur ce téléphone. '
            'Connecte-toi une fois, et les jours suivants seront disponibles '
            'même sans réseau.',
      );

  Widget _message(IconData icone, String titre, String texte) => Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icone, size: 48),
              const SizedBox(height: 16),
              Text(titre, style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 12),
              Text(texte, textAlign: TextAlign.center),
              const SizedBox(height: 24),
              OutlinedButton(onPressed: _charger, child: const Text('Réessayer')),
            ],
          ),
        ),
      );
}

class _BandeauHorsLigne extends StatelessWidget {
  const _BandeauHorsLigne();

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        color: Theme.of(context).colorScheme.secondaryContainer,
        padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.cloud_off, size: 18),
            const SizedBox(width: 8),
            // Ce que l'utilisateur doit comprendre : il peut continuer.
            // « Pas de connexion » seul suggère qu'il faut attendre.
            Flexible(child: Text('Hors ligne — tu peux continuer',
                style: Theme.of(context).textTheme.bodySmall)),
          ],
        ),
      );
}

class _BandeauEnAttente extends StatelessWidget {
  const _BandeauEnAttente({required this.n});
  final int n;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        color: Theme.of(context).colorScheme.surfaceContainerHighest,
        padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 16),
        child: Text(
          '$n réponse(s) à envoyer — rien n\'est perdu',
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.bodySmall,
        ),
      );
}
