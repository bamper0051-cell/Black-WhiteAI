// setup_screen.dart — Initial setup: login/register + Telegram config

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../theme/neon_theme.dart';
import '../animations/neon_animations.dart';
import '../services/api_service.dart';
import '../widgets/neon_text_field.dart';
import 'main_shell.dart';

enum _SetupMode { login, register }

class SetupScreen extends StatefulWidget {
  const SetupScreen({super.key});

  @override
  State<SetupScreen> createState() => _SetupScreenState();
}

class _SetupScreenState extends State<SetupScreen> {
  // Admin panel connection
  final _urlCtrl = TextEditingController(text: 'http://');
  final _userCtrl = TextEditingController();
  final _passCtrl = TextEditingController();
  final _pass2Ctrl = TextEditingController();

  // Telegram
  final _tgTokenCtrl = TextEditingController();
  final _tgAdminCtrl = TextEditingController();

  _SetupMode _mode = _SetupMode.login;
  bool _loading = false;
  String? _error;
  bool _obscurePass = true;
  bool _obscurePass2 = true;

  @override
  void dispose() {
    _urlCtrl.dispose();
    _userCtrl.dispose();
    _passCtrl.dispose();
    _pass2Ctrl.dispose();
    _tgTokenCtrl.dispose();
    _tgAdminCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final url = _urlCtrl.text.trim().replaceAll(RegExp(r'/$'), '');
    final username = _userCtrl.text.trim();
    final password = _passCtrl.text;

    if (url.isEmpty || username.isEmpty || password.isEmpty) {
      setState(() => _error = 'Заполни все обязательные поля');
      return;
    }
    if (_mode == _SetupMode.register) {
      if (_passCtrl.text != _pass2Ctrl.text) {
        setState(() => _error = 'Пароли не совпадают');
        return;
      }
    }

    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      String token;
      if (_mode == _SetupMode.register) {
        token = await ApiService.register(url, username, password);
      } else {
        token = await ApiService.login(url, username, password);
      }

      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('base_url', url);
      await prefs.setString('session_token', token);
      await prefs.setString('username', username);
      // Telegram settings (optional)
      final tgToken = _tgTokenCtrl.text.trim();
      final tgAdmin = _tgAdminCtrl.text.trim();
      if (tgToken.isNotEmpty) await prefs.setString('telegram_token', tgToken);
      if (tgAdmin.isNotEmpty) await prefs.setString('admin_id', tgAdmin);

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
        _error = 'Ошибка подключения: $e';
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
            painter: _SetupBgPainter(),
            size: MediaQuery.of(context).size,
          ),
          SafeArea(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24),
              child: Column(
                children: [
                  const SizedBox(height: 40),

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
                    _mode == _SetupMode.login
                        ? 'ВХОД В СИСТЕМУ'
                        : 'РЕГИСТРАЦИЯ',
                    color: NeonColors.purple,
                    fontSize: 11,
                    fontFamily: 'Orbitron',
                    glowRadius: 6,
                  ).animate().fadeIn(delay: 200.ms, duration: 600.ms),

                  const SizedBox(height: 48),

                  // ── Admin Panel Auth Card ──────────────────────────────
                  Container(
                    padding: const EdgeInsets.all(24),
                    decoration: neonCardDecoration(glowColor: NeonColors.cyan),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        NeonText(
                          '> ADMIN PANEL',
                          color: NeonColors.cyan,
                          fontSize: 12,
                          fontFamily: 'Orbitron',
                          glowRadius: 4,
                        ),
                        const SizedBox(height: 4),
                        const Text(
                          'Для подключения к серверу управления',
                          style: TextStyle(
                            color: NeonColors.textSecondary,
                            fontSize: 10,
                            fontFamily: 'JetBrainsMono',
                          ),
                        ),
                        const SizedBox(height: 20),

                        NeonTextField(
                          controller: _urlCtrl,
                          label: 'SERVER URL',
                          hint: 'http://192.168.1.1:8080',
                          prefixIcon: Icons.dns_outlined,
                          keyboardType: TextInputType.url,
                        ),
                        const SizedBox(height: 12),

                        NeonTextField(
                          controller: _userCtrl,
                          label: 'ИМЯ ПОЛЬЗОВАТЕЛЯ',
                          hint: 'admin',
                          prefixIcon: Icons.person_outline,
                        ),
                        const SizedBox(height: 12),

                        NeonTextField(
                          controller: _passCtrl,
                          label: 'ПАРОЛЬ',
                          hint: '••••••••',
                          prefixIcon: Icons.lock_outline,
                          obscureText: _obscurePass,
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
                        ),

                        if (_mode == _SetupMode.register) ...[
                          const SizedBox(height: 12),
                          NeonTextField(
                            controller: _pass2Ctrl,
                            label: 'ПОВТОР ПАРОЛЯ',
                            hint: '••••••••',
                            prefixIcon: Icons.lock_outline,
                            obscureText: _obscurePass2,
                            suffixIcon: IconButton(
                              icon: Icon(
                                _obscurePass2
                                    ? Icons.visibility_outlined
                                    : Icons.visibility_off_outlined,
                                color: NeonColors.textSecondary,
                                size: 18,
                              ),
                              onPressed: () => setState(
                                  () => _obscurePass2 = !_obscurePass2),
                            ),
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
                                    label: 'ПОДКЛЮЧЕНИЕ...',
                                    size: 40,
                                  ),
                                )
                              : _NeonButton(
                                  label: _mode == _SetupMode.login
                                      ? 'ВОЙТИ'
                                      : 'ЗАРЕГИСТРИРОВАТЬСЯ',
                                  icon: _mode == _SetupMode.login
                                      ? Icons.login
                                      : Icons.person_add_outlined,
                                  color: NeonColors.cyan,
                                  onTap: _submit,
                                ),
                        ),

                        const SizedBox(height: 16),

                        // Toggle login / register
                        GestureDetector(
                          onTap: () => setState(() {
                            _mode = _mode == _SetupMode.login
                                ? _SetupMode.register
                                : _SetupMode.login;
                            _error = null;
                          }),
                          child: Center(
                            child: Text(
                              _mode == _SetupMode.login
                                  ? 'Нет аккаунта? Зарегистрироваться'
                                  : 'Уже есть аккаунт? Войти',
                              style: const TextStyle(
                                color: NeonColors.cyan,
                                fontSize: 11,
                                fontFamily: 'JetBrainsMono',
                                decoration: TextDecoration.underline,
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ).animate().fadeIn(delay: 400.ms, duration: 600.ms).slideY(begin: 0.2),

                  const SizedBox(height: 24),

                  // ── Telegram Config Card ──────────────────────────────
                  Container(
                    padding: const EdgeInsets.all(24),
                    decoration:
                        neonCardDecoration(glowColor: NeonColors.purple),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        NeonText(
                          '> TELEGRAM',
                          color: NeonColors.purple,
                          fontSize: 12,
                          fontFamily: 'Orbitron',
                          glowRadius: 4,
                        ),
                        const SizedBox(height: 4),
                        const Text(
                          'Для связи с Telegram ботом (необязательно)',
                          style: TextStyle(
                            color: NeonColors.textSecondary,
                            fontSize: 10,
                            fontFamily: 'JetBrainsMono',
                          ),
                        ),
                        const SizedBox(height: 20),

                        NeonTextField(
                          controller: _tgTokenCtrl,
                          label: 'BOT TOKEN',
                          hint: '123456:ABC-DEF...',
                          prefixIcon: Icons.telegram_outlined,
                        ),
                        const SizedBox(height: 12),

                        NeonTextField(
                          controller: _tgAdminCtrl,
                          label: 'ADMIN ID',
                          hint: '123456789',
                          prefixIcon: Icons.admin_panel_settings_outlined,
                          keyboardType: TextInputType.number,
                        ),
                      ],
                    ),
                  ).animate().fadeIn(delay: 500.ms, duration: 600.ms),

                  const SizedBox(height: 24),

                  // ── Hints ─────────────────────────────────────────────
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: NeonColors.bgCard.withOpacity(0.5),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(
                          color: NeonColors.purpleGlow, width: 1),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        NeonText('> QUICK START',
                            color: NeonColors.purple,
                            fontSize: 10,
                            fontFamily: 'Orbitron'),
                        const SizedBox(height: 10),
                        _hintRow('1', 'Запусти: python main.py'),
                        _hintRow('2', 'URL: http://<ip>:8080'),
                        _hintRow('3', 'Зарегистрируй первого admin'),
                        _hintRow('4', 'Telegram: задай BOT TOKEN'),
                      ],
                    ),
                  ).animate().fadeIn(delay: 600.ms, duration: 600.ms),

                  const SizedBox(height: 24),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _hintRow(String num, String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        children: [
          Container(
            width: 18,
            height: 18,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              border:
                  Border.all(color: NeonColors.purple.withOpacity(0.6)),
              borderRadius: BorderRadius.circular(4),
            ),
            child: Text(
              num,
              style: const TextStyle(
                color: NeonColors.purple,
                fontSize: 10,
                fontFamily: 'Orbitron',
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              text,
              style: const TextStyle(
                color: NeonColors.textSecondary,
                fontSize: 11,
                fontFamily: 'JetBrainsMono',
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _SetupBgPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = NeonColors.purple.withOpacity(0.03)
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
