// main_shell.dart — Main navigation shell with bottom nav bar

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../theme/neon_theme.dart';
import '../animations/neon_animations.dart';
import '../services/api_service.dart';
import '../services/telegram_bot_service.dart';
import 'dashboard_screen.dart';
import 'tasks_screen.dart';
import 'agents_screen.dart';
import 'terminal_screen.dart';
import 'settings_screen.dart';
import 'telegram_screen.dart';

class MainShell extends StatefulWidget {
  const MainShell({super.key});

  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> with TickerProviderStateMixin {
  int _currentIndex = 0;
  late ApiService _api;
  TelegramBotService? _tgService;
  String _appMode = 'telegram'; // 'telegram' | 'server'
  bool _initialized = false;
  late AnimationController _navGlowCtrl;

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
    _appMode = prefs.getString('app_mode') ?? 'telegram';

    final baseUrl = prefs.getString('base_url') ?? '';
    final token = prefs.getString('admin_token') ?? '';
    _api = ApiService(baseUrl: baseUrl, adminToken: token);

    final tgToken = prefs.getString('telegram_token') ?? '';
    if (tgToken.isNotEmpty) {
      _tgService = TelegramBotService(tgToken);
    }

    setState(() => _initialized = true);
  }

  @override
  void dispose() {
    _navGlowCtrl.dispose();
    super.dispose();
  }

  List<Widget> get _screens => [
        DashboardScreen(appMode: _appMode),
        if (_appMode == 'server') const TasksScreen(),
        if (_appMode == 'server') const AgentsScreen(),
        TelegramScreen(tgService: _tgService),
        TerminalScreen(appMode: _appMode),
        SettingsScreen(appMode: _appMode),
      ];

  List<_NavItem> get _navItems => [
        const _NavItem(icon: Icons.dashboard_outlined, activeIcon: Icons.dashboard, label: 'ПАНЕЛЬ'),
        if (_appMode == 'server')
          const _NavItem(icon: Icons.list_outlined, activeIcon: Icons.list, label: 'ЗАДАЧИ'),
        if (_appMode == 'server')
          const _NavItem(icon: Icons.smart_toy_outlined, activeIcon: Icons.smart_toy, label: 'АГЕНТЫ'),
        const _NavItem(icon: Icons.telegram_outlined, activeIcon: Icons.telegram, label: 'BOT'),
        const _NavItem(icon: Icons.terminal_outlined, activeIcon: Icons.terminal, label: 'ТЕРМИНАЛ'),
        const _NavItem(icon: Icons.settings_outlined, activeIcon: Icons.settings, label: 'НАСТРОЙКИ'),
      ];

  @override
  Widget build(BuildContext context) {
    if (!_initialized) {
      return const Scaffold(
        backgroundColor: NeonColors.bgDeep,
        body: Center(child: NeonLoadingIndicator(label: 'LOADING...')),
      );
    }

    final screens = _screens;
    final navItems = _navItems;

    return AppStateProvider(
      api: _api,
      tgService: _tgService,
      appMode: _appMode,
      child: Scaffold(
        backgroundColor: NeonColors.bgDeep,
        body: IndexedStack(
          index: _currentIndex.clamp(0, screens.length - 1),
          children: screens,
        ),
        bottomNavigationBar: _NeonBottomNav(
          currentIndex: _currentIndex.clamp(0, navItems.length - 1),
          items: navItems,
          glowCtrl: _navGlowCtrl,
          onTap: (i) => setState(() => _currentIndex = i),
        ),
      ),
    );
  }
}

// ─── App State Provider ───────────────────────────────────────────────────────

class AppStateProvider extends InheritedWidget {
  final ApiService api;
  final TelegramBotService? tgService;
  final String appMode;

  const AppStateProvider({
    super.key,
    required this.api,
    required this.tgService,
    required this.appMode,
    required super.child,
  });

  static AppStateProvider of(BuildContext context) {
    return context.dependOnInheritedWidgetOfExactType<AppStateProvider>()!;
  }

  bool get isTelegramMode => appMode == 'telegram';
  bool get isServerMode => appMode == 'server';

  @override
  bool updateShouldNotify(AppStateProvider old) =>
      api != old.api || tgService != old.tgService || appMode != old.appMode;
}

// Keep backward compatibility
class ApiServiceProvider extends InheritedWidget {
  final ApiService api;

  const ApiServiceProvider({
    super.key,
    required this.api,
    required super.child,
  });

  static ApiService of(BuildContext context) {
    // Try AppStateProvider first
    final app = context.dependOnInheritedWidgetOfExactType<AppStateProvider>();
    if (app != null) return app.api;
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
                color: NeonColors.cyan
                    .withOpacity(0.05 + 0.05 * glowCtrl.value),
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
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
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
                                        color:
                                            NeonColors.cyan.withOpacity(0.8),
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
                              fontSize: 7,
                              fontWeight: isActive
                                  ? FontWeight.w700
                                  : FontWeight.normal,
                              color: isActive
                                  ? NeonColors.cyan
                                  : NeonColors.textSecondary,
                              letterSpacing: 0.5,
                            ),
                          ),
                        ],
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
