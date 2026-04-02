// neon_animations.dart — Нeon animations library for BlackBugsAI

import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../theme/neon_theme.dart';

// ─── Splash / Boot Screen Animation ──────────────────────────────────────────

class NeonBootAnimation extends StatefulWidget {
  final VoidCallback onComplete;
  const NeonBootAnimation({super.key, required this.onComplete});

  @override
  State<NeonBootAnimation> createState() => _NeonBootAnimationState();
}

class _NeonBootAnimationState extends State<NeonBootAnimation>
    with TickerProviderStateMixin {
  late AnimationController _glowCtrl;
  late AnimationController _scanCtrl;
  late AnimationController _textCtrl;
  late Animation<double> _glowAnim;
  late Animation<double> _scanAnim;

  final List<String> _bootLines = [
    '> INITIALIZING BLACKBUGSAI...',
    '> LOADING AGENT CORE... [OK]',
    '> CONNECTING LLM ROUTER... [OK]',
    '> STARTING TASK QUEUE... [OK]',
    '> AGENT NEO: ONLINE',
    '> AGENT MATRIX: ONLINE',
    '> SYSTEM READY.',
  ];

  int _currentLine = 0;

  @override
  void initState() {
    super.initState();

    _glowCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat(reverse: true);

    _scanCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2000),
    )..repeat();

    _textCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 3500),
    );

    _glowAnim = Tween<double>(begin: 0.4, end: 1.0).animate(
      CurvedAnimation(parent: _glowCtrl, curve: Curves.easeInOut),
    );
    _scanAnim = Tween<double>(begin: -1.0, end: 2.0).animate(
      CurvedAnimation(parent: _scanCtrl, curve: Curves.linear),
    );
    _textCtrl.forward();

    // Progress through boot lines
    for (int i = 0; i < _bootLines.length; i++) {
      Future.delayed(Duration(milliseconds: 400 + i * 450), () {
        if (mounted) setState(() => _currentLine = i + 1);
      });
    }

    // Complete
    Future.delayed(const Duration(milliseconds: 3800), () {
      if (mounted) widget.onComplete();
    });
  }

  @override
  void dispose() {
    _glowCtrl.dispose();
    _scanCtrl.dispose();
    _textCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: NeonColors.bgDeep,
      body: Stack(
        children: [
          // Grid background
          CustomPaint(
            painter: _GridPainter(),
            size: MediaQuery.of(context).size,
          ),

          // Scan line
          AnimatedBuilder(
            animation: _scanAnim,
            builder: (context, _) {
              final y = _scanAnim.value * MediaQuery.of(context).size.height;
              return Positioned(
                top: y,
                left: 0,
                right: 0,
                child: Container(
                  height: 2,
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [
                        Colors.transparent,
                        NeonColors.cyan.withOpacity(0.6),
                        NeonColors.cyan,
                        NeonColors.cyan.withOpacity(0.6),
                        Colors.transparent,
                      ],
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: NeonColors.cyan.withOpacity(0.4),
                        blurRadius: 12,
                        spreadRadius: 4,
                      ),
                    ],
                  ),
                ),
              );
            },
          ),

          // Content
          Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                // Logo with glow
                AnimatedBuilder(
                  animation: _glowAnim,
                  builder: (context, _) {
                    return Container(
                      decoration: BoxDecoration(
                        boxShadow: [
                          BoxShadow(
                            color: NeonColors.cyan
                                .withOpacity(0.3 * _glowAnim.value),
                            blurRadius: 40,
                            spreadRadius: 10,
                          ),
                          BoxShadow(
                            color: NeonColors.purple
                                .withOpacity(0.2 * _glowAnim.value),
                            blurRadius: 60,
                            spreadRadius: 5,
                          ),
                        ],
                      ),
                      child: NeonText(
                        'BLACK\nBUGS\nAI',
                        color: NeonColors.cyan,
                        fontSize: 48,
                        fontWeight: FontWeight.w700,
                        fontFamily: 'Orbitron',
                        glowRadius: 20 * _glowAnim.value,
                        textAlign: TextAlign.center,
                      ),
                    );
                  },
                ),
                const SizedBox(height: 8),
                NeonText(
                  'MULTI-AGENT PLATFORM',
                  color: NeonColors.purple,
                  fontSize: 11,
                  fontFamily: 'Orbitron',
                  glowRadius: 6,
                ),

                const SizedBox(height: 48),

                // Boot log
                Container(
                  width: 320,
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: NeonColors.bgCard.withOpacity(0.8),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: NeonColors.cyanGlow),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: List.generate(_bootLines.length, (i) {
                      final visible = i < _currentLine;
                      return AnimatedOpacity(
                        opacity: visible ? 1.0 : 0.0,
                        duration: const Duration(milliseconds: 200),
                        child: Padding(
                          padding: const EdgeInsets.only(bottom: 4),
                          child: Text(
                            _bootLines[i],
                            style: TextStyle(
                              fontFamily: 'JetBrainsMono',
                              fontSize: 10,
                              color: _bootLines[i].contains('[OK]')
                                  ? NeonColors.green
                                  : _bootLines[i].contains('ONLINE')
                                      ? NeonColors.cyan
                                      : _bootLines[i].contains('READY')
                                          ? NeonColors.yellow
                                          : NeonColors.textSecondary,
                            ),
                          ),
                        ),
                      );
                    }),
                  ),
                ),

                const SizedBox(height: 32),

                // Progress bar
                SizedBox(
                  width: 320,
                  child: AnimatedBuilder(
                    animation: _textCtrl,
                    builder: (context, _) {
                      return LinearProgressIndicator(
                        value: _currentLine / _bootLines.length,
                        backgroundColor: NeonColors.bgCard,
                        valueColor: const AlwaysStoppedAnimation(NeonColors.cyan),
                        minHeight: 2,
                      );
                    },
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ─── Grid background painter ──────────────────────────────────────────────────

class _GridPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = NeonColors.cyan.withOpacity(0.04)
      ..strokeWidth = 1;

    const step = 40.0;
    for (double x = 0; x < size.width; x += step) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), paint);
    }
    for (double y = 0; y < size.height; y += step) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), paint);
    }
  }

  @override
  bool shouldRepaint(_) => false;
}

// ─── Neon Loading Indicator ───────────────────────────────────────────────────

class NeonLoadingIndicator extends StatefulWidget {
  final Color color;
  final double size;
  final String? label;

  const NeonLoadingIndicator({
    super.key,
    this.color = NeonColors.cyan,
    this.size = 48,
    this.label,
  });

  @override
  State<NeonLoadingIndicator> createState() => _NeonLoadingIndicatorState();
}

class _NeonLoadingIndicatorState extends State<NeonLoadingIndicator>
    with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat();
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        AnimatedBuilder(
          animation: _ctrl,
          builder: (context, _) {
            return CustomPaint(
              size: Size(widget.size, widget.size),
              painter: _NeonSpinnerPainter(
                progress: _ctrl.value,
                color: widget.color,
              ),
            );
          },
        ),
        if (widget.label != null) ...[
          const SizedBox(height: 12),
          NeonText(
            widget.label!,
            color: widget.color,
            fontSize: 11,
            fontFamily: 'Orbitron',
          )
              .animate(onPlay: (c) => c.repeat(reverse: true))
              .fadeIn(duration: 600.ms)
              .fadeOut(delay: 400.ms, duration: 600.ms),
        ],
      ],
    );
  }
}

class _NeonSpinnerPainter extends CustomPainter {
  final double progress;
  final Color color;

  _NeonSpinnerPainter({required this.progress, required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2 - 4;

    // Background ring
    canvas.drawCircle(
      center,
      radius,
      Paint()
        ..color = color.withOpacity(0.1)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 3,
    );

    // Glow arc
    final sweepAngle = math.pi * 1.5;
    final startAngle = progress * math.pi * 2 - math.pi / 2;

    final glowPaint = Paint()
      ..color = color.withOpacity(0.3)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 6
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 6);

    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      startAngle,
      sweepAngle,
      false,
      glowPaint,
    );

    // Main arc
    final arcPaint = Paint()
      ..shader = SweepGradient(
        startAngle: startAngle,
        endAngle: startAngle + sweepAngle,
        colors: [color.withOpacity(0), color],
      ).createShader(Rect.fromCircle(center: center, radius: radius))
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3
      ..strokeCap = StrokeCap.round;

    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      startAngle,
      sweepAngle,
      false,
      arcPaint,
    );

    // Dot at end
    final dotAngle = startAngle + sweepAngle;
    final dotPos = Offset(
      center.dx + radius * math.cos(dotAngle),
      center.dy + radius * math.sin(dotAngle),
    );
    canvas.drawCircle(dotPos, 4, Paint()..color = color);
    canvas.drawCircle(
      dotPos,
      6,
      Paint()
        ..color = color.withOpacity(0.4)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 4),
    );
  }

  @override
  bool shouldRepaint(_NeonSpinnerPainter old) => old.progress != progress;
}

// ─── Page Transition: Neon Slide ─────────────────────────────────────────────

class NeonPageRoute<T> extends PageRouteBuilder<T> {
  final Widget child;

  NeonPageRoute({required this.child})
      : super(
          transitionDuration: const Duration(milliseconds: 400),
          reverseTransitionDuration: const Duration(milliseconds: 300),
          pageBuilder: (_, __, ___) => child,
          transitionsBuilder: (context, animation, secondaryAnimation, child) {
            return Stack(
              children: [
                // Outgoing page: fade out + slide left
                SlideTransition(
                  position: Tween<Offset>(
                    begin: Offset.zero,
                    end: const Offset(-0.3, 0),
                  ).animate(CurvedAnimation(
                    parent: secondaryAnimation,
                    curve: Curves.easeIn,
                  )),
                  child: FadeTransition(
                    opacity: Tween<double>(begin: 1, end: 0).animate(
                      CurvedAnimation(
                        parent: secondaryAnimation,
                        curve: Curves.easeIn,
                      ),
                    ),
                    child: child,
                  ),
                ),

                // Incoming page: slide from right + fade in
                SlideTransition(
                  position: Tween<Offset>(
                    begin: const Offset(1.0, 0),
                    end: Offset.zero,
                  ).animate(CurvedAnimation(
                    parent: animation,
                    curve: Curves.easeOutCubic,
                  )),
                  child: FadeTransition(
                    opacity: animation,
                    child: child,
                  ),
                ),

                // Neon scan line transition effect
                AnimatedBuilder(
                  animation: animation,
                  builder: (_, __) {
                    if (animation.value < 0.01 || animation.value > 0.99) {
                      return const SizedBox.shrink();
                    }
                    return Positioned(
                      left: MediaQuery.of(context).size.width *
                          (animation.value - 0.02),
                      top: 0,
                      bottom: 0,
                      width: 3,
                      child: Container(
                        decoration: BoxDecoration(
                          gradient: LinearGradient(
                            begin: Alignment.topCenter,
                            end: Alignment.bottomCenter,
                            colors: [
                              Colors.transparent,
                              NeonColors.cyan.withOpacity(0.8),
                              NeonColors.cyan,
                              NeonColors.cyan.withOpacity(0.8),
                              Colors.transparent,
                            ],
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: NeonColors.cyan.withOpacity(0.5),
                              blurRadius: 12,
                              spreadRadius: 4,
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
              ],
            );
          },
        );
}

// ─── Pulse Glow Animation ─────────────────────────────────────────────────────

class PulseGlow extends StatefulWidget {
  final Widget child;
  final Color color;
  final double minOpacity;
  final double maxOpacity;
  final Duration duration;

  const PulseGlow({
    super.key,
    required this.child,
    this.color = NeonColors.cyan,
    this.minOpacity = 0.2,
    this.maxOpacity = 0.8,
    this.duration = const Duration(milliseconds: 1500),
  });

  @override
  State<PulseGlow> createState() => _PulseGlowState();
}

class _PulseGlowState extends State<PulseGlow>
    with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  late Animation<double> _anim;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(vsync: this, duration: widget.duration)
      ..repeat(reverse: true);
    _anim = Tween<double>(
      begin: widget.minOpacity,
      end: widget.maxOpacity,
    ).animate(CurvedAnimation(parent: _ctrl, curve: Curves.easeInOut));
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _anim,
      builder: (_, child) => Container(
        decoration: BoxDecoration(
          boxShadow: [
            BoxShadow(
              color: widget.color.withOpacity(_anim.value * 0.5),
              blurRadius: 16,
              spreadRadius: 2,
            ),
          ],
        ),
        child: child,
      ),
      child: widget.child,
    );
  }
}

// ─── Typewriter text animation ────────────────────────────────────────────────

class NeonTypewriter extends StatefulWidget {
  final String text;
  final TextStyle? style;
  final Duration charDelay;

  const NeonTypewriter({
    super.key,
    required this.text,
    this.style,
    this.charDelay = const Duration(milliseconds: 40),
  });

  @override
  State<NeonTypewriter> createState() => _NeonTypewriterState();
}

class _NeonTypewriterState extends State<NeonTypewriter> {
  String _displayed = '';
  int _charIndex = 0;

  @override
  void initState() {
    super.initState();
    _type();
  }

  void _type() {
    if (_charIndex >= widget.text.length) return;
    Future.delayed(widget.charDelay, () {
      if (!mounted) return;
      setState(() {
        _displayed = widget.text.substring(0, ++_charIndex);
      });
      _type();
    });
  }

  @override
  Widget build(BuildContext context) {
    return RichText(
      text: TextSpan(
        text: _displayed,
        style: widget.style ??
            const TextStyle(
              fontFamily: 'JetBrainsMono',
              color: NeonColors.green,
              fontSize: 13,
            ),
        children: [
          // Cursor blink
          if (_charIndex < widget.text.length)
            WidgetSpan(
              child: _BlinkingCursor(
                color: widget.style?.color ?? NeonColors.green,
              ),
            ),
        ],
      ),
    );
  }
}

class _BlinkingCursor extends StatefulWidget {
  final Color color;
  const _BlinkingCursor({required this.color});

  @override
  State<_BlinkingCursor> createState() => _BlinkingCursorState();
}

class _BlinkingCursorState extends State<_BlinkingCursor>
    with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 530),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _ctrl,
      child: Container(
        width: 8,
        height: 14,
        color: widget.color,
        margin: const EdgeInsets.only(left: 2),
      ),
    );
  }
}
