// main.dart — BlackBugsAI Android App entry point

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'theme/neon_theme.dart';
import 'screens/splash_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();

  // Force portrait mode
  SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);

  // Transparent status/nav bars
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    statusBarIconBrightness: Brightness.light,
    systemNavigationBarColor: NeonColors.bgDark,
    systemNavigationBarIconBrightness: Brightness.light,
  ));

  runApp(const BlackBugsApp());
}

class BlackBugsApp extends StatelessWidget {
  const BlackBugsApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'BlackBugsAI',
      theme: NeonTheme.theme,
      debugShowCheckedModeBanner: false,
      home: const SplashScreen(),
    );
  }
}
