<<<<<<< HEAD
// main_shell.dart — Main navigation shell
// UPDATED: added Anderson, Pythia, Tanker, Operator to nav bar
=======
// main_shell.dart — Main navigation shell with bottom nav bar
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999

import 'package:flutter/material.dart';
import '../theme/neon_theme.dart';
import '../animations/neon_animations.dart';
import '../services/api_service.dart';
import '../services/auth_service.dart';
import 'dashboard_screen.dart';
import 'tasks_screen.dart';
import 'agents_screen.dart';
import 'terminal_screen.dart';
import 'settings_screen.dart';
import 'docker_screen.dart';
import 'pro_panel_screen.dart';

class MainShell extends StatefulWidget {
  const MainShell({super.key});

  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> with TickerProviderStateMixin {
<<<<<<< HEAD
  int        _currentIndex = 0;
  late ApiService _api;
  bool       _initialized  = false;
=======
  int _currentIndex = 0;
  late ApiService _api;
  bool _initialized = false;
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
  late AnimationController _navGlowCtrl;

  final _screens = const [
    DashboardScreen(),
    TasksScreen(),
    AgentsScreen(),
    TerminalScreen(),
    DockerScreen(),
    ProPanelScreen(),
    SettingsScreen(),
  ];

  final _navItems = const [
<<<<<<< HEAD
    _NavItem(icon: Icons.dashboard_outlined,         activeIcon: Icons.dashboard,         label: 'MATRIX'),
    _NavItem(icon: Icons.list_outlined,              activeIcon: Icons.list,              label: 'TASKS'),
    _NavItem(icon: Icons.smart_toy_outlined,         activeIcon: Icons.smart_toy,         label: 'AGENTS'),
    _NavItem(icon: Icons.terminal_outlined,          activeIcon: Icons.terminal,          label: 'SHELL'),
    _NavItem(icon: Icons.cloud_queue_outlined,       activeIcon: Icons.cloud_queue,       label: 'DOCKER'),
    _NavItem(icon: Icons.workspace_premium_outlined, activeIcon: Icons.workspace_premium, label: 'PRO'),
    _NavItem(icon: Icons.settings_outlined,          activeIcon: Icons.settings,          label: 'CFG'),
=======
    _NavItem(icon: Icons.dashboard_outlined, activeIcon: Icons.dashboard, label: 'MATRIX'),
    _NavItem(icon: Icons.list_outlined, activeIcon: Icons.list, label: 'TASKS'),
    _NavItem(icon: Icons.smart_toy_outlined, activeIcon: Icons.smart_toy, label: 'AGENTS'),
    _NavItem(icon: Icons.terminal_outlined, activeIcon: Icons.terminal, label: 'SHELL'),
    _NavItem(icon: Icons.cloud_queue_outlined, activeIcon: Icons.cloud_queue, label: 'DOCKER'),
    _NavItem(icon: Icons.workspace_premium_outlined, activeIcon: Icons.workspace_premium, label: 'PRO'),
    _NavItem(icon: Icons.settings_outlined, activeIcon: Icons.settings, label: 'CONFIG'),
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
  ];

  @override
  void initState() {
    super.initState();
<<<<<<< HEAD
    _navGlowCtrl = AnimationController(vsync: this,
        duration: const Duration(milliseconds: 1500))
      ..repeat(reverse: true);
=======
    _navGlowCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat(reverse: true);
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
    _init();
  }

  Future<void> _init() async {
    final session = await AuthService.loadSession();
    _api = ApiService(
<<<<<<< HEAD
      baseUrl:    session['base_url']    ?? '',
      adminToken: session['token']       ?? '',
    );
    if (!mounted) return;
=======
      baseUrl: session['base_url'] ?? '',
      adminToken: session['token'] ?? '',
    );
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
    setState(() => _initialized = true);
  }

  @override
<<<<<<< HEAD
  void dispose() { _navGlowCtrl.dispose(); super.dispose(); }
=======
  void dispose() {
    _navGlowCtrl.dispose();
    super.dispose();
  }
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999

  @override
  Widget build(BuildContext context) {
    if (!_initialized) {
      return const Scaffold(
        backgroundColor: NeonColors.bgDeep,
        body: Center(child: NeonLoadingIndicator(label: 'LOADING...')),
      );
    }
<<<<<<< HEAD
=======

>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
    return ApiServiceProvider(
      api: _api,
      child: Scaffold(
        backgroundColor: NeonColors.bgDeep,
<<<<<<< HEAD
        body: IndexedStack(index: _currentIndex, children: _screens),
        bottomNavigationBar: _NeonBottomNav(
          currentIndex: _currentIndex,
          items:        _navItems,
          glowCtrl:     _navGlowCtrl,
=======
        body: IndexedStack(
          index: _currentIndex,
          children: _screens,
        ),
        bottomNavigationBar: _NeonBottomNav(
          currentIndex: _currentIndex,
          items: _navItems,
          glowCtrl: _navGlowCtrl,
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
          onTap: (i) => setState(() => _currentIndex = i),
        ),
      ),
    );
  }
}

<<<<<<< HEAD
// ─── API Service Provider ─────────────────────────────────────────────────────
=======
// ─── API Service Provider (InheritedWidget) ───────────────────────────────────
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999

class ApiServiceProvider extends InheritedWidget {
  final ApiService api;

  const ApiServiceProvider({
<<<<<<< HEAD
    super.key, required this.api, required super.child,
  });

  static ApiService of(BuildContext context) =>
      context.dependOnInheritedWidgetOfExactType<ApiServiceProvider>()!.api;
=======
    super.key,
    required this.api,
    required super.child,
  });

  static ApiService of(BuildContext context) {
    return context
        .dependOnInheritedWidgetOfExactType<ApiServiceProvider>()!
        .api;
  }
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999

  @override
  bool updateShouldNotify(ApiServiceProvider old) => api != old.api;
}

<<<<<<< HEAD
// ─── Nav item ─────────────────────────────────────────────────────────────────
=======
// ─── Neon Bottom Nav ──────────────────────────────────────────────────────────
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999

class _NavItem {
  final IconData icon;
  final IconData activeIcon;
<<<<<<< HEAD
  final String   label;
  const _NavItem({required this.icon, required this.activeIcon, required this.label});
}

class _NeonBottomNav extends StatelessWidget {
  final int                currentIndex;
  final List<_NavItem>     items;
  final AnimationController glowCtrl;
  final void Function(int)  onTap;

  const _NeonBottomNav({
    required this.currentIndex, required this.items,
    required this.glowCtrl,     required this.onTap,
=======
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
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
  });

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: glowCtrl,
<<<<<<< HEAD
      builder: (context, _) => Container(
        decoration: BoxDecoration(
          color: NeonColors.bgDark,
          border: Border(
            top: BorderSide(
                color: NeonColors.cyan.withOpacity(0.2 + 0.1 * glowCtrl.value),
                width: 1),
          ),
        ),
        child: SafeArea(
          child: SizedBox(
            height: 60,
            child: Row(
              children: items.asMap().entries.map((e) {
                final i        = e.key;
                final item     = e.value;
                final isActive = i == currentIndex;
                return Expanded(
                  child: GestureDetector(
                    onTap:     () => onTap(i),
                    behavior:  HitTestBehavior.opaque,
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        AnimatedContainer(
                          duration: const Duration(milliseconds: 200),
                          height: 2, width: isActive ? 24 : 0,
                          margin: const EdgeInsets.only(bottom: 4),
                          decoration: BoxDecoration(
                            color: NeonColors.cyan,
                            borderRadius: BorderRadius.circular(1),
                            boxShadow: isActive
                                ? [BoxShadow(
                                    color: NeonColors.cyan.withOpacity(0.8),
                                    blurRadius: 6, spreadRadius: 1)]
                                : [],
                          ),
                        ),
                        Icon(
                          isActive ? item.activeIcon : item.icon,
                          color: isActive ? NeonColors.cyan : NeonColors.textSecondary,
                          size:  isActive ? 22 : 20,
                        ),
                        const SizedBox(height: 2),
                        Text(item.label,
                            style: TextStyle(
                              fontFamily:  'JetBrainsMono',
                              fontSize:    8,
                              fontWeight:  isActive ? FontWeight.w700 : FontWeight.normal,
                              color: isActive ? NeonColors.cyan : NeonColors.textSecondary,
                              letterSpacing: 1,
                            )),
                      ],
                    ),
                  ),
                );
              }).toList(),
            ),
          ),
        ),
      ),
=======
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
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
    );
  }
}
