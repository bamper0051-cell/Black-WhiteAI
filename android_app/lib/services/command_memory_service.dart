// command_memory_service.dart — persists terminal history and pinned commands

import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

class CommandMemoryService {
  static const _historyKey = 'cmd_history';
<<<<<<< HEAD
  static const _pinnedKey  = 'cmd_pinned';
  static const int _maxHistory = 50;
  static const int _maxPinned  = 20;
=======
  static const _pinnedKey = 'cmd_pinned';
  static const int _maxHistory = 50;
  static const int _maxPinned = 20;
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999

  static Future<List<String>> loadHistory() async {
    final prefs = await SharedPreferences.getInstance();
    return List<String>.from(prefs.getStringList(_historyKey) ?? []);
  }

  static Future<List<String>> addHistory(String cmd) async {
    final normalized = cmd.trim();
    if (normalized.isEmpty) return loadHistory();

<<<<<<< HEAD
    final prefs   = await SharedPreferences.getInstance();
    final history = List<String>.from(prefs.getStringList(_historyKey) ?? []);
    history.removeWhere((c) => c == normalized);
    history.insert(0, normalized);
    if (history.length > _maxHistory) history.removeRange(_maxHistory, history.length);
=======
    final prefs = await SharedPreferences.getInstance();
    final history = List<String>.from(prefs.getStringList(_historyKey) ?? []);
    history.removeWhere((c) => c == normalized);
    history.insert(0, normalized);
    if (history.length > _maxHistory) {
      history.removeRange(_maxHistory, history.length);
    }
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
    await prefs.setStringList(_historyKey, history);
    return history;
  }

  static Future<List<String>> loadPinned() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_pinnedKey);
    if (raw == null || raw.isEmpty) return [];
    try {
<<<<<<< HEAD
      return List<String>.from(jsonDecode(raw) ?? []);
=======
      final data = jsonDecode(raw);
      return List<String>.from(data ?? []);
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
    } catch (_) {
      return [];
    }
  }

  static Future<List<String>> togglePinned(String cmd) async {
<<<<<<< HEAD
    final prefs  = await SharedPreferences.getInstance();
=======
    final prefs = await SharedPreferences.getInstance();
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
    final pinned = await loadPinned();
    if (pinned.contains(cmd)) {
      pinned.remove(cmd);
    } else {
      pinned.insert(0, cmd);
<<<<<<< HEAD
      if (pinned.length > _maxPinned) pinned.removeRange(_maxPinned, pinned.length);
=======
      if (pinned.length > _maxPinned) {
        pinned.removeRange(_maxPinned, pinned.length);
      }
>>>>>>> 1b23aae79cb517aabb8db6904939521ab4d04999
    }
    await prefs.setString(_pinnedKey, jsonEncode(pinned));
    return pinned;
  }
}
