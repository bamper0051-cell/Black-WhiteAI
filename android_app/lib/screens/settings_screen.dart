// settings_screen.dart — App settings, account management, server config

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../theme/neon_theme.dart';
import '../animations/neon_animations.dart';
import '../widgets/neon_text_field.dart';
import '../widgets/neon_card.dart';
import '../services/auth_service.dart';
import 'setup_screen.dart';
import 'login_screen.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _urlCtrl = TextEditingController();
  bool _savingUrl = false;

  String? _username;
  String? _role;
  String? _baseUrl;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _urlCtrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final session = await AuthService.loadSession();
    setState(() {
      _username = session['username'];
      _role = session['role'];
      _baseUrl = session['base_url'];
      _urlCtrl.text = session['base_url'] ?? '';
    });
  }

  Future<void> _saveUrl() async {
    final url = _urlCtrl.text.trim().replaceAll(RegExp(r'/$'), '');
    if (url.isEmpty) return;
    setState(() => _savingUrl = true);

    // Test connection
    final auth = AuthService(baseUrl: url);
    final ok = await auth.ping();
    if (!mounted) return;

    if (!ok) {
      setState(() => _savingUrl = false);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Сервер не отвечает')),
      );
      return;
    }

    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('base_url', url);
    if (!mounted) return;
    setState(() {
      _baseUrl = url;
      _savingUrl = false;
    });
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('✅ Сервер обновлён')),
    );
  }

  Future<void> _logout() async {
    await AuthService.clearSession();
    if (!mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
      NeonPageRoute(child: LoginScreen(baseUrl: _baseUrl ?? '')),
      (_) => false,
    );
  }

  Future<void> _disconnect() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();
    if (!mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
      NeonPageRoute(child: const SetupScreen()),
      (_) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
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
            // ── Account section ──────────────────────────────────────────────
            NeonCard(
              glowColor: NeonColors.purple,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const NeonText('> АККАУНТ', color: NeonColors.purple,
                      fontSize: 11, fontFamily: 'Orbitron', glowRadius: 4),
                  const SizedBox(height: 16),

                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: NeonColors.purple.withOpacity(0.1),
                          shape: BoxShape.circle,
                          border: Border.all(
                              color: NeonColors.purple.withOpacity(0.4)),
                        ),
                        child: const Icon(Icons.person,
                            color: NeonColors.purple, size: 24),
                      ),
                      const SizedBox(width: 14),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          NeonText(
                            _username ?? '...',
                            color: NeonColors.textPrimary,
                            fontSize: 14,
                            fontFamily: 'Orbitron',
                            fontWeight: FontWeight.w700,
                          ),
                          const SizedBox(height: 4),
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 8, vertical: 2),
                            decoration: BoxDecoration(
                              color: _role == 'admin'
                                  ? NeonColors.cyan.withOpacity(0.1)
                                  : NeonColors.purple.withOpacity(0.1),
                              borderRadius: BorderRadius.circular(4),
                              border: Border.all(
                                color: _role == 'admin'
                                    ? NeonColors.cyan.withOpacity(0.5)
                                    : NeonColors.purple.withOpacity(0.5),
                              ),
                            ),
                            child: Text(
                              (_role ?? 'user').toUpperCase(),
                              style: TextStyle(
                                color: _role == 'admin'
                                    ? NeonColors.cyan
                                    : NeonColors.purple,
                                fontSize: 9,
                                fontFamily: 'Orbitron',
                                fontWeight: FontWeight.w700,
                                letterSpacing: 1,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),

                  const SizedBox(height: 16),

                  SizedBox(
                    width: double.infinity,
                    child: GestureDetector(
                      onTap: () => showDialog(
                        context: context,
                        builder: (_) => AlertDialog(
                          backgroundColor: NeonColors.bgDark,
                          title: const NeonText('ВЫЙТИ?',
                              color: NeonColors.purple,
                              fontSize: 14, fontFamily: 'Orbitron'),
                          content: const Text(
                            'Вы будете перенаправлены на экран входа.',
                            style: TextStyle(
                              color: NeonColors.textSecondary,
                              fontFamily: 'JetBrainsMono',
                              fontSize: 12,
                            ),
                          ),
                          actions: [
                            TextButton(
                              onPressed: () => Navigator.pop(context),
                              child: const Text('ОТМЕНА',
                                  style: TextStyle(
                                      color: NeonColors.textSecondary)),
                            ),
                            TextButton(
                              onPressed: () {
                                Navigator.pop(context);
                                _logout();
                              },
                              child: const NeonText('ВЫЙТИ',
                                  color: NeonColors.purple,
                                  fontFamily: 'Orbitron', fontSize: 12),
                            ),
                          ],
                        ),
                      ),
                      child: Container(
                        padding: const EdgeInsets.symmetric(vertical: 10),
                        decoration: BoxDecoration(
                          color: NeonColors.purple.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(
                              color: NeonColors.purple.withOpacity(0.5)),
                        ),
                        child: const Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.logout,
                                color: NeonColors.purple, size: 16),
                            SizedBox(width: 8),
                            NeonText('ВЫЙТИ ИЗ АККАУНТА',
                                color: NeonColors.purple,
                                fontSize: 11, fontFamily: 'Orbitron',
                                fontWeight: FontWeight.w700),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ).animate().fadeIn(duration: 400.ms),

            const SizedBox(height: 16),

            // ── Server settings ──────────────────────────────────────────────
            NeonCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const NeonText('> СЕРВЕР', color: NeonColors.cyan,
                      fontSize: 11, fontFamily: 'Orbitron', glowRadius: 4),
                  const SizedBox(height: 16),

                  NeonTextField(
                    controller: _urlCtrl,
                    label: 'АДРЕС СЕРВЕРА',
                    hint: 'http://192.168.1.1:8080',
                    prefixIcon: Icons.dns_outlined,
                    keyboardType: TextInputType.url,
                  ),
                  const SizedBox(height: 16),

                  _savingUrl
                      ? const Center(
                          child: NeonLoadingIndicator(
                              size: 32, label: 'ПРОВЕРЯЕМ...'))
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
            ).animate().fadeIn(delay: 100.ms, duration: 400.ms),

            const SizedBox(height: 16),

            // ── App info ─────────────────────────────────────────────────────
            NeonCard(
              glowColor: NeonColors.green,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const NeonText('> О ПРИЛОЖЕНИИ', color: NeonColors.green,
                      fontSize: 11, fontFamily: 'Orbitron', glowRadius: 4),
                  const SizedBox(height: 12),
                  _InfoRow('Версия', '1.0.0'),
                  _InfoRow('Платформа', 'Android'),
                  _InfoRow('Тема', 'Neon Dark'),
                  _InfoRow('Framework', 'Flutter 3.x'),
                  if (_baseUrl != null)
                    _InfoRow('Сервер', _baseUrl!),
                ],
              ),
            ).animate().fadeIn(delay: 200.ms, duration: 400.ms),

            const SizedBox(height: 16),

            // ── Danger zone ──────────────────────────────────────────────────
            NeonCard(
              glowColor: NeonColors.pink,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const NeonText('> ОПАСНАЯ ЗОНА', color: NeonColors.pink,
                      fontSize: 11, fontFamily: 'Orbitron', glowRadius: 4),
                  const SizedBox(height: 12),
                  SizedBox(
                    width: double.infinity,
                    child: GestureDetector(
                      onTap: () => showDialog(
                        context: context,
                        builder: (_) => AlertDialog(
                          backgroundColor: NeonColors.bgDark,
                          title: const NeonText('СБРОСИТЬ ВСЁ?',
                              color: NeonColors.pink,
                              fontSize: 14, fontFamily: 'Orbitron'),
                          content: const Text(
                            'Все настройки и сессия будут удалены.',
                            style: TextStyle(
                              color: NeonColors.textSecondary,
                              fontFamily: 'JetBrainsMono',
                              fontSize: 12,
                            ),
                          ),
                          actions: [
                            TextButton(
                              onPressed: () => Navigator.pop(context),
                              child: const Text('ОТМЕНА',
                                  style: TextStyle(
                                      color: NeonColors.textSecondary)),
                            ),
                            TextButton(
                              onPressed: () {
                                Navigator.pop(context);
                                _disconnect();
                              },
                              child: const NeonText('СБРОСИТЬ',
                                  color: NeonColors.pink,
                                  fontFamily: 'Orbitron', fontSize: 12),
                            ),
                          ],
                        ),
                      ),
                      child: Container(
                        padding: const EdgeInsets.symmetric(vertical: 12),
                        decoration: BoxDecoration(
                          color: NeonColors.pink.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(
                              color: NeonColors.pink.withOpacity(0.5)),
                        ),
                        child: const Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.link_off,
                                color: NeonColors.pink, size: 16),
                            SizedBox(width: 8),
                            NeonText('СБРОСИТЬ И ПЕРЕПОДКЛЮЧИТЬСЯ',
                                color: NeonColors.pink,
                                fontSize: 10, fontFamily: 'Orbitron',
                                fontWeight: FontWeight.w700),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ).animate().fadeIn(delay: 300.ms, duration: 400.ms),

            const SizedBox(height: 24),
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
          Text(
            label,
            style: const TextStyle(
              color: NeonColors.textSecondary,
              fontFamily: 'JetBrainsMono',
              fontSize: 11,
            ),
          ),
          const Spacer(),
          Flexible(
            child: Text(
              value,
              textAlign: TextAlign.right,
              style: const TextStyle(
                color: NeonColors.textPrimary,
                fontFamily: 'JetBrainsMono',
                fontSize: 11,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
