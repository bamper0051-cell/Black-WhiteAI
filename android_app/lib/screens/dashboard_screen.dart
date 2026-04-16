// dashboard_screen.dart — BlackBugsAI Dashboard
// Spark-inspired: GitHub dark canvas + neon agent status cards

import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/neon_theme.dart';
import '../models/models.dart';
import '../widgets/neon_card.dart';
import '../widgets/agent_status_chip.dart';
import '../widgets/task_status_bar.dart';
import 'main_shell.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});
  @override State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen>
    with SingleTickerProviderStateMixin {
  SystemStats? _stats;
  List<AgentInfo> _agents = [];
  bool _loading = true;
  String? _error;
  Timer? _timer;
  DateTime _lastRefresh = DateTime.now();
  late AnimationController _pulseCtrl;

  @override
  void initState() {
    super.initState();
    _pulseCtrl = AnimationController(vsync: this,
        duration: const Duration(milliseconds: 2000))
      ..repeat(reverse: true);
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
    _timer = Timer.periodic(const Duration(seconds: 15), (_) => _load());
  }

  @override
  void dispose() {
    _timer?.cancel();
    _pulseCtrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final api = ApiServiceProvider.of(context);
      final results = await Future.wait([api.getStats(), api.getAgents()]);
      if (!mounted) return;
      setState(() {
        _stats   = results[0] as SystemStats;
        _agents  = results[1] as List<AgentInfo>;
        _loading = false;
        _error   = null;
        _lastRefresh = DateTime.now();
      });
    } catch (e) {
      if (!mounted) return;
      setState(() { _error = e.toString(); _loading = false; });
    }
  }

  String _timeAgo(DateTime dt) {
    final d = DateTime.now().difference(dt);
    if (d.inSeconds < 5)  return 'just now';
    if (d.inSeconds < 60) return '${d.inSeconds}s ago';
    if (d.inMinutes < 60) return '${d.inMinutes}m ago';
    return '${d.inHours}h ago';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: NeonColors.canvas,
      body: CustomScrollView(
        physics: const BouncingScrollPhysics(),
        slivers: [
          _buildAppBar(),
          if (_loading && _stats == null)
            const SliverFillRemaining(child: Center(
              child: CircularProgressIndicator(color: NeonColors.cyan),
            ))
          else if (_error != null && _stats == null)
            SliverFillRemaining(child: _ErrorState(error: _error!, onRetry: _load))
          else
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 100),
              sliver: SliverList(
                delegate: SliverChildListDelegate([
                  const SizedBox(height: 16),
                  _buildStatusRow(),
                  const SizedBox(height: 20),
                  _buildStatsGrid(),
                  const SizedBox(height: 24),
                  _buildAgentsSection(),
                  const SizedBox(height: 24),
                  _buildRecentTasks(),
                  const SizedBox(height: 8),
                  _buildFooter(),
                ]),
              ),
            ),
        ],
      ),
    );
  }

  // ── App Bar ─────────────────────────────────────────────────────────────────

  SliverAppBar _buildAppBar() => SliverAppBar(
        pinned: true,
        backgroundColor: NeonColors.bgDark,
        elevation: 0,
        expandedHeight: 0,
        titleSpacing: 0,
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Container(height: 1, color: NeonColors.border),
        ),
        title: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Row(
            children: [
              AnimatedBuilder(
                animation: _pulseCtrl,
                builder: (_, __) => Container(
                  width: 8, height: 8,
                  margin: const EdgeInsets.only(right: 10),
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: NeonColors.green,
                    boxShadow: [BoxShadow(
                      color: NeonColors.green.withOpacity(0.4 + 0.3 * _pulseCtrl.value),
                      blurRadius: 6,
                    )],
                  ),
                ),
              ),
              Text('BLACKBUGSAI',
                  style: GoogleFonts.orbitron(
                    fontSize: 14, fontWeight: FontWeight.w700,
                    color: NeonColors.textPrimary, letterSpacing: 2,
                  )),
              const Spacer(),
              if (_stats != null)
                Text(_timeAgo(_lastRefresh),
                    style: GoogleFonts.jetBrainsMono(
                      fontSize: 10, color: NeonColors.textMuted,
                    )),
              const SizedBox(width: 12),
              IconButton(
                icon: const Icon(Icons.refresh, size: 18),
                color: NeonColors.textSecondary,
                onPressed: _load,
                tooltip: 'Refresh',
              ),
            ],
          ),
        ),
      );

  // ── Status row ──────────────────────────────────────────────────────────────

  Widget _buildStatusRow() {
    final s = _stats;
    return Row(
      children: [
        _StatusPill(
          label: 'BOT',
          value: s?.botStatus ?? 'unknown',
          color: _statusColor(s?.botStatus ?? ''),
        ),
        const SizedBox(width: 8),
        _StatusPill(
          label: 'LLM',
          value: s?.llmProvider?.toUpperCase() ?? '—',
          color: NeonColors.blue,
        ),
        const SizedBox(width: 8),
        _StatusPill(
          label: 'TASKS',
          value: '${s?.activeTasks ?? 0} active',
          color: (s?.activeTasks ?? 0) > 0 ? NeonColors.cyan : NeonColors.textMuted,
        ),
        const Spacer(),
        if (s?.tunnelUrl != null && s!.tunnelUrl!.isNotEmpty)
          _TunnelChip(url: s.tunnelUrl!),
      ],
    );
  }

  Color _statusColor(String status) {
    switch (status.toLowerCase()) {
      case 'running': case 'ok': case 'online': return NeonColors.green;
      case 'error': case 'offline':             return NeonColors.pink;
      default:                                  return NeonColors.textMuted;
    }
  }

  // ── Stats grid ──────────────────────────────────────────────────────────────

  Widget _buildStatsGrid() {
    final s = _stats;
    final items = [
      _StatItem('CPU', '${s?.cpu?.toStringAsFixed(0) ?? '—'}%',   NeonColors.cyan,   Icons.memory),
      _StatItem('RAM', '${s?.ram?.toStringAsFixed(0) ?? '—'}%',   NeonColors.purple, Icons.storage),
      _StatItem('DONE', '${s?.tasksDone ?? '—'}',                  NeonColors.green,  Icons.check_circle_outline),
      _StatItem('USERS', '${s?.users ?? '—'}',                     NeonColors.orange, Icons.people_outline),
    ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SparkSectionHeader('System', accentColor: NeonColors.cyan),
        const SizedBox(height: 12),
        Row(
          children: items.map((item) => Expanded(
            child: _SparkStatCard(item: item).animate().fadeIn(
              duration: 300.ms,
              delay: Duration(milliseconds: 60 * items.indexOf(item)),
            ),
          )).toList(),
        ),
      ],
    );
  }

  // ── Agents section ──────────────────────────────────────────────────────────

  Widget _buildAgentsSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SparkSectionHeader(
          'Alliance',
          accentColor: NeonColors.purple,
          trailing: Text('${_agents.length} agents',
              style: GoogleFonts.jetBrainsMono(
                  fontSize: 10, color: NeonColors.textMuted)),
        ),
        const SizedBox(height: 12),
        if (_agents.isEmpty)
          _buildEmptyAgents()
        else
          ...List.generate(_agents.length, (i) =>
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: _AgentRow(agent: _agents[i])
                    .animate()
                    .fadeIn(duration: 250.ms, delay: Duration(milliseconds: 40 * i))
                    .slideX(begin: -0.05, end: 0),
              )),
      ],
    );
  }

  Widget _buildEmptyAgents() => Container(
        padding: const EdgeInsets.symmetric(vertical: 24),
        decoration: sparkCardDecoration(),
        child: Center(
          child: Column(children: [
            Icon(Icons.smart_toy_outlined, size: 32, color: NeonColors.textMuted),
            const SizedBox(height: 8),
            Text('No agents active',
                style: GoogleFonts.jetBrainsMono(
                    fontSize: 12, color: NeonColors.textMuted)),
          ]),
        ),
      );

  // ── Recent tasks ────────────────────────────────────────────────────────────

  Widget _buildRecentTasks() {
    final tasks = _stats?.recentTasks ?? [];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SparkSectionHeader('Recent Tasks', accentColor: NeonColors.orange),
        const SizedBox(height: 12),
        if (tasks.isEmpty)
          Container(
            padding: const EdgeInsets.all(16),
            decoration: sparkCardDecoration(),
            child: Row(children: [
              Icon(Icons.inbox_outlined, size: 16, color: NeonColors.textMuted),
              const SizedBox(width: 8),
              Text('No recent tasks',
                  style: GoogleFonts.jetBrainsMono(
                      fontSize: 12, color: NeonColors.textMuted)),
            ]),
          )
        else
          Container(
            decoration: sparkCardDecoration(),
            child: Column(
              children: List.generate(tasks.length > 5 ? 5 : tasks.length, (i) {
                final task = tasks[i];
                return _TaskRow(task: task, isLast: i == (tasks.length > 5 ? 4 : tasks.length - 1));
              }),
            ),
          ),
      ],
    );
  }

  // ── Footer ──────────────────────────────────────────────────────────────────

  Widget _buildFooter() {
    final s = _stats;
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            'v${s?.version ?? "—"} · ${_timeAgo(_lastRefresh)}',
            style: GoogleFonts.jetBrainsMono(
              fontSize: 10, color: NeonColors.textMuted,
            ),
          ),
        ],
      ),
    );
  }
}

// ── Sub-widgets ────────────────────────────────────────────────────────────────

class _StatusPill extends StatelessWidget {
  final String label;
  final String value;
  final Color  color;
  const _StatusPill({required this.label, required this.value, required this.color});

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: color.withOpacity(0.08),
          borderRadius: BorderRadius.circular(4),
          border: Border.all(color: color.withOpacity(0.3)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 6, height: 6,
              margin: const EdgeInsets.only(right: 5),
              decoration: BoxDecoration(shape: BoxShape.circle, color: color),
            ),
            Text(label,
                style: GoogleFonts.jetBrainsMono(
                    fontSize: 9, color: NeonColors.textMuted, fontWeight: FontWeight.w600)),
            const SizedBox(width: 4),
            Text(value,
                style: GoogleFonts.jetBrainsMono(
                    fontSize: 9, color: color, fontWeight: FontWeight.w700)),
          ],
        ),
      );
}

class _TunnelChip extends StatelessWidget {
  final String url;
  const _TunnelChip({required this.url});

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: NeonColors.cyan.withOpacity(0.08),
          borderRadius: BorderRadius.circular(4),
          border: Border.all(color: NeonColors.cyan.withOpacity(0.3)),
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          const Icon(Icons.link, size: 10, color: NeonColors.cyan),
          const SizedBox(width: 4),
          Text('TUNNEL',
              style: GoogleFonts.orbitron(
                  fontSize: 8, color: NeonColors.cyan, fontWeight: FontWeight.w700)),
        ]),
      );
}

class _StatItem {
  final String label;
  final String value;
  final Color  color;
  final IconData icon;
  const _StatItem(this.label, this.value, this.color, this.icon);
}

class _SparkStatCard extends StatelessWidget {
  final _StatItem item;
  const _SparkStatCard({super.key, required this.item});

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(right: 8),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: NeonColors.bgCard,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: NeonColors.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Icon(item.icon, size: 12, color: item.color),
              const SizedBox(width: 4),
              Text(item.label,
                  style: GoogleFonts.orbitron(
                      fontSize: 8, color: NeonColors.textMuted,
                      fontWeight: FontWeight.w700, letterSpacing: 1)),
            ]),
            const SizedBox(height: 8),
            Text(item.value,
                style: GoogleFonts.jetBrainsMono(
                    fontSize: 18, color: item.color, fontWeight: FontWeight.w700)),
          ],
        ),
      );
}

class _AgentRow extends StatelessWidget {
  final AgentInfo agent;
  const _AgentRow({required this.agent});

  @override
  Widget build(BuildContext context) {
    final agentColor = NeonTheme.agentColor(agent.id);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: sparkCardDecoration(highlighted: agent.status == 'active'),
      child: Row(
        children: [
          // Agent dot
          Container(
            width: 32, height: 32,
            decoration: BoxDecoration(
              color: agentColor.withOpacity(0.12),
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: agentColor.withOpacity(0.4)),
            ),
            child: Center(
              child: Text(
                agent.emoji ?? agent.id[0].toUpperCase(),
                style: const TextStyle(fontSize: 14),
              ),
            ),
          ),
          const SizedBox(width: 12),
          // Name + description
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(agent.name ?? agent.id.toUpperCase(),
                    style: GoogleFonts.orbitron(
                        fontSize: 11, color: agentColor,
                        fontWeight: FontWeight.w700, letterSpacing: 1)),
                if (agent.description != null) ...[
                  const SizedBox(height: 2),
                  Text(agent.description!,
                      maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: GoogleFonts.inter(
                          fontSize: 11, color: NeonColors.textSecondary)),
                ],
              ],
            ),
          ),
          // Status
          SparkStatusDot(agent.status ?? 'idle'),
          const SizedBox(width: 6),
          SparkBadge(
            agent.status ?? 'idle',
            color: statusColor(agent.status ?? 'idle'),
          ),
        ],
      ),
    );
  }
}

class _TaskRow extends StatelessWidget {
  final dynamic task;
  final bool isLast;
  const _TaskRow({required this.task, required this.isLast});

  @override
  Widget build(BuildContext context) {
    final color = statusColor((task.status ?? '').toString());
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          child: Row(
            children: [
              SparkStatusDot((task.status ?? 'idle').toString()),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      (task.text ?? 'Task').toString(),
                      maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: GoogleFonts.inter(
                          fontSize: 12, color: NeonColors.textPrimary),
                    ),
                    Text(
                      '${task.agent ?? '?'} · ${task.status ?? '?'}',
                      style: GoogleFonts.jetBrainsMono(
                          fontSize: 10, color: NeonColors.textMuted),
                    ),
                  ],
                ),
              ),
              SparkBadge((task.status ?? '—').toString(), color: color),
            ],
          ),
        ),
        if (!isLast) Divider(color: NeonColors.border, height: 1, indent: 14, endIndent: 14),
      ],
    );
  }
}

class _ErrorState extends StatelessWidget {
  final String error;
  final VoidCallback onRetry;
  const _ErrorState({required this.error, required this.onRetry});

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: NeonColors.pink.withOpacity(0.08),
                  shape: BoxShape.circle,
                  border: Border.all(color: NeonColors.pink.withOpacity(0.3)),
                ),
                child: const Icon(Icons.cloud_off, size: 32, color: NeonColors.pink),
              ),
              const SizedBox(height: 20),
              Text('CONNECTION ERROR',
                  style: GoogleFonts.orbitron(
                      fontSize: 12, color: NeonColors.pink,
                      fontWeight: FontWeight.w700, letterSpacing: 1.5)),
              const SizedBox(height: 8),
              Text(error,
                  textAlign: TextAlign.center,
                  maxLines: 3,
                  style: GoogleFonts.jetBrainsMono(
                      fontSize: 11, color: NeonColors.textSecondary)),
              const SizedBox(height: 20),
              OutlinedButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh, size: 14),
                label: const Text('RETRY'),
              ),
            ],
          ),
        ),
      );
}
