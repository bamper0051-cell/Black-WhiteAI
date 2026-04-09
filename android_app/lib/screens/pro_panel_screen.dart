// pro_panel_screen.dart — PRO control center with connectivity, agents and memory

import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../animations/neon_animations.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import '../services/command_memory_service.dart';
import '../theme/neon_theme.dart';
import '../widgets/neon_card.dart';

class ProPanelScreen extends StatefulWidget {
  const ProPanelScreen({super.key});

  @override
  State<ProPanelScreen> createState() => _ProPanelScreenState();
}

class _ProPanelScreenState extends State<ProPanelScreen> {
  bool _loading = true;
  bool _serverOnline = false;
  bool _internetOnline = false;
  bool _demoMode = false;
  String _baseUrl = '';
  String _adminToken = '';
  List<AgentInfo> _agents = [];
  List<LlmProvider> _providers = [];
  List<String> _pinnedCommands = [];
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final prefs = await SharedPreferences.getInstance();
      final baseUrl = prefs.getString('base_url') ?? '';
      final token = prefs.getString('admin_token') ?? '';
      final demo = await ApiService.isDemoMode();

      final api = ApiService(baseUrl: baseUrl, adminToken: token);
      final ping = await api.ping();
      final internet = await _checkInternet();
      final agents = await api.getAgents();
      final providers = await api.getProviders();
      final pinned = await CommandMemoryService.loadPinned();

      if (!mounted) return;
      setState(() {
        _baseUrl = baseUrl;
        _adminToken = token;
        _serverOnline = ping;
        _internetOnline = internet;
        _demoMode = demo;
        _agents = agents;
        _providers = providers;
        _pinnedCommands = pinned;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<bool> _checkInternet() async {
    try {
      final result = await InternetAddress.lookup('example.com');
      return result.isNotEmpty;
    } catch (_) {
      return false;
    }
  }

  Future<void> _setDemoMode(bool value) async {
    await ApiService.setDemoMode(value);
    if (!mounted) return;
    setState(() => _demoMode = value);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          value
              ? 'Demo mode включён — приложение работает автономно'
              : 'Demo mode выключен',
        ),
      ),
    );
    await _load();
  }

  String _maskToken(String token) {
    if (token.isEmpty) return '—';
    if (token.length <= 6) return '•••$token';
    return '•••• ${token.substring(token.length - 4)}';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: NeonColors.bgDeep,
      appBar: AppBar(
        title: const NeonText(
          'PRO CONTROL PANEL',
          fontFamily: 'Orbitron',
          fontSize: 14,
          fontWeight: FontWeight.w700,
          glowRadius: 8,
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: NeonColors.cyan),
            onPressed: _load,
          ),
        ],
      ),
      body: _loading
          ? const Center(
              child: NeonLoadingIndicator(label: 'SYNCING...', size: 48),
            )
          : _error != null
              ? _ErrorView(error: _error!, onRetry: _load)
              : RefreshIndicator(
                  color: NeonColors.cyan,
                  backgroundColor: NeonColors.bgCard,
                  onRefresh: _load,
                  child: ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      _buildConnectivityCard()
                          .animate()
                          .fadeIn(duration: 300.ms)
                          .slideY(begin: 0.05),
                      const SizedBox(height: 12),
                      _buildAgentCard()
                          .animate()
                          .fadeIn(delay: 80.ms, duration: 300.ms)
                          .slideY(begin: 0.05),
                      const SizedBox(height: 12),
                      _buildProvidersCard()
                          .animate()
                          .fadeIn(delay: 120.ms, duration: 300.ms)
                          .slideY(begin: 0.05),
                      const SizedBox(height: 12),
                      _buildMemoryCard()
                          .animate()
                          .fadeIn(delay: 160.ms, duration: 300.ms)
                          .slideY(begin: 0.05),
                    ],
                  ),
                ),
    );
  }

  Widget _buildConnectivityCard() {
    return NeonCard(
      glowColor: NeonColors.cyan,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const NeonText('> CONNECTIVITY', color: NeonColors.cyan,
              fontSize: 11, fontFamily: 'Orbitron', glowRadius: 4),
          const SizedBox(height: 12),
          _StatusRow(
            label: 'Server',
            value: _serverOnline ? 'ONLINE' : 'OFFLINE',
            color: _serverOnline ? NeonColors.green : NeonColors.pink,
          ),
          _StatusRow(
            label: 'Internet',
            value: _internetOnline ? 'CONNECTED' : 'NO ACCESS',
            color: _internetOnline ? NeonColors.green : NeonColors.pink,
          ),
          _StatusRow(
            label: 'Base URL',
            value: _baseUrl.isEmpty ? '—' : _baseUrl,
            color: NeonColors.textSecondary,
          ),
          _StatusRow(
            label: 'Admin Token',
            value: _maskToken(_adminToken),
            color: NeonColors.textSecondary,
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              const NeonText('OFFLINE / DEMO', color: NeonColors.green,
                  fontSize: 10, fontFamily: 'Orbitron', glowRadius: 4),
              const Spacer(),
              Switch(
                value: _demoMode,
                activeColor: NeonColors.green,
                onChanged: _setDemoMode,
              ),
            ],
          ),
          const SizedBox(height: 4),
          const Text(
            'Работает без ПК и сервера. Данные берутся из локальной памяти.',
            style: TextStyle(
              color: NeonColors.textSecondary,
              fontSize: 10,
              fontFamily: 'JetBrainsMono',
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAgentCard() {
    return NeonCard(
      glowColor: NeonColors.purple,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const NeonText('> AGENTS & STATUS', color: NeonColors.purple,
              fontSize: 11, fontFamily: 'Orbitron', glowRadius: 4),
          const SizedBox(height: 12),
          if (_agents.isEmpty)
            const Text(
              'Нет данных об агентах',
              style: TextStyle(
                color: NeonColors.textSecondary,
                fontFamily: 'JetBrainsMono',
                fontSize: 11,
              ),
            )
          else
            Column(
              children: _agents
                  .map((a) => Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: _AgentRow(agent: a),
                      ))
                  .toList(),
            ),
        ],
      ),
    );
  }

  Widget _buildProvidersCard() {
    return NeonCard(
      glowColor: NeonColors.orange,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const NeonText('> LLM PROVIDERS', color: NeonColors.orange,
              fontSize: 11, fontFamily: 'Orbitron', glowRadius: 4),
          const SizedBox(height: 12),
          if (_providers.isEmpty)
            const Text(
              'Провайдеры недоступны',
              style: TextStyle(
                color: NeonColors.textSecondary,
                fontSize: 11,
                fontFamily: 'JetBrainsMono',
              ),
            )
          else
            Column(
              children: _providers
                  .map(
                    (p) => Padding(
                      padding: const EdgeInsets.only(bottom: 6),
                      child: Row(
                        children: [
                          Icon(
                            p.enabled
                                ? Icons.check_circle_outline
                                : Icons.pause_circle_outline,
                            color: p.enabled
                                ? NeonColors.green
                                : NeonColors.textSecondary,
                            size: 16,
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              p.name,
                              style: const TextStyle(
                                color: NeonColors.textPrimary,
                                fontFamily: 'JetBrainsMono',
                                fontSize: 12,
                              ),
                            ),
                          ),
                          Text(
                            p.currentModel ?? (p.models.isNotEmpty ? p.models.first : '-'),
                            style: const TextStyle(
                              color: NeonColors.textSecondary,
                              fontFamily: 'JetBrainsMono',
                              fontSize: 11,
                            ),
                          ),
                        ],
                      ),
                    ),
                  )
                  .toList(),
            ),
        ],
      ),
    );
  }

  Widget _buildMemoryCard() {
    return NeonCard(
      glowColor: NeonColors.green,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const NeonText('> COMMAND MEMORY', color: NeonColors.green,
              fontSize: 11, fontFamily: 'Orbitron', glowRadius: 4),
          const SizedBox(height: 10),
          if (_pinnedCommands.isEmpty)
            const Text(
              'Сохраняйте команды в терминале, чтобы запускать их быстрее.',
              style: TextStyle(
                color: NeonColors.textSecondary,
                fontSize: 11,
                fontFamily: 'JetBrainsMono',
              ),
            )
          else
            Wrap(
              spacing: 8,
              runSpacing: 6,
              children: _pinnedCommands
                  .map(
                    (cmd) => GestureDetector(
                      onLongPress: () async {
                        final updated =
                            await CommandMemoryService.togglePinned(cmd);
                        if (!mounted) return;
                        setState(() => _pinnedCommands = updated);
                      },
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 6),
                        decoration: BoxDecoration(
                          color: NeonColors.green.withOpacity(0.08),
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(
                              color: NeonColors.green.withOpacity(0.4)),
                        ),
                        child: Text(
                          cmd,
                          style: const TextStyle(
                            color: NeonColors.textPrimary,
                            fontFamily: 'JetBrainsMono',
                            fontSize: 11,
                          ),
                        ),
                      ),
                    ),
                  )
                  .toList(),
            ),
          const SizedBox(height: 10),
          const Text(
            'Открывай вкладку SHELL, чтобы запускать сохранённые команды.',
            style: TextStyle(
              color: NeonColors.textSecondary,
              fontSize: 10,
              fontFamily: 'JetBrainsMono',
            ),
          ),
        ],
      ),
    );
  }
}

class _StatusRow extends StatelessWidget {
  final String label;
  final String value;
  final Color color;

  const _StatusRow({
    required this.label,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        children: [
          Text(
            label,
            style: const TextStyle(
              color: NeonColors.textSecondary,
              fontFamily: 'JetBrainsMono',
              fontSize: 11,
            ),
          ),
          const Spacer(),
          Text(
            value,
            style: TextStyle(
              color: color,
              fontFamily: 'JetBrainsMono',
              fontSize: 11,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

class _AgentRow extends StatelessWidget {
  final AgentInfo agent;
  const _AgentRow({required this.agent});

  @override
  Widget build(BuildContext context) {
    final color =
        agent.isOnline ? NeonColors.cyan : NeonColors.textSecondary;
    return Row(
      children: [
        PulseGlow(
          color: color,
          child: Container(
            width: 10,
            height: 10,
            decoration: BoxDecoration(
              color: color,
              shape: BoxShape.circle,
            ),
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                agent.name,
                style: const TextStyle(
                  color: NeonColors.textPrimary,
                  fontFamily: 'JetBrainsMono',
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                ),
              ),
              Text(
                agent.description,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  color: NeonColors.textSecondary,
                  fontFamily: 'JetBrainsMono',
                  fontSize: 10,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(width: 8),
        Text(
          '${agent.tasksCompleted}✓ / ${agent.tasksFailed}✕',
          style: const TextStyle(
            color: NeonColors.textSecondary,
            fontFamily: 'JetBrainsMono',
            fontSize: 10,
          ),
        ),
      ],
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
            const Icon(Icons.error_outline, color: NeonColors.pink, size: 48),
            const SizedBox(height: 12),
            Text(
              error,
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: NeonColors.textSecondary,
                fontSize: 11,
                fontFamily: 'JetBrainsMono',
              ),
            ),
            const SizedBox(height: 16),
            GestureDetector(
              onTap: onRetry,
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 18, vertical: 10),
                decoration: neonButtonDecoration(color: NeonColors.cyan),
                child: const NeonText(
                  'RETRY',
                  color: NeonColors.cyan,
                  fontSize: 12,
                  fontFamily: 'Orbitron',
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
