// agents_screen.dart — Agents overview and management

import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../theme/neon_theme.dart';
import '../animations/neon_animations.dart';
import '../models/models.dart';
import '../widgets/neon_card.dart';
import 'main_shell.dart';

class AgentsScreen extends StatefulWidget {
  const AgentsScreen({super.key});

  @override
  State<AgentsScreen> createState() => _AgentsScreenState();
}

class _AgentsScreenState extends State<AgentsScreen> {
  List<AgentInfo> _agents = [];
  bool _loading = true;

  final _agentDetails = {
    'neo': {
      'color': NeonColors.cyan,
      'icon': '🧠',
      'capabilities': ['Self-tool generation', 'Task decomposition', 'OSINT', 'ZIP artifacts'],
      'workspace': '/app/neo_workspace',
    },
    'matrix': {
      'color': NeonColors.purple,
      'icon': '🔀',
      'capabilities': ['Multi-role', 'GitHub tools', 'Coder/Tester/Security/OSINT', 'Self-evolving'],
      'workspace': '/app/matrix_workspace',
    },
    'coder3': {
      'color': NeonColors.green,
      'icon': '💻',
      'capabilities': ['Code generation', '15x auto-fix', 'Python sandbox', 'Multi-LLM'],
      'workspace': '/app/agent_projects',
    },
    'chat': {
      'color': NeonColors.orange,
      'icon': '💬',
      'capabilities': ['Conversational AI', 'Tool calling', 'Sessions', 'Multi-mode'],
      'workspace': '/app/artifacts',
    },
  };

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    try {
      final api = ApiServiceProvider.of(context);
      final agents = await api.getAgents();
      if (!mounted) return;
      setState(() {
        _agents = agents;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: NeonColors.bgDeep,
      appBar: AppBar(
        title: const NeonText('AGENT NETWORK', fontFamily: 'Orbitron',
            fontSize: 16, fontWeight: FontWeight.w700, glowRadius: 8),
      ),
      body: _loading
          ? const Center(child: NeonLoadingIndicator(label: 'SCANNING AGENTS...'))
          : RefreshIndicator(
              onRefresh: _load,
              color: NeonColors.cyan,
              backgroundColor: NeonColors.bgCard,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  // Network visualization
                  _NetworkVisualization(agents: _agents),
                  const SizedBox(height: 20),

                  // Agent cards
                  ..._agents.asMap().entries.map((entry) {
                    final i = entry.key;
                    final agent = entry.value;
                    final details = _agentDetails[agent.id] ?? {};
                    final color = details['color'] as Color? ?? NeonColors.cyan;
                    return _AgentDetailCard(
                      agent: agent,
                      color: color,
                      icon: details['icon'] as String? ?? '🤖',
                      capabilities: details['capabilities'] as List<String>? ?? [],
                    )
                        .animate()
                        .fadeIn(delay: Duration(milliseconds: 100 * i), duration: 400.ms)
                        .slideX(begin: 0.1);
                  }),
                ],
              ),
            ),
    );
  }
}

class _NetworkVisualization extends StatefulWidget {
  final List<AgentInfo> agents;
  const _NetworkVisualization({required this.agents});

  @override
  State<_NetworkVisualization> createState() => _NetworkVisualizationState();
}

class _NetworkVisualizationState extends State<_NetworkVisualization>
    with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 3),
    )..repeat();
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return NeonCard(
      child: Column(
        children: [
          const NeonText('> NEURAL NETWORK', color: NeonColors.cyan,
              fontSize: 10, fontFamily: 'Orbitron', glowRadius: 4),
          const SizedBox(height: 12),
          AnimatedBuilder(
            animation: _ctrl,
            builder: (_, __) => CustomPaint(
              size: const Size(double.infinity, 100),
              painter: _NetworkPainter(
                agents: widget.agents,
                progress: _ctrl.value,
              ),
            ),
          ),
        ],
      ),
    ).animate().fadeIn(duration: 600.ms);
  }
}

class _NetworkPainter extends CustomPainter {
  final List<AgentInfo> agents;
  final double progress;

  _NetworkPainter({required this.agents, required this.progress});

  @override
  void paint(Canvas canvas, Size size) {
    final colors = [NeonColors.cyan, NeonColors.purple, NeonColors.green, NeonColors.orange];
    final n = agents.length.clamp(1, 4);
    final cx = size.width / 2;
    final cy = size.height / 2;
    final r = size.height * 0.35;

    final positions = List.generate(n, (i) {
      final angle = (i / n) * math.pi * 2 - math.pi / 2;
      return Offset(cx + r * math.cos(angle), cy + r * math.sin(angle));
    });

    // Draw connection lines with animated pulse
    for (int i = 0; i < n; i++) {
      for (int j = i + 1; j < n; j++) {
        final paint = Paint()
          ..color = colors[i % colors.length].withOpacity(0.2)
          ..strokeWidth = 1;
        canvas.drawLine(positions[i], positions[j], paint);

        // Animated pulse dot along connection
        final t = (progress + i * 0.25) % 1.0;
        final px = positions[i].dx + (positions[j].dx - positions[i].dx) * t;
        final py = positions[i].dy + (positions[j].dy - positions[i].dy) * t;
        canvas.drawCircle(
          Offset(px, py),
          2,
          Paint()..color = colors[i % colors.length].withOpacity(0.8),
        );
      }
    }

    // Draw agent nodes
    for (int i = 0; i < n; i++) {
      final color = i < agents.length && agents[i].isOnline
          ? colors[i % colors.length]
          : NeonColors.textDisabled;

      // Glow
      canvas.drawCircle(
        positions[i],
        10,
        Paint()
          ..color = color.withOpacity(0.2)
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 8),
      );

      // Outer ring
      canvas.drawCircle(positions[i], 10, Paint()
        ..color = color.withOpacity(0.5)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.5);

      // Inner dot
      canvas.drawCircle(positions[i], 5, Paint()..color = color);
    }

    // Center node (LLM Router)
    final pulseSz = 8.0 + 2 * math.sin(progress * math.pi * 2);
    canvas.drawCircle(
      Offset(cx, cy),
      pulseSz + 4,
      Paint()
        ..color = NeonColors.cyan.withOpacity(0.15)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 8),
    );
    canvas.drawCircle(Offset(cx, cy), pulseSz, Paint()..color = NeonColors.cyan);

    // Center connections
    for (int i = 0; i < n; i++) {
      canvas.drawLine(
        Offset(cx, cy),
        positions[i],
        Paint()
          ..color = NeonColors.cyan.withOpacity(0.15)
          ..strokeWidth = 0.5,
      );
    }
  }

  @override
  bool shouldRepaint(_NetworkPainter old) => old.progress != progress;
}

class _AgentDetailCard extends StatelessWidget {
  final AgentInfo agent;
  final Color color;
  final String icon;
  final List<String> capabilities;

  const _AgentDetailCard({
    required this.agent,
    required this.color,
    required this.icon,
    required this.capabilities,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: NeonCard(
        glowColor: color,
        glowRadius: agent.isOnline ? 10 : 3,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(icon, style: const TextStyle(fontSize: 24)),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      NeonText(
                        agent.name,
                        color: color,
                        fontSize: 14,
                        fontWeight: FontWeight.w700,
                        fontFamily: 'Orbitron',
                        glowRadius: 6,
                      ),
                      Text(
                        agent.description,
                        style: const TextStyle(
                          color: NeonColors.textSecondary,
                          fontSize: 10,
                          fontFamily: 'JetBrainsMono',
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: (agent.isOnline ? color : NeonColors.textDisabled)
                        .withOpacity(0.15),
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(
                      color: (agent.isOnline ? color : NeonColors.textDisabled)
                          .withOpacity(0.5),
                    ),
                  ),
                  child: Text(
                    agent.status.toUpperCase(),
                    style: TextStyle(
                      color: agent.isOnline ? color : NeonColors.textDisabled,
                      fontFamily: 'Orbitron',
                      fontSize: 8,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),

            const SizedBox(height: 12),

            // Stats row
            Row(
              children: [
                _StatBadge('DONE', '${agent.tasksCompleted}', NeonColors.green),
                const SizedBox(width: 8),
                _StatBadge('FAIL', '${agent.tasksFailed}', NeonColors.pink),
              ],
            ),

            const SizedBox(height: 12),
            const Divider(color: NeonColors.cyanGlow, height: 1),
            const SizedBox(height: 10),

            // Capabilities
            NeonText('CAPABILITIES', color: color.withOpacity(0.7),
                fontSize: 8, fontFamily: 'Orbitron'),
            const SizedBox(height: 6),
            Wrap(
              spacing: 6,
              runSpacing: 4,
              children: capabilities
                  .map((c) => Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: color.withOpacity(0.08),
                          borderRadius: BorderRadius.circular(4),
                          border:
                              Border.all(color: color.withOpacity(0.3)),
                        ),
                        child: Text(
                          c,
                          style: TextStyle(
                            color: color.withOpacity(0.8),
                            fontSize: 9,
                            fontFamily: 'JetBrainsMono',
                          ),
                        ),
                      ))
                  .toList(),
            ),
          ],
        ),
      ),
    );
  }
}

class _StatBadge extends StatelessWidget {
  final String label;
  final String value;
  final Color color;

  const _StatBadge(this.label, this.value, this.color);

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            label,
            style: TextStyle(
              color: color.withOpacity(0.6),
              fontSize: 8,
              fontFamily: 'Orbitron',
            ),
          ),
          const SizedBox(width: 4),
          Text(
            value,
            style: TextStyle(
              color: color,
              fontSize: 10,
              fontFamily: 'Orbitron',
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}
