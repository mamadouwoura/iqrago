import 'package:flutter/material.dart';

import '../../core/api.dart';

class EcranConnexion extends StatefulWidget {
  const EcranConnexion({super.key, required this.api, required this.onConnecte});

  final Api api;
  final VoidCallback onConnecte;

  @override
  State<EcranConnexion> createState() => _EcranConnexionState();
}

class _EcranConnexionState extends State<EcranConnexion> {
  final _identifiant = TextEditingController();
  final _motDePasse = TextEditingController();
  String? _erreur;
  bool _enCours = false;

  Future<void> _valider() async {
    setState(() {
      _enCours = true;
      _erreur = null;
    });
    try {
      final erreur = await widget.api.connexion(
        _identifiant.text.trim(),
        _motDePasse.text,
      );
      if (!mounted) return;
      if (erreur == null) {
        widget.onConnecte();
      } else {
        setState(() => _erreur = erreur);
      }
    } catch (_) {
      if (mounted) {
        setState(() => _erreur = 'Serveur injoignable. Vérifie ta connexion.');
      }
    } finally {
      if (mounted) setState(() => _enCours = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text('IqraGo',
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.headlineMedium),
                const SizedBox(height: 8),
                Text('Apprends à lire l\'arabe, étape par étape.',
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.bodyMedium),
                const SizedBox(height: 32),
                TextField(
                  controller: _identifiant,
                  autofillHints: const [AutofillHints.username],
                  decoration: const InputDecoration(
                    labelText: 'E-mail ou téléphone',
                    // Un seul champ : demander de choisir avant de taper est
                    // une friction inutile, le serveur sait faire la
                    // différence.
                    helperText: 'Par exemple a@example.com ou +221771234567',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: _motDePasse,
                  obscureText: true,
                  onSubmitted: (_) => _valider(),
                  decoration: const InputDecoration(
                    labelText: 'Mot de passe',
                    border: OutlineInputBorder(),
                  ),
                ),
                if (_erreur != null) ...[
                  const SizedBox(height: 16),
                  Text(_erreur!,
                      style: TextStyle(color: Theme.of(context).colorScheme.error)),
                ],
                const SizedBox(height: 24),
                FilledButton(
                  onPressed: _enCours ? null : _valider,
                  style: FilledButton.styleFrom(
                    // Cible tactile confortable : la cible principale lit sur
                    // un écran de 5 pouces, parfois dans les transports.
                    minimumSize: const Size.fromHeight(52),
                  ),
                  child: _enCours
                      ? const SizedBox(
                          height: 20, width: 20,
                          child: CircularProgressIndicator(strokeWidth: 2))
                      : const Text('Se connecter'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  @override
  void dispose() {
    _identifiant.dispose();
    _motDePasse.dispose();
    super.dispose();
  }
}
