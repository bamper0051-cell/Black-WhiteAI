// settings_screen.dart — App settings and server configuration

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../theme/neon_theme.dart';
import '../animations/neon_animations.dart';
import '../widgets/neon_text_field.dart';
import '../widgets/neon_card.dart';
import 'setup_screen.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _urlCtrl = TextEditingController();
  final _tgTokenCtrl = TextEditingController();
  final _tgAdminCtrl = TextEditingController();
  bool _saving = false;
  bool _obscureTgToken = true;
  String _username = '';
  String _sessionToken = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _urlCtrl.dispose();
    _tgTokenCtrl.dispose();
    _tgAdminCtrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _urlCtrl.text = prefs.getString('base_url') ?? '';
      _tgTokenCtrl.text = prefs.getString('telegram_token') ?? '';
      _tgAdminCtrl.text = prefs.getString('admin_id') ?? '';
      _username = prefs.getString('username') ?? '';
      _sessionToken = prefs.getString('session_token') ?? '';
    });
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('base_url', _urlCtrl.text.trim());
    final tgToken = _tgTokenCtrl.text.trim();
    final tgAdmin = _tgAdminCtrl.text.trim();
    if (tgToken.isNotEmpty) {
      await prefs.setString('telegram_token', tgToken);
    } else {
      await prefs.remove('telegram_token');
    }
    if (tgAdmin.isNotEmpty) {
      await prefs.setString('admin_id', tgAdmin);
    } else {
      await prefs.remove('admin_id');
    }
    if (!mounted) return;
    setState(() => _saving = false);
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('✅ Настройки сохранены')),
    );
  }

  Future<void> _disconnect() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('base_url');
    await prefs.remove('session_token');
    await prefs.remove('username');
    await prefs.remove('telegram_token');
    await prefs.remove('admin_id');
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
        title: const NeonText('CONFIGURATION', fontFamily: 'Orbitron',
            fontSize: 14, fontWeight: FontWeight.w700, glowRadius: 8),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Account info
            NeonCard(
              glowColor: NeonColors.cyan,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const NeonText('> АККАУНТ', color: NeonColors.cyan,
                      fontSize: 11, fontFamily: 'Orbitron', glowRadius: 4),
                  const SizedBox(height: 12),
                  _InfoRow('Пользователь', _username.isNotEmpty ? _username : '—'),
                  _InfoRow('Сессия',
                      _sessionToken.isNotEmpty
                          ? '${_sessionToken.length >= 8 ? _sessionToken.substring(0, 8) : _sessionToken}...'
                          : '—'),
                ],
              ),
            ).animate().fadeIn(duration: 400.ms),

            const SizedBox(height: 16),

            // Server settings
            NeonCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const NeonText('> СЕРВЕР', color: NeonColors.cyan,
                      fontSize: 11, fontFamily: 'Orbitron', glowRadius: 4),
                  const SizedBox(height: 16),
                  NeonTextField(
                    controller: _urlCtrl,
                    label: 'SERVER URL',
                    hint: 'http://192.168.1.1:8080',
                    prefixIcon: Icons.dns_outlined,
                  ),
                  const SizedBox(height: 16),
                  _saving
                      ? const Center(
                          child: NeonLoadingIndicator(size: 32, label: 'SAVING...'))
                      : SizedBox(
                          width: double.infinity,
                          child: ElevatedButton.icon(
                            onPressed: _save,
                            icon: const Icon(Icons.save_outlined, size: 16),
                            label: const Text('SAVE'),
                          ),
                        ),
                ],
              ),
            ).animate().fadeIn(delay: 100.ms, duration: 400.ms),

            const SizedBox(height: 16),

            // Telegram settings
            NeonCard(
              glowColor: NeonColors.purple,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const NeonText('> TELEGRAM', color: NeonColors.purple,
                      fontSize: 11, fontFamily: 'Orbitron', glowRadius: 4),
                  const SizedBox(height: 4),
                  const Text(
                    'Токен бота и ID администратора',
                    style: TextStyle(
                      color: NeonColors.textSecondary,
                      fontSize: 10,
                      fontFamily: 'JetBrainsMono',
                    ),
                  ),
                  const SizedBox(height: 16),
                  NeonTextField(
                    controller: _tgTokenCtrl,
                    label: 'BOT TOKEN',
                    hint: '123456:ABC-DEF...',
                    prefixIcon: Icons.telegram_outlined,
                    obscureText: _obscureTgToken,
                    suffixIcon: IconButton(
                      icon: Icon(
                        _obscureTgToken
                            ? Icons.visibility_outlined
                            : Icons.visibility_off_outlined,
                        color: NeonColors.textSecondary,
                        size: 18,
                      ),
                      onPressed: () =>
                          setState(() => _obscureTgToken = !_obscureTgToken),
                    ),
                  ),
                  const SizedBox(height: 12),
                  NeonTextField(
                    controller: _tgAdminCtrl,
                    label: 'ADMIN ID',
                    hint: '123456789',
                    prefixIcon: Icons.admin_panel_settings_outlined,
                    keyboardType: TextInputType.number,
                  ),
                  const SizedBox(height: 16),
                  _saving
                      ? const SizedBox.shrink()
                      : SizedBox(
                          width: double.infinity,
                          child: ElevatedButton.icon(
                            onPressed: _save,
                            icon: const Icon(Icons.save_outlined, size: 16),
                            label: const Text('SAVE'),
                          ),
                        ),
                ],
              ),
            ).animate().fadeIn(delay: 150.ms, duration: 400.ms),

            const SizedBox(height: 16),

            // App info
            NeonCard(
              glowColor: NeonColors.purple,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const NeonText('> APP INFO', color: NeonColors.purple,
                      fontSize: 11, fontFamily: 'Orbitron', glowRadius: 4),
                  const SizedBox(height: 12),
                  _InfoRow('Version', '1.0.0'),
                  _InfoRow('Platform', 'Android'),
                  _InfoRow('Theme', 'Neon Dark'),
                  _InfoRow('Framework', 'Flutter 3.x'),
                ],
              ),
            ).animate().fadeIn(delay: 200.ms, duration: 400.ms),

            const SizedBox(height: 16),

            // Danger zone
            NeonCard(
              glowColor: NeonColors.pink,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const NeonText('> DANGER ZONE', color: NeonColors.pink,
                      fontSize: 11, fontFamily: 'Orbitron', glowRadius: 4),
                  const SizedBox(height: 12),
                  SizedBox(
                    width: double.infinity,
                    child: GestureDetector(
                      onTap: () => showDialog(
                        context: context,
                        builder: (_) => AlertDialog(
                          backgroundColor: NeonColors.bgDark,
                          title: const NeonText('ВЫЙТИ?',
                              color: NeonColors.pink,
                              fontSize: 14, fontFamily: 'Orbitron'),
                          content: const Text(
                            'Это очистит все сохранённые настройки и выполнит выход.',
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
                                  style: TextStyle(color: NeonColors.textSecondary)),
                            ),
                            TextButton(
                              onPressed: () {
                                Navigator.pop(context);
                                _disconnect();
                              },
                              child: const NeonText('ВЫЙТИ',
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
                            Icon(Icons.logout, color: NeonColors.pink, size: 16),
                            SizedBox(width: 8),
                            NeonText('ВЫЙТИ', color: NeonColors.pink,
                                fontSize: 11, fontFamily: 'Orbitron',
                                fontWeight: FontWeight.w700),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ).animate().fadeIn(delay: 250.ms, duration: 400.ms),
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
          Text(
            value,
            style: const TextStyle(
              color: NeonColors.textPrimary,
              fontFamily: 'JetBrainsMono',
              fontSize: 11,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}
