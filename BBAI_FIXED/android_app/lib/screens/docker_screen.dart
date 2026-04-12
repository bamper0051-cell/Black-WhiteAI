import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../theme/neon_theme.dart';
import '../animations/neon_animations.dart';
import '../models/gcp_models.dart';
import '../widgets/neon_card.dart';
import 'main_shell.dart';

class DockerScreen extends StatefulWidget {
  const DockerScreen({super.key});
  @override State<DockerScreen> createState() => _DockerScreenState();
}

class _DockerScreenState extends State<DockerScreen> {
  DockerContainerStatus? _status;
  bool _loading = false;
  String? _statusError;
  final _cmdCtrl = TextEditingController();
  bool _runningCmd = false;
  String? _cmdResult;
  final List<String> _logs = [];

  @override void initState() { super.initState(); _loadStatus(); }
  @override void dispose() { _cmdCtrl.dispose(); super.dispose(); }

  Future<void> _loadStatus() async {
    setState(() { _loading = true; _statusError = null; });
    try {
      final s = await ApiServiceProvider.of(context).getDockerStatus();
      if (!mounted) return;
      setState(() { _status = s; _loading = false; });
    } catch (e) { if (!mounted) return; setState(() { _statusError = e.toString(); _loading = false; }); }
  }

  Future<void> _sendCmd(String cmd) async {
    setState(() { _runningCmd = true; _cmdResult = null; });
    try {
      final r = await ApiServiceProvider.of(context).runDockerCommand(cmd);
      setState(() { _cmdResult = r; _runningCmd = false; });
    } catch (e) { setState(() { _cmdResult = 'Ошибка: \$e'; _runningCmd = false; }); }
    await _loadStatus();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: NeonColors.bgDeep,
      appBar: AppBar(
        title: const NeonText('DOCKER CONTROL', fontFamily: 'Orbitron', fontSize: 14, fontWeight: FontWeight.w700, glowRadius: 8),
        actions: [IconButton(icon: const Icon(Icons.refresh, color: NeonColors.cyan), onPressed: _loadStatus)],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          NeonCard(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              const NeonText('> CONTAINER STATUS', color: NeonColors.cyan, fontSize: 11, fontFamily: 'Orbitron', glowRadius: 4),
              const Spacer(),
              if (_loading) const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: NeonColors.cyan)),
            ]),
            const SizedBox(height: 16),
            if (_statusError != null) Text(_statusError!, style: const TextStyle(color: NeonColors.pink, fontFamily: 'JetBrainsMono', fontSize: 11))
            else if (_status != null) ...[
              _Row('Статус', _status!.status, _status!.isRunning ? NeonColors.green : NeonColors.pink),
              _Row('Контейнер', _status!.name),
              _Row('Образ', _status!.image),
              _Row('Uptime', _status!.uptime),
              _Row('CPU', '\${_status!.cpuPercent.toStringAsFixed(1)}%'),
              _Row('RAM', '\${_status!.memoryMb.toStringAsFixed(0)} MB'),
            ] else const Text('Нет данных', style: TextStyle(color: NeonColors.textSecondary, fontFamily: 'JetBrainsMono', fontSize: 11)),
          ])).animate().fadeIn(duration: 400.ms),
          const SizedBox(height: 14),

          NeonCard(glowColor: NeonColors.purple, child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const NeonText('> УПРАВЛЕНИЕ', color: NeonColors.purple, fontSize: 11, fontFamily: 'Orbitron', glowRadius: 4),
            const SizedBox(height: 16),
            Row(children: [
              Expanded(child: _Btn('СТАРТ',   Icons.play_arrow, NeonColors.green,  () => _sendCmd('start'))),
              const SizedBox(width: 8),
              Expanded(child: _Btn('СТОП',    Icons.stop,       NeonColors.pink,   () => _sendCmd('stop'))),
              const SizedBox(width: 8),
              Expanded(child: _Btn('РЕСТАРТ', Icons.refresh,    NeonColors.yellow, () => _sendCmd('restart'))),
            ]),
          ])).animate().fadeIn(delay: 100.ms, duration: 400.ms),
          const SizedBox(height: 14),

          NeonCard(glowColor: NeonColors.orange, child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const NeonText('> SHELL CMD', color: NeonColors.orange, fontSize: 11, fontFamily: 'Orbitron', glowRadius: 4),
            const SizedBox(height: 12),
            Row(children: [
              Expanded(child: TextField(controller: _cmdCtrl,
                style: const TextStyle(color: NeonColors.textPrimary, fontFamily: 'JetBrainsMono', fontSize: 12),
                decoration: InputDecoration(hintText: 'docker ps -a', hintStyle: const TextStyle(color: NeonColors.textDisabled, fontFamily: 'JetBrainsMono', fontSize: 12), contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10), border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: NeonColors.cyanGlow)), enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: NeonColors.cyanGlow)), focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: NeonColors.cyan, width: 2)), filled: true, fillColor: NeonColors.bgCard),
                onSubmitted: (_) { if (!_runningCmd) _sendCmd(_cmdCtrl.text.trim()); })),
              const SizedBox(width: 8),
              _runningCmd
                ? const SizedBox(width: 40, height: 40, child: CircularProgressIndicator(strokeWidth: 2, color: NeonColors.orange))
                : GestureDetector(onTap: () { final c = _cmdCtrl.text.trim(); if (c.isNotEmpty) _sendCmd(c); },
                    child: Container(width: 44, height: 44, decoration: BoxDecoration(color: NeonColors.orange.withOpacity(0.15), borderRadius: BorderRadius.circular(8), border: Border.all(color: NeonColors.orange)),
                      child: const Icon(Icons.send, color: NeonColors.orange, size: 18))),
            ]),
            if (_cmdResult != null) ...[const SizedBox(height: 12), Container(width: double.infinity, padding: const EdgeInsets.all(12), decoration: BoxDecoration(color: NeonColors.bgDeep, borderRadius: BorderRadius.circular(6), border: Border.all(color: NeonColors.orange.withOpacity(0.4))), child: Text(_cmdResult!, style: const TextStyle(color: NeonColors.green, fontFamily: 'JetBrainsMono', fontSize: 11)))],
          ])).animate().fadeIn(delay: 200.ms, duration: 400.ms),
        ]),
      ),
    );
  }
}

class _Row extends StatelessWidget {
  final String label, value; final Color valueColor;
  const _Row(this.label, this.value, [this.valueColor = NeonColors.textPrimary]);
  @override Widget build(BuildContext context) => Padding(padding: const EdgeInsets.only(bottom: 6),
    child: Row(children: [
      Text(label, style: const TextStyle(color: NeonColors.textSecondary, fontFamily: 'JetBrainsMono', fontSize: 11)),
      const Spacer(),
      Text(value, style: TextStyle(color: valueColor, fontFamily: 'JetBrainsMono', fontSize: 11, fontWeight: FontWeight.w700)),
    ]));
}

class _Btn extends StatelessWidget {
  final String label; final IconData icon; final Color color; final VoidCallback onTap;
  const _Btn(this.label, this.icon, this.color, this.onTap);
  @override Widget build(BuildContext context) => GestureDetector(onTap: onTap, child: Container(padding: const EdgeInsets.symmetric(vertical: 12),
    decoration: BoxDecoration(color: color.withOpacity(0.1), borderRadius: BorderRadius.circular(8), border: Border.all(color: color, width: 1.5)),
    child: Column(children: [Icon(icon, color: color, size: 20), const SizedBox(height: 4), Text(label, style: TextStyle(color: color, fontFamily: 'JetBrainsMono', fontSize: 9, fontWeight: FontWeight.w700))])));
}
