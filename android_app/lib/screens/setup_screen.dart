// setup_screen.dart — Server URL setup (step 1 of onboarding)

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../theme/neon_theme.dart';
import '../animations/neon_animations.dart';
import '../services/auth_service.dart';
import '../widgets/neon_text_field.dart';
import 'login_screen.dart';

class SetupScreen extends StatefulWidget {
  const SetupScreen({super.key});

  @override
  State<SetupScreen> createState() => _SetupScreenState();
}

class _SetupScreenState extends State<SetupScreen> {
  final _urlCtrl = TextEditingController(text: 'http://');
  bool _loading = false;
  String? _error;

  Future<void> _connect() async {
    final url = _urlCtrl.text.trim().replaceAll(RegExp(r'/$'), '');
    if (url.isEmpty || url == 'http://' || url == 'https://') {
      setState(() => _error = 'Введи URL сервера');
      return;
    }

    setState(() { _loading = true; _error = null; });

    try {
      final auth = AuthService(baseUrl: url);
      final ok = await auth.ping();

      if (!ok) {
        setState(() {
          _error = 'Сервер не отвечает. Проверь URL.';
          _loading = false;
        });
        return;
      }

      // Save server URL (without token — login screen will handle that)
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('base_url', url);

      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        NeonPageRoute(child: LoginScreen(baseUrl: url)),
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
            painter: _SetupBgPainter(),
            size: MediaQuery.of(context).size,
          ),
          SafeArea(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24),
              child: Column(
                children: [
                  const SizedBox(height: 40),

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
                    'ПОДКЛЮЧЕНИЕ К СЕРВЕРУ',
                    color: NeonColors.purple,
                    fontSize: 10,
                    fontFamily: 'Orbitron',
                    glowRadius: 5,
                  ).animate().fadeIn(delay: 200.ms),

                  const SizedBox(height: 48),

                  Container(
                    padding: const EdgeInsets.all(24),
                    decoration: neonCardDecoration(glowColor: NeonColors.cyan),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const NeonText('> SERVER URL', color: NeonColors.cyan,
                            fontSize: 11, fontFamily: 'Orbitron', glowRadius: 4),
                        const SizedBox(height: 20),

                        NeonTextField(
                          controller: _urlCtrl,
                          label: 'АДРЕС СЕРВЕРА',
                          hint: 'http://192.168.1.1:8080',
                          prefixIcon: Icons.dns_outlined,
                          keyboardType: TextInputType.url,
                          onChanged: (_) => setState(() => _error = null),
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

                        _loading
                            ? const Center(
                                child: NeonLoadingIndicator(
                                    size: 36, label: 'CONNECTING...'))
                            : SizedBox(
                                width: double.infinity,
                                child: GestureDetector(
                                  onTap: _connect,
                                  child: Container(
                                    padding: const EdgeInsets.symmetric(
                                        vertical: 14),
                                    decoration: neonButtonDecoration(
                                        color: NeonColors.cyan),
                                    child: const Row(
                                      mainAxisAlignment:
                                          MainAxisAlignment.center,
                                      children: [
                                        Icon(Icons.link,
                                            color: NeonColors.cyan, size: 18),
                                        SizedBox(width: 8),
                                        NeonText('CONNECT',
                                            color: NeonColors.cyan,
                                            fontSize: 13,
                                            fontFamily: 'Orbitron',
                                            fontWeight: FontWeight.w700),
                                      ],
                                    ),
                                  ),
                                ),
                              ),
                      ],
                    ),
                  ).animate().fadeIn(delay: 400.ms).slideY(begin: 0.2),

                  const SizedBox(height: 24),

                  // Quick hints
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: NeonColors.bgCard.withOpacity(0.5),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: NeonColors.purpleGlow),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const NeonText('> QUICK START',
                            color: NeonColors.purple,
                            fontSize: 9, fontFamily: 'Orbitron'),
                        const SizedBox(height: 10),
                        _hint('1', 'Запусти: docker-compose up -d'),
                        _hint('2', 'URL: http://<ip>:8080'),
                        _hint('3', 'Войди или зарегистрируйся'),
                      ],
                    ),
                  ).animate().fadeIn(delay: 600.ms),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _hint(String n, String text) => Padding(
    padding: const EdgeInsets.only(bottom: 6),
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
                fontSize: 11, fontFamily: 'JetBrainsMono')),
      ],
    ),
  );
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
