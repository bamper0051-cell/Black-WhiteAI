import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'neon_theme.dart';

/// Pulsating neon glow container
class NeonGlowContainer extends StatelessWidget {
  final Widget child;
  final Color glowColor;
  final double glowRadius;
  final double borderWidth;
  final BorderRadius? borderRadius;
  final bool animate;
  final Duration duration;

  const NeonGlowContainer({
    super.key,
    required this.child,
    this.glowColor = NeonColors.cyan,
    this.glowRadius = 12.0,
    this.borderWidth = 1.5,
    this.borderRadius,
    this.animate = true,
    this.duration = const Duration(seconds: 2),
  });

  @override
  Widget build(BuildContext context) {
    final container = Container(
      decoration: BoxDecoration(
        color: NeonColors.bgCard,
        borderRadius: borderRadius ?? BorderRadius.circular(12),
        border: Border.all(
          color: glowColor,
          width: borderWidth,
        ),
        boxShadow: [
          BoxShadow(
            color: glowColor.withOpacity(0.5),
            blurRadius: glowRadius,
            spreadRadius: 2,
          ),
          BoxShadow(
            color: glowColor.withOpacity(0.3),
            blurRadius: glowRadius * 2,
            spreadRadius: 4,
          ),
        ],
      ),
      child: child,
    );

    if (animate) {
      return container
          .animate(onPlay: (controller) => controller.repeat())
          .shimmer(
            duration: duration,
            color: glowColor.withOpacity(0.3),
          )
          .then()
          .animate(onPlay: (controller) => controller.repeat())
          .boxShadow(
            duration: duration,
            begin: BoxShadow(
              color: glowColor.withOpacity(0.3),
              blurRadius: glowRadius,
              spreadRadius: 0,
            ),
            end: BoxShadow(
              color: glowColor.withOpacity(0.6),
              blurRadius: glowRadius * 1.5,
              spreadRadius: 2,
            ),
          );
    }

    return container;
  }
}

/// Animated neon text with pulsating glow
class AnimatedNeonText extends StatelessWidget {
  final String text;
  final Color color;
  final double fontSize;
  final FontWeight fontWeight;
  final String? fontFamily;
  final TextAlign? textAlign;
  final Duration duration;

  const AnimatedNeonText(
    this.text, {
    super.key,
    this.color = NeonColors.cyan,
    this.fontSize = 14,
    this.fontWeight = FontWeight.normal,
    this.fontFamily,
    this.textAlign,
    this.duration = const Duration(seconds: 2),
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
            blurRadius: 8,
          ),
          Shadow(
            color: color.withOpacity(0.4),
            blurRadius: 16,
          ),
        ],
      ),
    )
        .animate(onPlay: (controller) => controller.repeat(reverse: true))
        .shimmer(
          duration: duration,
          color: color.withOpacity(0.5),
        );
  }
}

/// Neon border with animated glow
class NeonBorder extends StatelessWidget {
  final Widget child;
  final Color color;
  final double borderWidth;
  final BorderRadius? borderRadius;
  final EdgeInsetsGeometry padding;

  const NeonBorder({
    super.key,
    required this.child,
    this.color = NeonColors.cyan,
    this.borderWidth = 2.0,
    this.borderRadius,
    this.padding = const EdgeInsets.all(12),
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        borderRadius: borderRadius ?? BorderRadius.circular(8),
        border: Border.all(color: color, width: borderWidth),
        boxShadow: [
          BoxShadow(
            color: color.withOpacity(0.5),
            blurRadius: 12,
            spreadRadius: 0,
          ),
        ],
      ),
      child: child,
    )
        .animate(onPlay: (controller) => controller.repeat())
        .boxShadow(
          duration: const Duration(seconds: 2),
          begin: BoxShadow(
            color: color.withOpacity(0.3),
            blurRadius: 8,
            spreadRadius: 0,
          ),
          end: BoxShadow(
            color: color.withOpacity(0.7),
            blurRadius: 16,
            spreadRadius: 2,
          ),
        );
  }
}

/// Neon button with glow effect
class NeonButton extends StatelessWidget {
  final String text;
  final VoidCallback? onPressed;
  final Color color;
  final IconData? icon;
  final bool loading;

  const NeonButton({
    super.key,
    required this.text,
    required this.onPressed,
    this.color = NeonColors.cyan,
    this.icon,
    this.loading = false,
  });

  @override
  Widget build(BuildContext context) {
    Widget buttonChild = Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        if (loading)
          SizedBox(
            width: 16,
            height: 16,
            child: CircularProgressIndicator(
              strokeWidth: 2,
              valueColor: AlwaysStoppedAnimation<Color>(color),
            ),
          )
        else if (icon != null)
          Icon(icon, size: 18, color: color),
        if ((icon != null || loading) && text.isNotEmpty) const SizedBox(width: 8),
        if (text.isNotEmpty)
          Text(
            text,
            style: TextStyle(
              fontFamily: 'Orbitron',
              fontSize: 12,
              fontWeight: FontWeight.w700,
              letterSpacing: 1.5,
              color: color,
            ),
          ),
      ],
    );

    return InkWell(
      onTap: loading ? null : onPressed,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
        decoration: BoxDecoration(
          color: color.withOpacity(0.1),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: color, width: 1.5),
          boxShadow: [
            BoxShadow(
              color: color.withOpacity(0.4),
              blurRadius: 8,
              spreadRadius: 0,
            ),
          ],
        ),
        child: buttonChild,
      ),
    ).animate(target: loading ? 1 : 0).shimmer(duration: 1.seconds, color: color.withOpacity(0.5));
  }
}

/// Neon loading indicator
class NeonLoadingIndicator extends StatelessWidget {
  final Color color;
  final double size;

  const NeonLoadingIndicator({
    super.key,
    this.color = NeonColors.cyan,
    this.size = 40.0,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: CircularProgressIndicator(
        strokeWidth: 3,
        valueColor: AlwaysStoppedAnimation<Color>(color),
      ),
    )
        .animate(onPlay: (controller) => controller.repeat())
        .rotate(duration: const Duration(seconds: 2))
        .then()
        .animate(onPlay: (controller) => controller.repeat())
        .shimmer(
          duration: const Duration(seconds: 1),
          color: color.withOpacity(0.5),
        );
  }
}

/// Status indicator with color-coded neon glow
class NeonStatusIndicator extends StatelessWidget {
  final String status;
  final double size;

  const NeonStatusIndicator({
    super.key,
    required this.status,
    this.size = 12.0,
  });

  Color _getStatusColor() {
    switch (status.toLowerCase()) {
      case 'online':
      case 'active':
      case 'success':
      case 'done':
        return NeonColors.green;
      case 'offline':
      case 'error':
      case 'failed':
        return NeonColors.pink;
      case 'running':
      case 'pending':
        return NeonColors.cyan;
      case 'warning':
        return NeonColors.yellow;
      default:
        return NeonColors.textSecondary;
    }
  }

  @override
  Widget build(BuildContext context) {
    final color = _getStatusColor();

    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: color,
        boxShadow: [
          BoxShadow(
            color: color.withOpacity(0.6),
            blurRadius: size * 0.8,
            spreadRadius: size * 0.2,
          ),
        ],
      ),
    )
        .animate(onPlay: (controller) => controller.repeat())
        .fadeIn(duration: const Duration(milliseconds: 500))
        .then()
        .fadeOut(duration: const Duration(milliseconds: 500));
  }
}
