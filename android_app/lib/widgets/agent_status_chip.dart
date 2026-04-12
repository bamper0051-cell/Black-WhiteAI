// agent_status_chip.dart — Agent status display widget

import 'package:flutter/material.dart';
import '../theme/neon_theme.dart';
import '../animations/neon_animations.dart';
import '../models/models.dart';

class AgentStatusCard extends StatelessWidget {
  final AgentInfo agent;
<<<<<<< HEAD
=======

>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
  const AgentStatusCard({super.key, required this.agent});

  Color get _statusColor {
    switch (agent.status) {
<<<<<<< HEAD
      case 'online': return NeonColors.green;
      case 'busy':   return NeonColors.yellow;
      default:       return NeonColors.textDisabled;
=======
      case 'online':
        return NeonColors.green;
      case 'busy':
        return NeonColors.yellow;
      default:
        return NeonColors.textDisabled;
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: neonCardDecoration(
<<<<<<< HEAD
        glowColor:   _statusColor,
        glowRadius:  agent.isOnline ? 6 : 2,
=======
        glowColor: _statusColor,
        glowRadius: agent.isOnline ? 6 : 2,
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
        borderWidth: agent.isOnline ? 1 : 0.5,
      ),
      child: Row(
        children: [
<<<<<<< HEAD
=======
          // Status dot
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
          agent.isOnline
              ? PulseGlow(
                  color: _statusColor,
                  duration: const Duration(milliseconds: 1200),
                  child: Container(
<<<<<<< HEAD
                    width: 8, height: 8,
                    decoration: BoxDecoration(
                        color: _statusColor, shape: BoxShape.circle),
                  ),
                )
              : Container(
                  width: 8, height: 8,
                  decoration: BoxDecoration(
                      color: _statusColor, shape: BoxShape.circle),
=======
                    width: 8,
                    height: 8,
                    decoration: BoxDecoration(
                      color: _statusColor,
                      shape: BoxShape.circle,
                    ),
                  ),
                )
              : Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    color: _statusColor,
                    shape: BoxShape.circle,
                  ),
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
                ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
<<<<<<< HEAD
              mainAxisAlignment:  MainAxisAlignment.center,
=======
              mainAxisAlignment: MainAxisAlignment.center,
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
              children: [
                Text(
                  agent.name,
                  style: TextStyle(
<<<<<<< HEAD
                    color:      _statusColor,
                    fontFamily: 'JetBrainsMono',
                    fontSize:   9,
                    fontWeight: FontWeight.w700,
                    overflow:   TextOverflow.ellipsis,
=======
                    color: _statusColor,
                    fontFamily: 'Orbitron',
                    fontSize: 9,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.5,
                    overflow: TextOverflow.ellipsis,
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
                  ),
                  maxLines: 1,
                ),
                Text(
                  agent.status.toUpperCase(),
                  style: TextStyle(
<<<<<<< HEAD
                    color:      _statusColor.withOpacity(0.6),
                    fontFamily: 'JetBrainsMono',
                    fontSize:   8,
=======
                    color: _statusColor.withOpacity(0.6),
                    fontFamily: 'JetBrainsMono',
                    fontSize: 8,
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
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
