import 'package:flutter/material.dart';

import 'core/api.dart';
import 'core/depot.dart';
import 'core/stockage.dart';
import 'features/auth/ecran_connexion.dart';
import 'features/session/ecran_seance.dart';

void main() => runApp(const IqraGo());

class IqraGo extends StatefulWidget {
  const IqraGo({super.key});

  @override
  State<IqraGo> createState() => _IqraGoState();
}

class _IqraGoState extends State<IqraGo> {
  final _api = Api();
  late final _depot = Depot(_api, Stockage());
  bool? _connecte;

  @override
  void initState() {
    super.initState();
    _api.estConnecte().then((v) {
      if (mounted) setState(() => _connecte = v);
    });
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'IqraGo',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF0F766E)),
      ),
      home: switch (_connecte) {
        null => const Scaffold(body: Center(child: CircularProgressIndicator())),
        false => EcranConnexion(
            api: _api,
            onConnecte: () => setState(() => _connecte = true),
          ),
        true => EcranSeance(
            api: _api,
            depot: _depot,
            onDeconnexion: () => setState(() => _connecte = false),
          ),
      },
    );
  }
}
