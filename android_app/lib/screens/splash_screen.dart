// splash_screen.dart — Boot animation + session-aware routing
//
// Routing logic:
//   No base_url              → SetupScreen
//   Has base_url, no token:
//     auth_mode == 'token'   → SetupScreen (re-enter token)
//     auth_mode == 'login'   → LoginScreen
//     auth_mode == null      → SetupScreen
//   Has base_url + token     → MainShell (auto-connect)

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

        final baseUrl  = session['base_url'];
        final token    = session['token'];
        final authMode = session['auth_mode'];

        // No server configured
        if (baseUrl == null || baseUrl.isEmpty) {
        final prefs = await SharedPreferences.getInstance();
        final baseUrl = prefs.getString('base_url');
        final token = prefs.getString('admin_token');
        final demoMode = prefs.getBool('demo_mode') ?? false;

        if (!context.mounted) return;

        if (demoMode) {
          Navigator.of(context).pushReplacement(
            NeonPageRoute(child: const MainShell()),
          );
        } else if (baseUrl == null || token == null) {
          Navigator.of(context).pushReplacement(
            NeonPageRoute(child: const SetupScreen()),
          );
          return;
        }

        // Server known but no token
        if (token == null || token.isEmpty) {
          if (authMode == 'login') {
            Navigator.of(context).pushReplacement(
              NeonPageRoute(child: LoginScreen(baseUrl: baseUrl)),
            );
          } else {
            // token mode or unknown — re-setup
            Navigator.of(context).pushReplacement(
              NeonPageRoute(child: const SetupScreen()),
            );
          }
          return;
        }

        // Fully authenticated — go to main shell
        Navigator.of(context).pushReplacement(
          NeonPageRoute(child: const MainShell()),
        );
      },
    );
  }
}
