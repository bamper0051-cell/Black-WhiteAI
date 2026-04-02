// setup_screen.dart — Server URL setup + auth mode selection

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../theme/neon_theme.dart';
import '../animations/neon_animations.dart';
import '../services/auth_service.dart';
import '../widgets/neon_text_field.dart';
import 'login_screen.dart';
import 'main_shell.dart';

class SetupScreen extends StatefulWidget {
  const SetupScreen({super.key});

  @override
  State<SetupScreen> createState() => _SetupScreenState();
}

class _SetupScreenState extends State<SetupScreen>
    with SingleTickerProviderStateMixin {
  final _urlCtrl = TextEditingController(text: 'http://');
  final _tokenCtrl = TextEditingController();

  // Step 1 = enter URL, Step 2 = choose mode
  int _step = 1;
  bool _loading = false;
  bool _obscureToken = true;
  String? _error;
  late AnimationController _glowCtrl;

  @override
  void initState() {
    super.initState();
    _glowCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2000),
    )..repeat(reverse: true);
    _prefill();
  }

  Future<void> _prefill() async {
    final session = await AuthService.loadSession();
    if (session['base_url'] != null && session['base_url']!.isNotEmpty) {
      _urlCtrl.text = session['base_url']!;
    }
  }

  @override
  void dispose() {
    _glowCtrl.dispose();
    _urlCtrl.dispose();
    _tokenCtrl.dispose();
    super.dispose();
  }

  String get _cleanUrl =>
      _urlCtrl.text.trim().replaceAll(RegExp(r'/$'), '');

  Future<void> _pingAndNext() async {
    final url = _cleanUrl;
    if (url.isEmpty || url == 'http://' || url == 'https://') {
      setState(() => _error = 'Введи URL сервера');
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
    });

    final ok = await AuthService(baseUrl: url).ping();
    if (!mounted) return;

    if (!ok) {
      setState(() {
        _error = 'Сервер не отвечает. Проверь URL.';
        _loading = false;
      });
      return;
    }

    setState(() {
      _step = 2;
      _loading = false;
    });
  }

  Future<void> _connectWithToken() async {
    final token = _tokenCtrl.text.trim();
    if (token.isEmpty) {
      setState(() => _error = 'Введи токен');
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
    });

    final result = await AuthService(baseUrl: _cleanUrl).validateToken(token);
    if (!mounted) return;

    if (result.ok) {
      await AuthService.saveSession(
        baseUrl: _cleanUrl,
        token: token,
        username: result.username ?? 'admin',
        role: result.role ?? 'admin',
        authMode: 'token',
      );
      if (!mounted) return;
      Navigator.of(context).pushAndRemoveUntil(
        NeonPageRoute(child: const MainShell()),
        (_) => false,
      );
    } else {
      setState(() {
        _error = result.error;
        _loading = false;
      });
    }
  }

  void _goToLogin() {
    Navigator.of(context).push(
      NeonPageRoute(child: LoginScreen(baseUrl: _cleanUrl)),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: NeonColors.bgDeep,
      body: Stack(
        children: [
          // Animated background
          AnimatedBuilder(
            animation: _glowCtrl,
            builder: (_, __) => CustomPaint(
              painter: _SetupBgPainter(glow: _glowCtrl.value),
              size: MediaQuery.of(context).size,
            ),
          ),

          SafeArea(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24),
              child: Column(
                children: [
                  const SizedBox(height: 40),

                  // Logo
                  AnimatedBuilder(
                    animation: _glowCtrl,
                    builder: (_, __) => Container(
                      decoration: BoxDecoration(
                        boxShadow: [
                          BoxShadow(
                            color: NeonColors.cyan
                                .withOpacity(0.15 + 0.15 * _glowCtrl.value),
                            blurRadius: 40,
                            spreadRadius: 5,
                          ),
                        ],
                      ),
                      child: const NeonText(
                        'BLACKBUGS AI',
                        color: NeonColors.cyan,
                        fontSize: 28,
                        fontWeight: FontWeight.w700,
                        fontFamily: 'Orbitron',
                        glowRadius: 16,
                      ),
                    ),
                  ).animate().fadeIn(duration: 600.ms).slideY(begin: -0.3),

                  const SizedBox(height: 8),

                  NeonText(
                    _step == 1 ? 'ПОДКЛЮЧЕНИЕ К СЕРВЕРУ' : 'ВЫБЕРИ РЕЖИМ ВХОДА',
                    color: NeonColors.purple,
                    fontSize: 10,
                    fontFamily: 'Orbitron',
                    glowRadius: 5,
                  ).animate(key: ValueKey(_step)).fadeIn(delay: 200.ms),

                  const SizedBox(height: 40),

                  // Step indicator
                  _StepIndicator(current: _step),

                  const SizedBox(height: 32),

                  // ── Step 1: URL input ────────────────────────────────────
                  if (_step == 1)
                    Container(
                      padding: const EdgeInsets.all(24),
                      decoration: neonCardDecoration(glowColor: NeonColors.cyan),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const NeonText('> АДРЕС СЕРВЕРА',
                              color: NeonColors.cyan,
                              fontSize: 11, fontFamily: 'Orbitron', glowRadius: 4),
                          const SizedBox(height: 20),

                          NeonTextField(
                            controller: _urlCtrl,
                            label: 'SERVER URL',
                            hint: 'http://192.168.1.1:8080',
                            prefixIcon: Icons.dns_outlined,
                            keyboardType: TextInputType.url,
                            onChanged: (_) => setState(() => _error = null),
                          ),

                          _ErrorBox(error: _error),

                          const SizedBox(height: 20),

                          _loading
                              ? const Center(
                                  child: NeonLoadingIndicator(
                                      size: 36, label: 'ПРОВЕРЯЕМ...'))
                              : _BigButton(
                                  label: 'ДАЛЕЕ',
                                  icon: Icons.arrow_forward,
                                  color: NeonColors.cyan,
                                  onTap: _pingAndNext,
                                ),
                        ],
                      ),
                    ).animate().fadeIn(delay: 400.ms).slideY(begin: 0.2),

                  // ── Step 2: Mode selection ───────────────────────────────
                  if (_step == 2) ...[
                    // Server URL display
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 14, vertical: 8),
                      decoration: BoxDecoration(
                        color: NeonColors.bgCard,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: NeonColors.cyanGlow),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(Icons.check_circle_outline,
                              color: NeonColors.green, size: 14),
                          const SizedBox(width: 8),
                          Text(
                            _cleanUrl,
                            style: const TextStyle(
                              color: NeonColors.textSecondary,
                              fontFamily: 'JetBrainsMono',
                              fontSize: 11,
                            ),
                          ),
                          const SizedBox(width: 8),
                          GestureDetector(
                            onTap: () => setState(() {
                              _step = 1;
                              _error = null;
                            }),
                            child: const Icon(Icons.edit_outlined,
                                color: NeonColors.textDisabled, size: 14),
                          ),
                        ],
                      ),
                    ).animate().fadeIn(duration: 300.ms),

                    const SizedBox(height: 24),

                    // Option A — Login/Register
                    _ModeCard(
                      icon: Icons.person_outlined,
                      color: NeonColors.purple,
                      title: 'ЛОГИН / ПАРОЛЬ',
                      subtitle: 'Вход или регистрация через сервер.\nДля новых пользователей.',
                      onTap: _goToLogin,
                    ).animate().fadeIn(delay: 100.ms).slideX(begin: -0.1),

                    const SizedBox(height: 14),

                    // Option B — Token
                    _TokenModeCard(
                      tokenCtrl: _tokenCtrl,
                      obscure: _obscureToken,
                      onToggleObscure: () =>
                          setState(() => _obscureToken = !_obscureToken),
                      error: _error,
                      loading: _loading,
                      onConnect: _connectWithToken,
                      onChanged: (_) => setState(() => _error = null),
                    ).animate().fadeIn(delay: 200.ms).slideX(begin: 0.1),
                  ],

                  const SizedBox(height: 24),

                  // Quick start hints
                  Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: NeonColors.bgCard.withOpacity(0.4),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: NeonColors.purpleGlow),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const NeonText('> QUICK START',
                            color: NeonColors.purple,
                            fontSize: 9, fontFamily: 'Orbitron'),
                        const SizedBox(height: 8),
                        _hint('1', 'Запусти: docker-compose up -d'),
                        _hint('2', 'URL: http://<ip>:8080'),
                        _hint('3', 'Токен из .env → ADMIN_TOKEN'),
                      ],
                    ),
                  ).animate().fadeIn(delay: 600.ms),

                  const SizedBox(height: 24),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _hint(String n, String text) => Padding(
    padding: const EdgeInsets.only(bottom: 5),
    child: Row(
      children: [
        Container(
          width: 18, height: 18,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            border: Border.all(color: NeonColors.purple.withOpacity(0.6)),
            borderRadius: BorderRadius.circular(4),
          ),
          child: Text(n,
              style: const TextStyle(
                  color: NeonColors.purple,
                  fontSize: 10, fontFamily: 'Orbitron',
                  fontWeight: FontWeight.w700)),
        ),
        const SizedBox(width: 10),
        Text(text,
            style: const TextStyle(
                color: NeonColors.textSecondary,
                fontSize: 10, fontFamily: 'JetBrainsMono')),
      ],
    ),
  );
}

// ── Step indicator ────────────────────────────────────────────────────────────

class _StepIndicator extends StatelessWidget {
  final int current;
  const _StepIndicator({required this.current});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        _dot(1, current >= 1),
        Container(
          width: 40, height: 1,
          color: current >= 2 ? NeonColors.cyan : NeonColors.bgCard,
        ),
        _dot(2, current >= 2),
      ],
    );
  }

  Widget _dot(int n, bool active) => Container(
    width: 28, height: 28,
    alignment: Alignment.center,
    decoration: BoxDecoration(
      color: active ? NeonColors.cyan.withOpacity(0.15) : NeonColors.bgCard,
      shape: BoxShape.circle,
      border: Border.all(
        color: active ? NeonColors.cyan : NeonColors.textDisabled,
        width: 1.5,
      ),
      boxShadow: active
          ? [BoxShadow(
              color: NeonColors.cyan.withOpacity(0.4),
              blurRadius: 8, spreadRadius: 1)]
          : [],
    ),
    child: Text(
      '$n',
      style: TextStyle(
        color: active ? NeonColors.cyan : NeonColors.textDisabled,
        fontFamily: 'Orbitron',
        fontSize: 11,
        fontWeight: FontWeight.w700,
      ),
    ),
  );
}

// ── Mode card — Login ─────────────────────────────────────────────────────────

class _ModeCard extends StatelessWidget {
  final IconData icon;
  final Color color;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  const _ModeCard({
    required this.icon,
    required this.color,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(18),
        decoration: neonCardDecoration(glowColor: color),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: color.withOpacity(0.1),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: color.withOpacity(0.4)),
              ),
              child: Icon(icon, color: color, size: 26),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  NeonText(title,
                      color: color,
                      fontSize: 12, fontFamily: 'Orbitron',
                      fontWeight: FontWeight.w700, glowRadius: 4),
                  const SizedBox(height: 4),
                  Text(subtitle,
                      style: const TextStyle(
                        color: NeonColors.textSecondary,
                        fontFamily: 'JetBrainsMono',
                        fontSize: 10,
                        height: 1.4,
                      )),
                ],
              ),
            ),
            Icon(Icons.arrow_forward_ios,
                color: color.withOpacity(0.6), size: 14),
          ],
        ),
      ),
    );
  }
}

// ── Mode card — Token ─────────────────────────────────────────────────────────

class _TokenModeCard extends StatelessWidget {
  final TextEditingController tokenCtrl;
  final bool obscure;
  final VoidCallback onToggleObscure;
  final String? error;
  final bool loading;
  final VoidCallback onConnect;
  final void Function(String) onChanged;

  const _TokenModeCard({
    required this.tokenCtrl,
    required this.obscure,
    required this.onToggleObscure,
    required this.error,
    required this.loading,
    required this.onConnect,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: neonCardDecoration(glowColor: NeonColors.green),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: NeonColors.green.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: NeonColors.green.withOpacity(0.4)),
                ),
                child: const Icon(Icons.key_outlined,
                    color: NeonColors.green, size: 26),
              ),
              const SizedBox(width: 16),
              const Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    NeonText('ADMIN ТОКЕН',
                        color: NeonColors.green,
                        fontSize: 12, fontFamily: 'Orbitron',
                        fontWeight: FontWeight.w700, glowRadius: 4),
                    SizedBox(height: 4),
                    Text('Прямой доступ без регистрации.\nТокен из .env ADMIN_TOKEN.',
                        style: TextStyle(
                          color: NeonColors.textSecondary,
                          fontFamily: 'JetBrainsMono',
                          fontSize: 10,
                          height: 1.4,
                        )),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),

          NeonTextField(
            controller: tokenCtrl,
            label: 'ADMIN TOKEN',
            hint: 'ваш-секретный-токен',
            prefixIcon: Icons.lock_outline,
            color: NeonColors.green,
            obscureText: obscure,
            suffixIcon: IconButton(
              icon: Icon(
                obscure
                    ? Icons.visibility_outlined
                    : Icons.visibility_off_outlined,
                color: NeonColors.textSecondary,
                size: 18,
              ),
              onPressed: onToggleObscure,
            ),
            onChanged: onChanged,
          ),

          _ErrorBox(error: error),

          const SizedBox(height: 14),

          loading
              ? const Center(
                  child: NeonLoadingIndicator(
                      size: 32,
                      color: NeonColors.green,
                      label: 'ПРОВЕРЯЕМ...'))
              : _BigButton(
                  label: 'ПОДКЛЮЧИТЬСЯ',
                  icon: Icons.link,
                  color: NeonColors.green,
                  onTap: onConnect,
                ),
        ],
      ),
    );
  }
}

// ── Shared helpers ────────────────────────────────────────────────────────────

class _ErrorBox extends StatelessWidget {
  final String? error;
  const _ErrorBox({this.error});

  @override
  Widget build(BuildContext context) {
    if (error == null) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: Container(
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: NeonColors.pink.withOpacity(0.1),
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: NeonColors.pink.withOpacity(0.5)),
        ),
        child: Row(
          children: [
            const Icon(Icons.error_outline, color: NeonColors.pink, size: 14),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                error!,
                style: const TextStyle(
                  color: NeonColors.pink,
                  fontSize: 11,
                  fontFamily: 'JetBrainsMono',
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _BigButton extends StatefulWidget {
  final String label;
  final IconData icon;
  final Color color;
  final VoidCallback onTap;

  const _BigButton({
    required this.label,
    required this.icon,
    required this.color,
    required this.onTap,
  });

  @override
  State<_BigButton> createState() => _BigButtonState();
}

class _BigButtonState extends State<_BigButton> {
  bool _pressed = false;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTapDown: (_) => setState(() => _pressed = true),
      onTapUp: (_) {
        setState(() => _pressed = false);
        widget.onTap();
      },
      onTapCancel: () => setState(() => _pressed = false),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 80),
        width: double.infinity,
        padding: const EdgeInsets.symmetric(vertical: 14),
        decoration: BoxDecoration(
          color: _pressed
              ? widget.color.withOpacity(0.25)
              : widget.color.withOpacity(0.12),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: widget.color, width: 1.5),
          boxShadow: [
            BoxShadow(
              color: widget.color.withOpacity(_pressed ? 0.6 : 0.3),
              blurRadius: _pressed ? 20 : 10,
            ),
          ],
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(widget.icon, color: widget.color, size: 18),
            const SizedBox(width: 10),
            Text(
              widget.label,
              style: TextStyle(
                color: widget.color,
                fontFamily: 'Orbitron',
                fontSize: 13,
                fontWeight: FontWeight.w700,
                letterSpacing: 2,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Background ────────────────────────────────────────────────────────────────

class _SetupBgPainter extends CustomPainter {
  final double glow;
  _SetupBgPainter({required this.glow});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = NeonColors.purple.withOpacity(0.02 + 0.01 * glow)
      ..strokeWidth = 1;
    const step = 50.0;
    for (double x = 0; x < size.width; x += step) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), paint);
    }
    for (double y = 0; y < size.height; y += step) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), paint);
    }
    // Accent lines
    paint
      ..color = NeonColors.cyan.withOpacity(0.08 + 0.06 * glow)
      ..strokeWidth = 1.5;
    const len = 36.0;
    const m = 20.0;
    canvas.drawLine(const Offset(m, m), Offset(m + len, m), paint);
    canvas.drawLine(const Offset(m, m), Offset(m, m + len), paint);
    canvas.drawLine(Offset(size.width - m, m),
        Offset(size.width - m - len, m), paint);
    canvas.drawLine(Offset(size.width - m, m),
        Offset(size.width - m, m + len), paint);
  }

  @override
  bool shouldRepaint(_SetupBgPainter old) => old.glow != glow;
}
