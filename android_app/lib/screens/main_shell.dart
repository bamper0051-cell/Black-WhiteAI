// main_shell.dart — Main navigation shell with bottom nav bar

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../theme/neon_theme.dart';
import '../services/api_service.dart';
import 'dashboard_screen.dart';
import 'tasks_screen.dart';
import 'agents_screen.dart';
import 'terminal_screen.dart';
import 'settings_screen.dart';

class MainShell extends StatefulWidget {
  const MainShell({super.key});

  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> with TickerProviderStateMixin {
  int _currentIndex = 0;
  late ApiService _api;
  bool _initialized = false;
  late AnimationController _navGlowCtrl;

  final _screens = const [
    DashboardScreen(),
    TasksScreen(),
    AgentsScreen(),
    TerminalScreen(),
    SettingsScreen(),
  ];

  final _navItems = const [
    _NavItem(icon: Icons.dashboard_outlined, activeIcon: Icons.dashboard, label: 'MATRIX'),
    _NavItem(icon: Icons.list_outlined, activeIcon: Icons.list, label: 'TASKS'),
    _NavItem(icon: Icons.smart_toy_outlined, activeIcon: Icons.smart_toy, label: 'AGENTS'),
    _NavItem(icon: Icons.terminal_outlined, activeIcon: Icons.terminal, label: 'SHELL'),
    _NavItem(icon: Icons.settings_outlined, activeIcon: Icons.settings, label: 'CONFIG'),
  ];

  @override
  void initState() {
    super.initState();
    _navGlowCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat(reverse: true);
    _init();
  }

  Future<void> _init() async {
    final prefs = await SharedPreferences.getInstance();
    final baseUrl = prefs.getString('base_url') ?? '';
    final token = prefs.getString('session_token') ?? '';
    _api = ApiService(baseUrl: baseUrl, sessionToken: token);
    setState(() => _initialized = true);
  }

  @override
  void dispose() {
    _navGlowCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!_initialized) {
      return const Scaffold(
        backgroundColor: NeonColors.bgDeep,
        body: Center(child: NeonLoadingIndicator(label: 'LOADING...')),
      );
    }

    return ApiServiceProvider(
      api: _api,
      child: Scaffold(
        backgroundColor: NeonColors.bgDeep,
        body: IndexedStack(
          index: _currentIndex,
          children: _screens,
        ),
        bottomNavigationBar: _NeonBottomNav(
          currentIndex: _currentIndex,
          items: _navItems,
          glowCtrl: _navGlowCtrl,
          onTap: (i) => setState(() => _currentIndex = i),
        ),
      ),
    );
  }
}

// ─── API Service Provider (InheritedWidget) ───────────────────────────────────

class ApiServiceProvider extends InheritedWidget {
  final ApiService api;

  const ApiServiceProvider({
    super.key,
    required this.api,
    required super.child,
  });

  static ApiService of(BuildContext context) {
    return context
        .dependOnInheritedWidgetOfExactType<ApiServiceProvider>()!
        .api;
  }

  @override
  bool updateShouldNotify(ApiServiceProvider old) => api != old.api;
}

// ─── Neon Bottom Nav ──────────────────────────────────────────────────────────

class _NavItem {
  final IconData icon;
  final IconData activeIcon;
  final String label;
  const _NavItem(
      {required this.icon, required this.activeIcon, required this.label});
}

class _NeonBottomNav extends StatelessWidget {
  final int currentIndex;
  final List<_NavItem> items;
  final AnimationController glowCtrl;
  final void Function(int) onTap;

  const _NeonBottomNav({
    required this.currentIndex,
    required this.items,
    required this.glowCtrl,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: glowCtrl,
      builder: (context, _) {
        return Container(
          decoration: BoxDecoration(
            color: NeonColors.bgDark,
            border: Border(
              top: BorderSide(
                color: NeonColors.cyan.withOpacity(0.2 + 0.1 * glowCtrl.value),
                width: 1,
              ),
            ),
            boxShadow: [
              BoxShadow(
                color: NeonColors.cyan.withOpacity(0.05 + 0.05 * glowCtrl.value),
                blurRadius: 20,
                offset: const Offset(0, -4),
              ),
            ],
          ),
          child: SafeArea(
            child: SizedBox(
              height: 60,
              child: Row(
                children: items.asMap().entries.map((entry) {
                  final i = entry.key;
                  final item = entry.value;
                  final isActive = i == currentIndex;
                  return Expanded(
                    child: GestureDetector(
                      onTap: () => onTap(i),
                      behavior: HitTestBehavior.opaque,
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 200),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            // Active indicator bar
                            AnimatedContainer(
                              duration: const Duration(milliseconds: 200),
                              height: 2,
                              width: isActive ? 24 : 0,
                              margin: const EdgeInsets.only(bottom: 4),
                              decoration: BoxDecoration(
                                color: NeonColors.cyan,
                                borderRadius: BorderRadius.circular(1),
                                boxShadow: isActive
                                    ? [
                                        BoxShadow(
                                          color: NeonColors.cyan
                                              .withOpacity(0.8),
                                          blurRadius: 6,
                                          spreadRadius: 1,
                                        ),
                                      ]
                                    : [],
                              ),
                            ),

                            Icon(
                              isActive ? item.activeIcon : item.icon,
                              color: isActive
                                  ? NeonColors.cyan
                                  : NeonColors.textSecondary,
                              size: isActive ? 22 : 20,
                            ),
                            const SizedBox(height: 2),
                            Text(
                              item.label,
                              style: TextStyle(
                                fontFamily: 'Orbitron',
                                fontSize: 8,
                                fontWeight: isActive
                                    ? FontWeight.w700
                                    : FontWeight.normal,
                                color: isActive
                                    ? NeonColors.cyan
                                    : NeonColors.textSecondary,
                                letterSpacing: 1,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  );
                }).toList(),
              ),
            ),
          ),
        );
      },
    );
  }
}

// ─── Loading indicator import ─────────────────────────────────────────────────

import '../animations/neon_animations.dart';
