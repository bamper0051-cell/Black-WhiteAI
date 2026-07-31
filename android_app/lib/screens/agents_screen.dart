// agents_screen.dart — Alliance Registry
// Spark UI: agent cards with role badges, live status, quick-launch

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/neon_theme.dart';
import '../models/models.dart';
import 'main_shell.dart';

class AgentsScreen extends StatefulWidget {
  const AgentsScreen({super.key});
  @override State<AgentsScreen> createState() => _AgentsScreenState();
}

class _AgentsScreenState extends State<AgentsScreen> {
  List<AgentInfo> _agents = [];
  bool _loading = true;
  String? _selectedFilter;

  static const _agentMeta = {
    'neo': (
      emoji: '🧬', role: 'AUTONOMOUS',
      desc: 'Self-tool generation, sandbox execution, OSINT, ZIP artifacts',
      access: 'owner+',
    ),
    'matrix': (
      emoji: '🔮', role: 'TOOLSMITH',
      desc: 'Custom tool creation via LLM, GitHub, hybrid mode',
      access: 'owner+',
    ),
    'smith': (
      emoji: '🕶', role: 'GENERATOR',
      desc: 'Bot templates, project scaffolding, code generation',
      access: 'adm+',
    ),
    'pythia': (
      emoji: '💻', role: 'CODER',
      desc: 'Quick code, project mode, code review, autofix, sandbox',
      access: 'all',
    ),
    'anderson': (
      emoji: '🔍', role: 'SECURITY',
      desc: 'Vulnerability analysis, code audit, CVE scanner',
      access: 'all',
    ),
    'tanker': (
      emoji: '🚛', role: 'SCRAPER',
      desc: 'Web parsing, monitoring, RSS feeds, data extraction',
      access: 'all',
    ),
    'operator': (
      emoji: '🎛', role: 'ORCHESTRATOR',
      desc: 'System tasks, agent coordination, task planning',
      access: 'owner+',
    ),
    'morpheus': (
      emoji: '🟣', role: 'SYSTEM',
      desc: 'apt · pip · docker · systemctl · shell automation',
      access: 'owner+',
    ),
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
      setState(() { _agents = agents; _loading = false; });
    } catch (e) {
      if (!mounted) return;
      setState(() => _loading = false);
    }
  }

  AgentInfo _buildDemoAgent(String id) {
    final meta = _agentMeta[id];
    return AgentInfo(
      id: id,
      name: id.toUpperCase(),
      status: 'idle',
      emoji: meta?.emoji ?? '🤖',
      description: meta?.desc,
      available: true,
    );
  }

  List<AgentInfo> get _displayAgents {
    if (_agents.isNotEmpty) return _agents;
    return _agentMeta.keys.map(_buildDemoAgent).toList();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: NeonColors.canvas,
      body: CustomScrollView(
        physics: const BouncingScrollPhysics(),
        slivers: [
          _buildAppBar(),
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 100),
            sliver: SliverList(
              delegate: SliverChildListDelegate([
                _buildFilterRow(),
                const SizedBox(height: 16),
                ..._buildAgentCards(),
              ]),
            ),
          ),
        ],
      ),
    );
  }

  SliverAppBar _buildAppBar() => SliverAppBar(
        pinned: true,
        backgroundColor: NeonColors.bgDark,
        elevation: 0,
        titleSpacing: 0,
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Container(height: 1, color: NeonColors.border),
        ),
        title: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Row(children: [
            Text('ALLIANCE',
                style: GoogleFonts.orbitron(
                    fontSize: 16, fontWeight: FontWeight.w700,
                    color: NeonColors.purple, letterSpacing: 2)),
            const Spacer(),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: NeonColors.purple.withOpacity(0.12),
                borderRadius: BorderRadius.circular(4),
                border: Border.all(color: NeonColors.purple.withOpacity(0.3)),
              ),
              child: Text('${_displayAgents.length} AGENTS',
                  style: GoogleFonts.jetBrainsMono(
                      fontSize: 9, color: NeonColors.purple,
                      fontWeight: FontWeight.w700)),
            ),
          ]),
        ),
      );

  Widget _buildFilterRow() => Row(
        children: ['ALL', 'ACTIVE', 'LOCKED'].map((f) {
          final isSelected = _selectedFilter == f || (_selectedFilter == null && f == 'ALL');
          return Padding(
            padding: const EdgeInsets.only(right: 8),
            child: GestureDetector(
              onTap: () => setState(() => _selectedFilter = f == 'ALL' ? null : f),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: isSelected ? NeonColors.purple.withOpacity(0.15) : NeonColors.bgCard,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(
                    color: isSelected ? NeonColors.purple : NeonColors.border,
                  ),
                ),
                child: Text(f,
                    style: GoogleFonts.orbitron(
                        fontSize: 9, fontWeight: FontWeight.w700,
                        color: isSelected ? NeonColors.purple : NeonColors.textSecondary,
                        letterSpacing: 1)),
              ),
            ),
          );
        }).toList(),
      );

  List<Widget> _buildAgentCards() {
    final agents = _displayAgents;
    return List.generate(agents.length, (i) {
      final agent = agents[i];
      final locked = !(agent.available ?? true);
      if (_selectedFilter == 'ACTIVE' && agent.status != 'active') return const SizedBox.shrink();
      if (_selectedFilter == 'LOCKED' && !locked) return const SizedBox.shrink();
      return Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: _AgentCard(agent: agent, index: i)
            .animate()
            .fadeIn(duration: 300.ms, delay: Duration(milliseconds: 50 * i))
            .slideY(begin: 0.03, end: 0),
      );
    });
  }
}

// ── Agent Card ─────────────────────────────────────────────────────────────────

class _AgentCard extends StatelessWidget {
  final AgentInfo agent;
  final int index;
  const _AgentCard({required this.agent, required this.index});

  static const _agentRoles = {
    'neo': 'AUTONOMOUS', 'matrix': 'TOOLSMITH', 'smith': 'GENERATOR',
    'pythia': 'CODER', 'anderson': 'SECURITY', 'tanker': 'SCRAPER',
    'operator': 'ORCHESTRATOR', 'morpheus': 'SYSTEM',
  };

  static const _agentAccess = {
    'neo': 'owner+', 'matrix': 'owner+', 'smith': 'adm+',
    'operator': 'owner+', 'morpheus': 'owner+',
  };

  @override
  Widget build(BuildContext context) {
    final color   = NeonTheme.agentColor(agent.id);
    final locked  = !(agent.available ?? true);
    final isActive = agent.status == 'active' || agent.status == 'running';
    final role    = _agentRoles[agent.id.toLowerCase()] ?? 'AGENT';
    final access  = _agentAccess[agent.id.toLowerCase()] ?? 'all';

    return Container(
      decoration: BoxDecoration(
        color: NeonColors.bgCard,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: locked
              ? NeonColors.border
              : isActive
                  ? color.withOpacity(0.5)
                  : color.withOpacity(0.2),
          width: isActive ? 1.5 : 1,
        ),
        boxShadow: isActive
            ? [BoxShadow(color: color.withOpacity(0.1), blurRadius: 8, spreadRadius: 0)]
            : null,
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(8),
        child: Stack(
          children: [
            // Subtle left accent bar
            Positioned(
              left: 0, top: 0, bottom: 0,
              child: Container(width: 3, color: locked ? NeonColors.textMuted : color),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 14, 14, 14),
              child: Row(
                children: [
                  // Agent icon
                  _AgentIcon(agent: agent, color: color, locked: locked),
                  const SizedBox(width: 14),
                  // Info
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(children: [
                          Text(agent.name ?? agent.id.toUpperCase(),
                              style: GoogleFonts.orbitron(
                                  fontSize: 12,
                                  fontWeight: FontWeight.w700,
                                  color: locked ? NeonColors.textMuted : color,
                                  letterSpacing: 1)),
                          const SizedBox(width: 8),
                          SparkBadge(role, color: locked ? NeonColors.textMuted : color),
                          if (access != 'all') ...[
                            const SizedBox(width: 6),
                            SparkBadge('🔒 $access',
                                color: NeonColors.orange),
                          ],
                        ]),
                        const SizedBox(height: 4),
                        Text(
                          agent.description ?? _getDesc(agent.id),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: GoogleFonts.inter(
                              fontSize: 11,
                              color: locked ? NeonColors.textMuted : NeonColors.textSecondary),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 10),
                  // Status badge
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      SparkStatusDot(agent.status ?? 'idle', size: 9),
                      const SizedBox(height: 4),
                      Text(
                        (agent.status ?? 'idle').toUpperCase(),
                        style: GoogleFonts.orbitron(
                          fontSize: 7,
                          color: locked ? NeonColors.textMuted
                              : statusColor(agent.status ?? 'idle'),
                          fontWeight: FontWeight.w700,
                          letterSpacing: 0.5,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _getDesc(String id) {
    const descs = {
      'neo': 'Self-tool generation, sandbox execution, OSINT',
      'matrix': 'Custom tool creation via LLM, GitHub, hybrid mode',
      'smith': 'Bot templates, project scaffolding, code generation',
      'pythia': 'Quick code, project mode, code review, autofix',
      'anderson': 'Vulnerability analysis, code audit, CVE scanner',
      'tanker': 'Web parsing, monitoring, RSS feeds, data extraction',
      'operator': 'System tasks, agent coordination, planning',
      'morpheus': 'apt · pip · docker · systemctl · shell automation',
    };
    return descs[id.toLowerCase()] ?? 'AI agent';
  }
}

class _AgentIcon extends StatelessWidget {
  final AgentInfo agent;
  final Color color;
  final bool locked;
  const _AgentIcon({required this.agent, required this.color, required this.locked});

  @override
  Widget build(BuildContext context) => Container(
        width: 44, height: 44,
        decoration: BoxDecoration(
          color: locked ? NeonColors.bgElevated : color.withOpacity(0.12),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: locked ? NeonColors.border : color.withOpacity(0.4),
          ),
        ),
        child: Center(
          child: locked
              ? Icon(Icons.lock_outline, size: 18, color: NeonColors.textMuted)
              : Text(agent.emoji ?? agent.id[0].toUpperCase(),
                  style: const TextStyle(fontSize: 20)),
        ),
      );
}
