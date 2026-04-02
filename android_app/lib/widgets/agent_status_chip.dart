// agent_status_chip.dart — Agent status display widget

import 'package:flutter/material.dart';
import '../theme/neon_theme.dart';
import '../animations/neon_animations.dart';
import '../models/models.dart';

class AgentStatusCard extends StatelessWidget {
  final AgentInfo agent;

  const AgentStatusCard({super.key, required this.agent});

  Color get _statusColor {
    switch (agent.status) {
      case 'online':
        return NeonColors.green;
      case 'busy':
        return NeonColors.yellow;
      default:
        return NeonColors.textDisabled;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: neonCardDecoration(
        glowColor: _statusColor,
        glowRadius: agent.isOnline ? 6 : 2,
        borderWidth: agent.isOnline ? 1 : 0.5,
      ),
      child: Row(
        children: [
          // Status dot
          agent.isOnline
              ? PulseGlow(
                  color: _statusColor,
                  duration: const Duration(milliseconds: 1200),
                  child: Container(
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
                ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  agent.name,
                  style: TextStyle(
                    color: _statusColor,
                    fontFamily: 'Orbitron',
                    fontSize: 9,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.5,
                    overflow: TextOverflow.ellipsis,
                  ),
                  maxLines: 1,
                ),
                Text(
                  agent.status.toUpperCase(),
                  style: TextStyle(
                    color: _statusColor.withOpacity(0.6),
                    fontFamily: 'JetBrainsMono',
                    fontSize: 8,
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
