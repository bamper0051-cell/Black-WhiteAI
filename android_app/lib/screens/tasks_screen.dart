import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../theme/neon_theme.dart';
import '../animations/neon_animations.dart';
import '../models/models.dart';
import '../widgets/neon_card.dart';
import 'main_shell.dart';

class TasksScreen extends StatefulWidget {
  const TasksScreen({super.key});
  @override State<TasksScreen> createState() => _TasksScreenState();
}

class _TasksScreenState extends State<TasksScreen> with SingleTickerProviderStateMixin {
  List<Task> _tasks = [];
  bool _loading = true;
  String? _filterStatus;
  Timer? _timer;
  late TabController _tabCtrl;

  final _statusFilters = [null, 'running', 'pending', 'done', 'failed'];
  final _tabLabels = ['ALL', 'RUN', 'QUEUE', 'DONE', 'ERR'];

  @override void initState() {
    super.initState();
    _tabCtrl = TabController(length: _statusFilters.length, vsync: this);
    _tabCtrl.addListener(() { setState(() => _filterStatus = _statusFilters[_tabCtrl.index]); _load(); });
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
    _timer = Timer.periodic(const Duration(seconds: 8), (_) => _load());
  }

  @override void dispose() { _timer?.cancel(); _tabCtrl.dispose(); super.dispose(); }

  Future<void> _load() async {
    try {
      final api = ApiServiceProvider.of(context);
      final tasks = await api.getTasks(status: _filterStatus, limit: 30);
      if (!mounted) return;
      setState(() { _tasks = tasks; _loading = false; });
    } catch (e) { if (!mounted) return; setState(() => _loading = false); }
  }

  Color _statusColor(String status) {
    switch (status) {
      case 'done':    return NeonColors.green;
      case 'running': return NeonColors.cyan;
      case 'failed':  return NeonColors.pink;
      case 'pending': return NeonColors.yellow;
      default:        return NeonColors.textSecondary;
    }
  }

  IconData _statusIcon(String status) {
    switch (status) {
      case 'done':    return Icons.check_circle_outline;
      case 'running': return Icons.play_circle_outline;
      case 'failed':  return Icons.error_outline;
      case 'pending': return Icons.hourglass_empty;
      default:        return Icons.cancel_outlined;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: NeonColors.bgDeep,
      appBar: AppBar(
        title: const NeonText('TASK QUEUE', fontFamily: 'Orbitron', fontSize: 16, fontWeight: FontWeight.w700, glowRadius: 8),
        bottom: PreferredSize(preferredSize: const Size.fromHeight(36), child: TabBar(
          controller: _tabCtrl, isScrollable: true,
          indicatorColor: NeonColors.cyan, indicatorWeight: 2,
          labelColor: NeonColors.cyan, unselectedLabelColor: NeonColors.textSecondary,
          labelStyle: const TextStyle(fontFamily: 'JetBrainsMono', fontSize: 9, fontWeight: FontWeight.w700, letterSpacing: 1.5),
          tabs: _tabLabels.map((t) => Tab(text: t)).toList(),
        )),
      ),
      body: _loading
        ? const Center(child: NeonLoadingIndicator(label: 'LOADING TASKS...'))
        : _tasks.isEmpty
            ? Center(child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                Icon(Icons.inbox_outlined, color: NeonColors.textDisabled, size: 48),
                const SizedBox(height: 12),
                const NeonText('NO TASKS', color: NeonColors.textSecondary, fontSize: 14, fontFamily: 'Orbitron'),
              ]))
            : RefreshIndicator(onRefresh: _load, color: NeonColors.cyan, backgroundColor: NeonColors.bgCard,
                child: ListView.separated(
                  padding: const EdgeInsets.all(16),
                  itemCount: _tasks.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (_, i) {
                    final t = _tasks[i];
                    final color = _statusColor(t.status);
                    return NeonCard(glowColor: color, glowRadius: t.isRunning ? 10 : 4,
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Row(children: [
                          Icon(_statusIcon(t.status), color: color, size: 16),
                          const SizedBox(width: 8),
                          Expanded(child: Text(t.title, style: const TextStyle(color: NeonColors.textPrimary, fontFamily: 'JetBrainsMono', fontSize: 12, fontWeight: FontWeight.w700), overflow: TextOverflow.ellipsis)),
                          Container(padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2), decoration: BoxDecoration(color: color.withOpacity(0.15), borderRadius: BorderRadius.circular(4), border: Border.all(color: color.withOpacity(0.5))),
                            child: Text(t.status.toUpperCase(), style: TextStyle(color: color, fontSize: 8, fontFamily: 'JetBrainsMono', fontWeight: FontWeight.w700))),
                        ]),
                        const SizedBox(height: 4),
                        Text('ID: \${t.id.substring(0, t.id.length.clamp(0, 12).toInt())} · \${t.type.toUpperCase()}', style: const TextStyle(color: NeonColors.textSecondary, fontSize: 9, fontFamily: 'JetBrainsMono')),
                        if (t.isDone && t.result != null) ...[const SizedBox(height: 6), Container(padding: const EdgeInsets.all(8), decoration: BoxDecoration(color: NeonColors.bgSurface, borderRadius: BorderRadius.circular(4)), child: Text(t.result!.length > 100 ? '\${t.result!.substring(0, 100)}...' : t.result!, style: const TextStyle(color: NeonColors.textSecondary, fontSize: 10, fontFamily: 'JetBrainsMono')))],
                        if (t.isFailed && t.error != null) ...[const SizedBox(height: 6), Container(padding: const EdgeInsets.all(8), decoration: BoxDecoration(color: NeonColors.pink.withOpacity(0.05), borderRadius: BorderRadius.circular(4), border: Border.all(color: NeonColors.pink.withOpacity(0.2))), child: Text(t.error!, style: const TextStyle(color: NeonColors.pink, fontSize: 10, fontFamily: 'JetBrainsMono')))],
                        if (t.isFailed) ...[const SizedBox(height: 8), Align(alignment: Alignment.centerRight, child: GestureDetector(onTap: () async { await ApiServiceProvider.of(context).retryTask(t.id); _load(); }, child: Container(padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5), decoration: BoxDecoration(color: NeonColors.green.withOpacity(0.1), borderRadius: BorderRadius.circular(4), border: Border.all(color: NeonColors.green.withOpacity(0.5))), child: Row(mainAxisSize: MainAxisSize.min, children: [const Icon(Icons.refresh, color: NeonColors.green, size: 12), const SizedBox(width: 4), const Text('RETRY', style: TextStyle(color: NeonColors.green, fontFamily: 'JetBrainsMono', fontSize: 8, fontWeight: FontWeight.w700))]))))],
                      ])
                    ).animate().fadeIn(delay: Duration(milliseconds: 30*i));
                  },
                )),
    );
  }
}
