// splash_screen.dart — Boot animation + session-aware routing
//
// Routing logic:
//   demo_mode = true         → MainShell (offline)
//   No base_url or token     → SetupScreen (GCP config)
//   Has base_url + token     → MainShell (auto-connect)

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../animations/neon_animations.dart';
import 'setup_screen.dart';
import 'main_shell.dart';

class SplashScreen extends StatelessWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return NeonBootAnimation(
      onComplete: () async {
        final prefs = await SharedPreferences.getInstance();
        final baseUrl = prefs.getString('base_url');
        final token = prefs.getString('admin_token');
        final demoMode = prefs.getBool('demo_mode') ?? false;

        if (!context.mounted) return;

        if (demoMode) {
          Navigator.of(context).pushReplacement(
            NeonPageRoute(child: const MainShell()),
          );
        } else if (baseUrl == null || baseUrl.isEmpty ||
            token == null || token.isEmpty) {
          Navigator.of(context).pushReplacement(
            NeonPageRoute(child: const SetupScreen()),
          );
        } else {
          // Fully configured — go to main shell
          Navigator.of(context).pushReplacement(
            NeonPageRoute(child: const MainShell()),
          );
        }
      },
    );
  }
}
