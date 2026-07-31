// splash_screen.dart — Boot animation + session-aware routing

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../animations/neon_animations.dart';
import '../services/auth_service.dart';
import 'setup_screen.dart';
import 'login_screen.dart';
import 'main_shell.dart';

class SplashScreen extends StatelessWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return NeonBootAnimation(
      onComplete: () async {
        final prefs    = await SharedPreferences.getInstance();
        final demoMode = prefs.getBool('demo_mode') ?? false;

        if (!context.mounted) return;

        // Demo mode — skip server auth
        if (demoMode) {
          Navigator.of(context).pushReplacement(
              NeonPageRoute(child: const MainShell()));
          return;
        }

        final session  = await AuthService.loadSession();
        final baseUrl  = session['base_url'];
        final token    = session['token'];
        final authMode = session['auth_mode'];

        if (!context.mounted) return;

        // No server configured
        if (baseUrl == null || baseUrl.isEmpty) {
          Navigator.of(context).pushReplacement(
              NeonPageRoute(child: const SetupScreen()));
          return;
        }

        // Have server but no token
        if (token == null || token.isEmpty) {
          if (authMode == 'login') {
            Navigator.of(context).pushReplacement(
                NeonPageRoute(child: LoginScreen(baseUrl: baseUrl)));
          } else {
            Navigator.of(context).pushReplacement(
                NeonPageRoute(child: const SetupScreen()));
          }
          return;
        }

        // Fully authenticated
        Navigator.of(context).pushReplacement(
            NeonPageRoute(child: const MainShell()));
      },
    );
  }
}
