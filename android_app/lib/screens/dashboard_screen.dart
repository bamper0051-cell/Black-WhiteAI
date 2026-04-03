// dashboard_screen.dart — Main dashboard with live stats and agent monitor

import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:fl_chart/fl_chart.dart';
import '../theme/neon_theme.dart';
import '../animations/neon_animations.dart';
import '../models/models.dart';
import '../widgets/neon_card.dart';
import '../widgets/agent_status_chip.dart';
import '../widgets/task_status_bar.dart';
import 'main_shell.dart';

class DashboardScreen extends StatefulWidget {
  final String appMode;
  const DashboardScreen({super.key, this.appMode = 'server'});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  SystemStats? _stats;
  List<AgentInfo> _agents = [];
  bool _loading = true;
  String? _error;
  Timer? _refreshTimer;
  DateTime _lastRefresh = DateTime.now();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
    _refreshTimer = Timer.periodic(const Duration(seconds: 10), (_) => _load());
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    if (widget.appMode == 'telegram') {
      // In telegram mode, show bot stats via TelegramBotService
      try {
        final provider = AppStateProvider.of(context);
        final tgService = provider.tgService;
        if (tgService != null) {
          final tgStats = await tgService.getBotStats();
          if (!mounted) return;
          setState(() {
            _stats = SystemStats(
              totalTasks: tgStats.totalMessages,
              pendingTasks: 0,
              runningTasks: 0,
              doneTasks: tgStats.messagesToday,
              failedTasks: 0,
              totalUsers: tgStats.totalUsers,
              agents: [],
              tasksByType: {'messages': tgStats.totalMessages},
              timestamp: DateTime.now(),
            );
            _agents = [];
            _loading = false;
            _error = null;
            _lastRefresh = DateTime.now();
          });
        } else {
          if (!mounted) return;
          setState(() { _loading = false; _error = 'No Telegram service'; });
        }
      } catch (e) {
        if (!mounted) return;
        setState(() { _error = e.toString(); _loading = false; });
      }
      return;
    }
    try {
      final api = ApiServiceProvider.of(context);
      final stats = await api.getStats();
      final agents = await api.getAgents();
      if (!mounted) return;
      setState(() {
        _stats = stats;
        _agents = agents;
        _loading = false;
        _error = null;
        _lastRefresh = DateTime.now();
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: NeonColors.bgDeep,
      appBar: AppBar(
        title: const NeonText(
          'CONTROL MATRIX',
          fontFamily: 'Orbitron',
          fontSize: 16,
          fontWeight: FontWeight.w700,
          glowRadius: 8,
        ),
        actions: [
          // Live indicator
          Padding(
            padding: const EdgeInsets.only(right: 16),
            child: PulseGlow(
              color: NeonColors.green,
              child: Container(
                width: 8,
                height: 8,
                decoration: const BoxDecoration(
                  color: NeonColors.green,
                  shape: BoxShape.circle,
                ),
              ),
            ),
          ),
        ],
      ),
      body: _loading
          ? const Center(
              child: NeonLoadingIndicator(label: 'SYNCING...', size: 48))
          : _error != null
              ? _ErrorView(error: _error!, onRetry: _load)
              : RefreshIndicator(
                  onRefresh: _load,
                  color: NeonColors.cyan,
                  backgroundColor: NeonColors.bgCard,
                  child: SingleChildScrollView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _buildHeader(),
                        const SizedBox(height: 16),
                        _buildStatsRow(),
                        const SizedBox(height: 16),
                        _buildAgentGrid(),
                        const SizedBox(height: 16),
                        _buildTaskChart(),
                        const SizedBox(height: 16),
                        _buildRecentTasks(),
                      ],
                    ),
                  ),
                ),
    );
  }

  Widget _buildHeader() {
    return Row(
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              NeonTypewriter(
                text: '> SYSTEM STATUS: OPERATIONAL',
                style: const TextStyle(
                  fontFamily: 'JetBrainsMono',
                  color: NeonColors.green,
                  fontSize: 11,
                ),
                charDelay: const Duration(milliseconds: 30),
              ),
              const SizedBox(height: 4),
              Text(
                'Last sync: ${_timeAgo(_lastRefresh)}',
                style: const TextStyle(
                  color: NeonColors.textDisabled,
                  fontSize: 10,
                  fontFamily: 'JetBrainsMono',
                ),
              ),
            ],
          ),
        ),
        // Refresh button
        GestureDetector(
          onTap: _load,
          child: Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              border: Border.all(color: NeonColors.cyanGlow),
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(Icons.refresh, color: NeonColors.cyan, size: 18),
          ),
        ),
      ],
    ).animate().fadeIn(duration: 400.ms);
  }

  Widget _buildStatsRow() {
    final stats = _stats!;
    return Row(
      children: [
        Expanded(
            child: _StatCard(
                label: 'TOTAL', value: '${stats.totalTasks}',
                color: NeonColors.cyan, icon: Icons.list_alt)),
        const SizedBox(width: 8),
        Expanded(
            child: _StatCard(
                label: 'DONE', value: '${stats.doneTasks}',
                color: NeonColors.green, icon: Icons.check_circle_outline)),
        const SizedBox(width: 8),
        Expanded(
            child: _StatCard(
                label: 'RUNNING', value: '${stats.runningTasks}',
                color: NeonColors.cyan, icon: Icons.play_circle_outline)),
        const SizedBox(width: 8),
        Expanded(
            child: _StatCard(
                label: 'FAILED', value: '${stats.failedTasks}',
                color: NeonColors.pink, icon: Icons.error_outline)),
      ],
    ).animate().fadeIn(delay: 100.ms, duration: 400.ms).slideX(begin: -0.1);
  }

  Widget _buildAgentGrid() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        NeonText('> AGENTS', color: NeonColors.cyan,
            fontSize: 11, fontFamily: 'Orbitron', glowRadius: 4),
        const SizedBox(height: 10),
        GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 2,
            childAspectRatio: 2.2,
            mainAxisSpacing: 8,
            crossAxisSpacing: 8,
          ),
          itemCount: _agents.length,
          itemBuilder: (context, i) => AgentStatusCard(agent: _agents[i])
              .animate()
              .fadeIn(delay: Duration(milliseconds: 50 * i), duration: 300.ms)
              .scale(begin: const Offset(0.95, 0.95)),
        ),
      ],
    );
  }

  Widget _buildTaskChart() {
    final stats = _stats!;
    final total = stats.totalTasks;
    if (total == 0) return const SizedBox.shrink();

    return NeonCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          NeonText('> SUCCESS RATE', color: NeonColors.purple,
              fontSize: 11, fontFamily: 'Orbitron', glowRadius: 4),
          const SizedBox(height: 16),
          Row(
            children: [
              SizedBox(
                height: 100,
                width: 100,
                child: PieChart(
                  PieChartData(
                    sectionsSpace: 2,
                    centerSpaceRadius: 28,
                    sections: [
                      PieChartSectionData(
                        value: stats.doneTasks.toDouble(),
                        color: NeonColors.green,
                        radius: 18,
                        showTitle: false,
                      ),
                      PieChartSectionData(
                        value: stats.failedTasks.toDouble(),
                        color: NeonColors.pink,
                        radius: 18,
                        showTitle: false,
                      ),
                      PieChartSectionData(
                        value: stats.pendingTasks.toDouble(),
                        color: NeonColors.yellow,
                        radius: 18,
                        showTitle: false,
                      ),
                      if (stats.runningTasks > 0)
                        PieChartSectionData(
                          value: stats.runningTasks.toDouble(),
                          color: NeonColors.cyan,
                          radius: 18,
                          showTitle: false,
                        ),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 20),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _ChartLegend('DONE', NeonColors.green, stats.doneTasks),
                    _ChartLegend('FAILED', NeonColors.pink, stats.failedTasks),
                    _ChartLegend('PENDING', NeonColors.yellow, stats.pendingTasks),
                    if (stats.runningTasks > 0)
                      _ChartLegend('RUNNING', NeonColors.cyan, stats.runningTasks),
                    const SizedBox(height: 8),
                    Text(
                      '${(stats.successRate * 100).toStringAsFixed(1)}% SUCCESS',
                      style: const TextStyle(
                        color: NeonColors.green,
                        fontFamily: 'Orbitron',
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    ).animate().fadeIn(delay: 200.ms, duration: 400.ms);
  }

  Widget _buildRecentTasks() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        NeonText('> RECENT ACTIVITY', color: NeonColors.cyan,
            fontSize: 11, fontFamily: 'Orbitron', glowRadius: 4),
        const SizedBox(height: 10),
        ...(_stats?.tasksByType.entries.map((e) => Padding(
          padding: const EdgeInsets.only(bottom: 6),
          child: TaskStatusBar(type: e.key, count: e.value),
        )) ?? []),
      ],
    ).animate().fadeIn(delay: 300.ms, duration: 400.ms);
  }

  String _timeAgo(DateTime dt) {
    final diff = DateTime.now().difference(dt);
    if (diff.inSeconds < 5) return 'just now';
    if (diff.inSeconds < 60) return '${diff.inSeconds}s ago';
    return '${diff.inMinutes}m ago';
  }
}

// ─── Widgets ──────────────────────────────────────────────────────────────────

class _StatCard extends StatelessWidget {
  final String label;
  final String value;
  final Color color;
  final IconData icon;

  const _StatCard({
    required this.label,
    required this.value,
    required this.color,
    required this.icon,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: neonCardDecoration(glowColor: color, glowRadius: 6),
      child: Column(
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

class _ChartLegend extends StatelessWidget {
  final String label;
  final Color color;
  final int count;

  const _ChartLegend(this.label, this.color, this.count);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Row(
        children: [
          Container(
            width: 8, height: 8,
            decoration: BoxDecoration(color: color, shape: BoxShape.circle),
          ),
          const SizedBox(width: 6),
          Text(
            '$label: $count',
            style: TextStyle(
              color: color.withOpacity(0.8),
              fontSize: 10,
              fontFamily: 'JetBrainsMono',
            ),
          ),
        ],
      ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  final String error;
  final VoidCallback onRetry;

  const _ErrorView({required this.error, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.wifi_off, color: NeonColors.pink, size: 48),
            const SizedBox(height: 16),
            NeonText('CONNECTION LOST', color: NeonColors.pink,
                fontSize: 14, fontFamily: 'Orbitron', glowRadius: 8),
            const SizedBox(height: 8),
            Text(
              error,
              style: const TextStyle(
                color: NeonColors.textSecondary,
                fontSize: 11,
                fontFamily: 'JetBrainsMono',
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 24),
            GestureDetector(
              onTap: onRetry,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                decoration: neonButtonDecoration(color: NeonColors.cyan),
                child: const NeonText('RECONNECT', color: NeonColors.cyan,
                    fontSize: 12, fontFamily: 'Orbitron'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
