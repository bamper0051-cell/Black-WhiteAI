// terminal_screen.dart — Live terminal / shell interface

import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../theme/neon_theme.dart';
import '../animations/neon_animations.dart';
import 'main_shell.dart';

class TerminalScreen extends StatefulWidget {
  final String appMode;
  const TerminalScreen({super.key, this.appMode = 'telegram'});

  @override
  State<TerminalScreen> createState() => _TerminalScreenState();
}

class _TerminalScreenState extends State<TerminalScreen> {
  final _inputCtrl = TextEditingController();
  final _scrollCtrl = ScrollController();
  final List<_TerminalLine> _lines = [];
  bool _running = false;
  final List<String> _history = [];
  int _historyIdx = -1;

  static const _welcomeLines = [
    '╔══════════════════════════════════════╗',
    '║  BlackBugsAI Terminal v1.0           ║',
    '║  Type "help" for commands            ║',
    '╚══════════════════════════════════════╝',
    '',
  ];

  @override
  void initState() {
    super.initState();
    for (final l in _welcomeLines) {
      _lines.add(_TerminalLine(text: l, type: _LineType.system));
    }
  }

  @override
  void dispose() {
    _inputCtrl.dispose();
    _scrollCtrl.dispose();
    super.dispose();
  }

  Future<void> _execute(String cmd) async {
    cmd = cmd.trim();
    if (cmd.isEmpty) return;

    _history.insert(0, cmd);
    _historyIdx = -1;

    setState(() {
      _lines.add(_TerminalLine(text: '> $cmd', type: _LineType.input));
      _running = true;
    });

    _scrollToBottom();

    // Built-in commands
    if (cmd == 'help') {
      _addLines([
        'Available commands:',
        '  help       — show this help',
        '  clear      — clear terminal',
        '  status     — system status',
        '  agents     — list agents',
        '  tasks      — list tasks',
        '  <cmd>      — run shell command',
      ], _LineType.system);
      setState(() => _running = false);
      _scrollToBottom();
      return;
    }

    if (cmd == 'clear') {
      setState(() {
        _lines.clear();
        _running = false;
      });
      return;
    }

    if (cmd == 'status') {
      try {
        final api = ApiServiceProvider.of(context);
        final stats = await api.getStats();
        _addLines([
          '┌─ System Status ──────────────────┐',
          '│ Total tasks : ${stats.totalTasks}',
          '│ Running     : ${stats.runningTasks}',
          '│ Done        : ${stats.doneTasks}',
          '│ Failed      : ${stats.failedTasks}',
          '│ Users       : ${stats.totalUsers}',
          '│ Success rate: ${(stats.successRate * 100).toStringAsFixed(1)}%',
          '└──────────────────────────────────┘',
        ], _LineType.output);
      } catch (e) {
        _addLines(['Error: $e'], _LineType.error);
      }
      setState(() => _running = false);
      _scrollToBottom();
      return;
    }

    if (cmd == 'agents') {
      try {
        final api = ApiServiceProvider.of(context);
        final agents = await api.getAgents();
        final lines = ['┌─ Agents ─────────────────────────┐'];
        for (final a in agents) {
          final status = a.isOnline ? '● ONLINE' : '○ OFFLINE';
          lines.add('│ ${a.name.padRight(16)} $status');
        }
        lines.add('└──────────────────────────────────┘');
        _addLines(lines, _LineType.output);
      } catch (e) {
        _addLines(['Error: $e'], _LineType.error);
      }
      setState(() => _running = false);
      _scrollToBottom();
      return;
    }

    // Remote shell command
    try {
      final api = ApiServiceProvider.of(context);
      final output = await api.runShell(cmd);
      _addLines(output.split('\n'), _LineType.output);
    } catch (e) {
      _addLines(['Error: ${e.toString()}'], _LineType.error);
    }

    setState(() => _running = false);
    _scrollToBottom();
  }

  void _addLines(List<String> lines, _LineType type) {
    setState(() {
      for (final l in lines) {
        _lines.add(_TerminalLine(text: l, type: type));
      }
    });
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollCtrl.hasClients) {
        _scrollCtrl.animateTo(
          _scrollCtrl.position.maxScrollExtent,
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: NeonColors.bgDeep,
      appBar: AppBar(
        title: const NeonText('TERMINAL', fontFamily: 'Orbitron',
            fontSize: 16, fontWeight: FontWeight.w700, glowRadius: 8),
        actions: [
          IconButton(
            icon: const Icon(Icons.content_copy, size: 18),
            onPressed: () {
              final text = _lines.map((l) => l.text).join('\n');
              Clipboard.setData(ClipboardData(text: text));
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Copied to clipboard')),
              );
            },
          ),
          IconButton(
            icon: const Icon(Icons.clear_all, size: 18),
            onPressed: () => setState(() => _lines.clear()),
          ),
        ],
      ),
      body: Column(
        children: [
          // Output area
          Expanded(
            child: ListView.builder(
              controller: _scrollCtrl,
              padding: const EdgeInsets.all(12),
              itemCount: _lines.length,
              itemBuilder: (_, i) => _TerminalLineWidget(line: _lines[i]),
            ),
          ),

          // Running indicator
          if (_running)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
              child: Row(
                children: [
                  const NeonLoadingIndicator(size: 16, color: NeonColors.green),
                  const SizedBox(width: 8),
                  const NeonText('EXECUTING...', color: NeonColors.green,
                      fontSize: 10, fontFamily: 'JetBrainsMono'),
                ],
              ),
            ),

          // Input area
          Container(
            decoration: const BoxDecoration(
              color: NeonColors.bgDark,
              border: Border(top: BorderSide(color: NeonColors.cyanGlow)),
            ),
            padding: EdgeInsets.only(
              left: 12,
              right: 8,
              top: 8,
              bottom: MediaQuery.of(context).viewInsets.bottom + 8,
            ),
            child: Row(
              children: [
                const NeonText('>', color: NeonColors.green,
                    fontSize: 14, fontFamily: 'JetBrainsMono'),
                const SizedBox(width: 8),
                Expanded(
                  child: TextField(
                    controller: _inputCtrl,
                    style: const TextStyle(
                      color: NeonColors.textPrimary,
                      fontFamily: 'JetBrainsMono',
                      fontSize: 13,
                    ),
                    decoration: const InputDecoration(
                      hintText: 'Enter command...',
                      hintStyle: TextStyle(
                        color: NeonColors.textDisabled,
                        fontFamily: 'JetBrainsMono',
                        fontSize: 12,
                      ),
                      border: InputBorder.none,
                      isDense: true,
                      contentPadding: EdgeInsets.symmetric(vertical: 6),
                    ),
                    onSubmitted: (v) {
                      _execute(v);
                      _inputCtrl.clear();
                    },
                    onChanged: (_) => setState(() => _historyIdx = -1),
                  ),
                ),
                // History navigation
                GestureDetector(
                  onTap: () {
                    if (_history.isEmpty) return;
                    setState(() {
                      _historyIdx =
                          (_historyIdx + 1).clamp(0, _history.length - 1);
                      _inputCtrl.text = _history[_historyIdx];
                    });
                  },
                  child: const Icon(Icons.arrow_upward,
                      color: NeonColors.textSecondary, size: 18),
                ),
                const SizedBox(width: 4),
                GestureDetector(
                  onTap: () {
                    if (_inputCtrl.text.trim().isNotEmpty) {
                      _execute(_inputCtrl.text);
                      _inputCtrl.clear();
                    }
                  },
                  child: Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: NeonColors.green.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(
                          color: NeonColors.green.withOpacity(0.5)),
                    ),
                    child: const Icon(Icons.send,
                        color: NeonColors.green, size: 16),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

enum _LineType { input, output, error, system }

class _TerminalLine {
  final String text;
  final _LineType type;
  const _TerminalLine({required this.text, required this.type});
}

class _TerminalLineWidget extends StatelessWidget {
  final _TerminalLine line;
  const _TerminalLineWidget({super.key, required this.line});

  Color get _color {
    switch (line.type) {
      case _LineType.input: return NeonColors.cyan;
      case _LineType.output: return NeonColors.textPrimary;
      case _LineType.error: return NeonColors.pink;
      case _LineType.system: return NeonColors.purple;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 1),
      child: Text(
        line.text,
        style: TextStyle(
          color: _color,
          fontFamily: 'JetBrainsMono',
          fontSize: 11,
          height: 1.4,
        ),
      ),
    );
  }
}
