// Serveur statique minimal pour build/web.
// CanvasKit exige http:// — un file:// ne suffit pas.
// Usage : dart run serve.dart [port]

import 'dart:io';

const types = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript',
  '.mjs': 'application/javascript',
  '.json': 'application/json',
  '.wasm': 'application/wasm',
  '.css': 'text/css',
  '.png': 'image/png',
  '.ttf': 'font/ttf',
  '.otf': 'font/otf',
  '.ico': 'image/x-icon',
  '.symbols': 'application/octet-stream',
};

Future<void> main(List<String> args) async {
  final port = args.isEmpty ? 8080 : int.parse(args.first);
  final root = Directory('build/web').absolute;
  if (!root.existsSync()) {
    stderr.writeln('build/web absent — lancer `flutter build web --release` d\'abord.');
    exit(1);
  }

  final server = await HttpServer.bind(InternetAddress.loopbackIPv4, port);
  stdout.writeln('sert ${root.path} sur http://127.0.0.1:$port');

  await for (final req in server) {
    var path = req.uri.path;
    if (path == '/' || path.isEmpty) path = '/index.html';
    final file = File('${root.path}$path');
    if (!file.existsSync()) {
      req.response.statusCode = 404;
      await req.response.close();
      continue;
    }
    final ext = path.contains('.') ? path.substring(path.lastIndexOf('.')) : '';
    req.response.headers.contentType = ContentType.parse(types[ext] ?? 'application/octet-stream');
    // CanvasKit et les workers exigent ces en-têtes pour SharedArrayBuffer.
    req.response.headers.add('Cross-Origin-Opener-Policy', 'same-origin');
    req.response.headers.add('Cross-Origin-Embedder-Policy', 'require-corp');
    await req.response.addStream(file.openRead());
    await req.response.close();
  }
}
