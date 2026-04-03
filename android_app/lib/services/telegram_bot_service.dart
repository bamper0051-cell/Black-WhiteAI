// telegram_bot_service.dart — Direct Telegram Bot API (no server needed)

import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/models.dart';

class TelegramBotService {
  final String token;
  static const _base = 'https://api.telegram.org';

  TelegramBotService(this.token);

  String get _apiBase => '$_base/bot$token';

  Future<Map<String, dynamic>> _get(String method,
      [Map<String, String>? params]) async {
    final uri = Uri.parse('$_apiBase/$method').replace(
      queryParameters: params,
    );
    final resp = await http.get(uri).timeout(const Duration(seconds: 10));
    final data = jsonDecode(resp.body) as Map<String, dynamic>;
    if (data['ok'] != true) {
      throw Exception(data['description'] ?? 'Telegram API error');
    }
    return data['result'] as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> _post(
      String method, Map<String, dynamic> body) async {
    final uri = Uri.parse('$_apiBase/$method');
    final resp = await http
        .post(uri,
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode(body))
        .timeout(const Duration(seconds: 10));
    final data = jsonDecode(resp.body) as Map<String, dynamic>;
    if (data['ok'] != true) {
      throw Exception(data['description'] ?? 'Telegram API error');
    }
    return data['result'] is Map
        ? data['result'] as Map<String, dynamic>
        : {'result': data['result']};
  }

  // ── Validate token ─────────────────────────────────────────────────────────
  static Future<bool> validateToken(String token) async {
    try {
      final uri = Uri.parse('$_base/bot$token/getMe');
      final resp =
          await http.get(uri).timeout(const Duration(seconds: 8));
      final data = jsonDecode(resp.body);
      return data['ok'] == true;
    } catch (_) {
      return false;
    }
  }

  // ── Get bot info ───────────────────────────────────────────────────────────
  Future<BotInfo> getBotInfo() async {
    final data = await _get('getMe');
    return BotInfo.fromJson(data);
  }

  // ── Get bot stats (built from getUpdates + getChatMembersCount) ────────────
  Future<TelegramBotStats> getBotStats() async {
    try {
      final info = await getBotInfo();
      // Get recent updates to count activity
      final updates = await _getRecentUpdates();
      final uniqueUsers = <int>{};
      int msgCount = 0;
      for (final u in updates) {
        final msg = u['message'] as Map?;
        if (msg != null) {
          final from = msg['from'] as Map?;
          if (from != null) uniqueUsers.add(from['id'] as int);
          msgCount++;
        }
      }
      return TelegramBotStats(
        botUsername: info.username,
        isOnline: true,
        totalUsers: uniqueUsers.length,
        activeToday: uniqueUsers.length,
        messagesToday: msgCount,
        totalMessages: msgCount,
        usersByRole: {},
        lastActivity: updates.isNotEmpty ? DateTime.now() : null,
      );
    } catch (_) {
      final info = await getBotInfo();
      return TelegramBotStats(
        botUsername: info.username,
        isOnline: true,
        totalUsers: 0,
        activeToday: 0,
        messagesToday: 0,
        totalMessages: 0,
        usersByRole: {},
      );
    }
  }

  Future<List<Map<String, dynamic>>> _getRecentUpdates() async {
    try {
      final uri = Uri.parse('$_apiBase/getUpdates').replace(
        queryParameters: {'limit': '100', 'timeout': '0'},
      );
      final resp = await http.get(uri).timeout(const Duration(seconds: 5));
      final data = jsonDecode(resp.body);
      if (data['ok'] == true) {
        return List<Map<String, dynamic>>.from(data['result'] ?? []);
      }
    } catch (_) {}
    return [];
  }

  // ── Get recent messages ────────────────────────────────────────────────────
  Future<List<TelegramMessage>> getRecentMessages({int limit = 30}) async {
    final updates = await _getRecentUpdates();
    final messages = <TelegramMessage>[];
    for (final u in updates.take(limit)) {
      final msg = u['message'] as Map?;
      if (msg != null) {
        final from = msg['from'] as Map? ?? {};
        messages.add(TelegramMessage(
          id: msg['message_id'].toString(),
          userId: from['id']?.toString() ?? '',
          username: from['username'] ?? from['first_name'] ?? 'unknown',
          text: msg['text'] ?? '[media]',
          direction: 'in',
          timestamp: DateTime.fromMillisecondsSinceEpoch(
              (msg['date'] as int) * 1000),
        ));
      }
    }
    return messages.reversed.toList();
  }

  // ── Send message to a chat ─────────────────────────────────────────────────
  Future<bool> sendMessage(String chatId, String text) async {
    try {
      await _post('sendMessage', {
        'chat_id': chatId,
        'text': text,
        'parse_mode': 'HTML',
      });
      return true;
    } catch (_) {
      return false;
    }
  }

  // ── Get bot commands ───────────────────────────────────────────────────────
  Future<List<BotCommand>> getCommands() async {
    try {
      final uri = Uri.parse('$_apiBase/getMyCommands');
      final resp = await http.get(uri).timeout(const Duration(seconds: 5));
      final data = jsonDecode(resp.body);
      if (data['ok'] == true) {
        return List<Map<String, dynamic>>.from(data['result'] ?? [])
            .map((c) => BotCommand(
                  command: c['command'] as String,
                  description: c['description'] as String,
                ))
            .toList();
      }
    } catch (_) {}
    return [];
  }

  // ── Set commands ──────────────────────────────────────────────────────────
  Future<bool> setCommands(List<BotCommand> commands) async {
    try {
      await _post('setMyCommands', {
        'commands': commands
            .map((c) => {'command': c.command, 'description': c.description})
            .toList(),
      });
      return true;
    } catch (_) {
      return false;
    }
  }

  // ── Delete webhook (ensure polling mode) ──────────────────────────────────
  Future<void> deleteWebhook() async {
    try {
      await _post('deleteWebhook', {'drop_pending_updates': false});
    } catch (_) {}
  }
}

// ── Additional models ─────────────────────────────────────────────────────────

class BotInfo {
  final int id;
  final String username;
  final String firstName;
  final bool canJoinGroups;
  final bool canReadAllGroupMessages;

  const BotInfo({
    required this.id,
    required this.username,
    required this.firstName,
    this.canJoinGroups = false,
    this.canReadAllGroupMessages = false,
  });

  factory BotInfo.fromJson(Map<String, dynamic> j) => BotInfo(
        id: j['id'] as int,
        username: j['username'] as String? ?? '',
        firstName: j['first_name'] as String? ?? '',
        canJoinGroups: j['can_join_groups'] as bool? ?? false,
        canReadAllGroupMessages:
            j['can_read_all_group_messages'] as bool? ?? false,
      );
}

class BotCommand {
  final String command;
  final String description;
  const BotCommand({required this.command, required this.description});
}
