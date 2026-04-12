// main.dart — BlackBugsAI Android App entry point

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'theme/neon_theme.dart';
import 'screens/splash_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();

<<<<<<< HEAD
=======
  // Force portrait mode
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
  SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);

<<<<<<< HEAD
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor:                   Colors.transparent,
    statusBarIconBrightness:          Brightness.light,
    systemNavigationBarColor:         NeonColors.bgDark,
=======
  // Transparent status/nav bars
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    statusBarIconBrightness: Brightness.light,
    systemNavigationBarColor: NeonColors.bgDark,
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
    systemNavigationBarIconBrightness: Brightness.light,
  ));

  runApp(const BlackBugsApp());
}

class BlackBugsApp extends StatelessWidget {
  const BlackBugsApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
<<<<<<< HEAD
      title:                    'BlackBugsAI',
      theme:                    NeonTheme.theme,
      debugShowCheckedModeBanner: false,
      home:                     const SplashScreen(),
=======
      title: 'BlackBugsAI',
      theme: NeonTheme.theme,
      debugShowCheckedModeBanner: false,
      home: const SplashScreen(),
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
    );
  }
}
