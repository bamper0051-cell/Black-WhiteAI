// neon_theme.dart — Neon dark theme for BlackBugsAI

import 'package:flutter/material.dart';

class NeonColors {
  // Primary neon palette
  static const Color cyan = Color(0xFF00FFFF);
  static const Color purple = Color(0xFFBF00FF);
  static const Color green = Color(0xFF00FF41);
  static const Color pink = Color(0xFFFF0090);
  static const Color orange = Color(0xFFFF6B00);
  static const Color blue = Color(0xFF0080FF);
  static const Color yellow = Color(0xFFFFFF00);

  // Background shades
  static const Color bgDeep = Color(0xFF000000);
  static const Color bgDark = Color(0xFF050510);
  static const Color bgCard = Color(0xFF0A0A1A);
  static const Color bgSurface = Color(0xFF0F0F24);
  static const Color bgElevated = Color(0xFF141430);

  // Glow variants (semi-transparent)
  static const Color cyanGlow = Color(0x4000FFFF);
  static const Color purpleGlow = Color(0x40BF00FF);
  static const Color greenGlow = Color(0x4000FF41);
  static const Color pinkGlow = Color(0x40FF0090);
  static const Color blueGlow = Color(0x400080FF);

  // Text
  static const Color textPrimary = Color(0xFFE0E0FF);
  static const Color textSecondary = Color(0xFF8080A0);
  static const Color textDisabled = Color(0xFF404060);

  // Status
  static const Color statusDone = green;
  static const Color statusRunning = cyan;
  static const Color statusFailed = pink;
  static const Color statusPending = yellow;
  static const Color statusCancelled = textSecondary;
}

class NeonTheme {
  static ThemeData get theme => ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: NeonColors.bgDeep,
        primaryColor: NeonColors.cyan,
        colorScheme: const ColorScheme.dark(
          primary: NeonColors.cyan,
          secondary: NeonColors.purple,
          tertiary: NeonColors.green,
          surface: NeonColors.bgCard,
          error: NeonColors.pink,
          onPrimary: NeonColors.bgDeep,
          onSecondary: Colors.white,
          onSurface: NeonColors.textPrimary,
        ),
        fontFamily: 'JetBrainsMono',
        textTheme: const TextTheme(
          displayLarge: TextStyle(
            fontFamily: 'Orbitron',
            fontSize: 32,
            fontWeight: FontWeight.w700,
            color: NeonColors.cyan,
            letterSpacing: 2,
          ),
          displayMedium: TextStyle(
            fontFamily: 'Orbitron',
            fontSize: 24,
            fontWeight: FontWeight.w700,
            color: NeonColors.textPrimary,
            letterSpacing: 1.5,
          ),
          headlineLarge: TextStyle(
            fontFamily: 'Orbitron',
            fontSize: 20,
            fontWeight: FontWeight.w700,
            color: NeonColors.cyan,
            letterSpacing: 1,
          ),
          headlineMedium: TextStyle(
            fontFamily: 'Orbitron',
            fontSize: 16,
            fontWeight: FontWeight.w700,
            color: NeonColors.textPrimary,
          ),
          bodyLarge: TextStyle(
            fontFamily: 'JetBrainsMono',
            fontSize: 14,
            color: NeonColors.textPrimary,
          ),
          bodyMedium: TextStyle(
            fontFamily: 'JetBrainsMono',
            fontSize: 12,
            color: NeonColors.textSecondary,
          ),
          labelLarge: TextStyle(
            fontFamily: 'Orbitron',
            fontSize: 12,
            fontWeight: FontWeight.w700,
            color: NeonColors.cyan,
            letterSpacing: 2,
          ),
        ),
        appBarTheme: const AppBarTheme(
          backgroundColor: NeonColors.bgDark,
          foregroundColor: NeonColors.cyan,
          elevation: 0,
          centerTitle: true,
          titleTextStyle: TextStyle(
            fontFamily: 'Orbitron',
            fontSize: 18,
            fontWeight: FontWeight.w700,
            color: NeonColors.cyan,
            letterSpacing: 2,
          ),
          iconTheme: IconThemeData(color: NeonColors.cyan),
        ),
        cardTheme: CardTheme(
          color: NeonColors.bgCard,
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
            side: const BorderSide(color: NeonColors.cyanGlow, width: 1),
          ),
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: NeonColors.bgCard,
            foregroundColor: NeonColors.cyan,
            side: const BorderSide(color: NeonColors.cyan, width: 1.5),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(8),
            ),
            textStyle: const TextStyle(
              fontFamily: 'Orbitron',
              fontSize: 12,
              fontWeight: FontWeight.w700,
              letterSpacing: 1.5,
            ),
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
          ),
        ),
        iconTheme: const IconThemeData(color: NeonColors.cyan, size: 20),
        dividerTheme: const DividerThemeData(
          color: NeonColors.cyanGlow,
          thickness: 1,
        ),
        bottomNavigationBarTheme: const BottomNavigationBarThemeData(
          backgroundColor: NeonColors.bgDark,
          selectedItemColor: NeonColors.cyan,
          unselectedItemColor: NeonColors.textSecondary,
          showSelectedLabels: true,
          showUnselectedLabels: true,
          type: BottomNavigationBarType.fixed,
          selectedLabelStyle: TextStyle(
            fontFamily: 'Orbitron',
            fontSize: 9,
            fontWeight: FontWeight.w700,
            letterSpacing: 1,
          ),
          unselectedLabelStyle: TextStyle(
            fontFamily: 'Orbitron',
            fontSize: 9,
          ),
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: NeonColors.bgCard,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(8),
            borderSide: const BorderSide(color: NeonColors.cyanGlow),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(8),
            borderSide: const BorderSide(color: NeonColors.cyanGlow),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(8),
            borderSide: const BorderSide(color: NeonColors.cyan, width: 2),
          ),
          hintStyle: const TextStyle(color: NeonColors.textDisabled),
          labelStyle: const TextStyle(color: NeonColors.textSecondary),
        ),
        snackBarTheme: SnackBarThemeData(
          backgroundColor: NeonColors.bgElevated,
          contentTextStyle: const TextStyle(color: NeonColors.textPrimary),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
            side: const BorderSide(color: NeonColors.cyanGlow),
          ),
          behavior: SnackBarBehavior.floating,
        ),
      );
}

// ─── Neon Box Decoration helpers ──────────────────────────────────────────────

BoxDecoration neonCardDecoration({
  Color glowColor = NeonColors.cyan,
  double glowRadius = 8,
  double borderWidth = 1,
}) {
  return BoxDecoration(
    color: NeonColors.bgCard,
    borderRadius: BorderRadius.circular(12),
    border: Border.all(
      color: glowColor.withOpacity(0.6),
      width: borderWidth,
    ),
    boxShadow: [
      BoxShadow(
        color: glowColor.withOpacity(0.15),
        blurRadius: glowRadius,
        spreadRadius: 0,
      ),
    ],
  );
}

BoxDecoration neonButtonDecoration({Color color = NeonColors.cyan}) {
  return BoxDecoration(
    color: color.withOpacity(0.1),
    borderRadius: BorderRadius.circular(8),
    border: Border.all(color: color, width: 1.5),
    boxShadow: [
      BoxShadow(
        color: color.withOpacity(0.3),
        blurRadius: 8,
        spreadRadius: 0,
      ),
    ],
  );
}

// ─── Neon Text with glow ──────────────────────────────────────────────────────

class NeonText extends StatelessWidget {
  final String text;
  final Color color;
  final double fontSize;
  final FontWeight fontWeight;
  final String? fontFamily;
  final double glowRadius;
  final TextAlign? textAlign;

  const NeonText(
    this.text, {
    super.key,
    this.color = NeonColors.cyan,
    this.fontSize = 14,
    this.fontWeight = FontWeight.normal,
    this.fontFamily,
    this.glowRadius = 8,
    this.textAlign,
  });

  @override
  Widget build(BuildContext context) {
    return Text(
      text,
      textAlign: textAlign,
      style: TextStyle(
        color: color,
        fontSize: fontSize,
        fontWeight: fontWeight,
        fontFamily: fontFamily ?? 'JetBrainsMono',
        shadows: [
          Shadow(
            color: color.withOpacity(0.8),
            blurRadius: glowRadius,
          ),
          Shadow(
            color: color.withOpacity(0.4),
            blurRadius: glowRadius * 2,
          ),
        ],
      ),
    );
  }
}
