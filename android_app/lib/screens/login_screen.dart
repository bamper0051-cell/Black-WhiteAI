// login_screen.dart — Neon login / register screen

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../theme/neon_theme.dart';
import '../animations/neon_animations.dart';
import '../services/auth_service.dart';
import '../widgets/neon_text_field.dart';
import 'main_shell.dart';

class LoginScreen extends StatefulWidget {
  final String baseUrl;
  const LoginScreen({super.key, required this.baseUrl});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen>
    with SingleTickerProviderStateMixin {
  final _userCtrl = TextEditingController();
  final _passCtrl = TextEditingController();
  final _pass2Ctrl = TextEditingController();
  bool _isRegister = false;
  bool _loading = false;
  bool _obscurePass = true;
  String? _error;
  late AnimationController _glowCtrl;

  @override
  void initState() {
    super.initState();
    _glowCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2000),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _glowCtrl.dispose();
    _userCtrl.dispose();
    _passCtrl.dispose();
    _pass2Ctrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final username = _userCtrl.text.trim();
    final password = _passCtrl.text;

    if (username.isEmpty || password.isEmpty) {
      setState(() => _error = 'Заполни все поля');
      return;
    }
    if (_isRegister && _passCtrl.text != _pass2Ctrl.text) {
      setState(() => _error = 'Пароли не совпадают');
      return;
    }
    if (_isRegister && password.length < 6) {
      setState(() => _error = 'Пароль минимум 6 символов');
      return;
    }

    setState(() { _loading = true; _error = null; });

    final auth = AuthService(baseUrl: widget.baseUrl);
    final result = _isRegister
        ? await auth.register(username, password)
        : await auth.login(username, password);

    if (!mounted) return;

    if (result.ok) {
      await AuthService.saveSession(
        baseUrl: widget.baseUrl,
        token: result.token!,
        username: result.username!,
        role: result.role ?? 'user',
      );
      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        NeonPageRoute(child: const MainShell()),
      );
    } else {
      setState(() {
        _error = result.error;
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: NeonColors.bgDeep,
      body: Stack(
        children: [
          // Animated grid background
          CustomPaint(
            painter: _LoginBgPainter(glowCtrl: _glowCtrl),
            size: MediaQuery.of(context).size,
          ),

          SafeArea(
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: Column(
                children: [
                  const SizedBox(height: 48),

                  // Logo
                  AnimatedBuilder(
                    animation: _glowCtrl,
                    builder: (_, __) => Column(
                      children: [
                        Container(
                          decoration: BoxDecoration(
                            boxShadow: [
                              BoxShadow(
                                color: NeonColors.cyan
                                    .withOpacity(0.2 + 0.15 * _glowCtrl.value),
                                blurRadius: 40,
                                spreadRadius: 5,
                              ),
                            ],
                          ),
                          child: const NeonText(
                            'BLACK\nBUGS AI',
                            color: NeonColors.cyan,
                            fontSize: 36,
                            fontWeight: FontWeight.w700,
                            fontFamily: 'Orbitron',
                            glowRadius: 16,
                            textAlign: TextAlign.center,
                          ),
                        ),
                        const SizedBox(height: 6),
                        NeonText(
                          _isRegister ? 'СОЗДАТЬ АККАУНТ' : 'ВОЙТИ В СИСТЕМУ',
                          color: NeonColors.purple,
                          fontSize: 10,
                          fontFamily: 'Orbitron',
                          glowRadius: 4,
                        ),
                      ],
                    ),
                  ),

                  const SizedBox(height: 40),

                  // Server indicator
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: NeonColors.bgCard,
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: NeonColors.cyanGlow),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        PulseGlow(
                          color: NeonColors.green,
                          child: Container(
                            width: 6, height: 6,
                            decoration: const BoxDecoration(
                              color: NeonColors.green,
                              shape: BoxShape.circle,
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Text(
                          widget.baseUrl,
                          style: const TextStyle(
                            color: NeonColors.textSecondary,
                            fontFamily: 'JetBrainsMono',
                            fontSize: 10,
                          ),
                        ),
                      ],
                    ),
                  ).animate().fadeIn(delay: 200.ms),

                  const SizedBox(height: 32),

                  // Form card
                  Container(
                    padding: const EdgeInsets.all(24),
                    decoration: neonCardDecoration(
                      glowColor: _isRegister ? NeonColors.purple : NeonColors.cyan,
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        NeonText(
                          _isRegister ? '> РЕГИСТРАЦИЯ' : '> ВХОД',
                          color: _isRegister ? NeonColors.purple : NeonColors.cyan,
                          fontSize: 12,
                          fontFamily: 'Orbitron',
                          glowRadius: 4,
                        ),
                        const SizedBox(height: 20),

                        NeonTextField(
                          controller: _userCtrl,
                          label: 'ЛОГИН',
                          hint: 'username',
                          prefixIcon: Icons.person_outline,
                          color: _isRegister ? NeonColors.purple : NeonColors.cyan,
                          onChanged: (_) => setState(() => _error = null),
                        ),
                        const SizedBox(height: 14),

                        NeonTextField(
                          controller: _passCtrl,
                          label: 'ПАРОЛЬ',
                          hint: '••••••••',
                          prefixIcon: Icons.lock_outline,
                          obscureText: _obscurePass,
                          color: _isRegister ? NeonColors.purple : NeonColors.cyan,
                          suffixIcon: IconButton(
                            icon: Icon(
                              _obscurePass
                                  ? Icons.visibility_outlined
                                  : Icons.visibility_off_outlined,
                              color: NeonColors.textSecondary,
                              size: 18,
                            ),
                            onPressed: () =>
                                setState(() => _obscurePass = !_obscurePass),
                          ),
                          onChanged: (_) => setState(() => _error = null),
                        ),

                        if (_isRegister) ...[
                          const SizedBox(height: 14),
                          NeonTextField(
                            controller: _pass2Ctrl,
                            label: 'ПОДТВЕРДИ ПАРОЛЬ',
                            hint: '••••••••',
                            prefixIcon: Icons.lock_outline,
                            obscureText: _obscurePass,
                            color: NeonColors.purple,
                            onChanged: (_) => setState(() => _error = null),
                          ),
                        ],

                        if (_error != null) ...[
                          const SizedBox(height: 12),
                          Container(
                            padding: const EdgeInsets.all(10),
                            decoration: BoxDecoration(
                              color: NeonColors.pink.withOpacity(0.1),
                              borderRadius: BorderRadius.circular(6),
                              border: Border.all(
                                  color: NeonColors.pink.withOpacity(0.5)),
                            ),
                            child: Row(
                              children: [
                                const Icon(Icons.error_outline,
                                    color: NeonColors.pink, size: 14),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Text(
                                    _error!,
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
                        ],

                        const SizedBox(height: 24),

                        // Submit button
                        _loading
                            ? Center(
                                child: NeonLoadingIndicator(
                                  size: 36,
                                  color: _isRegister
                                      ? NeonColors.purple
                                      : NeonColors.cyan,
                                  label: _isRegister ? 'СОЗДАЁМ...' : 'ВХОДИМ...',
                                ),
                              )
                            : _NeonActionButton(
                                label: _isRegister ? 'СОЗДАТЬ АККАУНТ' : 'ВОЙТИ',
                                color: _isRegister
                                    ? NeonColors.purple
                                    : NeonColors.cyan,
                                icon: _isRegister
                                    ? Icons.person_add_outlined
                                    : Icons.login,
                                onTap: _submit,
                              ),
                      ],
                    ),
                  ).animate().fadeIn(delay: 300.ms, duration: 500.ms).slideY(begin: 0.1),

                  const SizedBox(height: 16),

                  // Toggle login/register
                  GestureDetector(
                    onTap: () => setState(() {
                      _isRegister = !_isRegister;
                      _error = null;
                      _pass2Ctrl.clear();
                    }),
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 20, vertical: 12),
                      decoration: BoxDecoration(
                        color: NeonColors.bgCard.withOpacity(0.5),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text(
                            _isRegister
                                ? 'Уже есть аккаунт? '
                                : 'Нет аккаунта? ',
                            style: const TextStyle(
                              color: NeonColors.textSecondary,
                              fontFamily: 'JetBrainsMono',
                              fontSize: 12,
                            ),
                          ),
                          NeonText(
                            _isRegister ? 'ВОЙТИ' : 'РЕГИСТРАЦИЯ',
                            color: _isRegister
                                ? NeonColors.cyan
                                : NeonColors.purple,
                            fontSize: 12,
                            fontFamily: 'Orbitron',
                            fontWeight: FontWeight.w700,
                            glowRadius: 4,
                          ),
                        ],
                      ),
                    ),
                  ).animate().fadeIn(delay: 500.ms),

                  const SizedBox(height: 12),

                  // Change server link
                  GestureDetector(
                    onTap: () => Navigator.of(context).pop(),
                    child: const Text(
                      '← Изменить сервер',
                      style: TextStyle(
                        color: NeonColors.textDisabled,
                        fontFamily: 'JetBrainsMono',
                        fontSize: 10,
                      ),
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
}

// ── Background painter ────────────────────────────────────────────────────────

class _LoginBgPainter extends CustomPainter {
  final AnimationController glowCtrl;
  _LoginBgPainter({required this.glowCtrl}) : super(repaint: glowCtrl);

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..strokeWidth = 1;

    // Grid
    paint.color = NeonColors.cyan.withOpacity(0.03 + 0.02 * glowCtrl.value);
    const step = 45.0;
    for (double x = 0; x < size.width; x += step) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), paint);
    }
    for (double y = 0; y < size.height; y += step) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), paint);
    }

    // Corner accent lines
    paint.color = NeonColors.cyan.withOpacity(0.15 + 0.1 * glowCtrl.value);
    paint.strokeWidth = 1.5;
    const len = 40.0;
    // Top-left
    canvas.drawLine(const Offset(24, 24), Offset(24 + len, 24), paint);
    canvas.drawLine(const Offset(24, 24), Offset(24, 24 + len), paint);
    // Top-right
    canvas.drawLine(Offset(size.width - 24, 24),
        Offset(size.width - 24 - len, 24), paint);
    canvas.drawLine(Offset(size.width - 24, 24),
        Offset(size.width - 24, 24 + len), paint);
    // Bottom-left
    canvas.drawLine(Offset(24, size.height - 24),
        Offset(24 + len, size.height - 24), paint);
    canvas.drawLine(Offset(24, size.height - 24),
        Offset(24, size.height - 24 - len), paint);
    // Bottom-right
    canvas.drawLine(Offset(size.width - 24, size.height - 24),
        Offset(size.width - 24 - len, size.height - 24), paint);
    canvas.drawLine(Offset(size.width - 24, size.height - 24),
        Offset(size.width - 24, size.height - 24 - len), paint);
  }

  @override
  bool shouldRepaint(_) => true;
}

// ── Neon action button ────────────────────────────────────────────────────────

class _NeonActionButton extends StatefulWidget {
  final String label;
  final Color color;
  final IconData icon;
  final VoidCallback onTap;

  const _NeonActionButton({
    required this.label,
    required this.color,
    required this.icon,
    required this.onTap,
  });

  @override
  State<_NeonActionButton> createState() => _NeonActionButtonState();
}

class _NeonActionButtonState extends State<_NeonActionButton> {
  bool _pressed = false;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTapDown: (_) => setState(() => _pressed = true),
      onTapUp: (_) { setState(() => _pressed = false); widget.onTap(); },
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
              spreadRadius: _pressed ? 2 : 0,
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
