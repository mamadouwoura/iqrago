import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:iqrago/shared/arabic_text.dart';

/// Ces valeurs sortent de 720 mesures au pixel (docs/07-rendu-arabe.md).
/// Les verrouiller par un test évite qu'une modification les défasse en
/// silence — le rognage des harakat ne casse aucun test fonctionnel.
void main() {
  test('la configuration mesurée ne bouge pas', () {
    expect(ArabicText.famille, 'NotoNaskhArabic',
        reason: 'seule police à 0,00 px de débordement sur les 12 cas');
    expect(ArabicText.hauteurLigne, 1.5,
        reason: 'height 1.0 rogne jusqu\'à 31 px : jamais l\'écrire');
  });

  testWidgets('rend en RTL avec la police embarquée', (tester) async {
    await tester.pumpWidget(const MaterialApp(
      home: Scaffold(body: ArabicText('بُّ')),
    ));

    final texte = tester.widget<Text>(find.byType(Text));
    expect(texte.style!.fontFamily, ArabicText.famille);
    expect(texte.style!.height, ArabicText.hauteurLigne);

    final dir = tester.widget<Directionality>(
        find.ancestor(of: find.byType(Text), matching: find.byType(Directionality)).first);
    expect(dir.textDirection, TextDirection.rtl);
  });

  testWidgets('une taille trop petite est relevée au plancher lisible',
      (tester) async {
    await tester.pumpWidget(const MaterialApp(
      home: Scaffold(body: ArabicText('بَ', taille: 8)),
    ));
    final texte = tester.widget<Text>(find.byType(Text));
    expect(texte.style!.fontSize, ArabicText.tailleMinimale);
  });
}
