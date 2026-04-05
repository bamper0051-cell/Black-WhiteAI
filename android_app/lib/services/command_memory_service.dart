// command_memory_service.dart — persists terminal history and pinned commands

import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

class CommandMemoryService {
  static const _historyKey = 'cmd_history';
  static const _pinnedKey = 'cmd_pinned';
  static const int _maxHistory = 50;
  static const int _maxPinned = 20;

  static Future<List<String>> loadHistory() async {
    final prefs = await SharedPreferences.getInstance();
    return List<String>.from(prefs.getStringList(_historyKey) ?? []);
  }

  static Future<List<String>> addHistory(String cmd) async {
    final normalized = cmd.trim();
    if (normalized.isEmpty) return loadHistory();

    final prefs = await SharedPreferences.getInstance();
    final history = List<String>.from(prefs.getStringList(_historyKey) ?? []);
    history.removeWhere((c) => c == normalized);
    history.insert(0, normalized);
    if (history.length > _maxHistory) {
      history.removeRange(_maxHistory, history.length);
    }
    await prefs.setStringList(_historyKey, history);
    return history;
  }

  static Future<List<String>> loadPinned() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_pinnedKey);
    if (raw == null || raw.isEmpty) return [];
    try {
      final data = jsonDecode(raw);
      return List<String>.from(data ?? []);
    } catch (_) {
      return [];
    }
  }

  static Future<List<String>> togglePinned(String cmd) async {
    final prefs = await SharedPreferences.getInstance();
    final pinned = await loadPinned();
    if (pinned.contains(cmd)) {
      pinned.remove(cmd);
    } else {
      pinned.insert(0, cmd);
      if (pinned.length > _maxPinned) {
        pinned.removeRange(_maxPinned, pinned.length);
      }
    }
    await prefs.setString(_pinnedKey, jsonEncode(pinned));
    return pinned;
  }
}
