<<<<<<< HEAD
// task_status_bar.dart — Task type progress bar widget
=======
// task_status_bar.dart — Task type bar widget
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999

import 'package:flutter/material.dart';
import '../theme/neon_theme.dart';

class TaskStatusBar extends StatelessWidget {
  final String type;
<<<<<<< HEAD
  final int    count;
=======
  final int count;

>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
  const TaskStatusBar({super.key, required this.type, required this.count});

  Color get _color {
    switch (type.toLowerCase()) {
<<<<<<< HEAD
      case 'chat':  return NeonColors.cyan;
      case 'code':  return NeonColors.purple;
      case 'image': return NeonColors.pink;
      case 'tts':   return NeonColors.orange;
      case 'shell': return NeonColors.green;
      case 'tool':  return NeonColors.blue;
      case 'cycle': return NeonColors.yellow;
      default:      return NeonColors.textSecondary;
=======
      case 'chat': return NeonColors.cyan;
      case 'code': return NeonColors.purple;
      case 'image': return NeonColors.pink;
      case 'tts': return NeonColors.orange;
      case 'shell': return NeonColors.green;
      case 'tool': return NeonColors.blue;
      case 'cycle': return NeonColors.yellow;
      default: return NeonColors.textSecondary;
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
    }
  }

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        SizedBox(
          width: 56,
<<<<<<< HEAD
          child: Text(type.toUpperCase(),
              style: TextStyle(
                color:      _color,
                fontFamily: 'JetBrainsMono',
                fontSize:   8,
                fontWeight: FontWeight.w700,
                letterSpacing: 1,
              )),
=======
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
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
        ),
        Expanded(
          child: ClipRRect(
            borderRadius: BorderRadius.circular(2),
            child: LinearProgressIndicator(
<<<<<<< HEAD
              value:          count / (count + 1),
              backgroundColor: NeonColors.bgCard,
              valueColor:      AlwaysStoppedAnimation(_color),
              minHeight:       8,
=======
              value: count / (count + 1),
              backgroundColor: NeonColors.bgCard,
              valueColor: AlwaysStoppedAnimation(_color),
              minHeight: 8,
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
            ),
          ),
        ),
        const SizedBox(width: 8),
<<<<<<< HEAD
        Text('$count',
            style: TextStyle(
              color:      _color,
              fontFamily: 'JetBrainsMono',
              fontSize:   10,
              fontWeight: FontWeight.w700,
            )),
=======
        Text(
          '$count',
          style: TextStyle(
            color: _color,
            fontFamily: 'JetBrainsMono',
            fontSize: 10,
            fontWeight: FontWeight.w700,
          ),
        ),
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
      ],
    );
  }
}
