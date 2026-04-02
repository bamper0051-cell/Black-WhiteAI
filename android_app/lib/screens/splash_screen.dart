// splash_screen.dart — Boot/Splash screen with neon animation

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../animations/neon_animations.dart';
import 'setup_screen.dart';
import 'login_screen.dart';
import 'main_shell.dart';

class SplashScreen extends StatelessWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return NeonBootAnimation(
      onComplete: () async {
        final prefs = await SharedPreferences.getInstance();
        final baseUrl = prefs.getString('base_url');
        final token = prefs.getString('auth_token');

        if (!context.mounted) return;

        if (baseUrl == null || baseUrl.isEmpty) {
          // Нет сохранённого сервера — сначала настройка
          Navigator.of(context).pushReplacement(
            NeonPageRoute(child: const SetupScreen()),
          );
        } else if (token == null || token.isEmpty) {
          // Сервер есть, но не залогинены — экран входа
          Navigator.of(context).pushReplacement(
            NeonPageRoute(child: const LoginScreen()),
          );
        } else {
          // Всё есть — сразу в приложение
          Navigator.of(context).pushReplacement(
            NeonPageRoute(child: const MainShell()),
          );
        }
      },
    );
  }
}
