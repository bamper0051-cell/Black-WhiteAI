// splash_screen.dart — Boot/Splash screen with neon animation

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

        if (!context.mounted) return;

        if (baseUrl == null || token == null) {
          Navigator.of(context).pushReplacement(
            NeonPageRoute(child: const SetupScreen()),
          );
        } else {
          Navigator.of(context).pushReplacement(
            NeonPageRoute(child: const MainShell()),
          );
        }
      },
    );
  }
}
