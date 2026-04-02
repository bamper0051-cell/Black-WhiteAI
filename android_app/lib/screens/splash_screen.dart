// splash_screen.dart — Boot/Splash screen with neon animation + server startup

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../animations/neon_animations.dart';
import '../services/api_service.dart';
import 'setup_screen.dart';
import 'login_screen.dart';
import 'main_shell.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  // Route decision resolved during boot animation
  Widget? _nextScreen;

  @override
  void initState() {
    super.initState();
    _checkState();
  }

  /// Pings the server and checks auth state in parallel with boot animation.
  Future<void> _checkState() async {
    final prefs = await SharedPreferences.getInstance();
    final baseUrl = prefs.getString('base_url');
    final adminToken = prefs.getString('admin_token') ?? '';
    final appToken = prefs.getString('app_token');

    if (baseUrl == null || baseUrl.isEmpty) {
      _nextScreen = const SetupScreen();
      return;
    }

    // Try to connect to server (server startup check)
    try {
      final api = ApiService(baseUrl: baseUrl, adminToken: adminToken);
      await api.ping();
    } catch (_) {
      // Server unreachable — still proceed, user can retry from settings
    }

    if (appToken == null || appToken.isEmpty) {
      _nextScreen = const LoginScreen();
    } else {
      _nextScreen = const MainShell();
    }
  }

  @override
  Widget build(BuildContext context) {
    return NeonBootAnimation(
      onComplete: () async {
        // Ensure _checkState has finished
        if (_nextScreen == null) {
          final prefs = await SharedPreferences.getInstance();
          final baseUrl = prefs.getString('base_url');
          if (baseUrl == null || baseUrl.isEmpty) {
            _nextScreen = const SetupScreen();
          } else {
            final appToken = prefs.getString('app_token');
            _nextScreen = (appToken != null && appToken.isNotEmpty)
                ? const MainShell()
                : const LoginScreen();
          }
        }

        if (!context.mounted) return;
        Navigator.of(context).pushReplacement(
          NeonPageRoute(child: _nextScreen!),
        );
      },
    );
  }
}
