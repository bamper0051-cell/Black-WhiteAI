// splash_screen.dart — Boot animation + auto-connect to server

import 'package:flutter/material.dart';
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
        final session = await AuthService.loadSession();

        if (!context.mounted) return;

        final baseUrl = session['base_url'];
        final token = session['token'];

        // No server configured — go to setup
        if (baseUrl == null || baseUrl.isEmpty) {
          Navigator.of(context).pushReplacement(
            NeonPageRoute(child: const SetupScreen()),
          );
          return;
        }

        // Server configured but not logged in — ping then go to login
        if (token == null || token.isEmpty) {
          Navigator.of(context).pushReplacement(
            NeonPageRoute(child: LoginScreen(baseUrl: baseUrl)),
          );
          return;
        }

        // Fully logged in — auto-connect to main shell
        Navigator.of(context).pushReplacement(
          NeonPageRoute(child: const MainShell()),
        );
      },
    );
  }
}
