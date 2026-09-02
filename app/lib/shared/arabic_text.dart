import 'package:flutter/material.dart';

/// Le **seul** widget autorisé à afficher de l'arabe.
///
/// Cette contrainte n'est pas cosmétique. Les signes diacritiques débordent de
/// la boîte de mise en page calculée par Flutter, et se font rogner dans tout
/// conteneur à hauteur contrainte — carte d'exercice, bouton, ligne de liste.
/// Une application qui enseigne fathah, kasra et damma en les affichant
/// coupés n'enseigne rien.
///
/// Les trois valeurs ci-dessous sortent de 720 mesures au pixel
/// (`docs/07-rendu-arabe.md`) :
///
/// | Police | défaut | 1.0 | 1.5 | 1.8 |
/// |---|---|---|---|---|
/// | **Noto Naskh Arabic** | 0,00 | 11,00 | **0,00** | 0,00 |
/// | Scheherazade New | 2,00 | 28,00 | 13,00 | 6,00 |
/// | Amiri | 8,00 | 31,00 | 16,00 | 7,00 |
///
/// `height: 1.0` — la valeur qu'on écrit spontanément pour serrer une carte —
/// rogne sur les trois polices, jusqu'à 31 px sur `بُّ`. C'est la valeur à ne
/// jamais écrire.
class ArabicText extends StatelessWidget {
  const ArabicText(
    this.texte, {
    super.key,
    this.taille = 32,
    this.couleur,
    this.textAlign = TextAlign.center,
  });

  /// Police embarquée, jamais celle du système : elle varie selon le
  /// constructeur et la version d'Android.
  static const famille = 'NotoNaskhArabic';

  /// Mesurée, pas choisie au jugé.
  static const hauteurLigne = 1.5;

  /// En dessous, les signes deviennent illisibles sur un écran de 5 pouces.
  static const tailleMinimale = 20.0;

  final String texte;
  final double taille;
  final Color? couleur;
  final TextAlign textAlign;

  @override
  Widget build(BuildContext context) {
    return Directionality(
      // L'arabe se lit de droite à gauche, même enchâssé dans une interface
      // française qui va dans l'autre sens.
      textDirection: TextDirection.rtl,
      child: Text(
        texte,
        textAlign: textAlign,
        style: TextStyle(
          fontFamily: famille,
          fontSize: taille < tailleMinimale ? tailleMinimale : taille,
          height: hauteurLigne,
          color: couleur ?? Theme.of(context).colorScheme.onSurface,
        ),
        // `applyHeightToFirstAscent: true` — la valeur par défaut. La variante
        // à `false` gagnait de la place mais rognait à nouveau : mesurée,
        // écartée.
        textHeightBehavior: const TextHeightBehavior(),
      ),
    );
  }
}
