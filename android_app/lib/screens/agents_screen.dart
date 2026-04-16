import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../theme/neon_theme.dart';
import '../animations/neon_animations.dart';
import '../models/models.dart';
import '../widgets/neon_card.dart';
import 'main_shell.dart';

class AgentsScreen extends StatefulWidget {
  const AgentsScreen({super.key});
  @override State<AgentsScreen> createState() => _AgentsScreenState();
}

class _AgentsScreenState extends State<AgentsScreen> {
  List<AgentInfo> _agents = [];
  bool _loading = true;

  final _colors = {
    'neo': NeonColors.cyan, 'matrix': NeonColors.pink,
    'smith': NeonColors.orange, 'anderson': NeonColors.purple,
    'pythia': Color(0xFF00FFFF), 'tanker': NeonColors.yellow,
    'operator': NeonColors.green,
  };

  @override void initState() { super.initState(); WidgetsBinding.instance.addPostFrameCallback((_) => _load()); }

  Future<void> _load() async {
    try {
      final api = ApiServiceProvider.of(context);
      final agents = await api.getAgents();
      if (!mounted) return;
      setState(() { _agents = agents; _loading = false; });
    } catch (e) { if (!mounted) return; setState(() => _loading = false); }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: NeonColors.bgDeep,
      appBar: AppBar(title: const NeonText('AGENT NETWORK', fontFamily: 'Orbitron', fontSize: 16, fontWeight: FontWeight.w700, glowRadius: 8)),
      body: _loading
        ? const Center(child: NeonLoadingIndicator(label: 'SCANNING AGENTS...'))
        : RefreshIndicator(onRefresh: _load, color: NeonColors.cyan, backgroundColor: NeonColors.bgCard,
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: _agents.length,
              itemBuilder: (_, i) {
                final a = _agents[i];
                final color = _colors[a.id] ?? NeonColors.cyan;
                return Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: NeonCard(glowColor: color, glowRadius: a.isOnline ? 8 : 3, child: Row(children: [
                    Container(width: 4, height: 60, decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(2))),
                    const SizedBox(width: 12),
                    Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      NeonText(a.name, color: color, fontSize: 13, fontFamily: 'Orbitron', fontWeight: FontWeight.w700, glowRadius: 5),
                      Text(a.description, style: const TextStyle(color: NeonColors.textSecondary, fontFamily: 'JetBrainsMono', fontSize: 10), maxLines: 1, overflow: TextOverflow.ellipsis),
                      const SizedBox(height: 4),
                      Row(children: [
                        Text('✅ \${a.tasksCompleted}', style: TextStyle(color: NeonColors.green, fontSize: 10, fontFamily: 'JetBrainsMono')),
                        const SizedBox(width: 10),
                        Text('❌ \${a.tasksFailed}', style: const TextStyle(color: NeonColors.pink, fontSize: 10, fontFamily: 'JetBrainsMono')),
                      ]),
                    ])),
                    Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(color: (a.isOnline ? color : NeonColors.textDisabled).withOpacity(0.15),
                        borderRadius: BorderRadius.circular(4), border: Border.all(color: (a.isOnline ? color : NeonColors.textDisabled).withOpacity(0.5))),
                      child: Text(a.status.toUpperCase(), style: TextStyle(color: a.isOnline ? color : NeonColors.textDisabled, fontFamily: 'JetBrainsMono', fontSize: 8, fontWeight: FontWeight.w700))),
                  ])),
                ).animate().fadeIn(delay: Duration(milliseconds: 80*i)).slideX(begin: 0.1);
              },
            )),
    );
  }
}
