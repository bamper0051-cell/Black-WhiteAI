// setup_screen.dart — Initial setup: Telegram-only OR server mode

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../theme/neon_theme.dart';
import '../animations/neon_animations.dart';
import '../services/api_service.dart';
import '../services/telegram_bot_service.dart';
import '../widgets/neon_text_field.dart';
import 'main_shell.dart';

class SetupScreen extends StatefulWidget {
  const SetupScreen({super.key});

  @override
  State<SetupScreen> createState() => _SetupScreenState();
}

class _SetupScreenState extends State<SetupScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabCtrl;

  // Telegram-only mode
  final _tgTokenCtrl = TextEditingController();
  bool _obscureTg = true;

  // Server mode
  final _urlCtrl = TextEditingController(text: 'http://');
  final _serverTokenCtrl = TextEditingController();
  bool _obscureServer = true;

  bool _loading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _tabCtrl = TabController(length: 2, vsync: this);
    _tabCtrl.addListener(() => setState(() => _error = null));
  }

  @override
  void dispose() {
    _tabCtrl.dispose();
    _tgTokenCtrl.dispose();
    _urlCtrl.dispose();
    _serverTokenCtrl.dispose();
    super.dispose();
  }

  // ── Telegram-only login ────────────────────────────────────────────────────
  Future<void> _connectTelegram() async {
    final token = _tgTokenCtrl.text.trim();
    if (token.isEmpty) {
      setState(() => _error = 'Введи Telegram Bot Token');
      return;
    }

    setState(() { _loading = true; _error = null; });

    try {
      final ok = await TelegramBotService.validateToken(token);
      if (!ok) {
        setState(() {
          _error = 'Неверный токен. Проверь его в @BotFather.';
          _loading = false;
        });
        return;
      }

      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('telegram_token', token);
      await prefs.setString('app_mode', 'telegram');
      await prefs.remove('base_url');
      await prefs.remove('admin_token');

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

  // ── Server mode login ──────────────────────────────────────────────────────
  Future<void> _connectServer() async {
    final url = _urlCtrl.text.trim().replaceAll(RegExp(r'/$'), '');
    final token = _serverTokenCtrl.text.trim();

    if (url.isEmpty || token.isEmpty) {
      setState(() => _error = 'Заполни все поля');
      return;
    }

    setState(() { _loading = true; _error = null; });

    try {
      final api = ApiService(baseUrl: url, adminToken: token);
      final ok = await api.ping();
      if (!ok) {
        setState(() {
          _error = 'Сервер не отвечает. Проверь URL и токен.';
          _loading = false;
        });
        return;
      }

      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('base_url', url);
      await prefs.setString('admin_token', token);
      await prefs.setString('app_mode', 'server');
      await prefs.remove('telegram_token');

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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: NeonColors.bgDeep,
      body: Stack(
        children: [
          CustomPaint(
            painter: _GridPainter(),
            size: MediaQuery.of(context).size,
          ),
          SafeArea(
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: Column(
                children: [
                  const SizedBox(height: 36),

                  // ── Logo ──
                  Column(
                    children: [
                      NeonText(
                        'BLACKBUGS AI',
                        color: NeonColors.cyan,
                        fontSize: 26,
                        fontWeight: FontWeight.w700,
                        fontFamily: 'Orbitron',
                        glowRadius: 16,
                      ).animate().fadeIn(duration: 600.ms).slideY(begin: -0.3),
                      const SizedBox(height: 6),
                      NeonText(
                        'ADMIN PANEL',
                        color: NeonColors.purple,
                        fontSize: 11,
                        fontFamily: 'Orbitron',
                        glowRadius: 6,
                      ).animate().fadeIn(delay: 200.ms),
                    ],
                  ),

                  const SizedBox(height: 36),

                  // ── Mode switcher ──
                  Container(
                    decoration: BoxDecoration(
                      color: NeonColors.bgCard,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: NeonColors.cyanGlow),
                    ),
                    child: TabBar(
                      controller: _tabCtrl,
                      indicator: BoxDecoration(
                        color: NeonColors.cyan.withOpacity(0.15),
                        borderRadius: BorderRadius.circular(9),
                        border: Border.all(color: NeonColors.cyan, width: 1.5),
                      ),
                      labelColor: NeonColors.cyan,
                      unselectedLabelColor: NeonColors.textSecondary,
                      labelStyle: const TextStyle(
                        fontFamily: 'Orbitron',
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 1,
                      ),
                      dividerColor: Colors.transparent,
                      tabs: const [
                        Tab(
                          icon: Icon(Icons.telegram, size: 18),
                          text: 'TELEGRAM ONLY',
                        ),
                        Tab(
                          icon: Icon(Icons.dns_outlined, size: 18),
                          text: 'SERVER',
                        ),
                      ],
                    ),
                  ).animate().fadeIn(delay: 300.ms),

                  const SizedBox(height: 24),

                  // ── Tab content ──
                  AnimatedBuilder(
                    animation: _tabCtrl,
                    builder: (context, _) {
                      return _tabCtrl.index == 0
                          ? _buildTelegramTab()
                          : _buildServerTab();
                    },
                  ),

                  // ── Error ──
                  if (_error != null) ...[
                    const SizedBox(height: 12),
                    _ErrorBox(message: _error!),
                  ],

                  const SizedBox(height: 20),

                  // ── Connect button ──
                  _loading
                      ? const NeonLoadingIndicator(label: 'CONNECTING...', size: 40)
                      : _NeonButton(
                          label: _tabCtrl.index == 0 ? 'ВОЙТИ' : 'CONNECT',
                          icon: _tabCtrl.index == 0
                              ? Icons.telegram
                              : Icons.link,
                          color: _tabCtrl.index == 0
                              ? NeonColors.cyan
                              : NeonColors.purple,
                          onTap: _tabCtrl.index == 0
                              ? _connectTelegram
                              : _connectServer,
                        ),

                  const SizedBox(height: 28),

                  // ── Info card ──
                  _InfoCard(isTelegramMode: _tabCtrl.index == 0)
                      .animate()
                      .fadeIn(delay: 600.ms),

                  const SizedBox(height: 24),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTelegramTab() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: neonCardDecoration(glowColor: NeonColors.cyan),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.telegram, color: NeonColors.cyan, size: 18),
              const SizedBox(width: 8),
              const NeonText(
                '> BOT TOKEN',
                color: NeonColors.cyan,
                fontSize: 11,
                fontFamily: 'Orbitron',
                glowRadius: 4,
              ),
            ],
          ),
          const SizedBox(height: 6),
          const Text(
            'Получи токен у @BotFather в Telegram',
            style: TextStyle(
              color: NeonColors.textSecondary,
              fontSize: 11,
              fontFamily: 'JetBrainsMono',
            ),
          ),
          const SizedBox(height: 16),
          NeonTextField(
            controller: _tgTokenCtrl,
            label: 'BOT TOKEN',
            hint: '1234567890:AAExxxxxxxxxxxxxxxxxxxxxxxxxx',
            prefixIcon: Icons.vpn_key_outlined,
            obscureText: _obscureTg,
            suffixIcon: IconButton(
              icon: Icon(
                _obscureTg
                    ? Icons.visibility_outlined
                    : Icons.visibility_off_outlined,
                color: NeonColors.textSecondary,
                size: 18,
              ),
              onPressed: () => setState(() => _obscureTg = !_obscureTg),
            ),
          ),
        ],
      ),
    ).animate().fadeIn(duration: 300.ms);
  }

  Widget _buildServerTab() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: neonCardDecoration(glowColor: NeonColors.purple),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.dns_outlined, color: NeonColors.purple, size: 18),
              const SizedBox(width: 8),
              const NeonText(
                '> SERVER CONFIG',
                color: NeonColors.purple,
                fontSize: 11,
                fontFamily: 'Orbitron',
                glowRadius: 4,
              ),
            ],
          ),
          const SizedBox(height: 16),
          NeonTextField(
            controller: _urlCtrl,
            label: 'SERVER URL',
            hint: 'http://192.168.1.1:8080',
            prefixIcon: Icons.dns_outlined,
            keyboardType: TextInputType.url,
            color: NeonColors.purple,
          ),
          const SizedBox(height: 12),
          NeonTextField(
            controller: _serverTokenCtrl,
            label: 'ADMIN TOKEN',
            hint: 'your_secret_token',
            prefixIcon: Icons.key_outlined,
            obscureText: _obscureServer,
            color: NeonColors.purple,
            suffixIcon: IconButton(
              icon: Icon(
                _obscureServer
                    ? Icons.visibility_outlined
                    : Icons.visibility_off_outlined,
                color: NeonColors.textSecondary,
                size: 18,
              ),
              onPressed: () => setState(() => _obscureServer = !_obscureServer),
            ),
          ),
        ],
      ),
    ).animate().fadeIn(duration: 300.ms);
  }
}

// ─── Widgets ──────────────────────────────────────────────────────────────────

class _ErrorBox extends StatelessWidget {
  final String message;
  const _ErrorBox({required this.message});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: NeonColors.pink.withOpacity(0.1),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: NeonColors.pink.withOpacity(0.5)),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline, color: NeonColors.pink, size: 16),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              message,
              style: const TextStyle(
                color: NeonColors.pink,
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

class _InfoCard extends StatelessWidget {
  final bool isTelegramMode;
  const _InfoCard({required this.isTelegramMode});

  @override
  Widget build(BuildContext context) {
    final color = isTelegramMode ? NeonColors.cyan : NeonColors.purple;
    final items = isTelegramMode
        ? [
            '1. Открой Telegram → @BotFather',
            '2. Напиши /newbot или /mybots',
            '3. Скопируй токен вида 123:ABC...',
            '4. Вставь выше и нажми ВОЙТИ',
          ]
        : [
            '1. Запусти docker-compose up -d',
            '2. URL: http://<ip>:8080',
            '3. Токен: ADMIN_TOKEN из .env',
          ];

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: color.withOpacity(0.05),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          NeonText(
            isTelegramMode ? '> КАК ПОЛУЧИТЬ ТОКЕН' : '> QUICK START',
            color: color,
            fontSize: 10,
            fontFamily: 'Orbitron',
            glowRadius: 3,
          ),
          const SizedBox(height: 10),
          ...items.map(
            (t) => Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Text(
                t,
                style: TextStyle(
                  color: color.withOpacity(0.7),
                  fontSize: 11,
                  fontFamily: 'JetBrainsMono',
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _GridPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = NeonColors.cyan.withOpacity(0.02)
      ..strokeWidth = 1;
    const step = 48.0;
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
    return SizedBox(
      width: double.infinity,
      child: GestureDetector(
        onTapDown: (_) => setState(() => _pressed = true),
        onTapUp: (_) {
          setState(() => _pressed = false);
          widget.onTap();
        },
        onTapCancel: () => setState(() => _pressed = false),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 100),
          padding: const EdgeInsets.symmetric(vertical: 16),
          decoration: BoxDecoration(
            color: _pressed
                ? widget.color.withOpacity(0.25)
                : widget.color.withOpacity(0.12),
            borderRadius: BorderRadius.circular(10),
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
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 2,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
