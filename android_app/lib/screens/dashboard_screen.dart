import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../theme/neon_theme.dart';
import '../animations/neon_animations.dart';
import '../models/models.dart';
import '../widgets/neon_card.dart';
import '../widgets/agent_status_chip.dart';
import '../widgets/task_status_bar.dart';
import 'main_shell.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});
  @override State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  SystemStats? _stats;
  List<AgentInfo> _agents = [];
  bool _loading = true;
  String? _error;
  Timer? _timer;
  DateTime _lastRefresh = DateTime.now();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
    _timer = Timer.periodic(const Duration(seconds: 15), (_) => _load());
  }

  @override void dispose() { _timer?.cancel(); super.dispose(); }

  Future<void> _load() async {
    try {
      final api = ApiServiceProvider.of(context);
      final stats  = await api.getStats();
      final agents = await api.getAgents();
      if (!mounted) return;
      setState(() { _stats=stats; _agents=agents; _loading=false; _error=null; _lastRefresh=DateTime.now(); });
    } catch (e) {
      if (!mounted) return;
      setState(() { _error = e.toString(); _loading = false; });
    }
  }

  String _timeAgo(DateTime dt) {
    final d = DateTime.now().difference(dt);
    if (d.inSeconds < 5) return 'just now';
    if (d.inSeconds < 60) return '\${d.inSeconds}s ago';
    return '\${d.inMinutes}m ago';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: NeonColors.bgDeep,
      appBar: AppBar(
        title: const NeonText('CONTROL MATRIX', fontFamily: 'Orbitron', fontSize: 16, fontWeight: FontWeight.w700, glowRadius: 8),
        actions: [Padding(padding: const EdgeInsets.only(right: 16),
          child: PulseGlow(color: NeonColors.green,
            child: Container(width: 8, height: 8, decoration: const BoxDecoration(color: NeonColors.green, shape: BoxShape.circle))))],
      ),
      body: _loading
        ? const Center(child: NeonLoadingIndicator(label: 'SYNCING...', size: 48))
        : _error != null
            ? Center(child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                const Icon(Icons.wifi_off, color: NeonColors.pink, size: 48),
                const SizedBox(height: 16),
                NeonText(_error!, color: NeonColors.pink, fontSize: 12, fontFamily: 'Orbitron'),
                const SizedBox(height: 16),
                GestureDetector(onTap: _load, child: Container(padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                  decoration: neonButtonDecoration(color: NeonColors.cyan),
                  child: const NeonText('RETRY', color: NeonColors.cyan, fontSize: 12, fontFamily: 'Orbitron'))),
              ]))
            : RefreshIndicator(onRefresh: _load, color: NeonColors.cyan, backgroundColor: NeonColors.bgCard,
                child: SingleChildScrollView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  padding: const EdgeInsets.all(16),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Row(children: [
                      Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        NeonTypewriter(text: '> SYSTEM STATUS: OPERATIONAL',
                          style: const TextStyle(fontFamily: 'JetBrainsMono', color: NeonColors.green, fontSize: 11),
                          charDelay: const Duration(milliseconds: 30)),
                        Text('Last sync: \${_timeAgo(_lastRefresh)}',
                          style: const TextStyle(color: NeonColors.textDisabled, fontFamily: 'JetBrainsMono', fontSize: 10)),
                      ])),
                      GestureDetector(onTap: _load, child: Container(padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(border: Border.all(color: NeonColors.cyanGlow), borderRadius: BorderRadius.circular(8)),
                        child: const Icon(Icons.refresh, color: NeonColors.cyan, size: 18))),
                    ]).animate().fadeIn(duration: 400.ms),
                    const SizedBox(height: 16),

                    if (_stats != null) Row(children: [
                      Expanded(child: _StatCard(label: 'TOTAL',   value: '\${_stats!.totalTasks}',   color: NeonColors.cyan,  icon: Icons.list_alt)),
                      const SizedBox(width: 8),
                      Expanded(child: _StatCard(label: 'DONE',    value: '\${_stats!.doneTasks}',    color: NeonColors.green, icon: Icons.check_circle_outline)),
                      const SizedBox(width: 8),
                      Expanded(child: _StatCard(label: 'RUNNING', value: '\${_stats!.runningTasks}', color: NeonColors.cyan,  icon: Icons.play_circle_outline)),
                      const SizedBox(width: 8),
                      Expanded(child: _StatCard(label: 'FAILED',  value: '\${_stats!.failedTasks}',  color: NeonColors.pink,  icon: Icons.error_outline)),
                    ]).animate().fadeIn(delay: 100.ms),
                    const SizedBox(height: 16),

                    NeonText('> AGENTS (\${_agents.length})', color: NeonColors.cyan, fontSize: 11, fontFamily: 'Orbitron', glowRadius: 4),
                    const SizedBox(height: 10),
                    GridView.builder(
                      shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
                      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(crossAxisCount: 2, childAspectRatio: 2.4, mainAxisSpacing: 8, crossAxisSpacing: 8),
                      itemCount: _agents.length,
                      itemBuilder: (_, i) => AgentStatusCard(agent: _agents[i]).animate().fadeIn(delay: Duration(milliseconds: 50*i)),
                    ),
                    const SizedBox(height: 16),

                    if (_stats != null && _stats!.tasksByType.isNotEmpty) ...[
                      NeonText('> BREAKDOWN', color: NeonColors.purple, fontSize: 11, fontFamily: 'Orbitron', glowRadius: 4),
                      const SizedBox(height: 10),
                      ..._stats!.tasksByType.entries.map((e) => Padding(padding: const EdgeInsets.only(bottom: 6), child: TaskStatusBar(type: e.key, count: e.value))),
                    ],
                  ]),
                )),
    );
  }
}

class _StatCard extends StatelessWidget {
  final String label, value; final Color color; final IconData icon;
  const _StatCard({required this.label, required this.value, required this.color, required this.icon});
  @override Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(10), decoration: neonCardDecoration(glowColor: color, glowRadius: 6),
    child: Column(children: [
      Icon(icon, color: color, size: 16), const SizedBox(height: 4),
      Text(value, style: TextStyle(color: color, fontFamily: 'JetBrainsMono', fontSize: 18, fontWeight: FontWeight.w700, shadows: [Shadow(color: color.withOpacity(0.6), blurRadius: 8)])),
      Text(label, style: const TextStyle(color: NeonColors.textSecondary, fontFamily: 'JetBrainsMono', fontSize: 7, letterSpacing: 1)),
    ]),
  );
}
