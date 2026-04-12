// settings_screen.dart — Account, server config, auth mode management
<<<<<<< HEAD
// FIXED: removed duplicate dispose(), fixed SharedPreferences references,
//        fixed incomplete if-blocks, fixed ApiService references

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:shared_preferences/shared_preferences.dart';
=======

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
import '../theme/neon_theme.dart';
import '../animations/neon_animations.dart';
import '../widgets/neon_text_field.dart';
import '../widgets/neon_card.dart';
import '../services/auth_service.dart';
<<<<<<< HEAD
import '../services/api_service.dart';
=======
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
import 'setup_screen.dart';
import 'login_screen.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
<<<<<<< HEAD
  final _urlCtrl   = TextEditingController();
  final _tokenCtrl = TextEditingController();

  bool   _savingUrl    = false;
  bool   _saving       = false;
  bool   _obscureToken = true;
  bool   _demoMode     = false;
  String? _username;
  String? _role;
  String? _baseUrl;
  String? _authMode;
=======
  final _urlCtrl = TextEditingController();
  bool _savingUrl = false;

  String? _username;
  String? _role;
  String? _baseUrl;
  String? _authMode;    // 'login' | 'token'
  final _tokenCtrl = TextEditingController();
  bool _saving = false;
  bool _obscureToken = true;
  bool _demoMode = false;
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _urlCtrl.dispose();
<<<<<<< HEAD
    _tokenCtrl.dispose();
=======
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
    super.dispose();
  }

  Future<void> _load() async {
    final session = await AuthService.loadSession();
<<<<<<< HEAD
    final prefs   = await SharedPreferences.getInstance();
    if (!mounted) return;
    setState(() {
      _username  = session['username'];
      _role      = session['role'];
      _baseUrl   = session['base_url'];
      _authMode  = session['auth_mode'];
      _urlCtrl.text   = prefs.getString('base_url')    ?? session['base_url']  ?? '';
      _tokenCtrl.text = prefs.getString('admin_token') ?? session['token']     ?? '';
      _demoMode  = prefs.getBool('demo_mode') ?? false;
=======
    setState(() {
      _username = session['username'];
      _role     = session['role'];
      _baseUrl  = session['base_url'];
      _authMode = session['auth_mode'];
      _urlCtrl.text = session['base_url'] ?? '';
      _urlCtrl.text = prefs.getString('base_url') ?? '';
      _tokenCtrl.text = prefs.getString('admin_token') ?? '';
      _demoMode = prefs.getBool('demo_mode') ?? false;
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
    });
  }

  Future<void> _saveUrl() async {
    final url = _urlCtrl.text.trim().replaceAll(RegExp(r'/$'), '');
    if (url.isEmpty) return;
    setState(() => _savingUrl = true);

<<<<<<< HEAD
    final ok = await ApiService(baseUrl: url, adminToken: _tokenCtrl.text.trim()).ping();
=======
    final ok = await AuthService(baseUrl: url).ping();
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
    if (!mounted) return;

    if (!ok) {
      setState(() => _savingUrl = false);
      ScaffoldMessenger.of(context).showSnackBar(
<<<<<<< HEAD
        const SnackBar(content: Text('Сервер не отвечает. Проверь URL и токен.')),
=======
        const SnackBar(content: Text('Сервер не отвечает')),
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
      );
      return;
    }

<<<<<<< HEAD
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('base_url',     url);
    await prefs.setString('admin_token',  _tokenCtrl.text.trim());
    await prefs.setBool('demo_mode',      _demoMode);

    final session = await AuthService.loadSession();
    await AuthService.saveSession(
      baseUrl:  url,
      token:    _tokenCtrl.text.trim(),
      username: session['username'] ?? 'admin',
      role:     session['role']     ?? 'admin',
      authMode: session['auth_mode'] ?? 'token',
    );
    if (!mounted) return;
    setState(() {
      _baseUrl   = url;
      _savingUrl = false;
    });
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('✅ Настройки сохранены')),
    );
  }

  Future<void> _setDemoMode(bool value) async {
    await ApiService.setDemoMode(value);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('demo_mode', value);
    if (!mounted) return;
    setState(() => _demoMode = value);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(value
          ? 'Demo mode включён — автономная работа'
          : 'Demo mode выключен'),
      ),
    );
  }

=======
    final session = await AuthService.loadSession();
    await AuthService.saveSession(
      baseUrl: url,
      token: session['token'] ?? '',
      username: session['username'] ?? '',
      role: session['role'] ?? 'user',
      authMode: session['auth_mode'] ?? 'login',
    );
    if (!mounted) return;
    setState(() {
      _baseUrl = url;
      _savingUrl = false;
    });
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('✅ Сервер обновлён')),
    );
  }

  /// Logout: clear token but keep URL + auth_mode → back to login or setup
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
  Future<void> _logout() async {
    final mode = _authMode;
    final url  = _baseUrl ?? '';
    await AuthService.clearSession();
    if (!mounted) return;
<<<<<<< HEAD
    final dest = mode == 'login'
        ? LoginScreen(baseUrl: url)
        : const SetupScreen();
    Navigator.of(context).pushAndRemoveUntil(
      NeonPageRoute(child: dest), (_) => false,
    );
  }

=======
    Widget dest = mode == 'login'
        ? LoginScreen(baseUrl: url)
        : const SetupScreen();
    Navigator.of(context).pushAndRemoveUntil(
      NeonPageRoute(child: dest),
      (_) => false,
    );
  }

  /// Switch mode: clears session and goes back to setup
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
  Future<void> _switchMode() async {
    await AuthService.clearSession();
    if (!mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
<<<<<<< HEAD
      NeonPageRoute(child: const SetupScreen()), (_) => false,
=======
      NeonPageRoute(child: const SetupScreen()),
      (_) => false,
    );
  }

  /// Full reset: clears everything
  Future<void> _setDemoMode(bool value) async {
    await ApiService.setDemoMode(value);
    if (!mounted) return;
    setState(() => _demoMode = value);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(value
            ? 'Demo mode enabled — offline data'
            : 'Demo mode disabled'),
      ),
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
    );
  }

  Future<void> _disconnect() async {
    await AuthService.clearAll();
    if (!mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
<<<<<<< HEAD
      NeonPageRoute(child: const SetupScreen()), (_) => false,
=======
      NeonPageRoute(child: const SetupScreen()),
      (_) => false,
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
    );
  }

  @override
  Widget build(BuildContext context) {
<<<<<<< HEAD
    final isLogin   = _authMode == 'login';
    final modeColor = isLogin ? NeonColors.purple : NeonColors.green;
    final modeLabel = isLogin ? 'ЛОГИН / ПАРОЛЬ' : 'ADMIN ТОКЕН';
    final modeIcon  = isLogin ? Icons.person_outlined : Icons.key_outlined;
=======
    final isLogin = _authMode == 'login';
    final modeColor  = isLogin ? NeonColors.purple : NeonColors.green;
    final modeLabel  = isLogin ? 'ЛОГИН / ПАРОЛЬ' : 'ADMIN ТОКЕН';
    final modeIcon   = isLogin ? Icons.person_outlined : Icons.key_outlined;
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999

    return Scaffold(
      backgroundColor: NeonColors.bgDeep,
      appBar: AppBar(
        title: const NeonText('КОНФИГУРАЦИЯ', fontFamily: 'Orbitron',
            fontSize: 14, fontWeight: FontWeight.w700, glowRadius: 8),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [

<<<<<<< HEAD
            // ── Auth mode badge ────────────────────────────────────────────
=======
            // ── Auth mode badge ──────────────────────────────────────────────
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
            NeonCard(
              glowColor: modeColor,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
<<<<<<< HEAD
                  const NeonText('> РЕЖИМ ДОСТУПА',
                      color: NeonColors.textSecondary,
=======
                  const NeonText('> РЕЖИМ ДОСТУПА', color: NeonColors.textSecondary,
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
                      fontSize: 10, fontFamily: 'Orbitron', glowRadius: 2),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: modeColor.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(color: modeColor.withOpacity(0.4)),
                        ),
                        child: Icon(modeIcon, color: modeColor, size: 22),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            NeonText(modeLabel,
<<<<<<< HEAD
                                color: modeColor, fontSize: 13,
                                fontFamily: 'Orbitron',
                                fontWeight: FontWeight.w700, glowRadius: 4),
                            const SizedBox(height: 3),
                            Text(
                              isLogin ? 'Авторизация через сервер'
                                      : 'Прямой токен доступа',
                              style: const TextStyle(
                                color: NeonColors.textSecondary,
                                fontFamily: 'JetBrainsMono', fontSize: 10,
=======
                                color: modeColor,
                                fontSize: 13, fontFamily: 'Orbitron',
                                fontWeight: FontWeight.w700, glowRadius: 4),
                            const SizedBox(height: 3),
                            Text(
                              isLogin
                                  ? 'Авторизация через сервер'
                                  : 'Прямой токен доступа',
                              style: const TextStyle(
                                color: NeonColors.textSecondary,
                                fontFamily: 'JetBrainsMono',
                                fontSize: 10,
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
                              ),
                            ),
                          ],
                        ),
                      ),
                      GestureDetector(
                        onTap: _switchMode,
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 10, vertical: 6),
                          decoration: BoxDecoration(
                            color: NeonColors.bgCard,
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(
                                color: NeonColors.textDisabled.withOpacity(0.4)),
                          ),
<<<<<<< HEAD
                          child: const Text('СМЕНИТЬ',
                              style: TextStyle(
                                color: NeonColors.textSecondary,
                                fontFamily: 'Orbitron', fontSize: 9,
                                fontWeight: FontWeight.w700)),
=======
                          child: const Text(
                            'СМЕНИТЬ',
                            style: TextStyle(
                              color: NeonColors.textSecondary,
                              fontFamily: 'Orbitron',
                              fontSize: 9,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ).animate().fadeIn(duration: 300.ms),

            const SizedBox(height: 14),

<<<<<<< HEAD
            // ── Account ────────────────────────────────────────────────────
=======
            // ── Account section ──────────────────────────────────────────────
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
            NeonCard(
              glowColor: NeonColors.cyan,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
<<<<<<< HEAD
                  const NeonText('> АККАУНТ',
                      color: NeonColors.cyan,
                      fontSize: 11, fontFamily: 'Orbitron', glowRadius: 4),
                  const SizedBox(height: 14),
=======
                  const NeonText('> АККАУНТ', color: NeonColors.cyan,
                      fontSize: 11, fontFamily: 'Orbitron', glowRadius: 4),
                  const SizedBox(height: 14),

>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: NeonColors.cyan.withOpacity(0.1),
                          shape: BoxShape.circle,
                          border: Border.all(
                              color: NeonColors.cyan.withOpacity(0.4)),
                        ),
                        child: const Icon(Icons.person,
                            color: NeonColors.cyan, size: 22),
                      ),
                      const SizedBox(width: 14),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
<<<<<<< HEAD
                          NeonText(_username ?? '...',
                              color: NeonColors.textPrimary, fontSize: 14,
                              fontFamily: 'Orbitron',
                              fontWeight: FontWeight.w700),
=======
                          NeonText(
                            _username ?? '...',
                            color: NeonColors.textPrimary,
                            fontSize: 14,
                            fontFamily: 'Orbitron',
                            fontWeight: FontWeight.w700,
                          ),
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
                          const SizedBox(height: 4),
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 8, vertical: 2),
                            decoration: BoxDecoration(
                              color: (_role == 'admin'
<<<<<<< HEAD
                                      ? NeonColors.cyan : NeonColors.purple)
=======
                                      ? NeonColors.cyan
                                      : NeonColors.purple)
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
                                  .withOpacity(0.1),
                              borderRadius: BorderRadius.circular(4),
                              border: Border.all(
                                color: (_role == 'admin'
<<<<<<< HEAD
                                        ? NeonColors.cyan : NeonColors.purple)
=======
                                        ? NeonColors.cyan
                                        : NeonColors.purple)
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
                                    .withOpacity(0.5),
                              ),
                            ),
                            child: Text(
                              (_role ?? 'user').toUpperCase(),
                              style: TextStyle(
                                color: _role == 'admin'
<<<<<<< HEAD
                                    ? NeonColors.cyan : NeonColors.purple,
                                fontSize: 9, fontFamily: 'Orbitron',
                                fontWeight: FontWeight.w700, letterSpacing: 1,
=======
                                    ? NeonColors.cyan
                                    : NeonColors.purple,
                                fontSize: 9,
                                fontFamily: 'Orbitron',
                                fontWeight: FontWeight.w700,
                                letterSpacing: 1,
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
<<<<<<< HEAD
                  const SizedBox(height: 14),
=======

                  const SizedBox(height: 14),

>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
                  _OutlineButton(
                    label: 'ВЫЙТИ ИЗ АККАУНТА',
                    icon: Icons.logout,
                    color: NeonColors.cyan,
                    onTap: () => _confirmDialog(
                      title: 'ВЫЙТИ?',
<<<<<<< HEAD
                      body: isLogin ? 'Вернёт на экран входа.'
                                    : 'Вернёт на экран настройки токена.',
=======
                      body: isLogin
                          ? 'Вернёт на экран входа.'
                          : 'Вернёт на экран настройки токена.',
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
                      color: NeonColors.cyan,
                      actionLabel: 'ВЫЙТИ',
                      onConfirm: _logout,
                    ),
                  ),
                ],
              ),
            ).animate().fadeIn(delay: 100.ms, duration: 400.ms),

            const SizedBox(height: 14),

<<<<<<< HEAD
            // ── Server settings ────────────────────────────────────────────
=======
            // ── Server settings ──────────────────────────────────────────────
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
            NeonCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
<<<<<<< HEAD
                  const NeonText('> СЕРВЕР',
                      color: NeonColors.purple,
=======
                  const NeonText('> СЕРВЕР', color: NeonColors.purple,
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
                      fontSize: 11, fontFamily: 'Orbitron', glowRadius: 4),
                  const SizedBox(height: 14),

                  NeonTextField(
                    controller: _urlCtrl,
                    label: 'АДРЕС СЕРВЕРА',
                    hint: 'http://192.168.1.1:8080',
                    prefixIcon: Icons.dns_outlined,
                    color: NeonColors.purple,
                    keyboardType: TextInputType.url,
                  ),
<<<<<<< HEAD
=======
                  const SizedBox(height: 14),

                  _savingUrl
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
                  const SizedBox(height: 12),
                  NeonTextField(
                    controller: _tokenCtrl,
                    label: 'ADMIN TOKEN',
                    hint: '••••••••',
                    prefixIcon: Icons.key_outlined,
                    obscureText: _obscureToken,
                    suffixIcon: IconButton(
                      icon: Icon(
                        _obscureToken
                            ? Icons.visibility_outlined
                            : Icons.visibility_off_outlined,
<<<<<<< HEAD
                        color: NeonColors.textSecondary, size: 18,
=======
                        color: NeonColors.textSecondary,
                        size: 18,
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
                      ),
                      onPressed: () =>
                          setState(() => _obscureToken = !_obscureToken),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
<<<<<<< HEAD
                      const NeonText('DEMO MODE',
                          color: NeonColors.green, fontSize: 11,
                          fontFamily: 'Orbitron', glowRadius: 4),
                      const SizedBox(width: 8),
                      const Text('Работа без сервера',
                          style: TextStyle(
                            color: NeonColors.textSecondary,
                            fontSize: 10, fontFamily: 'JetBrainsMono')),
=======
                      const NeonText(
                        'DEMO MODE',
                        color: NeonColors.green,
                        fontSize: 11,
                        fontFamily: 'Orbitron',
                        glowRadius: 4,
                      ),
                      const SizedBox(width: 8),
                      const Text(
                        'Работа без сервера',
                        style: TextStyle(
                          color: NeonColors.textSecondary,
                          fontSize: 10,
                          fontFamily: 'JetBrainsMono',
                        ),
                      ),
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
                      const Spacer(),
                      Switch(
                        value: _demoMode,
                        onChanged: _setDemoMode,
                        activeColor: NeonColors.green,
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
<<<<<<< HEAD
                  _savingUrl
=======
                  _saving
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
                      ? const Center(
                          child: NeonLoadingIndicator(
                              size: 30, label: 'ПРОВЕРЯЕМ...'))
                      : SizedBox(
                          width: double.infinity,
                          child: ElevatedButton.icon(
                            onPressed: _saveUrl,
                            icon: const Icon(Icons.save_outlined, size: 16),
                            label: const Text('СОХРАНИТЬ'),
                          ),
                        ),
                ],
              ),
            ).animate().fadeIn(delay: 200.ms, duration: 400.ms),

            const SizedBox(height: 14),

<<<<<<< HEAD
            // ── GCP reconnect ──────────────────────────────────────────────
=======
            // ── App info ─────────────────────────────────────────────────────
            // GCP Server Connection
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
            NeonCard(
              glowColor: NeonColors.cyan,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
<<<<<<< HEAD
                  const NeonText('> GCP SERVER CONNECTION',
                      color: NeonColors.cyan,
                      fontSize: 11, fontFamily: 'Orbitron', glowRadius: 4),
                  const SizedBox(height: 12),
                  const Text('Переконфигурировать подключение к GCP Docker-серверу',
                      style: TextStyle(
                        color: NeonColors.textSecondary,
                        fontFamily: 'JetBrainsMono', fontSize: 11)),
=======
                  const NeonText(
                    '> GCP SERVER CONNECTION',
                    color: NeonColors.cyan,
                    fontSize: 11,
                    fontFamily: 'Orbitron',
                    glowRadius: 4,
                  ),
                  const SizedBox(height: 12),
                  const Text(
                    'Переконфигурировать подключение к GCP Docker-серверу',
                    style: TextStyle(
                      color: NeonColors.textSecondary,
                      fontFamily: 'JetBrainsMono',
                      fontSize: 11,
                    ),
                  ),
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
                  const SizedBox(height: 12),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
<<<<<<< HEAD
                      onPressed: () => Navigator.of(context).push(
                        NeonPageRoute(child: const SetupScreen()),
                      ),
=======
                      onPressed: () {
                        Navigator.of(context).push(
                          NeonPageRoute(child: const SetupScreen()),
                        );
                      },
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
                      icon: const Icon(Icons.cloud_outlined, size: 16),
                      label: const Text('ПЕРЕПОДКЛЮЧИТЬ / ПЕРЕНАСТРОИТЬ'),
                    ),
                  ),
                ],
              ),
<<<<<<< HEAD
            ).animate().fadeIn(delay: 250.ms, duration: 400.ms),

            const SizedBox(height: 14),

            // ── About ──────────────────────────────────────────────────────
=======
            ).animate().fadeIn(delay: 50.ms, duration: 400.ms),

            const SizedBox(height: 16),
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
            NeonCard(
              glowColor: NeonColors.green,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
<<<<<<< HEAD
                  const NeonText('> О ПРИЛОЖЕНИИ',
                      color: NeonColors.green,
                      fontSize: 11, fontFamily: 'Orbitron', glowRadius: 4),
                  const SizedBox(height: 10),
                  _InfoRow('Версия', '1.1.0'),
                  _InfoRow('Платформа', 'Android'),
                  _InfoRow('Тема', 'Neon Dark'),
                  if (_baseUrl != null) _InfoRow('Сервер', _baseUrl!),
=======
                  const NeonText('> О ПРИЛОЖЕНИИ', color: NeonColors.green,
                      fontSize: 11, fontFamily: 'Orbitron', glowRadius: 4),
                  const SizedBox(height: 10),
                  _InfoRow('Версия', '1.0.0'),
                  _InfoRow('Платформа', 'Android'),
                  _InfoRow('Тема', 'Neon Dark'),
                  if (_baseUrl != null)
                    _InfoRow('Сервер', _baseUrl!),
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
                ],
              ),
            ).animate().fadeIn(delay: 300.ms, duration: 400.ms),

            const SizedBox(height: 14),

<<<<<<< HEAD
            // ── Danger zone ────────────────────────────────────────────────
=======
            // ── Danger zone ──────────────────────────────────────────────────
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
            NeonCard(
              glowColor: NeonColors.pink,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
<<<<<<< HEAD
                  const NeonText('> ОПАСНАЯ ЗОНА',
                      color: NeonColors.pink,
=======
                  const NeonText('> ОПАСНАЯ ЗОНА', color: NeonColors.pink,
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
                      fontSize: 11, fontFamily: 'Orbitron', glowRadius: 4),
                  const SizedBox(height: 10),
                  _OutlineButton(
                    label: 'СБРОСИТЬ И ПЕРЕПОДКЛЮЧИТЬСЯ',
                    icon: Icons.link_off,
                    color: NeonColors.pink,
                    onTap: () => _confirmDialog(
                      title: 'СБРОСИТЬ ВСЁ?',
                      body: 'Все настройки и сессия будут удалены.',
                      color: NeonColors.pink,
                      actionLabel: 'СБРОСИТЬ',
                      onConfirm: _disconnect,
                    ),
                  ),
                ],
              ),
            ).animate().fadeIn(delay: 400.ms, duration: 400.ms),

            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }

  void _confirmDialog({
    required String title,
    required String body,
    required Color color,
    required String actionLabel,
    required VoidCallback onConfirm,
  }) {
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: NeonColors.bgDark,
        title: NeonText(title,
            color: color, fontSize: 14, fontFamily: 'Orbitron'),
<<<<<<< HEAD
        content: Text(body,
            style: const TextStyle(
              color: NeonColors.textSecondary,
              fontFamily: 'JetBrainsMono', fontSize: 12)),
=======
        content: Text(
          body,
          style: const TextStyle(
            color: NeonColors.textSecondary,
            fontFamily: 'JetBrainsMono',
            fontSize: 12,
          ),
        ),
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('ОТМЕНА',
                style: TextStyle(color: NeonColors.textSecondary)),
          ),
          TextButton(
<<<<<<< HEAD
            onPressed: () { Navigator.pop(context); onConfirm(); },
=======
            onPressed: () {
              Navigator.pop(context);
              onConfirm();
            },
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
            child: NeonText(actionLabel,
                color: color, fontFamily: 'Orbitron', fontSize: 12),
          ),
        ],
      ),
    );
  }
}

<<<<<<< HEAD
// ── Shared widgets ─────────────────────────────────────────────────────────────
=======
// ── Shared widgets ────────────────────────────────────────────────────────────
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999

class _OutlineButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final Color color;
  final VoidCallback onTap;

  const _OutlineButton({
<<<<<<< HEAD
    required this.label, required this.icon,
    required this.color, required this.onTap,
=======
    required this.label,
    required this.icon,
    required this.color,
    required this.onTap,
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(vertical: 11),
        decoration: BoxDecoration(
          color: color.withOpacity(0.1),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: color.withOpacity(0.5)),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, color: color, size: 16),
            const SizedBox(width: 8),
<<<<<<< HEAD
            NeonText(label, color: color, fontSize: 10,
                fontFamily: 'Orbitron', fontWeight: FontWeight.w700),
=======
            NeonText(label,
                color: color,
                fontSize: 10, fontFamily: 'Orbitron',
                fontWeight: FontWeight.w700),
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
          ],
        ),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;
  const _InfoRow(this.label, this.value);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        children: [
          Text(label,
              style: const TextStyle(
                color: NeonColors.textSecondary,
<<<<<<< HEAD
                fontFamily: 'JetBrainsMono', fontSize: 11)),
=======
                fontFamily: 'JetBrainsMono',
                fontSize: 11,
              )),
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
          const Spacer(),
          Flexible(
            child: Text(value,
                textAlign: TextAlign.right,
                style: const TextStyle(
                  color: NeonColors.textPrimary,
<<<<<<< HEAD
                  fontFamily: 'JetBrainsMono', fontSize: 11,
                  fontWeight: FontWeight.w700)),
=======
                  fontFamily: 'JetBrainsMono',
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                )),
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
          ),
        ],
      ),
    );
  }
}
