import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../theme/neon_theme.dart';
import '../animations/neon_animations.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import '../services/command_memory_service.dart';
import '../widgets/neon_card.dart';
import 'main_shell.dart';

class ProPanelScreen extends StatefulWidget {
  const ProPanelScreen({super.key});
  @override State<ProPanelScreen> createState() => _ProPanelScreenState();
}

class _ProPanelScreenState extends State<ProPanelScreen> {
  bool _loading = true, _serverOnline = false, _internetOnline = false, _demoMode = false;
  String _baseUrl = '', _adminToken = '';
  List<AgentInfo> _agents = [];
  List<LlmProvider> _providers = [];
  List<String> _pinned = [];
  String? _error;

  @override void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try {
      final prefs   = await SharedPreferences.getInstance();
      final baseUrl = prefs.getString('base_url') ?? '';
      final token   = prefs.getString('admin_token') ?? '';
      final demo    = await ApiService.isDemoMode();
      final api     = ApiService(baseUrl: baseUrl, adminToken: token);
      final ping    = await api.ping();
      bool internet = false;
      try { final r = await InternetAddress.lookup('example.com'); internet = r.isNotEmpty; } catch (_) {}
      final agents    = await api.getAgents();
      final providers = await api.getProviders();
      final pinned    = await CommandMemoryService.loadPinned();
      if (!mounted) return;
      setState(() { _baseUrl = baseUrl; _adminToken = token; _serverOnline = ping; _internetOnline = internet; _demoMode = demo; _agents = agents; _providers = providers; _pinned = pinned; _loading = false; });
    } catch (e) { if (!mounted) return; setState(() { _error = e.toString(); _loading = false; }); }
  }

  Future<void> _setDemoMode(bool v) async { await ApiService.setDemoMode(v); if (!mounted) return; setState(() => _demoMode = v); }

  String _maskToken(String t) { if (t.isEmpty) return '—'; if (t.length <= 6) return '•••$t'; return '•••• \${t.substring(t.length-4)}'; }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: NeonColors.bgDeep,
      appBar: AppBar(title: const NeonText('PRO PANEL', fontFamily: 'Orbitron', fontSize: 14, fontWeight: FontWeight.w700, glowRadius: 8), actions: [IconButton(icon: const Icon(Icons.refresh, color: NeonColors.cyan), onPressed: _load)]),
      body: _loading ? const Center(child: NeonLoadingIndicator(label: 'SYNCING...', size: 48))
        : _error != null ? Center(child: Text(_error!, style: const TextStyle(color: NeonColors.pink, fontFamily: 'JetBrainsMono')))
        : RefreshIndicator(onRefresh: _load, color: NeonColors.cyan, backgroundColor: NeonColors.bgCard,
            child: ListView(padding: const EdgeInsets.all(16), children: [
              NeonCard(glowColor: NeonColors.cyan, child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const NeonText('> CONNECTIVITY', color: NeonColors.cyan, fontSize: 11, fontFamily: 'Orbitron', glowRadius: 4),
                const SizedBox(height: 12),
                _SR('Server',   _serverOnline   ? 'ONLINE'     : 'OFFLINE',  _serverOnline   ? NeonColors.green : NeonColors.pink),
                _SR('Internet', _internetOnline ? 'CONNECTED'  : 'NO ACCESS', _internetOnline ? NeonColors.green : NeonColors.pink),
                _SR('Base URL', _baseUrl.isEmpty ? '—' : _baseUrl),
                _SR('Token',    _maskToken(_adminToken)),
                const SizedBox(height: 10),
                Row(children: [const NeonText('DEMO MODE', color: NeonColors.green, fontSize: 10, fontFamily: 'Orbitron', glowRadius: 4), const Spacer(), Switch(value: _demoMode, activeColor: NeonColors.green, onChanged: _setDemoMode)]),
              ])).animate().fadeIn(duration: 300.ms),
              const SizedBox(height: 12),
              NeonCard(glowColor: NeonColors.purple, child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                NeonText('> AGENTS (\${_agents.length})', color: NeonColors.purple, fontSize: 11, fontFamily: 'Orbitron', glowRadius: 4),
                const SizedBox(height: 12),
                ..._agents.map((a) => Padding(padding: const EdgeInsets.only(bottom: 8), child: Row(children: [
                  Container(width: 10, height: 10, decoration: BoxDecoration(color: a.isOnline ? NeonColors.green : NeonColors.textDisabled, shape: BoxShape.circle)),
                  const SizedBox(width: 8),
                  Expanded(child: Text(a.name, style: const TextStyle(color: NeonColors.textPrimary, fontFamily: 'JetBrainsMono', fontSize: 12))),
                  Text('\${a.tasksCompleted}✓', style: const TextStyle(color: NeonColors.textSecondary, fontFamily: 'JetBrainsMono', fontSize: 10)),
                ]))),
              ])).animate().fadeIn(delay: 80.ms, duration: 300.ms),
              const SizedBox(height: 12),
              NeonCard(glowColor: NeonColors.green, child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const NeonText('> PINNED COMMANDS', color: NeonColors.green, fontSize: 11, fontFamily: 'Orbitron', glowRadius: 4),
                const SizedBox(height: 10),
                _pinned.isEmpty
                  ? const Text('Сохраняй команды в терминале (☆)', style: TextStyle(color: NeonColors.textSecondary, fontFamily: 'JetBrainsMono', fontSize: 11))
                  : Wrap(spacing: 8, runSpacing: 6, children: _pinned.map((cmd) => Container(padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      decoration: BoxDecoration(color: NeonColors.green.withOpacity(0.08), borderRadius: BorderRadius.circular(6), border: Border.all(color: NeonColors.green.withOpacity(0.4))),
                      child: Text(cmd, style: const TextStyle(color: NeonColors.textPrimary, fontFamily: 'JetBrainsMono', fontSize: 11)))).toList()),
              ])).animate().fadeIn(delay: 160.ms, duration: 300.ms),
            ])),
    );
  }
}

class _SR extends StatelessWidget {
  final String label, value; final Color color;
  const _SR(this.label, this.value, [this.color = NeonColors.textPrimary]);
  @override Widget build(BuildContext context) => Padding(padding: const EdgeInsets.only(bottom: 6),
    child: Row(children: [
      Text(label, style: const TextStyle(color: NeonColors.textSecondary, fontFamily: 'JetBrainsMono', fontSize: 11)),
      const Spacer(),
      Text(value, style: TextStyle(color: color, fontFamily: 'JetBrainsMono', fontSize: 11, fontWeight: FontWeight.w700)),
    ]));
}
