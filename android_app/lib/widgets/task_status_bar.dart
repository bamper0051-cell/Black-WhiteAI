// task_status_bar.dart — Task type bar widget

import 'package:flutter/material.dart';
import '../theme/neon_theme.dart';

class TaskStatusBar extends StatelessWidget {
  final String type;
  final int count;

  const TaskStatusBar({super.key, required this.type, required this.count});

  Color get _color {
    switch (type.toLowerCase()) {
      case 'chat': return NeonColors.cyan;
      case 'code': return NeonColors.purple;
      case 'image': return NeonColors.pink;
      case 'tts': return NeonColors.orange;
      case 'shell': return NeonColors.green;
      case 'tool': return NeonColors.blue;
      case 'cycle': return NeonColors.yellow;
      default: return NeonColors.textSecondary;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        SizedBox(
          width: 56,
          child: Text(
            type.toUpperCase(),
            style: TextStyle(
              color: _color,
              fontFamily: 'Orbitron',
              fontSize: 8,
              fontWeight: FontWeight.w700,
              letterSpacing: 1,
            ),
          ),
        ),
        Expanded(
          child: ClipRRect(
            borderRadius: BorderRadius.circular(2),
            child: LinearProgressIndicator(
              value: count / (count + 1),
              backgroundColor: NeonColors.bgCard,
              valueColor: AlwaysStoppedAnimation(_color),
              minHeight: 8,
            ),
          ),
        ),
        const SizedBox(width: 8),
        Text(
          '$count',
          style: TextStyle(
            color: _color,
            fontFamily: 'JetBrainsMono',
            fontSize: 10,
            fontWeight: FontWeight.w700,
          ),
        ),
      ],
    );
  }
}
