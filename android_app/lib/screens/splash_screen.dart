// splash_screen.dart — Boot animation + session-aware routing
<<<<<<< HEAD

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
=======
//
// Routing logic:
//   No base_url              → SetupScreen
//   Has base_url, no token:
//     auth_mode == 'token'   → SetupScreen (re-enter token)
//     auth_mode == 'login'   → LoginScreen
//     auth_mode == null      → SetupScreen
//   Has base_url + token     → MainShell (auto-connect)

import 'package:flutter/material.dart';
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
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
<<<<<<< HEAD
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
=======
        final session = await AuthService.loadSession();
        if (!context.mounted) return;

>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
        final baseUrl  = session['base_url'];
        final token    = session['token'];
        final authMode = session['auth_mode'];

<<<<<<< HEAD
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
=======
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
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
          }
          return;
        }

<<<<<<< HEAD
        // Fully authenticated
        Navigator.of(context).pushReplacement(
            NeonPageRoute(child: const MainShell()));
=======
        // Fully authenticated — go to main shell
        Navigator.of(context).pushReplacement(
          NeonPageRoute(child: const MainShell()),
        );
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
      },
    );
  }
}
