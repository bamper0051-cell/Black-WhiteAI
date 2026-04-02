// settings_screen.dart — App settings and server configuration

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../theme/neon_theme.dart';
import '../animations/neon_animations.dart';
import '../widgets/neon_text_field.dart';
import '../widgets/neon_card.dart';
import 'setup_screen.dart';
import 'login_screen.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _urlCtrl = TextEditingController();
  String _username = '';
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _urlCtrl.text = prefs.getString('base_url') ?? '';
      _username = prefs.getString('username') ?? '';
    });
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('base_url', _urlCtrl.text.trim());
    if (!mounted) return;
    setState(() => _saving = false);
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('✅ Settings saved')),
    );
  }

  Future<void> _logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('auth_token');
    await prefs.remove('username');
    if (!mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
      NeonPageRoute(child: const LoginScreen()),
      (_) => false,
    );
  }

  Future<void> _disconnect() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('base_url');
    await prefs.remove('auth_token');
    await prefs.remove('username');
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
            // Server settings
            NeonCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const NeonText('> SERVER', color: NeonColors.cyan,
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
            ).animate().fadeIn(duration: 400.ms),

            const SizedBox(height: 16),

            // Account info
            NeonCard(
              glowColor: NeonColors.purple,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const NeonText('> ACCOUNT', color: NeonColors.purple,
                      fontSize: 11, fontFamily: 'Orbitron', glowRadius: 4),
                  const SizedBox(height: 12),
                  _InfoRow('User', _username.isEmpty ? '—' : _username),
                  const SizedBox(height: 12),
                  SizedBox(
                    width: double.infinity,
                    child: GestureDetector(
                      onTap: _logout,
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
                            Icon(Icons.logout, color: NeonColors.purple, size: 16),
                            SizedBox(width: 8),
                            NeonText('LOGOUT', color: NeonColors.purple,
                                fontSize: 11, fontFamily: 'Orbitron',
                                fontWeight: FontWeight.w700),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ).animate().fadeIn(delay: 100.ms, duration: 400.ms),

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
            ).animate().fadeIn(delay: 150.ms, duration: 400.ms),

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
                          title: const NeonText('DISCONNECT?',
                              color: NeonColors.pink,
                              fontSize: 14, fontFamily: 'Orbitron'),
                          content: const Text(
                            'This will clear all saved settings and log you out.',
                            style: TextStyle(
                              color: NeonColors.textSecondary,
                              fontFamily: 'JetBrainsMono',
                              fontSize: 12,
                            ),
                          ),
                          actions: [
                            TextButton(
                              onPressed: () => Navigator.pop(context),
                              child: const Text('CANCEL',
                                  style: TextStyle(color: NeonColors.textSecondary)),
                            ),
                            TextButton(
                              onPressed: () {
                                Navigator.pop(context);
                                _disconnect();
                              },
                              child: const NeonText('DISCONNECT',
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
                            Icon(Icons.link_off, color: NeonColors.pink, size: 16),
                            SizedBox(width: 8),
                            NeonText('DISCONNECT', color: NeonColors.pink,
                                fontSize: 11, fontFamily: 'Orbitron',
                                fontWeight: FontWeight.w700),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ).animate().fadeIn(delay: 200.ms, duration: 400.ms),
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

