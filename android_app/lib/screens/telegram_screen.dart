// telegram_screen.dart — Telegram Bot Admin Panel

import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../theme/neon_theme.dart';
import '../animations/neon_animations.dart';
import '../models/models.dart';
import '../widgets/neon_card.dart';
import '../widgets/neon_text_field.dart';
import 'main_shell.dart';
import '../services/telegram_bot_service.dart';

class TelegramScreen extends StatefulWidget {
  final TelegramBotService? tgService;
  const TelegramScreen({super.key, this.tgService});

  @override
  State<TelegramScreen> createState() => _TelegramScreenState();
}

class _TelegramScreenState extends State<TelegramScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabCtrl;
  TelegramBotStats? _stats;
  bool _loadingStats = true;
  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();
    _tabCtrl = TabController(length: 3, vsync: this);
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadStats());
    _refreshTimer =
        Timer.periodic(const Duration(seconds: 15), (_) => _loadStats());
  }

  @override
  void dispose() {
    _tabCtrl.dispose();
    _refreshTimer?.cancel();
    super.dispose();
  }

  Future<void> _loadStats() async {
    try {
      TelegramBotStats stats;
      final tgService = widget.tgService ?? AppStateProvider.of(context).tgService;
      if (tgService != null) {
        stats = await tgService.getBotStats();
      } else {
        final api = ApiServiceProvider.of(context);
        stats = await api.getBotStats();
      }
      if (!mounted) return;
      setState(() {
        _stats = stats;
        _loadingStats = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _loadingStats = false);
    }
  }

  Future<void> _restartBot() async {
    final api = AppStateProvider.of(context).api;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: NeonColors.bgDark,
        title: const NeonText('RESTART BOT?',
            color: NeonColors.yellow,
            fontSize: 14,
            fontFamily: 'Orbitron',
            glowRadius: 8),
        content: const Text(
          'The bot will restart. Active sessions may be interrupted.',
          style: TextStyle(
              color: NeonColors.textSecondary,
              fontFamily: 'JetBrainsMono',
              fontSize: 12),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('CANCEL',
                style: TextStyle(color: NeonColors.textSecondary)),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const NeonText('RESTART',
                color: NeonColors.yellow,
                fontFamily: 'Orbitron',
                fontSize: 12),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      final ok = await api.restartBot();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(ok ? '✅ Bot restarting...' : '❌ Restart failed'),
          backgroundColor: ok ? NeonColors.bgCard : NeonColors.pink,
        ),
      );
      if (ok) {
        await Future.delayed(const Duration(seconds: 3));
        _loadStats();
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: NeonColors.bgDeep,
      appBar: AppBar(
        title: Row(
          children: [
            const Icon(Icons.telegram, color: NeonColors.cyan, size: 20),
            const SizedBox(width: 8),
            const NeonText(
              'TELEGRAM BOT',
              fontFamily: 'Orbitron',
              fontSize: 14,
              fontWeight: FontWeight.w700,
              glowRadius: 8,
            ),
          ],
        ),
        actions: [
          // Bot status indicator
          if (_stats != null)
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: Center(
                child: PulseGlow(
                  color: _stats!.isOnline
                      ? NeonColors.green
                      : NeonColors.pink,
                  child: Container(
                    width: 8,
                    height: 8,
                    decoration: BoxDecoration(
                      color: _stats!.isOnline
                          ? NeonColors.green
                          : NeonColors.pink,
                      shape: BoxShape.circle,
                    ),
                  ),
                ),
              ),
            ),
          IconButton(
            icon: const Icon(Icons.restart_alt,
                color: NeonColors.yellow, size: 20),
            tooltip: 'Restart Bot',
            onPressed: _restartBot,
          ),
          IconButton(
            icon: const Icon(Icons.refresh, color: NeonColors.cyan, size: 20),
            onPressed: _loadStats,
          ),
        ],
        bottom: TabBar(
          controller: _tabCtrl,
          indicatorColor: NeonColors.cyan,
          indicatorWeight: 2,
          labelColor: NeonColors.cyan,
          unselectedLabelColor: NeonColors.textSecondary,
          labelStyle: const TextStyle(
            fontFamily: 'Orbitron',
            fontSize: 9,
            letterSpacing: 1,
          ),
          tabs: const [
            Tab(text: 'STATUS'),
            Tab(text: 'USERS'),
            Tab(text: 'BROADCAST'),
          ],
        ),
      ),
      body: _loadingStats
          ? const Center(
              child: NeonLoadingIndicator(label: 'CONNECTING...', size: 48))
          : TabBarView(
              controller: _tabCtrl,
              children: [
                _StatusTab(stats: _stats, onRefresh: _loadStats),
                const _UsersTab(),
                const _BroadcastTab(),
              ],
            ),
    );
  }
}

// ─── STATUS TAB ───────────────────────────────────────────────────────────────

class _StatusTab extends StatelessWidget {
  final TelegramBotStats? stats;
  final VoidCallback onRefresh;

  const _StatusTab({required this.stats, required this.onRefresh});

  @override
  Widget build(BuildContext context) {
    if (stats == null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.cloud_off, color: NeonColors.pink, size: 48),
            const SizedBox(height: 16),
            const NeonText('BOT OFFLINE',
                color: NeonColors.pink,
                fontSize: 14,
                fontFamily: 'Orbitron',
                glowRadius: 8),
            const SizedBox(height: 8),
            const Text(
              'Cannot connect to bot API',
              style: TextStyle(
                  color: NeonColors.textSecondary,
                  fontFamily: 'JetBrainsMono',
                  fontSize: 11),
            ),
            const SizedBox(height: 24),
            GestureDetector(
              onTap: onRefresh,
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                decoration: neonButtonDecoration(color: NeonColors.cyan),
                child: const NeonText('RETRY',
                    color: NeonColors.cyan,
                    fontFamily: 'Orbitron',
                    fontSize: 12),
              ),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () async => onRefresh(),
      color: NeonColors.cyan,
      backgroundColor: NeonColors.bgCard,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Bot Info Card
            NeonCard(
              glowColor:
                  stats!.isOnline ? NeonColors.green : NeonColors.pink,
              child: Row(
                children: [
                  Container(
                    width: 48,
                    height: 48,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      border: Border.all(
                        color: stats!.isOnline
                            ? NeonColors.green
                            : NeonColors.pink,
                        width: 2,
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: (stats!.isOnline
                                  ? NeonColors.green
                                  : NeonColors.pink)
                              .withOpacity(0.4),
                          blurRadius: 8,
                        )
                      ],
                    ),
                    child: Icon(
                      Icons.telegram,
                      color: stats!.isOnline
                          ? NeonColors.green
                          : NeonColors.pink,
                      size: 28,
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        NeonText(
                          '@${stats!.botUsername}',
                          color: NeonColors.textPrimary,
                          fontSize: 15,
                          fontFamily: 'Orbitron',
                          fontWeight: FontWeight.w700,
                          glowRadius: 4,
                        ),
                        const SizedBox(height: 4),
                        Row(
                          children: [
                            Container(
                              width: 6,
                              height: 6,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                color: stats!.isOnline
                                    ? NeonColors.green
                                    : NeonColors.pink,
                              ),
                            ),
                            const SizedBox(width: 6),
                            Text(
                              stats!.isOnline ? 'ONLINE' : 'OFFLINE',
                              style: TextStyle(
                                color: stats!.isOnline
                                    ? NeonColors.green
                                    : NeonColors.pink,
                                fontFamily: 'JetBrainsMono',
                                fontSize: 11,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  GestureDetector(
                    onTap: () {
                      Clipboard.setData(
                          ClipboardData(text: '@${stats!.botUsername}'));
                    },
                    child: const Icon(Icons.copy,
                        color: NeonColors.textSecondary, size: 16),
                  ),
                ],
              ),
            ).animate().fadeIn(duration: 400.ms),

            const SizedBox(height: 16),

            // Stats Grid
            GridView.count(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisCount: 2,
              childAspectRatio: 2.2,
              mainAxisSpacing: 8,
              crossAxisSpacing: 8,
              children: [
                _BotStatCard(
                  label: 'TOTAL USERS',
                  value: '${stats!.totalUsers}',
                  icon: Icons.people_outline,
                  color: NeonColors.cyan,
                ),
                _BotStatCard(
                  label: 'ACTIVE TODAY',
                  value: '${stats!.activeToday}',
                  icon: Icons.today_outlined,
                  color: NeonColors.green,
                ),
                _BotStatCard(
                  label: 'MSG TODAY',
                  value: '${stats!.messagesToday}',
                  icon: Icons.chat_bubble_outline,
                  color: NeonColors.purple,
                ),
                _BotStatCard(
                  label: 'TOTAL MSGS',
                  value: '${stats!.totalMessages}',
                  icon: Icons.forum_outlined,
                  color: NeonColors.yellow,
                ),
              ],
            ).animate().fadeIn(delay: 100.ms, duration: 400.ms),

            const SizedBox(height: 16),

            // Users by Role
            if (stats!.usersByRole.isNotEmpty)
              NeonCard(
                glowColor: NeonColors.purple,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const NeonText('> USERS BY ROLE',
                        color: NeonColors.purple,
                        fontSize: 11,
                        fontFamily: 'Orbitron',
                        glowRadius: 4),
                    const SizedBox(height: 12),
                    ...stats!.usersByRole.entries.map(
                      (e) => _RoleBar(role: e.key, count: e.value,
                          total: stats!.totalUsers),
                    ),
                  ],
                ),
              ).animate().fadeIn(delay: 200.ms, duration: 400.ms),

            const SizedBox(height: 16),

            // Last activity
            if (stats!.lastActivity != null)
              NeonCard(
                child: Row(
                  children: [
                    const Icon(Icons.access_time,
                        color: NeonColors.textSecondary, size: 16),
                    const SizedBox(width: 8),
                    Text(
                      'Last activity: ',
                      style: const TextStyle(
                          color: NeonColors.textSecondary,
                          fontFamily: 'JetBrainsMono',
                          fontSize: 11),
                    ),
                    Text(
                      _formatTime(stats!.lastActivity!),
                      style: const TextStyle(
                          color: NeonColors.textPrimary,
                          fontFamily: 'JetBrainsMono',
                          fontSize: 11,
                          fontWeight: FontWeight.w700),
                    ),
                  ],
                ),
              ).animate().fadeIn(delay: 300.ms, duration: 400.ms),
          ],
        ),
      ),
    );
  }

  String _formatTime(DateTime dt) {
    final diff = DateTime.now().difference(dt);
    if (diff.inSeconds < 60) return '${diff.inSeconds}s ago';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    return '${dt.day}.${dt.month} ${dt.hour}:${dt.minute.toString().padLeft(2, '0')}';
  }
}

class _BotStatCard extends StatelessWidget {
  final String label;
  final String value;
  final IconData icon;
  final Color color;

  const _BotStatCard({
    required this.label,
    required this.value,
    required this.icon,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: neonCardDecoration(glowColor: color, glowRadius: 6),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, color: color, size: 16),
          const SizedBox(height: 4),
          Text(
            value,
            style: TextStyle(
              color: color,
              fontFamily: 'Orbitron',
              fontSize: 18,
              fontWeight: FontWeight.w700,
              shadows: [Shadow(color: color.withOpacity(0.6), blurRadius: 8)],
            ),
          ),
          Text(
            label,
            style: const TextStyle(
              color: NeonColors.textSecondary,
              fontFamily: 'Orbitron',
              fontSize: 7,
              letterSpacing: 1,
            ),
          ),
        ],
      ),
    );
  }
}

class _RoleBar extends StatelessWidget {
  final String role;
  final int count;
  final int total;

  const _RoleBar(
      {required this.role, required this.count, required this.total});

  Color get _color {
    switch (role) {
      case 'god':
        return NeonColors.pink;
      case 'admin':
        return NeonColors.yellow;
      case 'vip':
        return NeonColors.purple;
      case 'user':
        return NeonColors.cyan;
      case 'noob':
        return NeonColors.textSecondary;
      case 'ban':
        return Colors.red;
      default:
        return NeonColors.cyan;
    }
  }

  @override
  Widget build(BuildContext context) {
    final pct = total > 0 ? count / total : 0.0;
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          SizedBox(
            width: 48,
            child: Text(
              role.toUpperCase(),
              style: TextStyle(
                  color: _color,
                  fontFamily: 'JetBrainsMono',
                  fontSize: 10,
                  fontWeight: FontWeight.w700),
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: ClipRRect(
              borderRadius: BorderRadius.circular(2),
              child: LinearProgressIndicator(
                value: pct,
                backgroundColor: _color.withOpacity(0.1),
                valueColor: AlwaysStoppedAnimation<Color>(_color),
                minHeight: 6,
              ),
            ),
          ),
          const SizedBox(width: 8),
          Text(
            '$count',
            style: TextStyle(
                color: _color,
                fontFamily: 'JetBrainsMono',
                fontSize: 10,
                fontWeight: FontWeight.w700),
          ),
        ],
      ),
    );
  }
}

// ─── USERS TAB ────────────────────────────────────────────────────────────────

class _UsersTab extends StatefulWidget {
  const _UsersTab();

  @override
  State<_UsersTab> createState() => _UsersTabState();
}

class _UsersTabState extends State<_UsersTab> {
  List<TelegramUser> _users = [];
  bool _loading = true;
  String _filterRole = 'all';
  String _search = '';
  final _searchCtrl = TextEditingController();

  static const _roles = ['all', 'god', 'admin', 'vip', 'user', 'noob', 'ban'];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final api = ApiServiceProvider.of(context);
      final users = await api.getBotUsers(limit: 100);
      if (!mounted) return;
      setState(() {
        _users = users;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _loading = false);
    }
  }

  List<TelegramUser> get _filtered {
    return _users.where((u) {
      final roleMatch = _filterRole == 'all' || u.role == _filterRole;
      final searchMatch = _search.isEmpty ||
          u.username.toLowerCase().contains(_search.toLowerCase()) ||
          u.firstName.toLowerCase().contains(_search.toLowerCase()) ||
          u.id.contains(_search);
      return roleMatch && searchMatch;
    }).toList();
  }

  void _showUserActions(TelegramUser user) {
    showModalBottomSheet(
      context: context,
      backgroundColor: NeonColors.bgDark,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
        side: BorderSide(color: NeonColors.cyanGlow),
      ),
      builder: (_) => _UserActionsSheet(
        user: user,
        onAction: (action, value) async {
          Navigator.pop(context);
          final api = ApiServiceProvider.of(context);
          bool ok = false;
          if (action == 'role') {
            ok = await api.setUserRole(user.id, value!);
          } else if (action == 'ban') {
            ok = await api.banUser(user.id);
          } else if (action == 'unban') {
            ok = await api.unbanUser(user.id);
          }
          if (!mounted) return;
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(ok ? '✅ Done' : '❌ Failed'),
              backgroundColor: ok ? NeonColors.bgCard : NeonColors.pink,
            ),
          );
          if (ok) _load();
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Search bar
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 12, 12, 0),
          child: NeonTextField(
            controller: _searchCtrl,
            label: 'SEARCH',
            hint: 'username, name or id...',
            prefixIcon: Icons.search,
            onChanged: (v) => setState(() => _search = v),
          ),
        ),

        // Role filter chips
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          child: Row(
            children: _roles.map((role) {
              final isActive = _filterRole == role;
              final color = _roleColor(role);
              return Padding(
                padding: const EdgeInsets.only(right: 6),
                child: GestureDetector(
                  onTap: () => setState(() => _filterRole = role),
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    padding: const EdgeInsets.symmetric(
                        horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: isActive
                          ? color.withOpacity(0.2)
                          : Colors.transparent,
                      border: Border.all(
                        color: isActive
                            ? color
                            : color.withOpacity(0.3),
                      ),
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: Text(
                      role.toUpperCase(),
                      style: TextStyle(
                        color: isActive ? color : color.withOpacity(0.6),
                        fontFamily: 'Orbitron',
                        fontSize: 9,
                        letterSpacing: 1,
                        fontWeight: isActive
                            ? FontWeight.w700
                            : FontWeight.normal,
                      ),
                    ),
                  ),
                ),
              );
            }).toList(),
          ),
        ),

        // Users list
        Expanded(
          child: _loading
              ? const Center(
                  child: NeonLoadingIndicator(
                      label: 'LOADING USERS...', size: 40))
              : _filtered.isEmpty
                  ? const Center(
                      child: Text('No users found',
                          style: TextStyle(
                              color: NeonColors.textSecondary,
                              fontFamily: 'JetBrainsMono',
                              fontSize: 12)))
                  : RefreshIndicator(
                      onRefresh: _load,
                      color: NeonColors.cyan,
                      backgroundColor: NeonColors.bgCard,
                      child: ListView.builder(
                        padding: const EdgeInsets.fromLTRB(12, 0, 12, 16),
                        itemCount: _filtered.length,
                        itemBuilder: (context, i) {
                          return _UserTile(
                            user: _filtered[i],
                            onTap: () => _showUserActions(_filtered[i]),
                          )
                              .animate()
                              .fadeIn(
                                  delay: Duration(milliseconds: 30 * i),
                                  duration: 250.ms)
                              .slideX(begin: 0.05);
                        },
                      ),
                    ),
        ),
      ],
    );
  }

  Color _roleColor(String role) {
    switch (role) {
      case 'god':
        return NeonColors.pink;
      case 'admin':
        return NeonColors.yellow;
      case 'vip':
        return NeonColors.purple;
      case 'user':
        return NeonColors.cyan;
      case 'noob':
        return NeonColors.textSecondary;
      case 'ban':
        return Colors.red;
      default:
        return NeonColors.cyan;
    }
  }
}

class _UserTile extends StatelessWidget {
  final TelegramUser user;
  final VoidCallback onTap;

  const _UserTile({required this.user, required this.onTap});

  Color get _roleColor {
    switch (user.role) {
      case 'god':
        return NeonColors.pink;
      case 'admin':
        return NeonColors.yellow;
      case 'vip':
        return NeonColors.purple;
      case 'ban':
        return Colors.red;
      case 'noob':
        return NeonColors.textSecondary;
      default:
        return NeonColors.cyan;
    }
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: neonCardDecoration(
          glowColor: user.isBanned ? Colors.red : _roleColor,
          glowRadius: user.isBanned ? 6 : 4,
        ),
        child: Row(
          children: [
            // Avatar
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(color: _roleColor, width: 1.5),
                color: _roleColor.withOpacity(0.1),
              ),
              child: Center(
                child: Text(
                  user.firstName.isNotEmpty
                      ? user.firstName[0].toUpperCase()
                      : (user.username.isNotEmpty
                          ? user.username[0].toUpperCase()
                          : '?'),
                  style: TextStyle(
                    color: _roleColor,
                    fontFamily: 'Orbitron',
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 10),

            // User info
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Flexible(
                        child: Text(
                          user.displayName,
                          style: const TextStyle(
                            color: NeonColors.textPrimary,
                            fontFamily: 'JetBrainsMono',
                            fontSize: 12,
                            fontWeight: FontWeight.w700,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      if (user.username.isNotEmpty) ...[
                        const SizedBox(width: 4),
                        Text(
                          '@${user.username}',
                          style: const TextStyle(
                            color: NeonColors.textSecondary,
                            fontFamily: 'JetBrainsMono',
                            fontSize: 10,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ],
                  ),
                  const SizedBox(height: 2),
                  Row(
                    children: [
                      Text(
                        'ID: ${user.id}',
                        style: const TextStyle(
                          color: NeonColors.textDisabled,
                          fontFamily: 'JetBrainsMono',
                          fontSize: 9,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        '${user.messageCount} msgs',
                        style: const TextStyle(
                          color: NeonColors.textDisabled,
                          fontFamily: 'JetBrainsMono',
                          fontSize: 9,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),

            // Role badge
            Container(
              padding:
                  const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: _roleColor.withOpacity(0.15),
                border: Border.all(color: _roleColor.withOpacity(0.5)),
                borderRadius: BorderRadius.circular(4),
              ),
              child: Text(
                user.role.toUpperCase(),
                style: TextStyle(
                  color: _roleColor,
                  fontFamily: 'Orbitron',
                  fontSize: 8,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),

            const SizedBox(width: 8),
            const Icon(Icons.chevron_right,
                color: NeonColors.textSecondary, size: 16),
          ],
        ),
      ),
    );
  }
}

class _UserActionsSheet extends StatelessWidget {
  final TelegramUser user;
  final void Function(String action, String? value) onAction;

  static const _roles = ['god', 'admin', 'vip', 'user', 'noob'];

  const _UserActionsSheet({required this.user, required this.onAction});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            children: [
              const Icon(Icons.manage_accounts,
                  color: NeonColors.cyan, size: 20),
              const SizedBox(width: 8),
              Expanded(
                child: NeonText(
                  user.displayName,
                  color: NeonColors.textPrimary,
                  fontSize: 14,
                  fontFamily: 'Orbitron',
                  fontWeight: FontWeight.w700,
                  glowRadius: 4,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            'ID: ${user.id}  •  Role: ${user.role}',
            style: const TextStyle(
                color: NeonColors.textSecondary,
                fontFamily: 'JetBrainsMono',
                fontSize: 10),
          ),
          const Divider(color: NeonColors.cyanGlow, height: 24),

          // Change role
          const NeonText('CHANGE ROLE',
              color: NeonColors.cyan,
              fontSize: 10,
              fontFamily: 'Orbitron',
              glowRadius: 4),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: _roles.map((role) {
              final isCurrentRole = user.role == role;
              final color = _roleColor(role);
              return GestureDetector(
                onTap: isCurrentRole
                    ? null
                    : () => onAction('role', role),
                child: Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 14, vertical: 8),
                  decoration: BoxDecoration(
                    color: isCurrentRole
                        ? color.withOpacity(0.3)
                        : color.withOpacity(0.1),
                    border: Border.all(
                      color: isCurrentRole ? color : color.withOpacity(0.4),
                    ),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    role.toUpperCase(),
                    style: TextStyle(
                      color: isCurrentRole
                          ? color
                          : color.withOpacity(0.7),
                      fontFamily: 'Orbitron',
                      fontSize: 10,
                      fontWeight: isCurrentRole
                          ? FontWeight.w700
                          : FontWeight.normal,
                    ),
                  ),
                ),
              );
            }).toList(),
          ),

          const SizedBox(height: 16),

          // Ban/Unban
          SizedBox(
            width: double.infinity,
            child: GestureDetector(
              onTap: () =>
                  onAction(user.isBanned ? 'unban' : 'ban', null),
              child: Container(
                padding: const EdgeInsets.symmetric(vertical: 12),
                decoration: BoxDecoration(
                  color: (user.isBanned ? NeonColors.green : Colors.red)
                      .withOpacity(0.1),
                  border: Border.all(
                    color: (user.isBanned ? NeonColors.green : Colors.red)
                        .withOpacity(0.5),
                  ),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      user.isBanned ? Icons.lock_open : Icons.block,
                      color: user.isBanned ? NeonColors.green : Colors.red,
                      size: 16,
                    ),
                    const SizedBox(width: 8),
                    NeonText(
                      user.isBanned ? 'UNBAN USER' : 'BAN USER',
                      color: user.isBanned ? NeonColors.green : Colors.red,
                      fontFamily: 'Orbitron',
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                    ),
                  ],
                ),
              ),
            ),
          ),
          const SizedBox(height: 8),
        ],
      ),
    );
  }

  Color _roleColor(String role) {
    switch (role) {
      case 'god':
        return NeonColors.pink;
      case 'admin':
        return NeonColors.yellow;
      case 'vip':
        return NeonColors.purple;
      case 'user':
        return NeonColors.cyan;
      case 'noob':
        return NeonColors.textSecondary;
      default:
        return NeonColors.cyan;
    }
  }
}

// ─── BROADCAST TAB ────────────────────────────────────────────────────────────

class _BroadcastTab extends StatefulWidget {
  const _BroadcastTab();

  @override
  State<_BroadcastTab> createState() => _BroadcastTabState();
}

class _BroadcastTabState extends State<_BroadcastTab> {
  final _msgCtrl = TextEditingController();
  String _targetRole = 'all';
  bool _sending = false;
  List<_SentMessage> _history = [];

  static const _targets = [
    ('all', 'ALL USERS', NeonColors.cyan),
    ('vip', 'VIP', NeonColors.purple),
    ('admin', 'ADMINS', NeonColors.yellow),
    ('user', 'USERS', NeonColors.green),
  ];

  @override
  void dispose() {
    _msgCtrl.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final text = _msgCtrl.text.trim();
    if (text.isEmpty) return;

    setState(() => _sending = true);
    final api = ApiServiceProvider.of(context);
    final ok = await api.sendBroadcast(
      text,
      role: _targetRole == 'all' ? null : _targetRole,
    );

    if (!mounted) return;
    setState(() {
      _sending = false;
      if (ok) {
        _history.insert(
          0,
          _SentMessage(
            text: text,
            target: _targetRole,
            sentAt: DateTime.now(),
          ),
        );
        _msgCtrl.clear();
      }
    });

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(ok ? '✅ Broadcast sent!' : '❌ Send failed'),
        backgroundColor: ok ? NeonColors.bgCard : NeonColors.pink,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Target selection
          NeonCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const NeonText('> TARGET AUDIENCE',
                    color: NeonColors.cyan,
                    fontSize: 11,
                    fontFamily: 'Orbitron',
                    glowRadius: 4),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: _targets.map((t) {
                    final (role, label, color) = t;
                    final isActive = _targetRole == role;
                    return GestureDetector(
                      onTap: () => setState(() => _targetRole = role),
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 200),
                        padding: const EdgeInsets.symmetric(
                            horizontal: 14, vertical: 8),
                        decoration: BoxDecoration(
                          color: isActive
                              ? color.withOpacity(0.2)
                              : Colors.transparent,
                          border: Border.all(
                              color: isActive
                                  ? color
                                  : color.withOpacity(0.3)),
                          borderRadius: BorderRadius.circular(8),
                          boxShadow: isActive
                              ? [
                                  BoxShadow(
                                      color: color.withOpacity(0.3),
                                      blurRadius: 8)
                                ]
                              : [],
                        ),
                        child: Text(
                          label,
                          style: TextStyle(
                            color: isActive ? color : color.withOpacity(0.6),
                            fontFamily: 'Orbitron',
                            fontSize: 10,
                            fontWeight: isActive
                                ? FontWeight.w700
                                : FontWeight.normal,
                          ),
                        ),
                      ),
                    );
                  }).toList(),
                ),
              ],
            ),
          ).animate().fadeIn(duration: 400.ms),

          const SizedBox(height: 16),

          // Message input
          NeonCard(
            glowColor: NeonColors.purple,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const NeonText('> MESSAGE',
                    color: NeonColors.purple,
                    fontSize: 11,
                    fontFamily: 'Orbitron',
                    glowRadius: 4),
                const SizedBox(height: 12),
                TextField(
                  controller: _msgCtrl,
                  maxLines: 5,
                  style: const TextStyle(
                    color: NeonColors.textPrimary,
                    fontFamily: 'JetBrainsMono',
                    fontSize: 13,
                  ),
                  decoration: InputDecoration(
                    hintText: 'Enter broadcast message...',
                    hintStyle: const TextStyle(
                      color: NeonColors.textDisabled,
                      fontFamily: 'JetBrainsMono',
                      fontSize: 12,
                    ),
                    filled: true,
                    fillColor: NeonColors.bgDeep,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                      borderSide:
                          const BorderSide(color: NeonColors.cyanGlow),
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                      borderSide:
                          const BorderSide(color: NeonColors.purple, width: 2),
                    ),
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                      borderSide:
                          const BorderSide(color: NeonColors.cyanGlow),
                    ),
                    contentPadding: const EdgeInsets.all(12),
                  ),
                ),
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: _sending
                      ? const Center(
                          child: NeonLoadingIndicator(
                              label: 'SENDING...', size: 32))
                      : GestureDetector(
                          onTap: _send,
                          child: Container(
                            padding:
                                const EdgeInsets.symmetric(vertical: 14),
                            decoration: neonButtonDecoration(
                                color: NeonColors.purple),
                            child: const Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(Icons.send,
                                    color: NeonColors.purple, size: 16),
                                SizedBox(width: 8),
                                NeonText('SEND BROADCAST',
                                    color: NeonColors.purple,
                                    fontFamily: 'Orbitron',
                                    fontSize: 12,
                                    fontWeight: FontWeight.w700),
                              ],
                            ),
                          ),
                        ),
                ),
              ],
            ),
          ).animate().fadeIn(delay: 100.ms, duration: 400.ms),

          // Sent history
          if (_history.isNotEmpty) ...[
            const SizedBox(height: 16),
            const NeonText('> SENT',
                color: NeonColors.cyan,
                fontSize: 11,
                fontFamily: 'Orbitron',
                glowRadius: 4),
            const SizedBox(height: 10),
            ..._history.take(5).map((m) => _HistoryTile(msg: m)),
          ],
        ],
      ),
    );
  }
}

class _SentMessage {
  final String text;
  final String target;
  final DateTime sentAt;

  const _SentMessage(
      {required this.text, required this.target, required this.sentAt});
}

class _HistoryTile extends StatelessWidget {
  final _SentMessage msg;

  const _HistoryTile({required this.msg});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(10),
      decoration: neonCardDecoration(
          glowColor: NeonColors.purple, glowRadius: 3),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.send, color: NeonColors.purple, size: 12),
              const SizedBox(width: 6),
              Text(
                '→ ${msg.target.toUpperCase()}',
                style: const TextStyle(
                    color: NeonColors.purple,
                    fontFamily: 'Orbitron',
                    fontSize: 9,
                    fontWeight: FontWeight.w700),
              ),
              const Spacer(),
              Text(
                _fmt(msg.sentAt),
                style: const TextStyle(
                    color: NeonColors.textDisabled,
                    fontFamily: 'JetBrainsMono',
                    fontSize: 9),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            msg.text,
            style: const TextStyle(
                color: NeonColors.textSecondary,
                fontFamily: 'JetBrainsMono',
                fontSize: 11),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    ).animate().fadeIn(duration: 300.ms).slideY(begin: -0.05);
  }

  String _fmt(DateTime dt) {
    return '${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
  }
}
