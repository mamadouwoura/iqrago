import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Client HTTP de l'application.
///
/// Une seule instance : le jeton vit ici, et un intercepteur le pose sur
/// chaque requête. Aucun écran ne manipule d'en-tête d'authentification.
class Api {
  Api({String? base})
      : _dio = Dio(BaseOptions(
          baseUrl: base ?? baseParDefaut,
          connectTimeout: const Duration(seconds: 10),
          receiveTimeout: const Duration(seconds: 20),
          // Ne pas lever sur 4xx : les refus (403 droit manquant, 401 jeton
          // expiré) sont des réponses métier, pas des pannes.
          validateStatus: (c) => c != null && c < 500,
        )) {
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final jeton = await _jetonAcces();
        if (jeton != null) {
          options.headers['Authorization'] = 'Bearer $jeton';
        }
        handler.next(options);
      },
    ));
  }

  /// `10.0.2.2` est l'hôte vu depuis un émulateur Android ; `127.0.0.1`
  /// depuis le web et le bureau. Réglable au lancement :
  ///   flutter run --dart-define=API_BASE=http://192.168.1.20:8000/api/v1
  static const baseParDefaut = String.fromEnvironment(
    'API_BASE',
    defaultValue: 'http://127.0.0.1:8000/api/v1',
  );

  final Dio _dio;
  final _coffre = const FlutterSecureStorage();

  Future<String?> _jetonAcces() => _coffre.read(key: 'access');

  Future<bool> estConnecte() async => (await _jetonAcces()) != null;

  Future<void> oublierJetons() async {
    await _coffre.delete(key: 'access');
    await _coffre.delete(key: 'refresh');
  }

  /// Connexion par e-mail **ou** téléphone : le serveur fait la différence,
  /// l'utilisateur n'a pas à choisir avant de taper.
  Future<String?> connexion(String identifiant, String motDePasse) async {
    final r = await _dio.post('/auth/login', data: {
      'identifier': identifiant,
      'password': motDePasse,
    });
    if (r.statusCode == 200) {
      await _coffre.write(key: 'access', value: r.data['tokens']['access']);
      await _coffre.write(key: 'refresh', value: r.data['tokens']['refresh']);
      return null;
    }
    if (r.statusCode == 429) {
      return 'Trop de tentatives. Attends une minute.';
    }
    return 'Identifiant ou mot de passe incorrect.';
  }

  /// `jour` sert au préchargement : ranger les séances suivantes pendant que
  /// l'utilisateur joue celle du jour. Sans lui, la première soirée sans
  /// réseau arrête tout.
  Future<Response<dynamic>> seanceDuJour({int? jour}) => _dio.get(
        '/session/today',
        queryParameters: jour == null ? null : {'jour': jour},
      );

  Future<Response<dynamic>> synchroniser(Map<String, dynamic> lot) =>
      _dio.post('/session/sync', data: lot);

  Future<Response<dynamic>> apercu() => _dio.get('/progress/overview');
}
