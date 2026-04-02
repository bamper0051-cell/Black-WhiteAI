// register_screen.dart — Register new account with username and password

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../theme/neon_theme.dart';
import '../animations/neon_animations.dart';
import '../services/api_service.dart';
import '../widgets/neon_text_field.dart';
import 'main_shell.dart';
import 'login_screen.dart';

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _usernameCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  final _confirmCtrl = TextEditingController();
  bool _loading = false;
  String? _error;
  bool _obscurePassword = true;
  bool _obscureConfirm = true;

  Future<void> _register() async {
    final username = _usernameCtrl.text.trim();
    final password = _passwordCtrl.text.trim();
    final confirm = _confirmCtrl.text.trim();

    if (username.isEmpty || password.isEmpty || confirm.isEmpty) {
      setState(() => _error = 'Заполни все поля');
      return;
    }
    if (password != confirm) {
      setState(() => _error = 'Пароли не совпадают');
      return;
    }
    if (password.length < 6) {
      setState(() => _error = 'Пароль: минимум 6 символов');
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final prefs = await SharedPreferences.getInstance();
      final baseUrl = prefs.getString('base_url') ?? '';
      final api = ApiService(baseUrl: baseUrl, token: '');
      final result = await api.register(username, password);

      if (result['ok'] != true) {
        setState(() {
          _error = result['error'] ?? 'Ошибка регистрации';
          _loading = false;
        });
        return;
      }

      await prefs.setString('auth_token', result['token'] as String);
      await prefs.setString('username', username);

      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        NeonPageRoute(child: const MainShell()),
      );
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
            painter: _BgPainter(),
            size: MediaQuery.of(context).size,
          ),
          SafeArea(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24),
              child: Column(
                children: [
                  const SizedBox(height: 48),

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
                    'РЕГИСТРАЦИЯ',
                    color: NeonColors.green,
                    fontSize: 11,
                    fontFamily: 'Orbitron',
                    glowRadius: 6,
                  ).animate().fadeIn(delay: 200.ms, duration: 600.ms),

                  const SizedBox(height: 48),

                  Container(
                    padding: const EdgeInsets.all(24),
                    decoration: neonCardDecoration(glowColor: NeonColors.green),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        NeonText(
                          '> NEW ACCOUNT',
                          color: NeonColors.green,
                          fontSize: 12,
                          fontFamily: 'Orbitron',
                          glowRadius: 4,
                        ),
                        const SizedBox(height: 20),

                        NeonTextField(
                          controller: _usernameCtrl,
                          label: 'USERNAME',
                          hint: 'your_username',
                          prefixIcon: Icons.person_outline,
                          color: NeonColors.green,
                        ),
                        const SizedBox(height: 16),

                        NeonTextField(
                          controller: _passwordCtrl,
                          label: 'PASSWORD',
                          hint: '••••••••',
                          prefixIcon: Icons.lock_outline,
                          obscureText: _obscurePassword,
                          color: NeonColors.green,
                          suffixIcon: IconButton(
                            icon: Icon(
                              _obscurePassword
                                  ? Icons.visibility_outlined
                                  : Icons.visibility_off_outlined,
                              color: NeonColors.textSecondary,
                              size: 18,
                            ),
                            onPressed: () =>
                                setState(() => _obscurePassword = !_obscurePassword),
                          ),
                        ),
                        const SizedBox(height: 16),

                        NeonTextField(
                          controller: _confirmCtrl,
                          label: 'CONFIRM PASSWORD',
                          hint: '••••••••',
                          prefixIcon: Icons.lock_outline,
                          obscureText: _obscureConfirm,
                          color: NeonColors.green,
                          suffixIcon: IconButton(
                            icon: Icon(
                              _obscureConfirm
                                  ? Icons.visibility_outlined
                                  : Icons.visibility_off_outlined,
                              color: NeonColors.textSecondary,
                              size: 18,
                            ),
                            onPressed: () =>
                                setState(() => _obscureConfirm = !_obscureConfirm),
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
                                    label: 'РЕГИСТРАЦИЯ...',
                                    size: 40,
                                  ),
                                )
                              : _NeonButton(
                                  label: 'ЗАРЕГИСТРИРОВАТЬСЯ',
                                  icon: Icons.person_add_outlined,
                                  color: NeonColors.green,
                                  onTap: _register,
                                ),
                        ),
                      ],
                    ),
                  ).animate().fadeIn(delay: 400.ms, duration: 600.ms).slideY(begin: 0.2),

                  const SizedBox(height: 24),

                  // Login link
                  GestureDetector(
                    onTap: () => Navigator.of(context).pushReplacement(
                      NeonPageRoute(child: const LoginScreen()),
                    ),
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          vertical: 14, horizontal: 24),
                      decoration: BoxDecoration(
                        color: NeonColors.bgCard.withOpacity(0.5),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                            color: NeonColors.cyanGlow, width: 1),
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(Icons.login,
                              color: NeonColors.cyan, size: 16),
                          const SizedBox(width: 8),
                          NeonText(
                            'УЖЕ ЕСТЬ АККАУНТ? ВОЙТИ',
                            color: NeonColors.cyan,
                            fontSize: 10,
                            fontFamily: 'Orbitron',
                            glowRadius: 4,
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

class _BgPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = NeonColors.green.withOpacity(0.03)
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
