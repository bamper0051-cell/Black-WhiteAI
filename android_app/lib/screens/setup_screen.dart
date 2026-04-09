// setup_screen.dart — Начальная настройка: подключение к серверу BlackBugsAI

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../theme/neon_theme.dart';
import '../animations/neon_animations.dart';
import '../services/api_service.dart';
import '../services/ssh_tunnel_service.dart';
import '../widgets/neon_text_field.dart';
import 'main_shell.dart';

class SetupScreen extends StatefulWidget {
  const SetupScreen({super.key});

  @override
  State<SetupScreen> createState() => _SetupScreenState();
}

class _SetupScreenState extends State<SetupScreen> {
  final _hostCtrl = TextEditingController();
  final _sshPortCtrl = TextEditingController(text: '22');
  final _usernameCtrl = TextEditingController(text: 'ubuntu');
  final _dockerPortCtrl = TextEditingController(text: '8080');
  final _tokenCtrl = TextEditingController();
  bool _useHttps = false;
  bool _loading = false;
  bool _testing = false;
  String? _error;
  String? _testResult;
  bool _obscureToken = true;

  @override
  void dispose() {
    _hostCtrl.dispose();
    _sshPortCtrl.dispose();
    _usernameCtrl.dispose();
    _dockerPortCtrl.dispose();
    _tokenCtrl.dispose();
    super.dispose();
  }

  Future<void> _testConnection() async {
    final host = _hostCtrl.text.trim();
    final token = _tokenCtrl.text.trim();

    if (host.isEmpty || token.isEmpty) {
      setState(() => _error = 'Введи IP сервера и токен');
      return;
    }

    setState(() {
      _testing = true;
      _error = null;
      _testResult = null;
    });

    try {
      final dockerPort = int.tryParse(_dockerPortCtrl.text.trim()) ?? 8080;
      final scheme = _useHttps ? 'https' : 'http';
      final baseUrl = '$scheme://$host:$dockerPort';
      final api = ApiService(baseUrl: baseUrl, adminToken: token);
      final ok = await api.ping();
      setState(() {
        _testResult = ok ? '✅ Сервер доступен' : '❌ Сервер не отвечает';
        _testing = false;
      });
    } catch (e) {
      setState(() {
        _testResult = '❌ Ошибка: $e';
        _testing = false;
      });
    }
  }

  Future<void> _connect() async {
    final host = _hostCtrl.text.trim();
    final token = _tokenCtrl.text.trim();

    if (host.isEmpty || token.isEmpty) {
      setState(() => _error = 'Заполни все поля');
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final sshPort = int.tryParse(_sshPortCtrl.text.trim()) ?? 22;
      final dockerPort = int.tryParse(_dockerPortCtrl.text.trim()) ?? 8080;

      final cfg = SshConnectionConfig(
        host: host,
        port: sshPort,
        username: _usernameCtrl.text.trim().isEmpty
            ? 'ubuntu'
            : _usernameCtrl.text.trim(),
        remotePort: dockerPort,
        useHttps: _useHttps,
        adminToken: token,
      );

      await SshTunnelService.saveConfig(cfg);

      final scheme = _useHttps ? 'https' : 'http';
      final baseUrl = '$scheme://$host:$dockerPort';
      final api = ApiService(baseUrl: baseUrl, adminToken: token);
      final ok = await api.ping();

      if (!ok) {
        setState(() {
          _error = 'Сервер не отвечает. Проверь IP и токен.';
          _loading = false;
        });
        return;
      }

      await ApiService.setDemoMode(false);

      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        NeonPageRoute(child: const MainShell()),
      );
    } catch (e) {
      setState(() {
        _error = 'Ошибка подключения: $e';
        _loading = false;
      });
    }
  }

  Future<void> _useDemoMode() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove('base_url');
      await prefs.remove('admin_token');
      await ApiService.setDemoMode(true);
      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        NeonPageRoute(child: const MainShell()),
      );
    } catch (e) {
      setState(() {
        _error = 'Не удалось включить офлайн режим: $e';
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
                    'GCP DOCKER CONNECT',
                    color: NeonColors.purple,
                    fontSize: 11,
                    fontFamily: 'Orbitron',
                    glowRadius: 6,
                  ).animate().fadeIn(delay: 200.ms, duration: 600.ms),

                  const SizedBox(height: 48),

                  // Карточка настроек GCP
                  Container(
                    padding: const EdgeInsets.all(24),
                    decoration: neonCardDecoration(glowColor: NeonColors.cyan),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        NeonText(
                          '> GCP SERVER CONFIG',
                          color: NeonColors.cyan,
                          fontSize: 12,
                          fontFamily: 'Orbitron',
                          glowRadius: 4,
                        ),
                        const SizedBox(height: 20),

                        NeonTextField(
                          controller: _hostCtrl,
                          label: 'GCP SERVER IP / HOSTNAME',
                          hint: '34.xx.xx.xx',
                          prefixIcon: Icons.cloud_outlined,
                          keyboardType: TextInputType.text,
                        ),
                        const SizedBox(height: 12),

                        Row(
                          children: [
                            Expanded(
                              child: NeonTextField(
                                controller: _sshPortCtrl,
                                label: 'SSH PORT',
                                hint: '22',
                                prefixIcon: Icons.lock_outline,
                                keyboardType: TextInputType.number,
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: NeonTextField(
                                controller: _dockerPortCtrl,
                                label: 'DOCKER PORT',
                                hint: '8080',
                                prefixIcon: Icons.dock_outlined,
                                keyboardType: TextInputType.number,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),

                        NeonTextField(
                          controller: _usernameCtrl,
                          label: 'SSH USERNAME',
                          hint: 'ubuntu',
                          prefixIcon: Icons.person_outline,
                        ),
                        const SizedBox(height: 12),

                        NeonTextField(
                          controller: _tokenCtrl,
                          label: 'ADMIN TOKEN',
                          hint: 'your_secret_token',
                          prefixIcon: Icons.key_outlined,
                          obscureText: _obscureToken,
                          suffixIcon: IconButton(
                            icon: Icon(
                              _obscureToken
                                  ? Icons.visibility_outlined
                                  : Icons.visibility_off_outlined,
                              color: NeonColors.textSecondary,
                              size: 18,
                            ),
                            onPressed: () =>
                                setState(() => _obscureToken = !_obscureToken),
                          ),
                        ),
                        const SizedBox(height: 12),

                        // Переключатель HTTPS
                        GestureDetector(
                          onTap: () =>
                              setState(() => _useHttps = !_useHttps),
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 12, vertical: 10),
                            decoration: BoxDecoration(
                              color: NeonColors.bgSurface,
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(
                                  color: NeonColors.cyanGlow),
                            ),
                            child: Row(
                              children: [
                                Icon(
                                  _useHttps
                                      ? Icons.https_outlined
                                      : Icons.http_outlined,
                                  color: _useHttps
                                      ? NeonColors.green
                                      : NeonColors.textSecondary,
                                  size: 18,
                                ),
                                const SizedBox(width: 8),
                                Text(
                                  'USE HTTPS',
                                  style: TextStyle(
                                    color: _useHttps
                                        ? NeonColors.green
                                        : NeonColors.textSecondary,
                                    fontFamily: 'Orbitron',
                                    fontSize: 11,
                                    letterSpacing: 1,
                                  ),
                                ),
                                const Spacer(),
                                Switch(
                                  value: _useHttps,
                                  onChanged: (v) =>
                                      setState(() => _useHttps = v),
                                  activeColor: NeonColors.green,
                                  inactiveThumbColor:
                                      NeonColors.textSecondary,
                                ),
                              ],
                            ),
                          ),
                        ),

                        if (_testResult != null) ...[
                          const SizedBox(height: 12),
                          Container(
                            padding: const EdgeInsets.all(10),
                            decoration: BoxDecoration(
                              color: _testResult!.startsWith('✅')
                                  ? NeonColors.green.withOpacity(0.1)
                                  : NeonColors.pink.withOpacity(0.1),
                              borderRadius: BorderRadius.circular(6),
                              border: Border.all(
                                color: _testResult!.startsWith('✅')
                                    ? NeonColors.green.withOpacity(0.5)
                                    : NeonColors.pink.withOpacity(0.5),
                              ),
                            ),
                            child: Text(
                              _testResult!,
                              style: TextStyle(
                                color: _testResult!.startsWith('✅')
                                    ? NeonColors.green
                                    : NeonColors.pink,
                                fontSize: 11,
                                fontFamily: 'JetBrainsMono',
                              ),
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

                        const SizedBox(height: 20),

                        // Кнопки
                        Row(
                          children: [
                            Expanded(
                              child: _testing
                                  ? const Center(
                                      child: NeonLoadingIndicator(
                                          size: 32,
                                          label: 'TEST...'))
                                  : _NeonButton(
                                      label: 'ТЕСТ',
                                      icon: Icons.network_ping,
                                      color: NeonColors.purple,
                                      onTap: _testConnection,
                                    ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              flex: 2,
                              child: _loading
                                  ? const Center(
                                      child: NeonLoadingIndicator(
                                        label: 'CONNECTING...',
                                        size: 40,
                                      ),
                                    )
                                  : _NeonButton(
                                      label: 'СОХРАНИТЬ И ПОДКЛЮЧИТЬСЯ',
                                      icon: Icons.link,
                                      color: NeonColors.cyan,
                                      onTap: _connect,
                                    ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ).animate().fadeIn(delay: 400.ms, duration: 600.ms).slideY(begin: 0.2),

                  const SizedBox(height: 32),

                  // Подсказки
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
                        NeonText('> QUICK START', color: NeonColors.purple,
                            fontSize: 10, fontFamily: 'Orbitron'),
                        const SizedBox(height: 10),
                        _hintRow('1', 'На GCP VM: docker-compose up -d'),
                        _hintRow('2', 'IP: публичный IP GCP VM'),
                        _hintRow('3', 'Порт Docker: 8080 (по умолчанию)'),
                        _hintRow('4', 'Токен: ADMIN_TOKEN из .env'),
                      ],
                    ),
                  ).animate().fadeIn(delay: 600.ms, duration: 600.ms),

                  const SizedBox(height: 16),

                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(16),
                    decoration: neonCardDecoration(
                      glowColor: NeonColors.green,
                      glowRadius: 10,
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const NeonText(
                          '> OFFLINE / DEMO MODE',
                          color: NeonColors.green,
                          fontSize: 11,
                          fontFamily: 'Orbitron',
                          glowRadius: 6,
                        ),
                        const SizedBox(height: 8),
                        const Text(
                          'Использовать приложение без ПК и сервера. Доступны агенты, терминал и визуализации с локальными данными.',
                          style: TextStyle(
                            color: NeonColors.textSecondary,
                            fontSize: 11,
                            fontFamily: 'JetBrainsMono',
                          ),
                        ),
                        const SizedBox(height: 12),
                        _loading
                            ? const Center(
                                child: NeonLoadingIndicator(
                                  size: 28,
                                  label: 'ACTIVATING...',
                                ),
                              )
                            : GestureDetector(
                                onTap: _useDemoMode,
                                child: Container(
                                  width: double.infinity,
                                  padding: const EdgeInsets.symmetric(
                                      vertical: 12),
                                  decoration: neonButtonDecoration(
                                      color: NeonColors.green),
                                  child: const Center(
                                    child: NeonText(
                                      'ЗАПУСТИТЬ ОФЛАЙН',
                                      color: NeonColors.green,
                                      fontSize: 11,
                                      fontFamily: 'Orbitron',
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                ),
                              ),
                      ],
                    ),
                  ).animate().fadeIn(delay: 700.ms, duration: 600.ms),
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
              border: Border.all(color: NeonColors.purple.withOpacity(0.6)),
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
            Flexible(
              child: Text(
                widget.label,
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: widget.color,
                  fontFamily: 'Orbitron',
                  fontSize: 10,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
