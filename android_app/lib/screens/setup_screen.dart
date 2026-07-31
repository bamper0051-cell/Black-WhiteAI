// setup_screen.dart — Server URL + token setup screen

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../theme/neon_theme.dart';
import '../animations/neon_animations.dart';
import '../services/api_service.dart';
import '../services/auth_service.dart';
import '../services/ssh_tunnel_service.dart';
import '../widgets/neon_text_field.dart';
import 'login_screen.dart';
import 'main_shell.dart';

class SetupScreen extends StatefulWidget {
  const SetupScreen({super.key});

  @override
  State<SetupScreen> createState() => _SetupScreenState();
}

class _SetupScreenState extends State<SetupScreen> {
  final _hostCtrl       = TextEditingController();
  final _dockerPortCtrl = TextEditingController(text: '8080');
  final _tokenCtrl      = TextEditingController();

  bool   _useHttps    = false;
  bool   _loading     = false;
  bool   _testing     = false;
  bool   _obscureToken = true;
  String? _error;
  String? _testResult;

  @override
  void initState() {
    super.initState();
    _prefill();
  }

  @override
  void dispose() {
    _hostCtrl.dispose();
    _dockerPortCtrl.dispose();
    _tokenCtrl.dispose();
    super.dispose();
  }

  Future<void> _prefill() async {
    final cfg = await SshTunnelService.loadConfig();
    if (cfg != null && mounted) {
      setState(() {
        _hostCtrl.text       = cfg.host;
        _dockerPortCtrl.text = cfg.remotePort.toString();
        _tokenCtrl.text      = cfg.adminToken;
        _useHttps            = cfg.useHttps;
      });
    }
  }

  String get _baseUrl {
    final host = _hostCtrl.text.trim();
    final port = int.tryParse(_dockerPortCtrl.text.trim()) ?? 8080;
    final scheme = _useHttps ? 'https' : 'http';
    if (host.startsWith('http://') || host.startsWith('https://')) {
      return host.replaceAll(RegExp(r'/$'), '');
    }
    return '$scheme://$host:$port';
  }

  Future<void> _testConnection() async {
    final host  = _hostCtrl.text.trim();
    final token = _tokenCtrl.text.trim();
    if (host.isEmpty || token.isEmpty) {
      setState(() => _error = 'Введи IP сервера и токен');
      return;
    }
    setState(() { _testing = true; _error = null; _testResult = null; });
    try {
      final api = ApiService(baseUrl: _baseUrl, adminToken: token);
      final ok  = await api.ping();
      setState(() {
        _testResult = ok ? '✅ Сервер доступен' : '❌ Сервер не отвечает';
        _testing    = false;
      });
    } catch (e) {
      setState(() { _testResult = '❌ Ошибка: $e'; _testing = false; });
    }
  }

  Future<void> _connect() async {
    final host  = _hostCtrl.text.trim();
    final token = _tokenCtrl.text.trim();
    if (host.isEmpty || token.isEmpty) {
      setState(() => _error = 'Заполни все поля'); return;
    }
    setState(() { _loading = true; _error = null; });
    try {
      final port = int.tryParse(_dockerPortCtrl.text.trim()) ?? 8080;
      final cfg  = SshConnectionConfig(
        host:       host, remotePort: port,
        useHttps:   _useHttps, adminToken: token,
      );
      await SshTunnelService.saveConfig(cfg);
      final api = ApiService(baseUrl: _baseUrl, adminToken: token);
      final ok  = await api.ping();
      if (!ok) {
        setState(() { _error = 'Сервер не отвечает. Проверь IP и токен.'; _loading = false; });
        return;
      }
      await ApiService.setDemoMode(false);
      await AuthService.saveSession(
        baseUrl: _baseUrl, token: token,
        username: 'admin', role: 'admin', authMode: 'token',
      );
      if (!mounted) return;
      Navigator.of(context).pushAndRemoveUntil(
          NeonPageRoute(child: const MainShell()), (_) => false);
    } catch (e) {
      setState(() { _error = 'Ошибка: $e'; _loading = false; });
    }
  }

  Future<void> _goToLogin() async {
    final host = _hostCtrl.text.trim();
    if (host.isEmpty) { setState(() => _error = 'Введи IP сервера'); return; }
    Navigator.of(context).push(
        NeonPageRoute(child: LoginScreen(baseUrl: _baseUrl)));
  }

  Future<void> _useDemoMode() async {
    setState(() { _loading = true; _error = null; });
    await ApiService.setDemoMode(true);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('demo_mode', true);
    if (!mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
        NeonPageRoute(child: const MainShell()), (_) => false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: NeonColors.bgDeep,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            children: [
              const SizedBox(height: 40),
              NeonText('BLACKBUGS AI', color: NeonColors.cyan,
                  fontSize: 28, fontWeight: FontWeight.w700,
                  fontFamily: 'Orbitron', glowRadius: 16)
                  .animate().fadeIn(duration: 600.ms).slideY(begin: -0.3),
              const SizedBox(height: 8),
              NeonText('GCP DOCKER CONNECT', color: NeonColors.purple,
                  fontSize: 10, fontFamily: 'Orbitron', glowRadius: 5)
                  .animate().fadeIn(delay: 200.ms),
              const SizedBox(height: 40),

              // ── Config card ──────────────────────────────────────────────
              Container(
                padding: const EdgeInsets.all(24),
                decoration: neonCardDecoration(glowColor: NeonColors.cyan),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    NeonText('> НАСТРОЙКИ СЕРВЕРА', color: NeonColors.cyan,
                        fontSize: 11, fontFamily: 'Orbitron', glowRadius: 4),
                    const SizedBox(height: 20),

                    NeonTextField(controller: _hostCtrl,
                        label: 'IP / HOSTNAME', hint: '34.xx.xx.xx или localhost',
                        prefixIcon: Icons.cloud_outlined,
                        keyboardType: TextInputType.text),
                    const SizedBox(height: 12),
                    NeonTextField(controller: _dockerPortCtrl,
                        label: 'ПОРТ', hint: '8080',
                        prefixIcon: Icons.dock_outlined,
                        keyboardType: TextInputType.number),
                    const SizedBox(height: 12),
                    NeonTextField(controller: _tokenCtrl,
                        label: 'ADMIN TOKEN', hint: 'ADMIN_WEB_TOKEN из .env',
                        prefixIcon: Icons.key_outlined,
                        obscureText: _obscureToken,
                        suffixIcon: IconButton(
                          icon: Icon(
                            _obscureToken ? Icons.visibility_outlined
                                          : Icons.visibility_off_outlined,
                            color: NeonColors.textSecondary, size: 18),
                          onPressed: () =>
                              setState(() => _obscureToken = !_obscureToken),
                        )),
                    const SizedBox(height: 12),

                    // HTTPS toggle
                    GestureDetector(
                      onTap: () => setState(() => _useHttps = !_useHttps),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 12, vertical: 10),
                        decoration: BoxDecoration(
                          color:  NeonColors.bgSurface,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: NeonColors.cyanGlow),
                        ),
                        child: Row(
                          children: [
                            Icon(
                              _useHttps ? Icons.https_outlined : Icons.http_outlined,
                              color: _useHttps ? NeonColors.green : NeonColors.textSecondary,
                              size: 18),
                            const SizedBox(width: 8),
                            Text('USE HTTPS',
                                style: TextStyle(
                                  color: _useHttps ? NeonColors.green : NeonColors.textSecondary,
                                  fontFamily: 'JetBrainsMono', fontSize: 11)),
                            const Spacer(),
                            Switch(value: _useHttps,
                                onChanged: (v) => setState(() => _useHttps = v),
                                activeColor: NeonColors.green),
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
                                : NeonColors.pink.withOpacity(0.5)),
                        ),
                        child: Text(_testResult!,
                            style: TextStyle(
                              color: _testResult!.startsWith('✅')
                                  ? NeonColors.green : NeonColors.pink,
                              fontFamily: 'JetBrainsMono', fontSize: 11)),
                      ),
                    ],

                    if (_error != null) ...[
                      const SizedBox(height: 12),
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: NeonColors.pink.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: NeonColors.pink.withOpacity(0.5)),
                        ),
                        child: Row(children: [
                          const Icon(Icons.error_outline,
                              color: NeonColors.pink, size: 14),
                          const SizedBox(width: 8),
                          Expanded(child: Text(_error!,
                              style: const TextStyle(
                                  color: NeonColors.pink,
                                  fontFamily: 'JetBrainsMono', fontSize: 11))),
                        ]),
                      ),
                    ],

                    const SizedBox(height: 20),
                    Row(
                      children: [
                        Expanded(
                          child: _testing
                              ? const Center(child: NeonLoadingIndicator(
                                  size: 32, label: 'TEST...'))
                              : _NeonBtn(label: 'ТЕСТ', icon: Icons.network_ping,
                                  color: NeonColors.purple, onTap: _testConnection),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          flex: 2,
                          child: _loading
                              ? const Center(child: NeonLoadingIndicator(
                                  label: 'CONNECTING...', size: 36))
                              : _NeonBtn(label: 'ПОДКЛЮЧИТЬСЯ',
                                  icon: Icons.link, color: NeonColors.cyan,
                                  onTap: _connect),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    SizedBox(
                      width: double.infinity,
                      child: _NeonBtn(label: 'ВОЙТИ ПО ЛОГИНУ/ПАРОЛЮ',
                          icon: Icons.person_outlined,
                          color: NeonColors.purple, onTap: _goToLogin),
                    ),
                  ],
                ),
              ).animate().fadeIn(delay: 400.ms, duration: 600.ms),

              const SizedBox(height: 20),

              // Hints
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
                    NeonText('> QUICK START', color: NeonColors.purple,
                        fontSize: 10, fontFamily: 'Orbitron'),
                    const SizedBox(height: 10),
                    _hint('1', 'На сервере: docker compose up -d'),
                    _hint('2', 'IP: публичный IP или LAN'),
                    _hint('3', 'Порт: 8080 (по умолчанию)'),
                    _hint('4', 'Токен: ADMIN_WEB_TOKEN из .env'),
                  ],
                ),
              ).animate().fadeIn(delay: 600.ms),

              const SizedBox(height: 16),

              // Demo mode
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(16),
                decoration: neonCardDecoration(glowColor: NeonColors.green),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    NeonText('> DEMO / OFFLINE', color: NeonColors.green,
                        fontSize: 11, fontFamily: 'Orbitron', glowRadius: 6),
                    const SizedBox(height: 8),
                    const Text(
                      'Работает без сервера — демонстрационные данные',
                      style: TextStyle(
                          color: NeonColors.textSecondary,
                          fontFamily: 'JetBrainsMono', fontSize: 11)),
                    const SizedBox(height: 12),
                    _loading
                        ? const Center(child: NeonLoadingIndicator(size: 28))
                        : SizedBox(
                            width: double.infinity,
                            child: _NeonBtn(
                              label: 'ЗАПУСТИТЬ ОФЛАЙН',
                              icon:  Icons.offline_bolt_outlined,
                              color: NeonColors.green,
                              onTap: _useDemoMode,
                            ),
                          ),
                  ],
                ),
              ).animate().fadeIn(delay: 700.ms),

              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }

  Widget _hint(String n, String text) => Padding(
    padding: const EdgeInsets.only(bottom: 5),
    child: Row(children: [
      Container(
        width: 18, height: 18, alignment: Alignment.center,
        decoration: BoxDecoration(
          border: Border.all(color: NeonColors.purple.withOpacity(0.6)),
          borderRadius: BorderRadius.circular(4)),
        child: Text(n, style: const TextStyle(
            color: NeonColors.purple, fontSize: 10, fontFamily: 'JetBrainsMono',
            fontWeight: FontWeight.w700)),
      ),
      const SizedBox(width: 10),
      Text(text, style: const TextStyle(
          color: NeonColors.textSecondary,
          fontSize: 10, fontFamily: 'JetBrainsMono')),
    ]),
  );
}

class _NeonBtn extends StatefulWidget {
  final String   label;
  final IconData icon;
  final Color    color;
  final VoidCallback onTap;
  const _NeonBtn({required this.label, required this.icon,
      required this.color, required this.onTap});

  @override
  State<_NeonBtn> createState() => _NeonBtnState();
}

class _NeonBtnState extends State<_NeonBtn> {
  bool _pressed = false;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTapDown:   (_) => setState(() => _pressed = true),
      onTapUp:     (_) { setState(() => _pressed = false); widget.onTap(); },
      onTapCancel: ()  => setState(() => _pressed = false),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 80),
        padding: const EdgeInsets.symmetric(vertical: 13),
        decoration: BoxDecoration(
          color: _pressed
              ? widget.color.withOpacity(0.25)
              : widget.color.withOpacity(0.12),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: widget.color, width: 1.5),
          boxShadow: [BoxShadow(
              color:     widget.color.withOpacity(_pressed ? 0.6 : 0.3),
              blurRadius: _pressed ? 20 : 10)],
        ),
        child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
          Icon(widget.icon, color: widget.color, size: 16),
          const SizedBox(width: 8),
          Text(widget.label, style: TextStyle(
              color: widget.color, fontFamily: 'JetBrainsMono',
              fontSize: 11, fontWeight: FontWeight.w700, letterSpacing: 1)),
        ]),
      ),
    );
  }
}
