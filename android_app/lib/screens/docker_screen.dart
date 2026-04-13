<<<<<<< HEAD
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../theme/neon_theme.dart';
import '../animations/neon_animations.dart';
=======
// docker_screen.dart — Управление Docker-контейнером на GCP

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../theme/neon_theme.dart';
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
import '../models/gcp_models.dart';
import '../widgets/neon_card.dart';
import 'main_shell.dart';

class DockerScreen extends StatefulWidget {
  const DockerScreen({super.key});
<<<<<<< HEAD
  @override State<DockerScreen> createState() => _DockerScreenState();
=======

  @override
  State<DockerScreen> createState() => _DockerScreenState();
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
}

class _DockerScreenState extends State<DockerScreen> {
  DockerContainerStatus? _status;
<<<<<<< HEAD
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
=======
  bool _loadingStatus = false;
  String? _statusError;

  final List<String> _logs = [];
  bool _logsConnected = false;

  final _cmdCtrl = TextEditingController();
  bool _runningCmd = false;
  String? _cmdResult;

  @override
  void initState() {
    super.initState();
    _loadStatus();
    _connectLogs();
  }

  @override
  void dispose() {
    _cmdCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadStatus() async {
    setState(() {
      _loadingStatus = true;
      _statusError = null;
    });
    try {
      final api = ApiServiceProvider.of(context);
      final status = await api.getDockerStatus();
      setState(() {
        _status = status;
        _loadingStatus = false;
      });
    } catch (e) {
      setState(() {
        _statusError = 'Ошибка получения статуса: $e';
        _loadingStatus = false;
      });
    }
  }

  void _connectLogs() {
    try {
      final api = ApiServiceProvider.of(context);
      setState(() => _logsConnected = true);
      api.subscribeToLogs().listen(
        (line) {
          if (mounted) {
            setState(() {
              _logs.add(line);
              if (_logs.length > 200) _logs.removeAt(0);
            });
          }
        },
        onDone: () {
          if (mounted) setState(() => _logsConnected = false);
        },
        onError: (_) {
          if (mounted) setState(() => _logsConnected = false);
        },
      );
    } catch (_) {
      setState(() => _logsConnected = false);
    }
  }

  Future<void> _sendDockerCommand(String cmd) async {
    setState(() {
      _runningCmd = true;
      _cmdResult = null;
    });
    try {
      final api = ApiServiceProvider.of(context);
      // For Docker actions (start/stop/restart), pass container name
      // For other commands, use shell command
      final container = _status?.name;
      String result;
      if (['start', 'stop', 'restart'].contains(cmd) && container != null) {
        result = await api.runDockerCommand(cmd, container: container);
      } else {
        result = await api.runShellCommand(cmd);
      }
      setState(() {
        _cmdResult = result;
        _runningCmd = false;
      });
    } catch (e) {
      setState(() {
        _cmdResult = 'Ошибка: $e';
        _runningCmd = false;
      });
    }
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
    await _loadStatus();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: NeonColors.bgDeep,
      appBar: AppBar(
<<<<<<< HEAD
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
=======
        title: const NeonText(
          'DOCKER CONTROL',
          fontFamily: 'Orbitron',
          fontSize: 14,
          fontWeight: FontWeight.w700,
          glowRadius: 8,
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: NeonColors.cyan),
            onPressed: _loadStatus,
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Карточка статуса контейнера
            _buildStatusCard()
                .animate()
                .fadeIn(duration: 400.ms),

            const SizedBox(height: 16),

            // Кнопки управления контейнером
            _buildControlButtons()
                .animate()
                .fadeIn(delay: 100.ms, duration: 400.ms),

            const SizedBox(height: 16),

            // Секция выполнения команд
            _buildCommandSection()
                .animate()
                .fadeIn(delay: 200.ms, duration: 400.ms),

            const SizedBox(height: 16),

            // Секция Live Logs
            _buildLogsSection()
                .animate()
                .fadeIn(delay: 300.ms, duration: 400.ms),
          ],
        ),
      ),
    );
  }

  Widget _buildStatusCard() {
    return NeonCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const NeonText(
                '> СТАТУС КОНТЕЙНЕРА',
                color: NeonColors.cyan,
                fontSize: 11,
                fontFamily: 'Orbitron',
                glowRadius: 4,
              ),
              const Spacer(),
              if (_loadingStatus)
                const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: NeonColors.cyan,
                  ),
                ),
            ],
          ),
          const SizedBox(height: 16),
          if (_statusError != null)
            Text(
              _statusError!,
              style: const TextStyle(
                color: NeonColors.pink,
                fontSize: 11,
                fontFamily: 'JetBrainsMono',
              ),
            )
          else if (_status != null) ...[
            _StatusRow(
              label: 'Статус',
              value: _status!.status,
              valueColor: _status!.isRunning
                  ? NeonColors.green
                  : _status!.isRestarting
                      ? NeonColors.yellow
                      : NeonColors.pink,
            ),
            _StatusRow(label: 'Контейнер', value: _status!.name),
            _StatusRow(label: 'Образ', value: _status!.image),
            _StatusRow(label: 'Uptime', value: _status!.uptime),
            _StatusRow(
              label: 'CPU',
              value: '${_status!.cpuPercent.toStringAsFixed(1)}%',
            ),
            _StatusRow(
              label: 'RAM',
              value: '${_status!.memoryMb.toStringAsFixed(0)} MB',
            ),
          ] else
            const Text(
              'Нет данных',
              style: TextStyle(
                color: NeonColors.textSecondary,
                fontSize: 11,
                fontFamily: 'JetBrainsMono',
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildControlButtons() {
    return NeonCard(
      glowColor: NeonColors.purple,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const NeonText(
            '> УПРАВЛЕНИЕ',
            color: NeonColors.purple,
            fontSize: 11,
            fontFamily: 'Orbitron',
            glowRadius: 4,
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: _DockerButton(
                  label: 'СТАРТ',
                  icon: Icons.play_arrow,
                  color: NeonColors.green,
                  onTap: () => _sendDockerCommand('start'),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: _DockerButton(
                  label: 'СТОП',
                  icon: Icons.stop,
                  color: NeonColors.pink,
                  onTap: () => _sendDockerCommand('stop'),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: _DockerButton(
                  label: 'РЕСТАРТ',
                  icon: Icons.refresh,
                  color: NeonColors.yellow,
                  onTap: () => _sendDockerCommand('restart'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildCommandSection() {
    return NeonCard(
      glowColor: NeonColors.orange,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const NeonText(
            '> ВЫПОЛНИТЬ КОМАНДУ',
            color: NeonColors.orange,
            fontSize: 11,
            fontFamily: 'Orbitron',
            glowRadius: 4,
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _cmdCtrl,
                  style: const TextStyle(
                    color: NeonColors.textPrimary,
                    fontFamily: 'JetBrainsMono',
                    fontSize: 12,
                  ),
                  decoration: InputDecoration(
                    hintText: 'docker ps -a',
                    hintStyle: const TextStyle(
                      color: NeonColors.textDisabled,
                      fontFamily: 'JetBrainsMono',
                      fontSize: 12,
                    ),
                    contentPadding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 10,
                    ),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                      borderSide: const BorderSide(color: NeonColors.cyanGlow),
                    ),
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                      borderSide: const BorderSide(color: NeonColors.cyanGlow),
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                      borderSide:
                          const BorderSide(color: NeonColors.cyan, width: 2),
                    ),
                    filled: true,
                    fillColor: NeonColors.bgCard,
                  ),
                  onSubmitted: (_) {
                    if (!_runningCmd) {
                      _sendDockerCommand(_cmdCtrl.text.trim());
                    }
                  },
                ),
              ),
              const SizedBox(width: 8),
              _runningCmd
                  ? const SizedBox(
                      width: 40,
                      height: 40,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: NeonColors.orange,
                      ),
                    )
                  : GestureDetector(
                      onTap: () {
                        final cmd = _cmdCtrl.text.trim();
                        if (cmd.isNotEmpty) _sendDockerCommand(cmd);
                      },
                      child: Container(
                        width: 44,
                        height: 44,
                        decoration: BoxDecoration(
                          color: NeonColors.orange.withOpacity(0.15),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: NeonColors.orange),
                        ),
                        child: const Icon(
                          Icons.send,
                          color: NeonColors.orange,
                          size: 18,
                        ),
                      ),
                    ),
            ],
          ),
          if (_cmdResult != null) ...[
            const SizedBox(height: 12),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: NeonColors.bgDeep,
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: NeonColors.orange.withOpacity(0.4)),
              ),
              child: Text(
                _cmdResult!,
                style: const TextStyle(
                  color: NeonColors.green,
                  fontFamily: 'JetBrainsMono',
                  fontSize: 11,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildLogsSection() {
    return NeonCard(
      glowColor: NeonColors.green,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const NeonText(
                '> LIVE LOGS',
                color: NeonColors.green,
                fontSize: 11,
                fontFamily: 'Orbitron',
                glowRadius: 4,
              ),
              const SizedBox(width: 8),
              Container(
                width: 8,
                height: 8,
                decoration: BoxDecoration(
                  color: _logsConnected ? NeonColors.green : NeonColors.pink,
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: (_logsConnected ? NeonColors.green : NeonColors.pink)
                          .withOpacity(0.6),
                      blurRadius: 6,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 4),
              Text(
                _logsConnected ? 'ПОДКЛЮЧЕНО' : 'ОТКЛЮЧЕНО',
                style: TextStyle(
                  color: _logsConnected ? NeonColors.green : NeonColors.pink,
                  fontFamily: 'Orbitron',
                  fontSize: 8,
                  letterSpacing: 1,
                ),
              ),
              const Spacer(),
              GestureDetector(
                onTap: () {
                  setState(() => _logs.clear());
                  if (!_logsConnected) _connectLogs();
                },
                child: const Icon(
                  Icons.clear_all,
                  color: NeonColors.textSecondary,
                  size: 18,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Container(
            height: 240,
            width: double.infinity,
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: NeonColors.bgDeep,
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: NeonColors.greenGlow),
            ),
            child: _logs.isEmpty
                ? const Center(
                    child: Text(
                      'Ожидание логов...',
                      style: TextStyle(
                        color: NeonColors.textDisabled,
                        fontFamily: 'JetBrainsMono',
                        fontSize: 11,
                      ),
                    ),
                  )
                : ListView.builder(
                    reverse: true,
                    itemCount: _logs.length,
                    itemBuilder: (_, i) {
                      final line = _logs[_logs.length - 1 - i];
                      return Text(
                        line,
                        style: const TextStyle(
                          color: NeonColors.green,
                          fontFamily: 'JetBrainsMono',
                          fontSize: 10,
                        ),
                      );
                    },
                  ),
          ),
        ],
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
      ),
    );
  }
}

<<<<<<< HEAD
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
=======
class _StatusRow extends StatelessWidget {
  final String label;
  final String value;
  final Color valueColor;

  const _StatusRow({
    required this.label,
    required this.value,
    this.valueColor = NeonColors.textPrimary,
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
              color: valueColor,
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

class _DockerButton extends StatefulWidget {
  final String label;
  final IconData icon;
  final Color color;
  final VoidCallback onTap;

  const _DockerButton({
    required this.label,
    required this.icon,
    required this.color,
    required this.onTap,
  });

  @override
  State<_DockerButton> createState() => _DockerButtonState();
}

class _DockerButtonState extends State<_DockerButton> {
  bool _pressed = false;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTapDown: (_) => setState(() => _pressed = true),
      onTapUp: (_) {
        setState(() => _pressed = false);
        widget.onTap();
      },
      onTapCancel: () => setState(() => _pressed = false),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 100),
        padding: const EdgeInsets.symmetric(vertical: 12),
        decoration: BoxDecoration(
          color: _pressed
              ? widget.color.withOpacity(0.25)
              : widget.color.withOpacity(0.1),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: widget.color, width: 1.5),
          boxShadow: [
            BoxShadow(
              color: widget.color.withOpacity(_pressed ? 0.5 : 0.2),
              blurRadius: _pressed ? 12 : 6,
            ),
          ],
        ),
        child: Column(
          children: [
            Icon(widget.icon, color: widget.color, size: 20),
            const SizedBox(height: 4),
            Text(
              widget.label,
              style: TextStyle(
                color: widget.color,
                fontFamily: 'Orbitron',
                fontSize: 9,
                fontWeight: FontWeight.w700,
                letterSpacing: 1,
              ),
            ),
          ],
        ),
      ),
    );
  }
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
}
