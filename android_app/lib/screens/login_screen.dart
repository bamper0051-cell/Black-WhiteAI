// login_screen.dart — Login screen with username + password

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../theme/neon_theme.dart';
import '../animations/neon_animations.dart';
import '../services/api_service.dart';
import '../widgets/neon_text_field.dart';
import 'register_screen.dart';
import 'main_shell.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _usernameCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  bool _loading = false;
  String? _error;
  bool _obscurePassword = true;

  @override
  void dispose() {
    _usernameCtrl.dispose();
    _passwordCtrl.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    final username = _usernameCtrl.text.trim();
    final password = _passwordCtrl.text.trim();

    if (username.isEmpty || password.isEmpty) {
      setState(() => _error = 'Заполни все поля');
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final prefs = await SharedPreferences.getInstance();
      final baseUrl = prefs.getString('base_url') ?? '';
      final adminToken = prefs.getString('admin_token') ?? '';
      final api = ApiService(baseUrl: baseUrl, adminToken: adminToken);

      final result = await api.login(username, password);

      await prefs.setString('app_token', result.token);
      await prefs.setString('app_username', result.username);

      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        NeonPageRoute(child: const MainShell()),
      );
    } on ApiException catch (e) {
      setState(() {
        _error = e.message;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = 'Ошибка: $e';
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
          CustomPaint(
            painter: _LoginBgPainter(),
            size: MediaQuery.of(context).size,
          ),
          SafeArea(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24),
              child: Column(
                children: [
                  const SizedBox(height: 48),

                  // Logo
                  NeonText(
                    'BLACKBUGS AI',
                    color: NeonColors.cyan,
                    fontSize: 28,
                    fontWeight: FontWeight.w700,
                    fontFamily: 'Orbitron',
                    glowRadius: 16,
                  ).animate().fadeIn(duration: 600.ms).slideY(begin: -0.3),

                  const SizedBox(height: 8),
                  NeonText(
                    'ВХОД В СИСТЕМУ',
                    color: NeonColors.purple,
                    fontSize: 11,
                    fontFamily: 'Orbitron',
                    glowRadius: 6,
                  ).animate().fadeIn(delay: 200.ms, duration: 600.ms),

                  const SizedBox(height: 48),

                  // Login card
                  Container(
                    padding: const EdgeInsets.all(24),
                    decoration: neonCardDecoration(glowColor: NeonColors.cyan),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        NeonText(
                          '> LOGIN',
                          color: NeonColors.cyan,
                          fontSize: 12,
                          fontFamily: 'Orbitron',
                          glowRadius: 4,
                        ),
                        const SizedBox(height: 20),

                        NeonTextField(
                          controller: _usernameCtrl,
                          label: 'ЛОГИН',
                          hint: 'username',
                          prefixIcon: Icons.person_outline,
                        ),
                        const SizedBox(height: 16),

                        NeonTextField(
                          controller: _passwordCtrl,
                          label: 'ПАРОЛЬ',
                          hint: '••••••••',
                          prefixIcon: Icons.lock_outline,
                          obscureText: _obscurePassword,
                          suffixIcon: IconButton(
                            icon: Icon(
                              _obscurePassword
                                  ? Icons.visibility_outlined
                                  : Icons.visibility_off_outlined,
                              color: NeonColors.textSecondary,
                              size: 18,
                            ),
                            onPressed: () => setState(
                                () => _obscurePassword = !_obscurePassword),
                          ),
                        ),

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
                                    color: NeonColors.pink, size: 16),
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

                        SizedBox(
                          width: double.infinity,
                          child: _loading
                              ? const Center(
                                  child: NeonLoadingIndicator(
                                    label: 'ВХОДИМ...',
                                    size: 40,
                                  ),
                                )
                              : _NeonButton(
                                  label: 'ВОЙТИ',
                                  icon: Icons.login,
                                  color: NeonColors.cyan,
                                  onTap: _login,
                                ),
                        ),
                      ],
                    ),
                  ).animate().fadeIn(delay: 400.ms, duration: 600.ms).slideY(begin: 0.2),

                  const SizedBox(height: 24),

                  // Register link
                  GestureDetector(
                    onTap: () => Navigator.of(context).pushReplacement(
                      NeonPageRoute(child: const RegisterScreen()),
                    ),
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          vertical: 14, horizontal: 24),
                      decoration: BoxDecoration(
                        color: NeonColors.bgCard.withOpacity(0.6),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                            color: NeonColors.purple.withOpacity(0.5)),
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(Icons.person_add_outlined,
                              color: NeonColors.purple, size: 16),
                          const SizedBox(width: 8),
                          NeonText(
                            'НЕТ АККАУНТА? РЕГИСТРАЦИЯ',
                            color: NeonColors.purple,
                            fontSize: 11,
                            fontFamily: 'Orbitron',
                            fontWeight: FontWeight.w700,
                          ),
                        ],
                      ),
                    ),
                  ).animate().fadeIn(delay: 600.ms, duration: 600.ms),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ─── Background painter ────────────────────────────────────────────────────────

class _LoginBgPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = NeonColors.cyan.withOpacity(0.03)
      ..strokeWidth = 1;
    const step = 50.0;
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

// ─── Neon button ──────────────────────────────────────────────────────────────

class _NeonButton extends StatefulWidget {
  final String label;
  final IconData icon;
  final Color color;
  final VoidCallback onTap;

  const _NeonButton({
    required this.label,
    required this.icon,
    required this.color,
    required this.onTap,
  });

  @override
  State<_NeonButton> createState() => _NeonButtonState();
}

class _NeonButtonState extends State<_NeonButton> {
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
        duration: const Duration(milliseconds: 100),
        padding: const EdgeInsets.symmetric(vertical: 14),
        decoration: BoxDecoration(
          color: _pressed
              ? widget.color.withOpacity(0.2)
              : widget.color.withOpacity(0.1),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: widget.color, width: 1.5),
          boxShadow: [
            BoxShadow(
              color: widget.color.withOpacity(_pressed ? 0.5 : 0.3),
              blurRadius: _pressed ? 16 : 8,
              spreadRadius: _pressed ? 2 : 0,
            ),
          ],
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(widget.icon, color: widget.color, size: 18),
            const SizedBox(width: 8),
            Text(
              widget.label,
              style: TextStyle(
                color: widget.color,
                fontFamily: 'Orbitron',
                fontSize: 11,
                fontWeight: FontWeight.w700,
                letterSpacing: 1.5,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
