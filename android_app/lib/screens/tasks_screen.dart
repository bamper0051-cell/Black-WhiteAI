// tasks_screen.dart — Task queue management screen

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

  @override
  State<TasksScreen> createState() => _TasksScreenState();
}

class _TasksScreenState extends State<TasksScreen>
    with SingleTickerProviderStateMixin {
  List<Task> _tasks = [];
  bool _loading = true;
  String? _filterStatus;
  Timer? _timer;
  late TabController _tabCtrl;

  final _statusFilters = [null, 'running', 'pending', 'done', 'failed'];
  final _tabLabels = ['ALL', 'RUN', 'QUEUE', 'DONE', 'ERR'];

  @override
  void initState() {
    super.initState();
    _tabCtrl = TabController(length: _statusFilters.length, vsync: this);
    _tabCtrl.addListener(() {
      setState(() => _filterStatus = _statusFilters[_tabCtrl.index]);
      _load();
    });
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
    _timer = Timer.periodic(const Duration(seconds: 5), (_) => _load());
  }

  @override
  void dispose() {
    _timer?.cancel();
    _tabCtrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final api = ApiServiceProvider.of(context);
      final tasks = await api.getTasks(status: _filterStatus, limit: 30);
      if (!mounted) return;
      setState(() {
        _tasks = tasks;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _loading = false);
    }
  }

  Future<void> _createTask() async {
    final result = await showModalBottomSheet<Map<String, String>>(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (_) => const _CreateTaskSheet(),
    );

    if (result == null) return;
    final api = ApiServiceProvider.of(context);
    await api.createTask(
      userId: 'mobile_user',
      type: result['type'] ?? 'chat',
      title: result['title'] ?? 'New Task',
      payload: {'text': result['payload'] ?? ''},
    );
    _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: NeonColors.bgDeep,
      appBar: AppBar(
        title: const NeonText('TASK QUEUE', fontFamily: 'Orbitron',
            fontSize: 16, fontWeight: FontWeight.w700, glowRadius: 8),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(36),
          child: TabBar(
            controller: _tabCtrl,
            isScrollable: true,
            indicatorColor: NeonColors.cyan,
            indicatorWeight: 2,
            labelColor: NeonColors.cyan,
            unselectedLabelColor: NeonColors.textSecondary,
            labelStyle: const TextStyle(
              fontFamily: 'Orbitron', fontSize: 9, fontWeight: FontWeight.w700,
              letterSpacing: 1.5,
            ),
            tabs: _tabLabels.map((t) => Tab(text: t)).toList(),
          ),
        ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _createTask,
        backgroundColor: NeonColors.bgCard,
        foregroundColor: NeonColors.cyan,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: NeonColors.cyan, width: 1.5),
        ),
        child: const Icon(Icons.add),
      ),
      body: _loading
          ? const Center(child: NeonLoadingIndicator(label: 'LOADING TASKS...'))
          : _tasks.isEmpty
              ? _EmptyState()
              : RefreshIndicator(
                  onRefresh: _load,
                  color: NeonColors.cyan,
                  backgroundColor: NeonColors.bgCard,
                  child: ListView.separated(
                    padding: const EdgeInsets.all(16),
                    itemCount: _tasks.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 8),
                    itemBuilder: (context, i) => _TaskCard(
                      task: _tasks[i],
                      onRetry: () async {
                        final api = ApiServiceProvider.of(context);
                        await api.retryTask(_tasks[i].id);
                        _load();
                      },
                      onCancel: () async {
                        final api = ApiServiceProvider.of(context);
                        await api.cancelTask(_tasks[i].id);
                        _load();
                      },
                    )
                        .animate()
                        .fadeIn(
                            delay: Duration(milliseconds: 30 * i),
                            duration: 250.ms)
                        .slideX(begin: 0.05),
                  ),
                ),
    );
  }
}

class _TaskCard extends StatelessWidget {
  final Task task;
  final VoidCallback onRetry;
  final VoidCallback onCancel;

  const _TaskCard({
    required this.task,
    required this.onRetry,
    required this.onCancel,
  });

  Color get _statusColor {
    switch (task.status) {
      case 'done': return NeonColors.green;
      case 'running': return NeonColors.cyan;
      case 'failed': return NeonColors.pink;
      case 'pending': return NeonColors.yellow;
      default: return NeonColors.textSecondary;
    }
  }

  IconData get _statusIcon {
    switch (task.status) {
      case 'done': return Icons.check_circle_outline;
      case 'running': return Icons.play_circle_outline;
      case 'failed': return Icons.error_outline;
      case 'pending': return Icons.hourglass_empty;
      default: return Icons.cancel_outlined;
    }
  }

  @override
  Widget build(BuildContext context) {
    return NeonCard(
      glowColor: _statusColor,
      glowRadius: task.isRunning ? 10 : 4,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header row
          Row(
            children: [
              task.isRunning
                  ? PulseGlow(
                      color: _statusColor,
                      child: Icon(_statusIcon, color: _statusColor, size: 16),
                    )
                  : Icon(_statusIcon, color: _statusColor, size: 16),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  task.title,
                  style: const TextStyle(
                    color: NeonColors.textPrimary,
                    fontFamily: 'JetBrainsMono',
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: _statusColor.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(color: _statusColor.withOpacity(0.5)),
                ),
                child: Text(
                  task.status.toUpperCase(),
                  style: TextStyle(
                    color: _statusColor,
                    fontSize: 8,
                    fontFamily: 'Orbitron',
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),

          const SizedBox(height: 6),

          // Meta row
          Row(
            children: [
              Text(
                'ID: ${task.id}',
                style: const TextStyle(
                  color: NeonColors.textSecondary,
                  fontSize: 9,
                  fontFamily: 'JetBrainsMono',
                ),
              ),
              const SizedBox(width: 12),
              Text(
                task.type.toUpperCase(),
                style: const TextStyle(
                  color: NeonColors.purple,
                  fontSize: 9,
                  fontFamily: 'Orbitron',
                ),
              ),
              if (task.duration != null) ...[
                const SizedBox(width: 12),
                Text(
                  '${task.duration!.inSeconds}s',
                  style: const TextStyle(
                    color: NeonColors.textSecondary,
                    fontSize: 9,
                    fontFamily: 'JetBrainsMono',
                  ),
                ),
              ],
              const Spacer(),
              if (task.artifacts.isNotEmpty)
                Text(
                  '📎 ${task.artifacts.length}',
                  style: const TextStyle(
                    color: NeonColors.textSecondary,
                    fontSize: 9,
                  ),
                ),
            ],
          ),

          // Result preview
          if (task.isDone && task.result != null) ...[
            const SizedBox(height: 6),
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: NeonColors.bgSurface,
                borderRadius: BorderRadius.circular(4),
              ),
              child: Text(
                task.result!.length > 120
                    ? '${task.result!.substring(0, 120)}...'
                    : task.result!,
                style: const TextStyle(
                  color: NeonColors.textSecondary,
                  fontSize: 10,
                  fontFamily: 'JetBrainsMono',
                ),
              ),
            ),
          ],

          if (task.isFailed && task.error != null) ...[
            const SizedBox(height: 6),
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: NeonColors.pink.withOpacity(0.05),
                borderRadius: BorderRadius.circular(4),
                border: Border.all(color: NeonColors.pink.withOpacity(0.2)),
              ),
              child: Text(
                task.error!.length > 100
                    ? '${task.error!.substring(0, 100)}...'
                    : task.error!,
                style: const TextStyle(
                  color: NeonColors.pink,
                  fontSize: 10,
                  fontFamily: 'JetBrainsMono',
                ),
              ),
            ),
          ],

          // Action buttons
          if (task.isFailed || task.isCancelled || task.isRunning || task.isPending) ...[
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                if (task.isFailed || task.isCancelled)
                  _ActionButton(
                    label: 'RETRY',
                    color: NeonColors.green,
                    icon: Icons.refresh,
                    onTap: onRetry,
                  ),
                if (task.isRunning || task.isPending) ...[
                  const SizedBox(width: 8),
                  _ActionButton(
                    label: 'CANCEL',
                    color: NeonColors.pink,
                    icon: Icons.stop,
                    onTap: onCancel,
                  ),
                ],
              ],
            ),
          ],
        ],
      ),
    );
  }
}

class _ActionButton extends StatelessWidget {
  final String label;
  final Color color;
  final IconData icon;
  final VoidCallback onTap;

  const _ActionButton({
    required this.label,
    required this.color,
    required this.icon,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(
          color: color.withOpacity(0.1),
          borderRadius: BorderRadius.circular(4),
          border: Border.all(color: color.withOpacity(0.5)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: color, size: 12),
            const SizedBox(width: 4),
            Text(
              label,
              style: TextStyle(
                color: color,
                fontFamily: 'Orbitron',
                fontSize: 8,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.inbox_outlined, color: NeonColors.textDisabled, size: 48),
          const SizedBox(height: 12),
          const NeonText('NO TASKS', color: NeonColors.textSecondary,
              fontSize: 14, fontFamily: 'Orbitron'),
          const SizedBox(height: 4),
          const Text(
            'Press + to create a new task',
            style: TextStyle(color: NeonColors.textDisabled,
                fontSize: 11, fontFamily: 'JetBrainsMono'),
          ),
        ],
      ),
    );
  }
}

class _CreateTaskSheet extends StatefulWidget {
  const _CreateTaskSheet();

  @override
  State<_CreateTaskSheet> createState() => _CreateTaskSheetState();
}

class _CreateTaskSheetState extends State<_CreateTaskSheet> {
  final _titleCtrl = TextEditingController();
  final _payloadCtrl = TextEditingController();
  String _type = 'chat';

  final _types = ['chat', 'code', 'image', 'tts', 'shell', 'cycle'];

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.only(
        left: 24, right: 24, top: 24,
        bottom: MediaQuery.of(context).viewInsets.bottom + 24,
      ),
      decoration: const BoxDecoration(
        color: NeonColors.bgDark,
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
        border: Border(top: BorderSide(color: NeonColors.cyanGlow, width: 1)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const NeonText('> NEW TASK', color: NeonColors.cyan,
              fontSize: 13, fontFamily: 'Orbitron', glowRadius: 6),
          const SizedBox(height: 16),

          // Type selector
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: _types.map((t) => GestureDetector(
                onTap: () => setState(() => _type = t),
                child: Container(
                  margin: const EdgeInsets.only(right: 6),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: _type == t
                        ? NeonColors.cyan.withOpacity(0.15)
                        : NeonColors.bgCard,
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(
                      color: _type == t ? NeonColors.cyan : NeonColors.cyanGlow,
                      width: _type == t ? 1.5 : 1,
                    ),
                  ),
                  child: Text(
                    t.toUpperCase(),
                    style: TextStyle(
                      color: _type == t ? NeonColors.cyan : NeonColors.textSecondary,
                      fontFamily: 'Orbitron',
                      fontSize: 9,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              )).toList(),
            ),
          ),

          const SizedBox(height: 14),
          TextField(
            controller: _titleCtrl,
            style: const TextStyle(color: NeonColors.textPrimary,
                fontFamily: 'JetBrainsMono', fontSize: 13),
            decoration: InputDecoration(
              labelText: 'Title',
              labelStyle: const TextStyle(color: NeonColors.textSecondary, fontSize: 11),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(6),
                borderSide: const BorderSide(color: NeonColors.cyanGlow),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(6),
                borderSide: const BorderSide(color: NeonColors.cyan, width: 1.5),
              ),
              filled: true, fillColor: NeonColors.bgCard,
            ),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _payloadCtrl,
            maxLines: 3,
            style: const TextStyle(color: NeonColors.textPrimary,
                fontFamily: 'JetBrainsMono', fontSize: 12),
            decoration: InputDecoration(
              labelText: 'Payload / Task description',
              labelStyle: const TextStyle(color: NeonColors.textSecondary, fontSize: 11),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(6),
                borderSide: const BorderSide(color: NeonColors.cyanGlow),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(6),
                borderSide: const BorderSide(color: NeonColors.cyan, width: 1.5),
              ),
              filled: true, fillColor: NeonColors.bgCard,
            ),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: GestureDetector(
                  onTap: () => Navigator.pop(context),
                  child: Container(
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: NeonColors.textSecondary),
                    ),
                    child: const Center(
                      child: Text('CANCEL', style: TextStyle(
                        color: NeonColors.textSecondary, fontFamily: 'Orbitron',
                        fontSize: 11, fontWeight: FontWeight.w700,
                      )),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: GestureDetector(
                  onTap: () {
                    if (_titleCtrl.text.trim().isEmpty) return;
                    Navigator.pop(context, {
                      'type': _type,
                      'title': _titleCtrl.text.trim(),
                      'payload': _payloadCtrl.text.trim(),
                    });
                  },
                  child: Container(
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    decoration: neonButtonDecoration(color: NeonColors.cyan),
                    child: const Center(
                      child: NeonText('CREATE', color: NeonColors.cyan,
                          fontSize: 11, fontFamily: 'Orbitron',
                          fontWeight: FontWeight.w700),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
