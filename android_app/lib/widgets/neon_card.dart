// neon_card.dart — Reusable neon card widget

import 'package:flutter/material.dart';
import '../theme/neon_theme.dart';

class NeonCard extends StatelessWidget {
  final Widget child;
  final Color        glowColor;
  final EdgeInsets   padding;
  final double       glowRadius;
  final VoidCallback? onTap;

  const NeonCard({
    super.key,
    required this.child,
    this.glowColor  = NeonColors.cyan,
    this.padding    = const EdgeInsets.all(14),
    this.glowRadius = 8,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final card = Container(
      width:     double.infinity,
      padding:   padding,
      decoration: neonCardDecoration(
          glowColor: glowColor, glowRadius: glowRadius),
      child: child,
    );
    return onTap != null
        ? GestureDetector(onTap: onTap, child: card)
        : card;
  }
}
