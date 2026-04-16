import 'package:flutter/material.dart';
import '../theme/neon_theme.dart';
import '../animations/neon_animations.dart';
import '../services/auth_service.dart';
import '../widgets/neon_text_field.dart';
import 'main_shell.dart';
import 'setup_screen.dart';

class LoginScreen extends StatefulWidget {
  final String baseUrl;
  const LoginScreen({super.key, required this.baseUrl});
  @override State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _userCtrl = TextEditingController();
  final _passCtrl = TextEditingController();
  bool _isRegister = false, _loading = false, _obscure = true;
  String? _error;

  @override void dispose() { _userCtrl.dispose(); _passCtrl.dispose(); super.dispose(); }

  Future<void> _submit() async {
    final u = _userCtrl.text.trim(), p = _passCtrl.text;
    if (u.isEmpty || p.isEmpty) { setState(() => _error = 'Заполни все поля'); return; }
    setState(() { _loading = true; _error = null; });
    final auth = AuthService(baseUrl: widget.baseUrl);
    final r = _isRegister ? await auth.register(u, p) : await auth.login(u, p);
    if (!mounted) return;
    if (r.ok) {
      await AuthService.saveSession(baseUrl: widget.baseUrl, token: r.token!, username: r.username!, role: r.role ?? 'user', authMode: 'login');
      Navigator.of(context).pushAndRemoveUntil(NeonPageRoute(child: const MainShell()), (_) => false);
    } else {
      setState(() { _error = r.error; _loading = false; });
    }
  }

  @override Widget build(BuildContext context) => Scaffold(
    backgroundColor: NeonColors.bgDeep,
    body: SafeArea(child: SingleChildScrollView(padding: const EdgeInsets.all(24), child: Column(children: [
      const SizedBox(height: 48),
      NeonText(_isRegister ? 'РЕГИСТРАЦИЯ' : 'ВХОД', color: NeonColors.cyan, fontSize: 28, fontWeight: FontWeight.w700, fontFamily: 'Orbitron', glowRadius: 16),
      const SizedBox(height: 8),
      Text(widget.baseUrl, style: const TextStyle(color: NeonColors.textSecondary, fontFamily: 'JetBrainsMono', fontSize: 11)),
      const SizedBox(height: 40),
      Container(padding: const EdgeInsets.all(24), decoration: neonCardDecoration(glowColor: _isRegister ? NeonColors.purple : NeonColors.cyan), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        NeonTextField(controller: _userCtrl, label: 'ЛОГИН', hint: 'username', prefixIcon: Icons.person_outline, onChanged: (_) => setState(() => _error = null)),
        const SizedBox(height: 14),
        NeonTextField(controller: _passCtrl, label: 'ПАРОЛЬ', hint: '••••••••', prefixIcon: Icons.lock_outline, obscureText: _obscure, suffixIcon: IconButton(icon: Icon(_obscure ? Icons.visibility_outlined : Icons.visibility_off_outlined, color: NeonColors.textSecondary, size: 18), onPressed: () => setState(() => _obscure = !_obscure)), onChanged: (_) => setState(() => _error = null)),
        if (_error != null) ...[const SizedBox(height: 12), Container(padding: const EdgeInsets.all(10), decoration: BoxDecoration(color: NeonColors.pink.withOpacity(0.1), borderRadius: BorderRadius.circular(6), border: Border.all(color: NeonColors.pink.withOpacity(0.5))), child: Text(_error!, style: const TextStyle(color: NeonColors.pink, fontFamily: 'JetBrainsMono', fontSize: 11)))],
        const SizedBox(height: 24),
        _loading ? const Center(child: NeonLoadingIndicator(size: 36))
          : GestureDetector(onTap: _submit, child: Container(width: double.infinity, padding: const EdgeInsets.symmetric(vertical: 14), decoration: neonButtonDecoration(color: _isRegister ? NeonColors.purple : NeonColors.cyan), child: Center(child: NeonText(_isRegister ? 'СОЗДАТЬ АККАУНТ' : 'ВОЙТИ', color: _isRegister ? NeonColors.purple : NeonColors.cyan, fontSize: 13, fontFamily: 'Orbitron', fontWeight: FontWeight.w700)))),
      ])),
      const SizedBox(height: 16),
      GestureDetector(onTap: () => setState(() { _isRegister = !_isRegister; _error = null; }), child: Text(_isRegister ? 'Уже есть аккаунт? ВОЙТИ' : 'Нет аккаунта? РЕГИСТРАЦИЯ', style: const TextStyle(color: NeonColors.cyan, fontFamily: 'JetBrainsMono', fontSize: 12))),
      const SizedBox(height: 12),
      GestureDetector(onTap: () => Navigator.of(context).pop(), child: const Text('← Изменить сервер', style: TextStyle(color: NeonColors.textDisabled, fontFamily: 'JetBrainsMono', fontSize: 10))),
    ]))),
  );
}
