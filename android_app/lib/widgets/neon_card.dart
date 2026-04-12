// neon_card.dart — Reusable neon card widget

import 'package:flutter/material.dart';
import '../theme/neon_theme.dart';

class NeonCard extends StatelessWidget {
  final Widget child;
<<<<<<< HEAD
  final Color        glowColor;
  final EdgeInsets   padding;
  final double       glowRadius;
=======
  final Color glowColor;
  final EdgeInsets padding;
  final double glowRadius;
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
  final VoidCallback? onTap;

  const NeonCard({
    super.key,
    required this.child,
<<<<<<< HEAD
    this.glowColor  = NeonColors.cyan,
    this.padding    = const EdgeInsets.all(14),
=======
    this.glowColor = NeonColors.cyan,
    this.padding = const EdgeInsets.all(14),
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
    this.glowRadius = 8,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final card = Container(
<<<<<<< HEAD
      width:     double.infinity,
      padding:   padding,
      decoration: neonCardDecoration(
          glowColor: glowColor, glowRadius: glowRadius),
      child: child,
    );
    return onTap != null
        ? GestureDetector(onTap: onTap, child: card)
        : card;
=======
      width: double.infinity,
      padding: padding,
      decoration: neonCardDecoration(
        glowColor: glowColor,
        glowRadius: glowRadius,
      ),
      child: child,
    );

    if (onTap != null) {
      return GestureDetector(onTap: onTap, child: card);
    }
    return card;
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
  }
}
