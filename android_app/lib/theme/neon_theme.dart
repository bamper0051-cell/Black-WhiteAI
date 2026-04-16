// neon_theme.dart — BlackBugsAI Design System
// Spark-inspired: GitHub dark palette + neon agent accents
// Uses google_fonts — no local font files required

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

// ── Color Palette ──────────────────────────────────────────────────────────────
class NeonColors {
  // GitHub Spark / dark canvas
  static const Color canvas      = Color(0xFF0D1117);  // GitHub dark bg
  static const Color bgDeep      = Color(0xFF0D1117);
  static const Color bgDark      = Color(0xFF010409);
  static const Color bgCard      = Color(0xFF161B22);  // GitHub secondary
  static const Color bgSurface   = Color(0xFF1C2128);
  static const Color bgElevated  = Color(0xFF21262D);
  static const Color border      = Color(0xFF30363D);  // GitHub border
  static const Color borderMuted = Color(0xFF21262D);

  // Neon agent accents
  static const Color cyan   = Color(0xFF00D9FF);  // Neo
  static const Color purple = Color(0xFF9B59FF);  // Morpheus/Matrix
  static const Color green  = Color(0xFF00FF87);  // Online/OK
  static const Color pink   = Color(0xFFFF3CAC);  // Error/Smith
  static const Color orange = Color(0xFFFF8C42);  // Warning/Tanker
  static const Color blue   = Color(0xFF2188FF);  // Pythia
  static const Color yellow = Color(0xFFFFD60A);  // Pending

  // Glow variants
  static const Color cyanGlow   = Color(0x3000D9FF);
  static const Color purpleGlow = Color(0x309B59FF);
  static const Color greenGlow  = Color(0x3000FF87);
  static const Color pinkGlow   = Color(0x30FF3CAC);
  static const Color blueGlow   = Color(0x302188FF);

  // Text — GitHub muted scale
  static const Color textPrimary   = Color(0xFFF0F6FC);
  static const Color textSecondary = Color(0xFF8B949E);
  static const Color textMuted     = Color(0xFF484F58);
  static const Color textDisabled  = Color(0xFF30363D);
  static const Color textLink      = Color(0xFF58A6FF);

  // Status
  static const Color statusDone      = green;
  static const Color statusRunning   = cyan;
  static const Color statusFailed    = pink;
  static const Color statusPending   = yellow;
  static const Color statusCancelled = textSecondary;
  static const Color statusIdle      = textMuted;

  // Agent identity colors
  static const Color agentNeo      = cyan;
  static const Color agentMatrix   = purple;
  static const Color agentSmith    = pink;
  static const Color agentPythia   = blue;
  static const Color agentAnderson = orange;
  static const Color agentTanker   = Color(0xFF20C997);
  static const Color agentOperator = yellow;
  static const Color agentMorpheus = Color(0xFF7048E8);
}

// ── Typography helpers ─────────────────────────────────────────────────────────
class NeonTheme {
  static TextStyle _orbitron({
    double fontSize = 14,
    FontWeight weight = FontWeight.normal,
    Color color = NeonColors.cyan,
    double letterSpacing = 0,
  }) =>
      GoogleFonts.orbitron(
        fontSize: fontSize,
        fontWeight: weight,
        color: color,
        letterSpacing: letterSpacing,
      );

  static TextStyle _jetbrains({
    double fontSize = 13,
    FontWeight weight = FontWeight.normal,
    Color color = NeonColors.textPrimary,
    double letterSpacing = 0,
  }) =>
      GoogleFonts.jetBrainsMono(
        fontSize: fontSize,
        fontWeight: weight,
        color: color,
        letterSpacing: letterSpacing,
      );

  static TextStyle _inter({
    double fontSize = 14,
    FontWeight weight = FontWeight.normal,
    Color color = NeonColors.textPrimary,
  }) =>
      GoogleFonts.inter(
        fontSize: fontSize,
        fontWeight: weight,
        color: color,
      );

  static ThemeData get theme => ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: NeonColors.canvas,
        primaryColor: NeonColors.cyan,
        colorScheme: const ColorScheme.dark(
          primary:    NeonColors.cyan,
          secondary:  NeonColors.purple,
          tertiary:   NeonColors.green,
          surface:    NeonColors.bgCard,
          error:      NeonColors.pink,
          onPrimary:  NeonColors.bgDark,
          onSecondary: Colors.white,
          onSurface:  NeonColors.textPrimary,
          outline:    NeonColors.border,
        ),
        textTheme: TextTheme(
          displayLarge:  _orbitron(fontSize: 28, weight: FontWeight.w700, letterSpacing: 2),
          displayMedium: _orbitron(fontSize: 22, weight: FontWeight.w700, letterSpacing: 1.5),
          headlineLarge: _orbitron(fontSize: 18, weight: FontWeight.w700, letterSpacing: 1),
          headlineMedium: _orbitron(fontSize: 15, weight: FontWeight.w600, color: NeonColors.textPrimary),
          titleLarge:    _inter(fontSize: 16, weight: FontWeight.w600),
          titleMedium:   _inter(fontSize: 14, weight: FontWeight.w500),
          bodyLarge:     _jetbrains(fontSize: 13),
          bodyMedium:    _jetbrains(fontSize: 12, color: NeonColors.textSecondary),
          bodySmall:     _jetbrains(fontSize: 11, color: NeonColors.textMuted),
          labelLarge:    _orbitron(fontSize: 11, weight: FontWeight.w700, letterSpacing: 1.5),
          labelMedium:   _inter(fontSize: 12, weight: FontWeight.w500),
          labelSmall:    _jetbrains(fontSize: 10, color: NeonColors.textSecondary, letterSpacing: 0.5),
        ),
        appBarTheme: AppBarTheme(
          backgroundColor: NeonColors.bgDark,
          foregroundColor: NeonColors.textPrimary,
          elevation: 0,
          centerTitle: false,
          titleTextStyle: _orbitron(
            fontSize: 16, weight: FontWeight.w700,
            color: NeonColors.textPrimary, letterSpacing: 2,
          ),
          iconTheme: const IconThemeData(color: NeonColors.textSecondary),
          actionsIconTheme: const IconThemeData(color: NeonColors.textSecondary),
        ),
        cardTheme: CardTheme(
          color: NeonColors.bgCard,
          elevation: 0,
          margin: EdgeInsets.zero,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
            side: const BorderSide(color: NeonColors.border, width: 1),
          ),
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: NeonColors.cyan,
            foregroundColor: NeonColors.bgDark,
            elevation: 0,
            shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(6)),
            textStyle: _orbitron(
                fontSize: 11, weight: FontWeight.w700,
                color: NeonColors.bgDark, letterSpacing: 1),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          ),
        ),
        outlinedButtonTheme: OutlinedButtonThemeData(
          style: OutlinedButton.styleFrom(
            foregroundColor: NeonColors.cyan,
            side: const BorderSide(color: NeonColors.cyan, width: 1),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
            textStyle: _inter(fontSize: 13, weight: FontWeight.w500, color: NeonColors.cyan),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          ),
        ),
        iconTheme: const IconThemeData(color: NeonColors.textSecondary, size: 18),
        dividerTheme: const DividerThemeData(
          color: NeonColors.border,
          thickness: 1,
          space: 1,
        ),
        bottomNavigationBarTheme: BottomNavigationBarThemeData(
          backgroundColor: NeonColors.bgDark,
          selectedItemColor: NeonColors.cyan,
          unselectedItemColor: NeonColors.textMuted,
          showSelectedLabels: true,
          showUnselectedLabels: true,
          type: BottomNavigationBarType.fixed,
          elevation: 0,
          selectedLabelStyle: _orbitron(fontSize: 8, weight: FontWeight.w700, letterSpacing: 1),
          unselectedLabelStyle: _orbitron(fontSize: 8),
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: NeonColors.bgCard,
          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(6),
            borderSide: const BorderSide(color: NeonColors.border),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(6),
            borderSide: const BorderSide(color: NeonColors.border),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(6),
            borderSide: const BorderSide(color: NeonColors.cyan, width: 1.5),
          ),
          errorBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(6),
            borderSide: const BorderSide(color: NeonColors.pink),
          ),
          hintStyle: _jetbrains(fontSize: 12, color: NeonColors.textMuted),
          labelStyle: _inter(fontSize: 12, weight: FontWeight.w500, color: NeonColors.textSecondary),
        ),
        snackBarTheme: SnackBarThemeData(
          backgroundColor: NeonColors.bgElevated,
          contentTextStyle: _inter(fontSize: 13),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(6),
            side: const BorderSide(color: NeonColors.border),
          ),
          behavior: SnackBarBehavior.floating,
          insetPadding: const EdgeInsets.all(12),
        ),
        chipTheme: ChipThemeData(
          backgroundColor: NeonColors.bgElevated,
          selectedColor: NeonColors.cyanGlow,
          disabledColor: NeonColors.bgCard,
          side: const BorderSide(color: NeonColors.border),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
          labelStyle: _inter(fontSize: 11, weight: FontWeight.w500),
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        ),
      );

  // ── Agent color lookup ─────────────────────────────────────────────────
  static Color agentColor(String agentId) {
    switch (agentId.toLowerCase()) {
      case 'neo':      return NeonColors.agentNeo;
      case 'matrix':   return NeonColors.agentMatrix;
      case 'smith':    return NeonColors.agentSmith;
      case 'pythia':   return NeonColors.agentPythia;
      case 'anderson': return NeonColors.agentAnderson;
      case 'tanker':   return NeonColors.agentTanker;
      case 'operator': return NeonColors.agentOperator;
      case 'morpheus': return NeonColors.agentMorpheus;
      default:         return NeonColors.textSecondary;
    }
  }
}

// ── Decoration helpers ─────────────────────────────────────────────────────────

BoxDecoration neonCardDecoration({
  Color glowColor = NeonColors.cyan,
  double glowRadius = 6,
  double borderWidth = 1,
  bool glow = false,
}) =>
    BoxDecoration(
      color: NeonColors.bgCard,
      borderRadius: BorderRadius.circular(8),
      border: Border.all(
        color: glow ? glowColor.withOpacity(0.6) : NeonColors.border,
        width: borderWidth,
      ),
      boxShadow: glow
          ? [BoxShadow(color: glowColor.withOpacity(0.15), blurRadius: glowRadius)]
          : null,
    );

BoxDecoration sparkCardDecoration({bool highlighted = false}) => BoxDecoration(
      color: NeonColors.bgCard,
      borderRadius: BorderRadius.circular(8),
      border: Border.all(
        color: highlighted ? NeonColors.cyan.withOpacity(0.4) : NeonColors.border,
        width: 1,
      ),
    );

BoxDecoration neonButtonDecoration({Color color = NeonColors.cyan}) =>
    BoxDecoration(
      color: color.withOpacity(0.08),
      borderRadius: BorderRadius.circular(6),
      border: Border.all(color: color.withOpacity(0.6), width: 1),
    );

// ── Status badge ───────────────────────────────────────────────────────────────

Color statusColor(String status) {
  switch (status.toLowerCase()) {
    case 'running': case 'active': case 'online': return NeonColors.statusRunning;
    case 'done': case 'completed': case 'success': return NeonColors.statusDone;
    case 'error': case 'failed':  return NeonColors.statusFailed;
    case 'pending': case 'queued': return NeonColors.statusPending;
    case 'idle':    return NeonColors.statusIdle;
    default:        return NeonColors.textMuted;
  }
}

// ── NeonText widget ────────────────────────────────────────────────────────────

class NeonText extends StatelessWidget {
  final String text;
  final Color color;
  final double fontSize;
  final FontWeight fontWeight;
  final String? fontFamily;  // 'Orbitron' | 'JetBrainsMono' | null
  final double glowRadius;
  final TextAlign? textAlign;

  const NeonText(
    this.text, {
    super.key,
    this.color      = NeonColors.cyan,
    this.fontSize   = 14,
    this.fontWeight = FontWeight.normal,
    this.fontFamily,
    this.glowRadius = 6,
    this.textAlign,
  });

  @override
  Widget build(BuildContext context) {
    final useOrbitron = fontFamily == 'Orbitron' || fontFamily == null;
    final style = useOrbitron
        ? GoogleFonts.orbitron(
            color: color, fontSize: fontSize, fontWeight: fontWeight,
            shadows: [
              Shadow(color: color.withOpacity(0.7), blurRadius: glowRadius),
              Shadow(color: color.withOpacity(0.3), blurRadius: glowRadius * 2),
            ],
          )
        : GoogleFonts.jetBrainsMono(
            color: color, fontSize: fontSize, fontWeight: fontWeight,
            shadows: [Shadow(color: color.withOpacity(0.5), blurRadius: glowRadius)],
          );
    return Text(text, textAlign: textAlign, style: style);
  }
}

// ── SparkStatusDot ────────────────────────────────────────────────────────────

class SparkStatusDot extends StatelessWidget {
  final String status;
  final double size;

  const SparkStatusDot(this.status, {super.key, this.size = 8});

  @override
  Widget build(BuildContext context) {
    final color = statusColor(status);
    final isPulsing = status.toLowerCase() == 'running' || status.toLowerCase() == 'active';
    return Container(
      width: size, height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: color,
        boxShadow: isPulsing
            ? [BoxShadow(color: color.withOpacity(0.6), blurRadius: 4, spreadRadius: 1)]
            : null,
      ),
    );
  }
}

// ── SparkBadge ────────────────────────────────────────────────────────────────

class SparkBadge extends StatelessWidget {
  final String label;
  final Color color;
  final Color? bgColor;

  const SparkBadge(this.label, {
    super.key,
    this.color = NeonColors.cyan,
    this.bgColor,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: bgColor ?? color.withOpacity(0.12),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: color.withOpacity(0.4), width: 1),
      ),
      child: Text(
        label.toUpperCase(),
        style: GoogleFonts.jetBrainsMono(
          fontSize: 9, fontWeight: FontWeight.w700,
          color: color, letterSpacing: 0.5,
        ),
      ),
    );
  }
}

// ── SparkSectionHeader ────────────────────────────────────────────────────────

class SparkSectionHeader extends StatelessWidget {
  final String title;
  final Widget? trailing;
  final Color? accentColor;

  const SparkSectionHeader(this.title, {super.key, this.trailing, this.accentColor});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 3, height: 14,
          margin: const EdgeInsets.only(right: 8),
          decoration: BoxDecoration(
            color: accentColor ?? NeonColors.cyan,
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        Text(
          title.toUpperCase(),
          style: GoogleFonts.orbitron(
            fontSize: 11, fontWeight: FontWeight.w700,
            color: NeonColors.textSecondary, letterSpacing: 1.5,
          ),
        ),
        const Spacer(),
        if (trailing != null) trailing!,
      ],
    );
  }
}
