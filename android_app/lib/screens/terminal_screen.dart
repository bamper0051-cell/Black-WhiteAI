import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../theme/neon_theme.dart';
import '../animations/neon_animations.dart';
import '../services/command_memory_service.dart';
import 'main_shell.dart';

class TerminalScreen extends StatefulWidget {
  const TerminalScreen({super.key});
  @override State<TerminalScreen> createState() => _TerminalScreenState();
}

class _TerminalScreenState extends State<TerminalScreen> {
  final _inputCtrl  = TextEditingController();
  final _scrollCtrl = ScrollController();
  final List<_Line> _lines = [];
  bool _running = false;
  final List<String> _history = [];
  List<String> _pinned = [];
  int _historyIdx = -1;

  @override void initState() {
    super.initState();
    _addLine('BlackBugsAI Terminal v3.0 — type "help" for commands', _LT.system);
    _loadMem();
  }

  @override void dispose() { _inputCtrl.dispose(); _scrollCtrl.dispose(); super.dispose(); }

  Future<void> _loadMem() async {
    final h = await CommandMemoryService.loadHistory();
    final p = await CommandMemoryService.loadPinned();
    if (!mounted) return;
    setState(() { _history.addAll(h); _pinned = p; });
  }

  void _addLine(String text, _LT type) => setState(() => _lines.add(_Line(text, type)));

  void _scroll() => WidgetsBinding.instance.addPostFrameCallback((_) {
    if (_scrollCtrl.hasClients) _scrollCtrl.animateTo(_scrollCtrl.position.maxScrollExtent, duration: const Duration(milliseconds: 150), curve: Curves.easeOut);
  });

  Future<void> _run(String cmd) async {
    cmd = cmd.trim(); if (cmd.isEmpty) return;
    await CommandMemoryService.addHistory(cmd);
    _addLine('> \$cmd', _LT.input); _scroll();
    setState(() { _running = true; _historyIdx = -1; });

    if (cmd == 'clear') { setState(() { _lines.clear(); _running = false; }); return; }
    if (cmd == 'help') {
      _addLine('Commands: clear  help  status  <shell command>', _LT.system);
      setState(() => _running = false); _scroll(); return;
    }
    if (cmd == 'status') {
      try {
        final stats = await ApiServiceProvider.of(context).getStats();
        _addLine('Tasks: \${stats.totalTasks} total · \${stats.runningTasks} running · \${stats.doneTasks} done', _LT.output);
        _addLine('Agents: \${stats.agents.length} · Users: \${stats.totalUsers}', _LT.output);
      } catch (e) { _addLine('Error: \$e', _LT.error); }
      setState(() => _running = false); _scroll(); return;
    }
    try {
      final out = await ApiServiceProvider.of(context).runShell(cmd);
      for (final line in out.split('\n')) if (line.isNotEmpty) _addLine(line, _LT.output);
    } catch (e) { _addLine('Error: \$e', _LT.error); }
    setState(() => _running = false); _scroll();
  }

  Future<void> _togglePin(String cmd) async {
    final updated = await CommandMemoryService.togglePinned(cmd.trim());
    if (!mounted) return;
    setState(() => _pinned = updated);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: NeonColors.bgDeep,
      appBar: AppBar(
        title: const NeonText('TERMINAL', fontFamily: 'Orbitron', fontSize: 16, fontWeight: FontWeight.w700, glowRadius: 8),
        actions: [
          IconButton(icon: const Icon(Icons.content_copy, size: 18), onPressed: () { Clipboard.setData(ClipboardData(text: _lines.map((l) => l.text).join('\n'))); ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Copied'))); }),
          IconButton(icon: const Icon(Icons.clear_all, size: 18), onPressed: () => setState(() => _lines.clear())),
        ],
      ),
      body: Column(children: [
        if (_pinned.isNotEmpty) Container(
          margin: const EdgeInsets.all(8),
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(color: NeonColors.bgDark, borderRadius: BorderRadius.circular(8), border: Border.all(color: NeonColors.greenGlow)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const NeonText('> PINNED', color: NeonColors.green, fontSize: 10, fontFamily: 'Orbitron', glowRadius: 4),
            const SizedBox(height: 6),
            Wrap(spacing: 6, runSpacing: 6, children: _pinned.map((cmd) => GestureDetector(
              onTap: () { _inputCtrl.text = cmd; _run(cmd); _inputCtrl.clear(); },
              onLongPress: () => _togglePin(cmd),
              child: Container(padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(color: NeonColors.green.withOpacity(0.08), borderRadius: BorderRadius.circular(6), border: Border.all(color: NeonColors.green.withOpacity(0.4))),
                child: Text(cmd, style: const TextStyle(color: NeonColors.textPrimary, fontFamily: 'JetBrainsMono', fontSize: 11))),
            )).toList()),
          ]),
        ),
        Expanded(child: ListView.builder(controller: _scrollCtrl, padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          itemCount: _lines.length,
          itemBuilder: (_, i) {
            final l = _lines[i];
            final color = l.type == _LT.input ? NeonColors.cyan : l.type == _LT.error ? NeonColors.pink : l.type == _LT.system ? NeonColors.purple : NeonColors.textPrimary;
            return Padding(padding: const EdgeInsets.only(bottom: 1), child: Text(l.text, style: TextStyle(color: color, fontFamily: 'JetBrainsMono', fontSize: 11, height: 1.4)));
          })),
        if (_running) Padding(padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
          child: Row(children: [const NeonLoadingIndicator(size: 16, color: NeonColors.green), const SizedBox(width: 8), const NeonText('EXECUTING...', color: NeonColors.green, fontSize: 10, fontFamily: 'JetBrainsMono')])),
        Container(
          decoration: const BoxDecoration(color: NeonColors.bgDark, border: Border(top: BorderSide(color: NeonColors.cyanGlow))),
          padding: EdgeInsets.only(left: 12, right: 8, top: 8, bottom: MediaQuery.of(context).viewInsets.bottom + 8),
          child: Row(children: [
            const NeonText('>', color: NeonColors.green, fontSize: 14, fontFamily: 'JetBrainsMono'),
            const SizedBox(width: 8),
            Expanded(child: TextField(controller: _inputCtrl,
              style: const TextStyle(color: NeonColors.textPrimary, fontFamily: 'JetBrainsMono', fontSize: 13),
              decoration: const InputDecoration(hintText: 'Enter command...', hintStyle: TextStyle(color: NeonColors.textDisabled, fontFamily: 'JetBrainsMono', fontSize: 12), border: InputBorder.none, isDense: true, contentPadding: EdgeInsets.symmetric(vertical: 6)),
              onSubmitted: (v) { _run(v); _inputCtrl.clear(); },
              onChanged: (_) => setState(() => _historyIdx = -1))),
            GestureDetector(onTap: () { if (_history.isEmpty) return; setState(() { _historyIdx = (_historyIdx+1).clamp(0, _history.length-1).toInt(); _inputCtrl.text = _history[_historyIdx]; }); }, child: const Icon(Icons.arrow_upward, color: NeonColors.textSecondary, size: 18)),
            const SizedBox(width: 4),
            GestureDetector(onTap: () => _togglePin(_inputCtrl.text),
              child: Icon(_pinned.contains(_inputCtrl.text.trim()) ? Icons.star : Icons.star_border,
                color: _pinned.contains(_inputCtrl.text.trim()) ? NeonColors.yellow : NeonColors.textSecondary, size: 18)),
            const SizedBox(width: 4),
            GestureDetector(onTap: () { if (_inputCtrl.text.trim().isNotEmpty) { _run(_inputCtrl.text); _inputCtrl.clear(); } },
              child: Container(padding: const EdgeInsets.all(8), decoration: BoxDecoration(color: NeonColors.green.withOpacity(0.15), borderRadius: BorderRadius.circular(6), border: Border.all(color: NeonColors.green.withOpacity(0.5))),
                child: const Icon(Icons.send, color: NeonColors.green, size: 16))),
          ]),
        ),
      ]),
    );
  }
}

enum _LT { input, output, error, system }
class _Line { final String text; final _LT type; const _Line(this.text, this.type); }
